# Information Disclosure Ranjivosti MinIO Skladišta

Video sadržaj, DRM encryption keys i metadata skladišteni u MinIO Object Storage predstavljaju kritične resurse Video Streaming platforme čija kompromitacija direktno ugrožava intelektualnu svojinu instruktora i poslovni model servisa. Information Disclosure pretnje targetiraju MinIO skladišni sloj sa ciljem neautorizovanog pristupa ili curenja osetljivih podataka, narušavajući **poverljivost (Confidentiality)** kao fundamentalni bezbednosni princip.

Sledi pregled pretnji, napada, mitigacija vezanih za Information Leak MinIO skladišta opisanih dalje u nastavku dokumenta:

![Attack Tree - MinIO Information Disclosure](./attack-tree-minio.png)

---

## I. Praktičan Napad i Mitigacija: MinIO Bucket Policy Misconfiguration

### Identifikacija Ranjivosti

- **CWE-732** - Incorrect Permission Assignment for Critical Resource
- **CWE-284** - Improper Access Control
- **OWASP A01:2021** - Broken Access Control

---

### Opis Napada

MinIO implementira Amazon S3-compatible API sa bucket policy sistemom kontrole pristupa. Bucket policy je JSON dokument koji definiše ko može izvršavati koje operacije nad objektima unutar bucket-a kroz četiri atributa: **Principal** (ko ima pristup), **Action** (dozvoljene operacije), **Resource** (ciljni objekti), i opcioni **Condition** (dodatni uslovi).

MinIO default ponašanje je da su bucket-i privatni - samo autentifikovani korisnici sa eksplicitnim permisijama mogu pristupiti sadržaju. Međutim, bucket policy mora biti konfigurisana nakon kreiranja bucket-a, što predstavlja dodatni korak u deployment-u aplikacije. Na primer, AWS dokumentacija ukazuje da je najčešći razlog data breach-eva u cloud okruženjima upravo loša konfiguracija bucket-a, a ne konkretne sistemske ranjivosti.

Implementiranje autorizacije na aplikativnom nivou kroz npr. JWT validaciju na aplikativnom nivou može zanemariti storage-level security, oslanjajući se na pretpostavku da je kontrola pristupa u aplikaciji dovoljna zaštita. Međutim, ako je MinIO bucket konfigurisan sa `"Principal": "*"` (bilo ko), storage sloj nema sopstvenu zaštitu. Napadač koji otkrije MinIO endpoint može direktno pristupiti video fajlovima zaobilazeći celu aplikaciju.

Previd pri kom `"Principal": "*"` u skripti završi u produkciji ili naivno oslanjanje na činjenicu da je presigned URL za neki resurs dodeljen samo autorizovanim korisnicima na nivou aplikacije, te da stoga bucket može biti javan u kombinaciji sa predvidljivim pattern-om za generisani URL resursa, otvara prostor za napad. Napadač testira sekvencijalne ID-ove kroz zahteve koji proveravaju postojanje resursa. Svaki fajl koji vrati 200 OK je dostupan bez autentikacije i može biti preuzet.

---

### Primer Ranjive Konfiguracije
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": ["*"]
      },
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::videos/*"
      ]
    }
  ]
}
```

Primenjuje se na sve fajlove bez granularnosti i nedostaje `Condition` klauzula - nema ograničenja po IP adresi ili drugim kriterijumima.

---

### Primer Napada (Detekcija Javno Dostupnih Resursa sa Pattern-om)
```python
import requests

base_url = "http://storage.learnhub.com/videos"
found_files = []

for course in range(1, 100):
    for lesson in range(1, 20):
        filename = f"course-{course}-lesson-{lesson}.mp4"
        url = f"{base_url}/{filename}"
        
        response = requests.head(url)
        
        if response.status_code == 200:
            print(f"[FOUND] {url}")
            found_files.append(url)
            
            # Download fajl
            data = requests.get(url).content
            with open(filename, "wb") as f:
                f.write(data)

print(f"Total stolen videos: {len(found_files)}")
```

---

### Mitigacija

#### Primer Mitigovane Konfiguracije
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": {"AWS": ["*"]},
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::videos/*"],
      "Condition": {
        "StringNotEquals": {
          "s3:authType": "REST-HEADER"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": ["arn:aws:iam:::user/video-streaming-service"]
      },
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": ["arn:aws:s3:::videos/*"]
    }
  ]
}
```

**Primarna mitigacija** obuhvata eksplicitno odbijanje svih neautentifikovanih korisnika.

Prvi statement eksplicitno odbija sve zahteve koji nisu autentifikovani kroz REST-HEADER, a drugi dozvoljava pristup samo specificnom service account-u koji Golang video servis koristi - samo Go aplikacija može pristupiti bucket-u sa minimalnim potrebnim operacijama.

#### Presigned URL Strategija

Presigned URL strategija koristi privremene kriptografski potpisane URL-ove koje generiše Go servis nakon validacije. Ovakvim pristupom, čak i ako napadač leak-uje URL, može ga koristiti samo za specifičan fajl i samo dok ne istekne. Svaki student dobija jedinstveni URL pa sharing ne skalira.
```go
presignedURL, _ := minioClient.PresignedGetObject(
    context.Background(),
    "videos",
    fmt.Sprintf("course-%s/lesson-%s.mp4", courseID, lessonID),
    5 * time.Minute,  // Expiration
    url.Values{},
)
```

#### IP Whitelisting

IP whitelisting dodatno ograničava pristup, čime zahtevi moraju dolaziti sa Golang servera. Korisnički browser ne može direktno pristupiti MinIO resursu već mora pristupiti kroz Go proxy koji stream-uje sadržaj.

#### Monitoring i Anomaly Detection

Dalje, mitigacija obuhvata i uvođenje sistema za monitoring koji bi pratio anomalije i prečeste GetObject zahteve, pattern-e koji ukazuju na sekvencijalni pristup (automatizovana skripta), ili nagle skokove u 403 odgovorima. Neophodno je automatski blokirati sumnjive IP adrese ili rate limiting zahteva.

---

## II. Ostale MinIO Ranjivosti i Bad Practices koje Povećavaju Rizik Curenja Informacija

### 1. CVE-2023-28432 - Information Disclosure kroz Health Endpoint

CVE-2023-28432 je zvanično dokumentovana ranjivost u MinIO verzijama pre RELEASE.2023-03-20. Health check endpoint-i su standardna praksa u distribuiranim sistemima za monitoring dostupnosti i zdravlja servisa, ali ova specifična implementacija je leak-ovala osetljive informacije.

MinIO verzije pre patch-a izlažu `/minio/health/cluster` endpoint koji vraća JSON response sa metapodacima uključujući `MINIO_ROOT_PASSWORD` environment varijablu u plaintext-u. Sa ovim kredencijalima napadač može kompletno preuzeti MinIO instancu - pristupiti svim bucket-ima, brisati podatke, ili modifikovati bucket policies.

**Mitigacija** zahteva ažuriranje na RELEASE.2023-03-20T20-16-18Z ili noviju verziju gde je endpoint property zaštićen, postavljanje network firewall pravila koja blokiraju pristup `/minio/health/*` endpoint-ima sa spoljašnjih IP adresa, i konfigurisanje reverse proxy-ja da eksplicitno blokira admin endpoint-e koji nisu neophodni za legitimnu upotrebu.

---

### 2. Unencrypted Data at Rest - Neenkriptovano Skladištenje

MinIO podržava Server-Side Encryption (SSE) ali nije enabled po defaultu prilikom kreiranja bucket-a. Video fajlovi skladišteni na disku bez enkripcije mogu biti pristupljeni ako napadač dobije fizički pristup serveru, pristup disk snapshot-u u cloud okruženju, ili kompromituje operativni sistem i montira MinIO data volume direktno.

MinIO nudi dve SSE varijante:
- **SSE-S3**: MinIO automatski upravlja encryption key-ovima koristeći jedan master key
- **SSE-C**: Klijent dostavlja encryption key sa svakim zahtevom i MinIO nikad ne čuva key trajno

**Mitigacija** zahteva enabling SSE-S3 kroz bucket policy koji forsira enkripciju za sve nove objekte (`"s3:x-amz-server-side-encryption": "AES256"`), retroaktivno enkriptovanje postojećih objekata kroz batch encryption job, i konfigurisanje automatskog bucket encryption-a pri kreiranju tako da developer ne može zaboraviti da enable-uje.

---

### 3. Exposed MinIO Console - Neautentifikovani Admin Pristup

MinIO Console dostupan sa interneta sa default credentials-ima (`admin`/`password`) dozvoljava napadaču kompletnu kontrolu kroz browser. Brute-force napadi na login formu, credential stuffing sa leak-ovanim password listama, ili CSRF exploit-i mogu dovesti do kompromitovanja.

**Mitigacija** zahteva postavljanje jakih jedinstvenih kredencijala umesto defaultnih, ograničavanje Console pristupa samo sa proverenih IP adresa kroz firewall, dvofaktorska autentikacija, ili potpuno disable-ovanje Console-a u produkciji i upravljanje MinIO-om isključivo kroz Infrastructure-as-Code.

---

## Reference

- **CWE-732**: https://cwe.mitre.org/data/definitions/732.html
- **CWE-284**: https://cwe.mitre.org/data/definitions/284.html
- **OWASP A01:2021**: https://owasp.org/Top10/A01_2021-Broken_Access_Control/
- **CVE-2023-28432**: https://nvd.nist.gov/vuln/detail/CVE-2023-28432
- **MinIO Security Advisories**: https://github.com/minio/minio/security/advisories
- **AWS S3 Security Best Practices**: https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html
- **MinIO Server-Side Encryption**: https://min.io/docs/minio/linux/operations/server-side-encryption.html
