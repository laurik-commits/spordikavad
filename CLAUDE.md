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
