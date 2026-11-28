# Ela kaasa (elakaasa.ee): töökaart

Staatiline leht: mis spordivõistlusi Eestis kohapeal vaatamas saab käia. Python ehitab HTML-i (`build.py`), GitHub Actions
ehitab ja avaldab iga päev GitHub Pagesi. Omanik tahab hooldusele kulutada peaaegu null aega: lihtsus, automaatika, mitte
ühtegi tasulist teenust ega serverit. Vestlus ja tekstid on **eesti keeles**. Taust: `SPEC.md`, `docs/VISION.md`.

## Käsud
- Testid: `python -m unittest discover -s tests` (~20 s, peavad enne iga commit'i läbima)
- Ehitus kohapeal: `python build.py --offline` (5 s, kasutab salvestatud `data/`, tulemus `dist/`, gitignore'is)
- Lighthouse (mobiil): `python build.py --offline`, `cd dist && python3 -m http.server 8765 &`, `npx lighthouse http://localhost:8765/ --only-categories=performance,accessibility,best-practices,seo`
  (Chromium: `CHROME_PATH=/opt/pw-browsers/chromium`, lipud `--headless=new --no-sandbox`). Eesmärk: kõik ≥ 95 (mõõdetud 2026-11-26: 99–100, Best Practices 96:
  kohalikul serveril Cloudflare'i analüütika CORS-viga, päris lehel seda pole). Värvikontrast ≥ 4.5:1 (test kontrollib ala värve).
- Täisehitus võrguga käib ainult Actionsis (8–12 min, enamus on allikate viisakas ooteaeg). `data/` ja `archive/` commit'ib
  töövoog („Andmete uuendus …“): neid käsitsi ei muuda.

## Kus mis on
- `sports.toml`: **alade register** (üks ala = üks `[[sport]]` plokk: nimi, käänded, värv, rühm, allikate lingid,
  Delfi/Go3/ERR kava tuvastus). Sellest tuleb kõik: `scrapers/sports.py` → model, build, CSS/JS (markerid `/* @sports:… */` failides
  `site/style.css` ja `site/kalender.js` täidab `build.py`), kavad.
- `scrapers/<allikas>.py`: adapter (`fetch(fetcher)` ja `parse(html)`), `config.toml` `[[source]]`: allikas, hooaeg, tasemed
- `scrapers/model.py`: `Event` (valikulised väljad: `end`, `video`, `note`), tasemed `LEVELS` (1 tipp, 2 esi, 3 peidetud, 4 noored, 5 koondised)
- `venues.toml`: saalid (peavad olema siin ja linn `config.toml` `[geo]` all; test kontrollib), `config.toml [geo] foreign`: välismaa kohad
- `kasitsi.toml`: käsitsi lisatud mängud (otsinguagent); `allikad.toml`: allikate register; `ulekanded.toml` + `ulekanded.py`:
  kes mida näitab, kavad (Delfi, ERR, Go3), `[[koduhall]]` (kava rida → mäng)
- `build.py` (ehitus, leht, sitemap, mängulehed `/m/<id>/` KÕIGIL mängudel, ala- ja liigalehed `/<ala>/…`; `game_title`, `event_ld`),
  `site/*.html` (`game.html` mängulehed, `list.html` ala- ja liigalehed), `site/style.css`, `site/app.js`, `site/kalender.js`
- `site/praktikum/`: eraldiseisev praktikumi alamleht `/praktikum/` (omaniku TalTechi praktikum, tegi ChatGPT, avaldatud 2026-11-27): staatiline `index.html` + `assets/` (PDF, DOCX),
  `build.py` kopeerib kausta `site/praktikum/` väljundisse; `noindex, nofollow, noarchive`, sitemapis, menüüs ja statistikas pole, test `test_praktikum_is_private_from_navigation_and_search`.
  **Avalik** (GitHub Pages ei piira ligipääsu), seega ei pane sinna isikuandmeid ega salajast. Uus fail: pane `assets/` alla ja lisa link `index.html`-i.
- `analuus/` + `meeskonnad.toml` + `raportid/`: andmepõhine analüüs (kiirstart: `python -m analuus.nadalaraport --stdout`). `tulemus.py` ühtlustab võit/kaotus/viik/vahe ala kaupa,
  `meeskonnad.py` ühtlustab meeskonnanimed (`meeskonnad.toml` aliased; kandidaadid: `python -m analuus.meeskonnad`), `lood.py` detektorid (üllatused tabeli järgi,
  seeriad, tasavägised, rekordid), `nadalaraport.py` kirjutab `raportid/<nädal>.md` ja `.json` (töövoog igal ehitusel; sama nädal kirjutatakse üle). Tulemused on ainult
  7 alal, jalgpall on 92% neist; tabelit andmetes pole (arvutatakse), seetõttu loe `analuus/lood.py` docstringi enne tulemuste tõlgendamist.
- `paigad.toml` + `analuus/paigad.py` + `analuus/geokodeeri.py`: toimumiskohtade tabel: **paik** = üks või mitu `venues.toml` kohta ühe koordinaadiga (duplikaadid seotud),
  `tapsus` = `tapne` (OSM spordiobjekt, nimi ühtib) | `umbes` (lähedal olev objekt, asula, kool) | `linn` (ainult linna keskpunkt). Uus koht lehel:
  `python -m analuus.paigad --puudu`, siis `python -m analuus.geokodeeri` (Nominatim, 1 päring sekundis) ja lisa tulemus `paigad.toml`-i; test nõuab ≥ 95% mängudest paigaga.
- `analuus/kaart.py` + `site/kaart.html` + `site/kaart.js` + `site/vendor/leaflet/`: spordikaart `/kaart/` (Leaflet 1.9.4 oma koopiana, ei CDN-i; aluskaart OSM-i standardplaadid heledaks CSS-filtriga:
  CARTO `light_all` nõuab 2026. aastast API võtit ja annab vesimärgiga plaadi). Ringid paikade kaupa (suurus = mängude arv ajaaknas, värv = peamine ala), vaated kindel kuupäev (3 h aken, nimekiri kellaaja järgi,
  iga rida viib mängulehele) ja tüüpiline nädal (nädalapäev × kellaaeg, summa ÷ aktiivsete nädalate arv). `kaart/andmed.json` (paigad, linnad, mängud reana koos id-ga) ja `kaart/tekstid.json` (pealkirjad, laetakse hiljem).
  Mobiilis kaart kohe päise all ja filtrid kokkuvolditud ribas „Filtrid (N aktiivset)“ (CSS `order`); algvaade Tallinn või `?linn=`/localStorage `spordikavad-linn`; nupp „Kogu Eesti“; **seis on URL-is** (v, d, t, w, a, l, tbc, c, z; pushState/popstate).
  Ring ja nimekirja rida tõstavad teineteist esile, ringi klõps kerib nimekirja. Ainult nähtavad tasemed.
- `/analuus/` (`site/analuus.html`, `kaart.ehita_analuus`): praegu ainult „tulekul“, noindex, sitemapis pole; halli mõju tabelit seal ei avaldata enne omaniku ülevaatust.
  `analuus/halliefekt.py`: halli efekt = meeskonna kodu-% hallis miinus sama meeskonna võõrsil-% samal hooajal (kaalutud, viik eraldi, Newcombe'i vahemik; välistab koondised, turniirid/karika, mitte-regulaarkasutajad);
  raport: `python -m analuus.halliefekt --koht Wismari`. **Mitte põhjuslik.**
- `analuus/ennustus.py` + `analuus/tagasivaatav.py` + `analuus/ulevaade.py`: Elo-tüüpi tugevusnumber (jalgpall, võit/viik/kaotus), tagasivaatav test (`python -m analuus.tagasivaatav --kontroll`: parameetrid valitakse teistel liigadel, ennustus ainult varasemate mängudega) ja
  **mängu lehe automaatne ülevaade** (`site/game.html`): enne (tõenäosused, vorm, arvutatud tabelikoht, omavahelised mängud, koht; ennustus alles kui mõlemal meeskonnal ≥ 3 mängu liiga andmetes) ja pärast (kas ennustus pidas, üllatus,
  tugevusnumbri muutus, mõlema järgmine mäng). **Ainult arvutatud faktid** (ei vigastusi, taustu, piletiandmeid; kihlveofirmasid ei lingita, panustamise sõnavara pole); tekst on reeglipõhine, mitte keelemudeli kirjutatud ja lehel nii öeldud.
  Andmetes on üks hooaeg (2026), hooaja vahetuse taandumist pole testitud. Muud alad: ülevaadet pole.
- `ogimage.py` + `site/fonts/`: mängu OG-pilt (Pillow, DejaVu; igale eelseisvale mängule `m/<id>/og.png`, muul juhul üldine `og.png`)
- `scripts/`: `automerge_check.py` (agendi PR-i kontroll), `report_issues.py` (katkised allikad → GitHub Issue ja rida `MAINTENANCE.md`-i),
  `maintenance_log.py` (hoolduslogi ja kokkuvõte)
- `SOURCES.md`: **allikate otsused ala kaupa** (miks midagi kasutatakse või jäetakse välja). Loe ainult asjakohane osa
  (`grep -n "^## " SOURCES.md`), mitte kogu faili.

## Reeglid
- **Allikas peab olema avalik ja robots.txt lubab** (kontrolli enne iga uut allikat). Korvpalliliidu lehed (basket.ee,
  estlatbl.com) keelavad robotid: neid ei koguta, ka mitte käsitsi. Sotsiaalmeedia ei ole allikas. Isikuandmeid (mängijad,
  treenerid) ei lisata. Ainult Eestis toimuv. Iga allikas: viisakas päring, ühe päeva jooksul üks (`config.toml [http]`).
- Iga uue adapteri jaoks **fixture-test** (`tests/fixtures/…`, `tests/test_<allikas>.py`), fixture on päris lehe lühendatud HTML.
- Üritusalad (`event = true`): `home` = ürituse nimi, `away` tühi. Mitmepäevasel on `end`.
- **Hooldus:** kui parandad katkist allikat või teed muu hoolduse (PR), lisa rida `MAINTENANCE.md` tabelisse „Käsitsi hooldus“
  (kuupäev | mis oli katki | parandus + PR). Automaatsete Issue'de logi ja kokkuvõte täituvad ise (`scripts/report_issues.py`).
- Kõik vahele jäetud allikad ja põhjus kirjuta `SOURCES.md`-i; ka allikate register `allikad.toml` ja README „järgmised alad“.
- Commit'i sõnum eesti keeles, ühe rea kokkuvõte + lühike loend; lõppu eeldatud attribuutiread. **Püsiv luba (omanik 2026-11-26): PR-i teeb ja merge'ib (squash) agent ise, küsimata**,
  kui testid läbivad; seejärel kontrolli ehituse tulemust (Actions) ja anna lühike kokkuvõte. Jätkuvalt omaniku käsitsi samm: kontod (Search Console, Cloudflare).

## Alamagendid (`.claude/agents/`, omanik 2026-11-26 lubas kasutada töö keerukuse järgi)
- `allika-adapter` (Sonnet): uus allikas või ala mustri järgi (kontroll robots.txt-ga, adapter, fixture-test, seadistus, päris vastuse vastu proov). Ei tee PR-i.
- `ulevaataja` (Opus): loeb muudatuse üle enne merge'i (korrektsus, reeglid, testid, ehituse ja lehe mõju); ei muuda midagi.
- Põhisessioon teeb arhitektuuri, ümberehitused ja raske silumise ise; mustritööd ja kiired kontrollid võib delegeerida. Uus alamagent: fail
  `.claude/agents/<nimi>.md` (frontmatter `name`, `description`, `tools`, `model`); ainult need kaustas on repos, ülejäänud `.claude/` on gitignore'is.

## Uue ala lisamine (kontrollnimekiri)
1. `sports.toml`: uus `[[sport]]` (+ vajadusel `[[group]]`). Test `tests/test_alad.py` ja `tests/test_sports_register.py` kontrollivad.
2. Kui on adapter: `scrapers/<nimi>.py` + `config.toml [[source]]` (+ `venues.toml`, `[geo] foreign`/`place`) + fixture-test.
   Kui mitte: võistlused lisab agent `kasitsi.toml`-i, ainult `allikad.toml` kirje (`kasutus = "agent"`).
3. `allikad.toml` kirje, `SOURCES.md` osa, README järgmiste alade loend. Lõpuks testid.

## Uue allika lisamine olemasolevale alale
Adapter + `config.toml [[source]]` (`competitions` = „Meist“ tabel ja seire; `check = false` harva toimuvatel) +
venues + fixture-test + `allikad.toml` + `SOURCES.md`. Dedupe (`build.dedupe`) liidab sama mängu mitmest allikast.
