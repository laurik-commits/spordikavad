# spordikavad

Tallinna kõrgliigade spordimängud ühel lihtsal lehel: https://laurik-commits.github.io/spordikavad/

Lähteülesanne: [SPEC.md](SPEC.md). Andmeallikad ja nende kontroll: [SOURCES.md](SOURCES.md).

## Kuidas see töötab

1. **GitHub Actions** ([.github/workflows/build.yml](.github/workflows/build.yml)) käivitub iga päev kell 03:00 UTC (05:00 Tallinna talveajal), iga `main` haru muudatuse järel ja käsitsi (Actions → „Ehita ja avalda“ → Run workflow).
2. [build.py](build.py) käivitab iga allika adapteri (`scrapers/<ala>_<liiga>.py`), jätab alles Tallinna mängud ([venues.toml](venues.toml) järgi) ja salvestab need kausta `data/`.
3. Mallidest ([site/](site/)) genereeritakse kausta `dist/` staatiline leht: `index.html` (täna), üks leht päeva kohta 14 päeva ette, `events.json`, `sitemap.xml`.
4. `dist/` avaldatakse GitHub Pagesis.

**Kui allikas läheb katki** (viga või hooaja sees 0 mängu), kasutatakse selle allika viimaseid salvestatud andmeid, ülejäänud leht ehitatakse tavapäraselt ja GitHubis avatakse issue „Allikas katki: …“. Sellest tuleb e-kiri. Kui allikas hakkab jälle tööle, suletakse issue automaatselt. Tundmatute toimumiskohtade kohta tekib issue „Tundmatud toimumiskohad“.

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
   seasons = [["2026-09-15", "2027-05-15"]]
   ```

   Hooaja kuupäevad on olulised: väljaspool hooaega ei loeta 0 mängu veaks.

4. **Test.** Salvesta allika leht kausta `tests/fixtures/<name>.html` (üks kord, näiteks `py -c "from scrapers.http import Fetcher; ..."`) ja kirjuta `tests/test_<name>.py`, mis kontrollib mängude arvu ja üht konkreetset mängu (vaata näiteks [tests/test_jaahoki_optibet.py](tests/test_jaahoki_optibet.py)).

5. **Käivita** `python build.py` ja vaata kokkuvõtet. Kui logis on „Tundmatu toimumiskoht“, lisa see `venues.toml` faili õige linnaga.

## Hooldus

- **Kord hooajas** (august ja veebruar) vaata üle `config.toml` hooaegade kuupäevad ja liigade URL-id (võrkpalli DataProjecti `ID=29` on hooajapõhine, käsipalli liiga ID 359 võib uuel hooajal muutuda).
- **Issue tuli:** ava Actions'i logi, võrdle allika lehte salvestatud fixture'iga ja paranda adapterit. Kuni seda pole tehtud, näitab leht viimaseid töötanud andmeid.
- Kontaktaadress jaluses ja User-Agentis: `config.toml` → `site.contact_url` ja `http.contact`.

## Tulevikuideed

- **Piletid ja ülekanded** (omanikuga kokku lepitud 2026-11-20, teha pärast MVP-d):
  - Püsiinfo seadistusfailis: klubi → piletimüüja link, liiga → ülekandekanal. Mängu real „Piletid ↗“ ja „📺 kanal“. Üle vaadata kord hooajas.
  - Kui allika mängulehel on piletilink või ülekande info juba olemas, võtta see kaasa.
  - Mängupõhist kogumist piletimüüjatelt ega telekanalitelt ei tee (hooldus, tingimused).
- Päevade ribale kuu nimi, kui riba ulatub üle kuu vahetuse.
- Esiliigad ja naiste liigad (lähteülesande teine samm): jalgpall.ee, kasipall.ee ja saalihoki.ee kasutavad kõigi liigade jaoks sama süsteemi.
