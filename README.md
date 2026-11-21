# spordikavad

Tallinna kõrgliigade spordimängud ühel lihtsal lehel: https://laurik-commits.github.io/spordikavad/

Lähteülesanne: [SPEC.md](SPEC.md). Andmeallikad ja nende kontroll: [SOURCES.md](SOURCES.md).

## Kuidas see töötab

1. **GitHub Actions** ([.github/workflows/build.yml](.github/workflows/build.yml)) käivitub iga päev kell 03:00 UTC (05:00 Tallinna talveajal), iga `main` haru muudatuse järel ja käsitsi (Actions → „Ehita ja avalda“ → Run workflow).
2. [build.py](build.py) käivitab iga allika adapteri (`scrapers/<ala>_<liiga>.py`), jätab alles Eestis toimuvad mängud ([venues.toml](venues.toml) saalide linnade ja `config.toml` `[geo]` järgi) ja salvestab need kausta `data/`.
3. Mallidest ([site/](site/)) genereeritakse kausta `dist/` staatiline leht iga piirkonna kohta: Tallinn juurkaustas (`/`, `/2026-11-21/`), teised oma kaustas (`/tartu/…`, `/harjumaa/…`, `/eesti/…` = kogu Eesti). Igal piirkonnal on täna + 14 päeva. **Esiliigad** on eraldi kalender kaustas `/esiliigad/…` (sama linnajaotusega). Lisaks `events.json` ja `sitemap.xml`. Päise linna- ja tasemevalik („Kõrgliigad / Esiliigad“) jätavad valiku kasutaja brauserisse meelde ja avaleht suunab sinna.
4. `dist/` avaldatakse GitHub Pagesis.

**Jälgimine (GitHub Issues, sellest tuleb e-kiri):**
- **„Allikas katki: …“**: allikas annab vea või **hooaja sees pole 42 päeva jooksul ühtegi tulevast mängu**. Kontrolli tehakse iga võistluse kohta eraldi, möödunud mänge ei arvestata, nii et ka uuel hooajal muutunud liiga ID tuleb välja. Kui kõik võistlused on tühjad, kasutatakse viimaseid salvestatud andmeid. Kui tühi on ainult osa (`partial`), uuenevad teised tavapäraselt. Karikad ja playoffid on märgitud `check = false`, sest neil on pikad pausid.
- **„Tundmatud toimumiskohad“**: saal puudub `venues.toml` failist. Kui nimekiri muutub, issue uueneb.
- **„Mängud ilma toimumiskohata“**: lähipäevade mängul pole allikas saali märgitud.
- Kõik issue'd suletakse ise, kui probleem kaob.
- Hooajad on `config.toml`-is kujul `MM-DD` (nt `["09-15", "05-15"]`) ja kehtivad igal aastal.
- Kui igapäevane uuendus seiskub, näitab leht ise teadet „Andmed võivad olla vananenud“.

Lehel on ka „Mis siin on?“ leht (`/info/`). Möödunud päevade aadressid (`/2026-11-19/`) suunatakse 404-lehe kaudu tänasele päevale.

## Kohapeal käivitamine

Vaja on Python 3.12+.

```
pip install -r requirements.txt
python -m unittest discover -s tests -t .   # testid, võrku ei kasuta
python build.py                             # kogub andmed ja ehitab lehe
python build.py --offline                   # ehitab ainult data/ andmetest
python -m http.server 8765 --directory dist # vaata http://localhost:8765
```

Windowsis kasuta `python` asemel `py`.

## Uue liiga lisamine

Kolm sammu: adapter, konfiguratsioonirida ja test.

1. **Kontrolli allikat** ja kirjuta tulemus [SOURCES.md](SOURCES.md) faili: URL, andmete kuju, robots.txt, kasutustingimused ja hooaja kuupäevad. Kui robots.txt või tingimused keelavad automaatse kogumise, jäta allikas vahele.

2. **Adapter** `scrapers/<ala>_<liiga>.py`. Sisu peab olema selline:

   ```python
   NAME = "kasipall_esiliiga"          # sama mis faili nimi ja config.toml-i name
   SPORT = "kasipall"                  # võti scrapers/model.py SPORTS sõnastikust
   URL = "https://..."

   def parse(page: str) -> list[Event]:
       ...  # tagasta new_event(...) objektid; venue = koha nimi nii, nagu allikas selle kirjutab

   def fetch(fetcher) -> list[Event]:
       return parse(fetcher.get(URL))
   ```

   Linna järgi ise filtreerida pole vaja, `build.py` teeb selle `venues.toml` põhjal. Kui allikas kasutab sama süsteemi nagu olemasolev adapter (kasipall.ee, saalihoki.ee, jalgpall.ee, DataProject), kopeeri see ja muuda ainult liiga ID-d või nime.

3. **Konfiguratsioon** [config.toml](config.toml):

   ```toml
   [[source]]
   name = "kasipall_esiliiga"
   sport = "kasipall"
   league = "Esiliiga"
   enabled = true
   seasons = [["09-15", "05-15"]]   # igal aastal, võib üle aastavahetuse
   ```

   Hooaja kuupäevad on olulised: väljaspool hooaega ei loeta 0 mängu veaks.

   Kui liiga kasutab olemasolevat adapterit (jalgpall.ee, kasipall.ee, DataProject), piisab rea lisamisest selle `competitions` nimekirja. Esiliiga puhul lisa `level = 2`, siis läheb liiga „Esiliigad“ kalendrisse:

   ```toml
   { id = 360, league = "Esiliiga (mehed)", level = 2 },
   ```

4. **Test.** Salvesta allika leht kausta `tests/fixtures/<name>.html` (üks kord, näiteks `py -c "from scrapers.http import Fetcher; ..."`) ja kirjuta `tests/test_<name>.py`, mis kontrollib mängude arvu ja üht konkreetset mängu (vaata näiteks [tests/test_jaahoki_optibet.py](tests/test_jaahoki_optibet.py)).

5. **Käivita** `python build.py` ja vaata kokkuvõtet. Kui logis on „Tundmatu toimumiskoht“, lisa see `venues.toml` faili õige linnaga. Kui linn on uus, lisa see ka `config.toml` `[geo]` alla: suurem linn `[[geo.city]]`, väiksem koht `[geo.place]` (koht → maakond) või välismaa `geo.foreign`. Test `GeoTest` annab märku, kui mõni linn on lisamata.

## Hooldus

- **Kord hooajas** (august ja veebruar) vaata üle `config.toml` hooaegade kuupäevad ja liigade URL-id (võrkpalli DataProjecti ja baltichandball.eu võistluste ID-d muutuvad igal hooajal, vt `config.toml` → `competitions`; ka kasipall.ee ID-d võivad muutuda). Kui see ununeb, avab jälgimine issue „Allikas katki“, sest hooaja alguses pole uusi mänge..
- **Issue tuli:** ava Actions'i logi, võrdle allika lehte salvestatud fixture'iga ja paranda adapterit. Kuni seda pole tehtud, näitab leht viimaseid töötanud andmeid.
- Kontaktaadress jaluses ja User-Agentis: `config.toml` → `site.contact_url` ja `http.contact`.

## Tulevikuideed

- **Loapalved liitudele** (omaniku plaan 2026-11-20): kui leht on mõnda aega stabiilselt töötanud, kirjutab omanik ja küsib luba ajakava kasutamiseks või avalikku andmevoogu. Claude koostab siis kirjade mustandid.
  - **Eesti Korvpalliliit** (basket.ee, estlatbl.com): robots.txt keelab automaatse kogumise, seetõttu on lehel praegu ainult Bigbank/Kalevi mängud (klubi lehelt, adapter `korvpall_kalev`). Loa korral: liiga adapter (`scrapers/korvpall_...py`), `config.toml` rida ja test; korvpalli märkuse (`sport_note`) saab siis eemaldada. Taust: SOURCES.md → Korvpall.
  - **Eesti Jäähokiliit** (Unibet Hokiliiga, naiste hokiliiga): ajakava on ehs.eestihoki.ee lehel, aga brauser laadib selle hockeydata.net kommertsteenusest liidu API-võtmega. Küsida luba (või avalikku voogu / iCal-i), et tohiks seda kasutada. Loa korral: adapter (`scrapers/jaahoki_ehl.py`), `config.toml` rida ja test; `sport_note` jäähoki märkuse saab siis eemaldada. Taust: SOURCES.md → Täiendavate võistluste ülevaade.

- **Piletid ja ülekanded** (omanikuga kokku lepitud 2026-11-20, teha pärast MVP-d):
  - Püsiinfo seadistusfailis: klubi → piletimüüja link, liiga → ülekandekanal. Mängu real „Piletid ↗“ ja „📺 kanal“. Üle vaadata kord hooajas.
  - Kui allika mängulehel on piletilink või ülekande info juba olemas, võtta see kaasa.
  - Mängupõhist kogumist piletimüüjatelt ega telekanalitelt ei tee (hooldus, tingimused).
- Päevade ribale kuu nimi, kui riba ulatub üle kuu vahetuse.
- **Jalgpalli karikad** (omanikuga kokku lepitud „millalgi tulevikus“): Tipneri karikas, naiste karikas, superkarikas. Vaja on iCal-lugejat (vt SOURCES.md „Täiendavate võistluste ülevaade“).
- Eesti jäähoki liigad (Vipers, naiste liiga): vaata uuesti, kas ehis.eestihoki.ee-l on 2026/27 hooaeg.
- **Veel madalamad liigad** (II liiga jm): esiliigad on tehtud (2026-11-20, eraldi kalender). Kui tahad rohkem, lisa liigad `level = 2` reaga või tee kolmas tase (`scrapers/model.py` → `LEVELS`).
- Saalijalgpalli esiliigat jalgpall.ee avalikult ei näita. Lisa, kui see ilmub.
