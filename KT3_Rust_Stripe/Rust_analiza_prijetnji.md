# **Bezbjednosna Analiza: Rust Payment Service**

Slika ispod predstavlja stablo napada koje počinje od korijena -
prijetnje na visokom nivou, zatim konkretne prijetnje koja se u Rust
Payment Servicu realizuje kroz podskup napada izloženih u narednom nivou
stabla, i bezbjednosnih kontrola koje se izvlače iz analizirane
prijetnje.

![](./image1.png)

**Prijetnja - P1**

**Narušavanje integriteta finansijskih transakcija u Rust Payment
Servicu**

Napadač eksploatiše aritmetičku ranjivost u checkout endpointu kako bi
uzrokovao da iznos koji se prosljeđuje Stripeu bude drastično manji od
stvarnog iznosa narudžbe. Na ovaj način napadač stiče robu ili uslugu
bez adekvatne finansijske naknade, dok sistem procesuira transakciju kao
uspješnu. Narušeno sigurnosno svojstvo prema CIA trijadi je
\*\***Integritet (I)**\*\*- podaci o iznosu transakcije nisu tačni.

U nastavku su opisani napadi koji realizuju ovu prijetnju: jedan
praktično sproveden (A1) i jedan teorijski napad (A2) koji ostvaruju
istu prijetnju kroz drugačije ranjivosti i vektore napada.

**A1 - Praktično realizovan napad: Integer Overflow u checkout
endpointu**

U nastavku je opisan konkretan napad A1, sa priloženim videom
sprovedenog napada na metu. U prvom segmentu videa napadač napada
ranjivu verziju mete i ostvaruje konkretnu prijetnju P1, a u drugom
segmentu videa prikazana je mitigacija M1, gdje komentari naglašavaju
linije koda koje predstavljaju konkretnu bezbjednosnu kontrolu za
sprovedeni napad.

**Klasa ranjivosti - CWE-190: Integer Overflow or Wraparound**

CWE-190 opisuje klasu ranjivosti u kojoj aritmetička operacija proizvede
vrijednost koja prelazi opseg tipa podataka, a sistem to ne detektuje
ili ne obrađuje na pravi način. Kada se integer vrijednost uvećava do
vrijednosti koja je prevelika da bi se pohranila u pridruženoj
memorijskoj reprezentaciji, vrijednost može postati veoma mala,
negativna (kod signed tipova), ili se wraparound-ovati po pravilima
modularne aritmetike --- zavisno od implementacije i konteksta
izvršavanja.

U kontekstu konkretnog napada A1, kada rezultat množenja premaši
maksimalnu vrijednost tipa \`u32\` (4.294.967.295), u release buildu
overflow rezultira modularnim wraparound ponašanjem. To znači da se
vrijednost vrati na početak opsega bez generisanja greške, upozorenja
ili bilo kakvog vidljivog indikatora da je nastao problem.

**Terminološka napomena**: Pojmovi \"overflow\" i \"wraparound\" često
se koriste naizmjenično, ali postoji precizna razlika. Wraparound je
dobro definirano, standardno ponašanje koje prati specifična pravila za
rukovanje situacijama kada numerička vrijednost premašuje opseg
reprezentacije. Overflow tipično ukazuje na nestandardno ili
nedefinisano ponašanje. U Rustu, u release modu dešava se **wraparound**
- standardno i definisano ponašanje. U debug modu dešava se **panic**
 Rustov mehanizam zaštite tokom razvoja, koji je po efektu sličan
neuhvaćenom izuzetku u jezicima kao što je Java.

**Ranjivost**

Meta napada u Rust payment servisu je \`/checkout\` endpoint, čiji
handler koristi direktni aritmetički operator \`\*\` za izračunavanje
ukupnog iznosa narudžbe. Ova implementacija krši ANSSI LANG-ARITH
pravilo, koje eksplicitno zabranjuje direktne aritmetičke operatore kada
postoji mogućnost overflow-a i propisuje upotrebu specijalizovanih
metoda ili wrapper tipova koji osiguravaju eksplicitno i konzistentno
ponašanje bez obzira na kompilacijski profil.

Suštinska priroda ove ranjivosti leži u Rust-specifičnom ponašanju
kompajlera: isti kod ponašanje se drugačije zavisno od toga da li se
aplikacija kompajlira u debug ili release modu. U debug modu, kompajler
uključuje overflow provjere koje uzrokuju panic pri pokušaju
prekoračenja opsega - što developer percipira kao grešku i zaključuje
da je sistem zaštićen. U produkcijskom (release) modu, iste provjere su
isključene zbog optimizacija performansi, i overflow tiho wraparound-uje
po two\'s complement principu bez ikakve greške ili upozorenja. Upravo
ovaj jaz između ponašanja u razvoju i ponašanja u produkciji čini
LANG-ARITH klasu posebno podmukavom - developer koji testira
isključivo u debug modu nikada neće otkriti ranjivost koja postoji u
produkciji. Treba naglasiti da two\'s complement wraparound u Rustu nije
bug kompajlera, već svjesno odabrano ponašanje u svrhu performansi - i
upravo zato ANSSI eksplicitno propisuje LANG-ARITH pravilo, jer
kompajler sam po sebi neće upozoriti developera.

**Vektor napada**

Napad se odvija slanjem HTTP POST requesta na \`/checkout\` endpoint sa
malicioznom vrijednošću \`quantity\` parametra. Napadač namjerno bira
vrijednost koja uzrokuje da produkt \`item_price \* quantity\` prekorači
maksimalnu vrijednost tipa \`u32\`. Tip \`u32\` može pohraniti
vrijednosti od 0 do 4.294.967.295 - što odgovara 32 bita memorije.
Kada rezultat množenja premašuje taj maksimum, dolazi do wraparound-a -
vrijednost se resetuje na početak opsega i Stripe dobija drastično manji
iznos od stvarnog. U demonstriranom primjeru, narudžba vrijedna 429.496€
naplaćena je sa svega 7 centi, a transakcija je zaključena kao uspješna
bez ikakve greške. Kada developer testira aplikaciju pokretanjem \`cargo
run\` komande u terminalu u debug mod-u, overflow uzrokuje \`panic\`
koji se manifestuje kao greska, a kako je panic mehanizam Rust zastite
djeluje kao da je sistem zasticen. Međutim, u produkcijskom deploymentu
aplikacija se pokreće sa \`cargo run --release\` gdje ista provjera **ne
postoji**, i overflow prolazi tiho bez ikakve greške ili upozorenja -
Stripe naplaćuje iznos koji mu Rust proslijedi, i transakcija se zatvara
kao uspješna.

**Mitigacija - M1**

Mitigacija je zamjena direktnog \`\*\` operatora metodom
\`checked_mul()\`, koja provjerava da li će rezultat stati u ciljni tip
prije nego što operacija nastane, a greška se obrađuje kontrolisano kroz
validan HTTP odgovor. U drugom segmentu videa je demonstiran slucaj
izazivanja overflow-a u mitigovanoj verziji, gdje \`checked_mul()\`
vraća \`None\` umjesto pogrešnog rezultata - bez wraparound-a, bez
panike. \`None\` se mapira na \`400 Bad Request\` HTTP odgovor, i Stripe
se nikada nece pozvati sa pogresnim iznosom. Za razliku od ranjivog
koda, ponašanje mitigiranog endpointa je identično u debug i release
modu, što direktno ispunjava zahtjev ANSSI LANG-ARITH pravila.

**A2 - Teorijski napad: Numerička konverzija bez provjere u checkout
endpointu**

**Klasa ranjivosti - CWE-681: Incorrect Conversion Between Numeric
Types**

CWE-681 opisuje situaciju gdje pri konverziji iz jednog numeričkog tipa
u drugi podaci mogu biti izgubljeni ili transformisani na način koji
proizvodi neočekivanu vrijednost. Ako se rezultirajuća vrijednost
koristi u sigurnosno osjetljivom kontekstu, kao što je izračunavanje
finansijskog iznosa, mogu nastati opasne posljedice. Za razliku od
CWE-190 gdje problem nastaje pri samoj aritmetičkoj operaciji, ovdje
ranjivost leži isključivo u konverziji između tipova. Sama aritmetika
može biti potpuno ispravna, ali se rezultat gubi prilikom kastovanja u
manji tip.\
U Rustu, \`as\` operator tu konverziju izvodi tiho, bez greške i bez
upozorenja, podjednako u debug i release modu. Za razliku od integer
overflow-a (CWE-190), ovdje ne postoji debug zaštita koja bi developeru
signalizirala problem.\
Jedan od primjera koji potvrdjuje da su truncating konverzije realna i
dokumentovana klasa ranjivosti u produkcionom Rust kodu je
RUSTSEC-2024-0363, gdje SQLx - jedna od cesto koristenih Rust
biblioteka za komunikaciju sa bazama podataka - izvodi truncating cast
na način koji uzrokuje pogrešnu interpretaciju podataka u binarnom
protokolu pri radu sa veoma velikim vrijednostima.

**Ranjivost**

Ugrožena komponenta je sam Rust jezik - konkretno semantika \`as\`
operatora koji je dio jezičke specifikacije i čije ponašanje pri
narrowing konverziji je konzistentno i nepromjenljivo bez obzira na
build profil ili verziju kompajlera.**\
**Meta napada je \`/checkout\` endpoint U scenariju A2, developer
proširuje tipove item_price i quantity na u64 kako bi izbjegao overflow
pri množenju --- što je ispravan pristup. Međutim, nakon izračunavanja
ukupnog iznosa, rezultat konvertuje nazad u u32 korištenjem as
operatora. Razlog za ovu konverziju može biti pretpostavka da iznosi u
praksi neće dostići vrijednosti veće od u32::MAX, zahtjev internog
API-ja koji očekuje manji tip, ili legacy kod koji nije prilagođen većim
iznosima. Ako \`total_u64\` prelazi maksimalnu vrijednost \`u32\`,
dolazi do tihog trunkovanja. Gornji bitovi se odbacuju, a Stripe dobija
pogrešan, značajno manji iznos.\
Ova greška je posebno podmukla jer developer pokazuje svjesnost o
overflow problemu korištenjem \`u64\`. Međutim, u završnom koraku
konverzije, \`as\` operator tiho uništava ispravno izračunatu
vrijednost. Kompajler ne prijavljuje grešku, debug mod ne panikuje, a
problem postaje vidljiv tek kroz pogrešan finansijski iznos.

**Vektor napada**

Napadač šalje HTTP POST request na \`/checkout\` endpoint sa
kombinacijom \`item_price\` i \`quantity\` parametara čiji produkt
prekoračuje u32::MAX (4.294.967.295). Za razliku od A1, ovdje ne postoji
nikakva razlika između debug i release moda --- truncation se uvijek
dešava tiho. Developer koji testira ovaj kod u debug modu neće vidjeti
nikakvu grešku ni upozorenje, čak ni na malicioznom inputu. Sistem
procesuira transakciju kao uspješnu. Stripe naplaćuje iznos koji mu Rust
proslijedi --- napadač dobija robu ili uslugu bez adekvatne finansijske
naknade, čime se realizuje prijetnja P1.

**Mitigacija - M2**

U nastavku su opisane bezbjednosne kontrole koje se mogu primijeniti
nezavisno ili u kombinaciji kako bi se eliminisala ova ranjivost.

**M2.1 - try_from()** je primarna i jedina kontrola koja sama potpuno
eliminuše ranjivost. Za razliku od \`as\` operatora, \`try_from()\`
provjerava da li vrijednost staje u ciljni tip i vraća \`Result\` ---
\`Ok\` ako staje, \`Err\` ako ne, bez tihog odbacivanja podataka i
konzistentno u debug i release modu. MITRE za CWE-681 eksplicitno
preporučuje da se izbjegavaju konverzije između numeričkih tipova i
uvijek provjeravaju dozvoljeni opsezi.\
**M2.2 - Clippy lint \`cast_possible_truncation\`** je dopunska
kontrola koja djeluje tokom razvoja, ne u runtime. Clippy je Rustov
zvanični alat za statičku analizu koda --- nije dio kompajlera i ne
izvršava se automatski pri \`cargo build\`, nego se poziva eksplicitno
sa \`cargo clippy\`. Lint \`cast_possible_truncation\` detektuje
upotrebu \`as\` operatora u situacijama gdje može doći do gubitka
podataka i prijavljuje upozorenje. Aktivira se dodavanje direktive na
vrhu fajla: #\![warn(clippy::cast_possible_truncation)\].\
Sama po sebi nije dovoljna jer predstavlja upozorenje koje developer
može ignorisati i koje ne sprječava izvršavanje koda. U kombinaciji sa
M2.1 obezbjeđuje zaštitu na dva nezavisna nivoa --- M2.1 u runtime, M2.2
tokom pisanja koda.

**Reference**

ANSSI Rust Secure Coding Guide - LANG-ARITH pravilo\
anssi-fr.github.io/rust-guide

CWE-190: Integer Overflow or Wraparound\
cwe.mitre.org/data/definitions/190.html

CWE-681: Incorrect Conversion Between Numeric Types
cwe.mitre.org/data/definitions/681.html

Rust Reference - Overflow ponašanje u debug i release modu\
doc.rust-lang.org/reference/expressions/operator-expr.html#overflow

Rust Reference - Numeric cast (as operator)
doc.rust-lang.org/reference/expressions/operator-expr.html#type-cast-expressions

Rust RFC 0560 - Integer overflow\
github.com/rust-lang/rfcs/blob/master/text/0560-integer-overflow.md

RUSTSEC-2026-0007 - Integer overflow u BytesMut::reserve
rustsec.org/advisories/RUSTSEC-2026-0007

RUSTSEC-2024-0363 - sqlx truncating cast\
rustsec.org/advisories/RUSTSEC-2024-0363
