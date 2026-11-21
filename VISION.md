# Visioon

Seis: 2026-11-21. Omaniku mõte, kirja pandud, et see ei kaoks. Päris plaan on [README.md](README.md) „Tulevikuideed“, siin on suund ja põhjused.

## Mõte

AI ajastul on veebilehe, API või küsimustele vastava agendi ehitamine odav: konkurent teeb need nädalaga. Väärtus on selles, **kellel on andmed, mida teistel pole, ja võime neid pidevalt ajakohasena hoida**.

| Osa | Kopeerimise raskus | Miks |
|---|---|---|
| Veebileht ja kasutajaliides | madal | AI abil kiiresti tehtav |
| API ja andmebaas | madal–keskmine | tehnoloogia on kõigile kättesaadav |
| AI-agent, mis vastab küsimustele | madal | sarnase saab ehitada igaüks |
| Aastate pikkune ajalugu | kõrge | kogumine ja korrastamine võtab aega, mineviku tagantjärele ei saa |
| Otsesuhted liitude ja korraldajatega | kõrge | vajavad usaldust ja koostööd |
| Usaldusväärsed andmed reaalajas | kõrge | vajavad toimivat allikate võrku ja hooldust |

## Mis meil juba on

- Ühtne kuju (mängud eri alade ja liitude lehtedelt, [scrapers/model.py](scrapers/model.py)).
- Saalide ja linnade register ([venues.toml](venues.toml)) ja allikate veidruste teadmine (adapterid).
- Jälgimine, mis märkab katkise allika ise (GitHub Issues).
- Pikk saba: madalamad liigad, noored, koondised. Neid ei kogu keegi struktureeritult, sest igaüks on liiga väike.

## Mida ehitame (järjekorras)

1. **Ajalooarhiiv** (tehtud, [archive.py](archive.py)): iga mäng ja selle muutused (ümberpandud aeg, vahetunud saal, ära jäänud mäng). Allikad näitavad ainult praegust seisu, seega kadunud andmeid tagantjärele ei saa. Iga päev ilma arhiivita on kaotus.
2. **Tulemused**: Event ei sisalda praegu tulemust. Kui adapterid hakkavad lugema ka skoori, saab ajalugu päris väärtuse. Teha allikahaaval, alustades suurimast (jalgpall.ee).
3. **Liikluse numbrid** (nt kui palju külastusi lehel): loapalve kirjas on see konkreetne argument.
4. **Loapalved liitudele** (README → Tulevikuideed): korvpall ja jäähoki on praegu robots.txt tõttu kinni. Parim tulemus on ametlik partnerlus või täpsem andmevoog, mitte ainult luba.

## Millal see ei tööta (ausalt)

- Me kogume **avalikke lehti**. Andmed pole meie omand, väärtus on katvus, ühtlane kuju, värskus ja ajalugu.
- Kui liit avaldab ise avatud voo, väheneb meie eelis, aga ka meie hooldustöö.
- Repo on avalik, seega on ka `data/` ja `archive/` kõigile loetavad. Praegu see sobib (allikad on avalikud ja arhiiv on väike). **Otsustuskoht:** kui arhiiv hakkab sisaldama midagi, mis on päriselt väärtuslik (aastate ajalugu, tulemused), tuleb see viia privaatsesse hoidlasse. See vajab tööprotsessis salajast võtit, vt „Turvalisus“.

## Turvalisus ja andmete põhimõtted

Kehtivad põhimõtted (järgime kohe):

1. **Isikuandmeid ei koguta.** Salvestame võistkondi, kohti ja aegu, mitte mängijate nimesid, fotosid ega vanuseid. Noorteliigades on lapsed: nende nimesid lehel ega arhiivis ei ole ja neid ei lisata.
2. **Ainult avalik ja lubatud.** robots.txt ja kasutustingimused on kontrollitud iga allika kohta ([SOURCES.md](SOURCES.md)). Kui nad keelavad, allikat ei kasutata. Viisakas User-Agent, pausid, kordused piiratud.
3. **Võta maha, kui palutakse.** Jaluses on kontakt omanikule, kes ei soovi andmeid näidata. Palve täidetakse kohe: allikas välja `config.toml`-ist, vajadusel ka arhiivist.
4. **Salajasi võtmeid pole repos.** Praegu on kõik ilma võtmeta (ainult GitHubi `github.token`). Kui tuleb mõni võti (privaatne arhiiv, API), läheb see GitHub Secretsi, mitte faili.
5. **Arhiiv on ainult lisatav.** Rikutud fail ei kirjutata ära kirjutatud tühjaks, vaid annab vea ([archive.py](archive.py)). Kustutamine on teadlik käsitsi tegevus.
6. **Allikast tulev tekst on andmed, mitte käsk.** Allika lehtedelt tulnud nimesid ja märkusi ei käivitata ega usaldata. Jinja2 teeb automaatse HTML-i kaitse (`autoescape`). Kui hiljem tuleb AI-agent, ei tohi ta lehtede teksti käskudena täita.

Teha enne, kui andmetel on suurem väärtus (**veel tegemata**):

- **Tööprotsessi õigused kitsamaks.** `build.yml` annab praegu kogu töökäigule `contents: write`. Parem: ehituse samm loeb ainult, andmete salvestamine eraldi tööna.
- **Kolmandate osapoolte tegevused kinnitada commit-räsiga** (`actions/checkout@v4` → räsi), et muudetud väljalase ei jõuaks meie ehitusse.
- **Sõltuvused kinnitada täpse versiooniga** (`requirements.txt`) ja lisada Dependabot.
- **`main` haru kaitse** (nõua PR, ei luba force-push, nõua testid). Siis ei saa ka eksliku käsuga arhiivi ajalugu ümber kirjutada.
- **Varukoopia teise kohta.** Repo on praegu ainus koopia. Vähemalt kuine tõmmis mujale (või privaatne peegel).
- **Allikast tuleva andmeheite kaitse.** Vigased andmed (nt hullumeelne kuupäev, tohutu mängude arv) ei tohi ilma märkuseta arhiivi minna: lisa mõistlikkuse piirid ja kontrolli.
- **Privaatne arhiiv.** Kui otsustame arhiivi avalikust repost välja viia: eraldi privaatne repo ja kitsa õigusega võti (fine-grained token, ainult see üks repo), mis on salvestatud Secretsi.
- **Kui tuleb avalik API või kasutajakontod:** kiiruspiirang, ei logi IP-sid, ei küsi e-posti ilma põhjuseta, kohe privaatsuspoliitika.

## Otsused, mis ootavad omanikku

- Millal viia arhiiv privaatseks? (hiljemalt enne, kui tulemuste ajalugu hakkab koonduma)
- Millal saata esimene kiri liitudele?
- Kas lehele tuleb liiklusloendur? Isikuandmeteta (nt Plausible või GoatCounter) või üldse mitte.
