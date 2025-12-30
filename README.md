# LearnHub - Platforma za Online Kurseve

## 1. DOMEN PROBLEMA

### 1.1 Kratak opis domena

LearnHub je platforma gde instruktori postavljaju video kurseve, a studenti ih kupuju i gledaju. Instruktor napravi kurs sa video lekcijama, postavi cenu, student plati i dobije pristup. Platforma uzima procenat od svake prodaje. Kada student završi sve lekcije, dobija potvrdu o završetku.

### 1.2 Učesnici

**Studenti**
- Traže i kupuju kurseve
- Gledaju video lekcije
- Rade testove i kvizove
- Dobijaju sertifikat kada završe kurs
- Ostavljaju recenzije

**Instruktori**
- Prave kurseve i postavljaju videe
- Kreiraju testove
- Određuju cenu kursa
- Odgovaraju na pitanja studenata
- Dobijaju novac od prodaje

**Administratori**
- Odobravaju nove instruktore
- Proveravaju kvalitet kurseva pre objavljivanja
- Rešavaju probleme i žalbe
- Blokiraju lažne kurseve
- Vraćaju novac ako treba

**Stripe (platni sistem)**
- Naplaćuje kreditne kartice
- Šalje novac instruktorima

**Vimeo (video hosting)**
- Čuva video fajlove
- Emituje video u različitim kvalitetima

### 1.3 Poslovni procesi

**Pre kupovine:**
- Instruktor se registruje i dobija odobrenje
- Instruktor pravi kurs (snima videe, postavlja cenu)
- Admin proverava da kurs nije spam
- Kurs postaje dostupan za kupovinu
- Student pretražuje kurseve

**Tokom korišćenja:**
- Student kupuje kurs kreditnom karticom
- Student gleda video lekcije
- Sistem pamti gde je student stao
- Student radi testove na kraju svake sekcije
- Instruktor odgovara na pitanja

**Posle završetka:**
- Student završi sve lekcije i testove
- Sistem generiše PDF sertifikat
- Student ocenjuje kurs
- Platforma računa koliko je instruktor zaradio
- Svaki mesec šalje novac instruktoru

---

## 2. ARHITEKTURA SISTEMA

### 2.1 Arhitekturalni stil

Sistem je podeljen na nezavisne mikroservise koji komuniciraju preko poruka:

- **Course Service** - sve oko kurseva (kreiranje, izmena, brisanje)
- **Enrollment Service** - kupovina i praćenje napretka
- **Assessment Service** - testovi i ocenjivanje
- **Video Service** - stream video fajlova
- **Payment Service** - naplate i isplate


### 2.2 Tehnologije (9+)

#### *1. Spring Boot (Java) - Course Management Service*
*Uloga*: CRUD operacije za kurseve, sekcije, lekcije, odobravanje  
*Zašto*: Mature ecosystem, Spring Security za RBAC, laka integracija sa PostgreSQL

#### *2. Spring Boot (Java) - Enrollment Service*
*Uloga*: Upravljanje pristupom kursevima, tracking progress-a, completion logika  
*Zašto*: Transakciona konzistentnost (student progress ne sme biti lost)

#### *3. Python (Django) - Instructor CMS*
*Uloga*: Backoffice za instruktore, upload interface, analytics dashboard  
*Zašto*: Django admin je brz za developanje CMS-a, dobar za data analysis (pandas)

#### *4. Go - Video Streaming Proxy*
*Uloga*: Presretanje video requests, autorizacija pristupa, signed URL generisanje  
*Zašto*: Low latency, high throughput za streaming workload, concurrency

#### *5. PostgreSQL*
*Uloga*: Kursevi, korisnici, enrollments, transaction logs, quiz results  
*Zašto*: ACID za finansijske transakcije, foreign key constraints, relacijska struktura

#### *6. MongoDB*
*Uloga*: Video metadata, progress checkpoints (timestamp gde je student stao), forum Q&A  
*Zašto*: Fleksibilna šema (različiti kursevi imaju različitu strukturu), brze write operacije

#### *7. Redis*
*Uloga*: Session management, video playback state cache (da student nastavi odakle je stao), rate limiting  
*Zašto*: In-memory brzina, expire keys automatski

#### *8. Kafka*
*Uloga*: Event streaming - CoursePublished, Enrolled, LessonCompleted, QuizPassed  
*Zašto*: Audit trail, može se replay-ovati za analytics, decoupling servisa

#### *9. Elasticsearch*
*Uloga*: Full-text search kurseva (naslov, opis, tags), filtering po kategoriji/cijeni/rating-u  
*Zašto*: Relevance scoring, faceted search, real-time indexing

#### Dodatne komponente:

*Vimeo/Wistia API* - Video hosting sa DRM, adaptive streaming, analytics  
*Stripe API* - Payment processing, subscription billing, marketplace payouts  
*S3/MinIO* - Skladištenje PDF materijala, sertifikata, instructor profilnih slika  
*SendGrid* - Email notifikacije (enrollment confirmation, certificate delivery)

---

## 3. SLUČAJEVI KORIŠĆENJA

### 3.1 Upravljanje instruktorskim nalogom
Registracija i verifikacija instruktora od strane admina. Kreiranje i ažuriranje profila sa biografijom, kvalifikacijama i portfoliom. Pregled statistika o kursevima, studentima i prihodima.

### 3.2 Kreiranje i upravljanje kursevima
Kreiranje novog kursa sa osnovnim informacijama (naziv, opis, kategorija, cena). Strukturiranje sadržaja u sekcije i lekcije. Upload video fajlova i dodatnih materijala. Postavljanje preduslovnih kurseva. Slanje kursa na odobrenje i objavljivanje nakon provere.

### 3.3 Pretraga i otkrivanje kurseva
Pretraga kataloga kurseva po ključnim rečima i filterima (kategorija, težina, cena, ocena). Sortiranje rezultata po različitim kriterijumima. Pregled detalja kursa i recenzija drugih studenata. Preview funkcionalnost za proveru sadržaja pre kupovine.

### 3.4 Kupovina i pristup kursevima
Dodavanje kurseva u korpu i grupna kupovina. Unos i čuvanje platnih podataka. Procesiranje naplate preko platnog sistema. Dobijanje pristupa kupljenom sadržaju i email potvrde.

### 3.5 Praćenje kursa i napredak
Gledanje video lekcija sa automatskim pamćenjem pozicije. Adaptivno emitovanje videa prema brzini interneta. Označavanje završenih lekcija. Praćenje ukupnog napretka kroz kurs. Preuzimanje dodatnih materijala.

### 3.6 Testiranje i ocenjivanje
Kreiranje testova sa različitim tipovima pitanja od strane instruktora. Polaganje testova sa automatskim ocenjivanjem. Mogućnost ponovnog pokušaja. Završni ispit na kraju kursa. Pregled rezultata i povratnih informacija.

### 3.7 Komunikacija i podrška
Forum za postavljanje pitanja na pojedinačnim lekcijama. Odgovaranje instruktora na upite studenata. Učešće drugih studenata u diskusiji. Glasanje za korisna pitanja i odgovore. Sistem obaveštenja za nove odgovore.

### 3.8 Izdavanje sertifikata
Automatsko generisanje PDF sertifikata po završetku kursa i ispita. Slanje sertifikata emailom i čuvanje u profilu studenta. Jedinstveni identifikator za verifikaciju autentičnosti. Mogućnost provere validnosti sertifikata od strane trećih lica.

### 3.9 Recenzije i ocenjivanje
Ostavljanje ocene i tekstualnog komentara za završene kurseve. Prikaz prosečne ocene i svih recenzija na stranici kursa. Mogućnost instruktora da vidi i odgovori na feedback. Filtriranje recenzija po oceni i datumu.

### 3.10 Finansijsko upravljanje i isplate
Praćenje prihoda po kursu i ukupnih zarada za instruktore. Automatski izračun provizije platforme i dela za instruktora. Generisanje mesečnih izveštaja i računa. Transfer novca na bankovne račune instruktora. Čuvanje istorije transakcija.

### 3.11 Detekcija prevare i povraćaj novca
Praćenje sumnjive aktivnosti (lažni kursevi, kopirani sadržaji, false reviews). Sistem upozorenja za administratore. Proces za podnošenje i rešavanje žalbi. Odobravanje ili odbijanje zahteva za povraćaj novca sa obrazloženjem.

### 3.12 Administracija i moderacija
Pregled i odobravanje novih instruktorskih naloga. Provera kvaliteta kurseva pre objavljivanja. Uklanjanje neprimerenog sadržaja. Izbor istaknutih kurseva za promociju. Blokiranje korisnika koji krše pravila. Pregled evidencije svih admin akcija.

---

## 4. OSETLJIVI RESURSI (9)

### R1: **Korisnički nalozi**
**Naziv**: `user_accounts`  
**Security Goal**: Confidentiality  
**Prioritet**: KRITIČAN  
**Regulativa**: GDPR  
**Objašnjenje**: Kompromitovani kredencijali omogućavaju neovlašćen pristup nalozima

### R2: **Podaci o platnim karticama**
**Naziv**: `payment_cards`  
**Security Goal**: Confidentiality  
**Prioritet**: KRITIČAN  
**Regulativa**: PCI DSS  
**Objašnjenje**: Tokenizacija obavezna, originalni brojevi kartica se ne čuvaju

### R3: **Video sadržaj i DRM ključevi**
**Naziv**: `course_videos`, `drm_keys`  
**Security Goal**: Confidentiality, Integrity  
**Prioritet**: VISOK  
**Objašnjenje**: Neovlašćeno preuzimanje videa direktno utiče na prihode instruktora

### R4: **Napredak studenta kroz kurs**
**Naziv**: `student_progress`  
**Security Goal**: Confidentiality, Integrity  
**Prioritet**: VISOK  
**Regulativa**: GDPR  
**Objašnjenje**: Edukativni podaci su lični podaci, manipulacija napretka omogućava neovlašćeno dobijanje sertifikata

### R5: **Bankovni podaci instruktora**
**Naziv**: `instructor_payout_info`  
**Security Goal**: Confidentiality  
**Prioritet**: VISOK  
**Objašnjenje**: Pristup samo Payment servisa, enkripcija obavezna

### R6: **Pitanja i odgovori na testovima**
**Naziv**: `quiz_questions`  
**Security Goal**: Confidentiality  
**Prioritet**: VISOK  
**Objašnjenje**: Curenje omogućava varanje na testovima

### R7: **Izdati sertifikati**
**Naziv**: `certificates`  
**Security Goal**: Integrity, Non-repudiation  
**Prioritet**: SREDNJI  
**Objašnjenje**: Jedinstveni identifikatori za verifikaciju autentičnosti, immutable log

### R8: **Algoritam za određivanje cena**
**Naziv**: `pricing_algorithm`  
**Security Goal**: Confidentiality  
**Prioritet**: SREDNJI  
**Objašnjenje**: Poslovna tajna, eksploatacija može dovesti do zloupotrebe popusta

### R9: **Evidencija admin akcija**
**Naziv**: `admin_logs`  
**Security Goal**: Integrity, Non-repudiation  
**Prioritet**: VISOK  
**Objašnjenje**: Sve administrativne akcije se beležе u immutable log za audit potrebe
