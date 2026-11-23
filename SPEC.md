# spordikavad.ee: lähteülesanne

## Eesmärk

Lihtne veebileht, kus on näha, milliseid spordimänge saab **Tallinnas** kohapeal vaatamas käia. Stiil on nagu kinokavad.ee: üks kronoloogiline päevanimekiri, minimaalne kujundus, kiire ja telefonis mugav.

Tegu on hobiprojektiga, mille omanik tahab hooldusele kulutada **peaaegu null aega**. Seepärast on igas otsuses kõige olulisem lihtsus, automaatika ja töökindlus, mitte funktsioonide arv.

## Kasutaja vaade

Kasutaja avab lehe ja näeb kohe tänaseid mänge Tallinnas, kellaaja järgi järjestatult. Iga rea peal on:

- algusaeg (HH:MM, Europe/Tallinn)
- ala (näiteks korvpall), kuvatud lühikese sildi või ikoonina
- liiga (näiteks „Meistriliiga“)
- mäng: „Kodumeeskond – Külalismeeskond“
- toimumiskoht (saali või staadioni nimi)
- link allikale: liiga, klubi või piletimüüja mängulehele

Navigeerimine:
- „Eelmine päev“ / „Järgmine päev“ ja kuupäeva valik (vähemalt 14 päeva ette)
- lihtne alafilter (nupud: Kõik / Jalgpall / Korvpall / …), mis töötab kliendipoolselt ilma lehte uuesti laadimata
- kui päeval mänge pole, kuvatakse „Täna mänge pole“ ja link järgmisele päevale, kus mänge on

## Esimese versiooni ulatus (MVP)

**Linn:** ainult Tallinn (sh Tallinna piires olevad saalid ja staadionid).

**Alad ja liigad:** täiskasvanute kõrgliigad järgmistel aladel, kui avalik mängukava on olemas:
1. jalgpall
2. korvpall
3. jäähoki
4. võrkpall
5. käsipall
6. saalihoki

Liigade ametlikud nimed ja andmeallikad selgita välja ise (vaata „Andmeallikad“). Kui mõne ala jaoks sobivat allikat ei leia, jäta see välja ja märgi see `SOURCES.md` faili. Ära hakka seda ala jõuga tegema.

**Teine samm (pärast MVP-d, sama arhitektuuriga):** samade alade esiliigad ja naiste liigad. Madalamad liigad on projekti pikaajaline nišš, nii et arhitektuur peab võimaldama uue liiga lisamist ühe uue adapterfailiga.

**Esimesest versioonist on välja jäetud:** muud linnad, ühekordsed suurüritused, tulemused ja tabelid, live-skoorid, video, kasutajakontod, ingliskeelne versioon, reklaam.

## Andmeallikad ja kogumise põhimõtted

Omanik **ei suhtle liitudega**. Leht peab olema üles ehitatud nii, et andmete omanikul poleks põhjust pahaks panna:

- Kasuta ainult **avalikult kättesaadavaid** lehti või avalikke API-sid/vooge. Sisselogimise taga olevad andmed ei sobi.
- Kontrolli iga allika puhul **robots.txt-i ja kasutustingimusi**. Kui need keelavad automaatse kogumise, jäta allikas vahele ja kirjuta see `SOURCES.md` faili.
- Tee **üks uuendus päevas** ja ainult nii palju päringuid, kui vaja. Päringute vahel peab olema paus. Kasuta kirjeldavat User-Agenti koos kontaktaadressiga.
- Salvesta ja kuva ainult **fakte**: aeg, koht, võistkonnad, liiga ja link. Ära kopeeri tekste, pilte ega logosid.
- Iga mäng lingib alati tagasi allikale.

Iga allika kohta pane `SOURCES.md` faili kirja: URL, andmete kuju (HTML, JSON, iCal, PDF), robots/tingimuste kontrolli tulemus ja kuupäev, hooaja ligikaudne algus ja lõpp ning teadaolevad eripärad.

Eelista allikaid selles järjekorras: avalik JSON/API/iCal → staatiline HTML → JavaScriptiga renderdatud leht. PDF-iga allikad jäta MVP-st välja.

## Arhitektuur

Staatiline leht, server ja andmebaas puuduvad.

- **Keel:** Python 3.12+
- **Kogumine:** iga allika jaoks eraldi adapter (`scrapers/<ala>_<liiga>.py`), mis tagastab ühtse andmemudeli objektide loendi. Ühine HTTP-kiht (kordused, ajapiirangud, paus, User-Agent).
- **Genereerimine:** Jinja2 mallidest staatilised HTML-failid kausta `dist/`. Eraldi leht iga kuupäeva kohta (`/2026-11-21/`) ja `index.html` tänase päevaga. Lisaks `events.json` kogu andmestikuga.
- **Majutus:** GitHub Pages (või Cloudflare Pages). Hiljem kohandatud domeen spordikavad.ee.
- **Ajastus:** GitHub Actions käivitab kogumise ja genereerimise iga päev kell 05:00 Tallinna aja järgi ning lisaks käsitsi (`workflow_dispatch`).
- **Kliendipoolne JS:** ainult alafilter ja kuupäeva valik, kokku alla ~5 KB. Leht peab töötama ka ilma JS-ita.
- Ühe adapteri viga ei tohi kogu ehitust katki teha. Sel juhul kasutatakse selle allika viimaseid õnnestunud andmeid ja kirjutatakse logisse hoiatus.

### Andmemudel

```python
@dataclass
class Event:
    id: str            # stabiilne räsi (allikas + kuupäev + võistkonnad)
    sport: str         # "jalgpall" | "korvpall" | "jaahoki" | "vorkpall" | "kasipall" | "saalihoki"
    league: str        # inimloetav liiga nimi
    start: datetime    # ajavööndiga, Europe/Tallinn
    home: str
    away: str
    venue: str         # normaliseeritud saali nimi
    city: str          # "Tallinn"
    url: str           # link allika mängulehele (või liiga kalendrile)
    source: str        # adapteri nimi
    time_tbc: bool     # True, kui kellaaeg pole veel kinnitatud
    video: str         # otseülekande või järelvaatamise link (tühi, kui ei tea), vt ulekanded.py
    video_by: str      # kes näitab: "YouTube", "Postimees", "Delfi TV" …
```

### Toimumiskohad

- Hoia saalide nimekirja failis `venues.yaml`: normaliseeritud nimi, aliased (eri allikad kirjutavad sama saali eri moodi) ja linn.
- Linna järgi filtreeritakse `venues.yaml` põhjal. Tundmatu toimumiskoht kirjutatakse logisse, et selle saaks nimekirja lisada.

## Kujundus

- Kinokavade vaim: tekstipõhine, kiire, ilma piltideta, palju tühja ruumi, hea kontrast.
- Mobiil esikohal, töötab hästi alates 360 px laiusest.
- Süsteemifondid, väline CSS-raamistik puudub, üks väike CSS-fail.
- Toeta heledat ja tumedat režiimi (`prefers-color-scheme`).
- Kõik tekstid eesti keeles.
- Jaluses on:
  - „Andmed: liitude ja klubide avalikud kodulehed. Kontrolli aega enne kohaleminekut.“
  - kontaktaadress ja lause: „Kui olete andmete omanik ja ei soovi, et teie andmeid siin kuvataks, kirjutage meile.“
- Küpsiseid ja jälgimisskripte pole. Kui statistikat on vaja, kasuta Cloudflare Web Analyticsit (küpsisevaba) ja tee see konfigureeritavaks, vaikimisi välja lülitatuna.
- Lisa korralikud `<title>`, meta description, Open Graph sildid ja `sitemap.xml`, sest otsingumootorid on peamine liiklusallikas.

## Töökindlus ja jälgimine

Omanik ei taha lehte käsitsi kontrollida, seega peab leht ise vigadest teada andma:

- Kui adapter tagastab hooaja sees 0 mängu või viskab vea, avab GitHub Actions automaatselt **GitHub Issue** (sama allika kohta mitte rohkem kui üks avatud issue korraga).
- Hooaja kuupäevad on kirjas `SOURCES.md` failis ja konfiguratsioonis, et hooajavälisel ajal 0 mängu poleks viga.
- Iga adapteri jaoks on test salvestatud näidis-HTML/JSON-iga (`tests/fixtures/`), et parsimise loogikat saaks kontrollida ilma võrguta.
- Ehituse lõpus kirjutatakse logisse lühike kokkuvõte: mitu mängu igast allikast tuli ja millised allikad ebaõnnestusid.

## Repo struktuur (soovituslik)

```
scrapers/        # üks adapter allika kohta + ühine http.py
site/            # Jinja2 mallid, CSS, JS
data/            # viimased õnnestunud andmed allikate kaupa (JSON), commititakse
tests/           # testid + fixtures
venues.yaml
config.yaml      # allikad, hooajad, analüütika lüliti
SOURCES.md       # allikate kaardistus
README.md        # kuidas käivitada, kuidas lisada uut liigat
.github/workflows/build.yml
```

## Töö järjekord

1. **Allikate kaardistus:** uuri kõiki 6 ala, täida `SOURCES.md` ja vali MVP allikad. Anna omanikule lühikokkuvõte enne, kui hakkad adaptereid kirjutama.
2. Andmemudel, ühine HTTP-kiht, `venues.yaml`.
3. Esimene adapter ja kogu toru läbi: kogumine → JSON → HTML → GitHub Pages.
4. Ülejäänud adapterid.
5. Kujundus, filter, SEO.
6. Jälgimine (automaatsed issue'd), testid, README.

## Valmis on siis, kui

- Leht on GitHub Pagesis üleval ja uueneb iga päev automaatselt ilma käsitsi sekkumiseta.
- Vähemalt 4 ala 6-st on kaetud ja tänased ning järgmise 14 päeva Tallinna mängud on näha.
- Andmed kattuvad pistelisel kontrollil allikaga (kontrolli vähemalt 5 mängu eri allikatest).
- Leht laadib telefonis kiiresti, ilma küpsiste ja väliste skriptideta.
- Katkine allikas tekitab GitHub Issue ega lõhu ülejäänud lehte.
- README-s on selgitatud, kuidas lisada uus liiga (üks adapter + konfiguratsioonirida + fixture-test).

## Tööpõhimõtted agendile

- Kui kahest lahendusest üks on lihtsam ja vajab vähem hooldust, vali see.
- Ära lisa sõltuvusi, raamistikke ega teenuseid, mida pole tingimata vaja.
- Kui allikaga on küsitavusi (tingimused, robots.txt, JS-renderdus), jäta see allikas vahele ja kirjuta põhjus `SOURCES.md` faili. Ära otsi viise piirangutest mööda minna.
- Omaniku poole pöördu ainult siis, kui otsust ei saa ise teha (näiteks domeeni seadistus või GitHubi õigused). Muu kohta kirjuta lühike kokkuvõte iga sammu lõpus.
