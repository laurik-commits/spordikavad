# Ela kaasa (spordikavad)

**Visioon, põhimõtted ja strateegia: [docs/VISION.md](docs/VISION.md)**

Eesti spordimängud, mida saab kohapeal vaatama minna, ühel lihtsal lehel: https://elakaasa.ee/ (vana aadress laurik-commits.github.io/spordikavad suunab sinna).

Domeen elakaasa.ee on registreeritud Zone.ee kaudu (omanik: lehe omanik). Zone'i DNS-is on GitHub Pagesi A- ja AAAA-kirjed ning `www` CNAME → laurik-commits.github.io. Kohandatud domeen on seatud GitHub Pagesi seadetes (build_type workflow, seega CNAME-faili pole vaja).

Lähteülesanne: [SPEC.md](SPEC.md). Andmeallikad ja nende kontroll: [SOURCES.md](SOURCES.md). Suund, ajalooarhiiv ja turvalisus: [docs/VISION.md](docs/VISION.md).

## Kuidas see töötab

1. **GitHub Actions** ([.github/workflows/build.yml](.github/workflows/build.yml)) käivitub iga päev kell 03:00 UTC (05:00 Tallinna talveajal), iga `main` haru muudatuse järel ja käsitsi (Actions → „Ehita ja avalda“ → Run workflow).
2. [build.py](build.py) käivitab iga allika adapteri (`scrapers/<ala>_<liiga>.py`), jätab alles Eestis toimuvad mängud ([venues.toml](venues.toml) saalide linnade ja `config.toml` `[geo]` järgi) ja salvestab need kausta `data/`.
3. Mallidest ([site/](site/)) genereeritakse kausta `dist/` staatiline leht iga piirkonna ja taseme kohta. **Avaleht (juurkaust `/`, `/2026-11-21/`) on Kogu Eesti + kõik liigad** (`config.toml` → `[geo] default` ja `[site] default_level`); linnad ja maakonnad on oma kaustas (`/tallinn/…`, `/tartu/…`, `/harjumaa/…`). Vanad aadressid `/eesti/…` ja `/koik/…` suunab 404-leht ümber. Igal piirkonnal on täna + 14 päeva ette ja 14 päeva tagasi (`site.days_back`, vana päeva mängud tulevad [ajalooarhiivist](archive.py): tulemus, kui allikas seda andis, ja link allika lehele seisu ning statistika jaoks; vanad päevad on `noindex` ja sitemapis pole). **Kõrgliigad** on kaustas `/korgliigad/…`, **esiliigad** kaustas `/esiliigad/…` ja **madalamad liigad** kaustas `/madalamad/…` (sama linnajaotusega). Lisaks `events.json` ja `sitemap.xml`. **Noored** on neljas kalender kaustas `/noored/…`. **Koondised** on viies kalender kaustas `/koondised/…`. Päise linna- ja tasemevalik („Kõrgliigad / Esiliigad / Madalamad liigad / Noored / Koondised“) jätavad valiku kasutaja brauserisse meelde ja avaleht suunab sinna.
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

## Otsingumootorid (SEO) ja Search Console

Leht annab otsingumootoritele: igal mängul oma püsiv aadress `/m/<id>/` (pealkiri „Kodu – Külaline | Liiga | 28. nov 19:00 | Koht“,
kirjeldus, schema.org `SportsEvent` JSON-LD), ala- ja liigalehed (`/korvpall/`, `/korvpall/eesti-lati-korvpalliliiga/`) eelseisvate
mängudega, `sitemap.xml` (kõik eelseisvad mängu-, liiga- ja alalehed, uueneb iga ehitusega) ja `robots.txt`, mis viitab sellele.
Möödunud mängu leht jääb alles („Mäng on toimunud“, link sama liiga järgmistele mängudele), aga on `noindex` ja sitemapis pole.

**Mida omanik peab ühekordselt käsitsi tegema** (umbes 10 minutit, kontod on omaniku):
1. Ava [Google Search Console](https://search.google.com/search-console) → „Lisa omand“ → **Domeen** → `elakaasa.ee`.
2. Google annab TXT kirje kujul `google-site-verification=…`. Lisa see Zone.ee halduses domeeni `elakaasa.ee` DNS-kirjetesse
   (tüüp TXT, nimi tühi või `@`, väärtus kogu Google'i antud rida) ja salvesta. Oota paar minutit ja vajuta Search Console'is „Kinnita“.
   - **Alternatiiv ilma DNS-ita:** vali „URL-i prefiks“ `https://elakaasa.ee/` → meetod „HTML-silt“. Kopeeri sildi `content="…"` väärtus
     (ainult token) faili `config.toml` → `[site] google_site_verification = "…"`, merge'i muudatus, oota ehituse avaldamist ja
     vajuta „Kinnita“. Silt pannakse kõigile lehtedele.
3. Search Console'is: **Saidikaardid** → lisa `sitemap.xml` → „Esita“.
4. Valikuline: [Bing Webmaster Tools](https://www.bing.com/webmasters) → „Import from Google Search Console“ (üks klõps).
5. Paari päeva pärast vaata „Lehed“ ja „Tulemuslikkus“: kui palju lehti on indekseeritud ja mis päringutega leitakse.
Ilma selleta indekseerib Google lehe ka ise, aga Search Console näitab, kas ja mis puudu on.

## Spordikaart (`/kaart/`)

Kaart näitab, kus ja millal Eestis mängitakse (ainult kalendris olevad liigad): ringi suurus on mängude arv valitud ajaaknas, värv on koha peamine ala, punktiirringiga on kohad, mille asukoht on ligikaudne. Kaks vaadet: **kindel kuupäev** (3 tunni aken, ka kellaajata üritused; nimekiri kellaaja järgi, iga rida viib mängu lehele) ja **tüüpiline nädal** (nädalapäev × kellaaeg, mängude arv jagatud nädalate arvuga). Ala- ja tasemefilter. Ring ja nimekirja rida tõstavad teineteist esile; ringi klõps kerib nimekirja õige koha juurde.
Mobiilis on kaart kohe päise all ja filtrid kokkuvolditud ribas „Filtrid (N aktiivset)“. Algvaade on Tallinn (või viimati valitud linn); nupp „Kogu Eesti“. **Kogu seis on URL-is** (`?v=…&d=…&t=…&a=…&l=…&c=lat,lon&z=suum`): link taastab sama vaate, brauseri tagasi-nupp liigub eelmisele valikule.
**Halli mõju** statistikat kaardil ei ole. Leht `/analuus/` on praegu „tulekul“ (noindex); uus metoodika (`analuus/halliefekt.py`: meeskonna kodu-% miinus sama meeskonna võõrsil-% samal hooajal) avaldatakse alles pärast omaniku ülevaatust. See ei ole põhjuslik seos.
Tehnika: Leaflet 1.9.4 on repos (`site/vendor/leaflet/`), aluskaart OpenStreetMapi standardplaadid, heledaks CSS-filtriga; **CARTO „light_all" plaadid nõuavad 2026. aastast API võtit** (annavad vesimärgiga „API KEY REQUIRED"), seepärast neid ei kasutata. OSM-i plaadiserver on ühiskasutuses: kui liiklus kasvab, vaheta pakkuja (nt võtmega CARTO või MapTiler) `site/kaart.js`-is.

## Tulevikuideed

- **Uued alad**: kergejõustik, motosport, suusatamine, ratsasport, uisutamine, võitlusspordid ja autosport on lisatud (üritused, mitte mängud). Laskesuusatamise, poksi, maadluse ja autospordi suured võistlused lisatakse käsitsi (`kasitsi.toml`, otsinguagent). Järgmised kandidaadid (tantsusport, ujumine, ragby) koos allikatega on failis [docs/uued-alad.md](docs/uued-alad.md). Omanik otsustab, millal ja millest jätkata.

- **Lehe suuruse optimeerimine** (mõõdetud 2026-11-26, omanik otsustas mitte lõigata): kohalik ehitus on 134 MB ja 4691 faili, sellest 3625 on tasemete päevalehed, mille 58% (2088 lehte, 72 piirkonna ja taseme kombinatsiooni) on täiesti tühjad (30 päeva mänge pole). Neid **ei saa lihtsalt ära lõigata**: kõigile 72-le viitab menüü (nt Tartu tasemel „Koondised“) ja päevanavigatsioon, seega tekiks 404. Kui suurus läheneb 400 MB-le (GitHub Pagesi piir on 1 GB), tuleb enne lõikamist muuta menüü ja päevanavigatsioon (tühi kombinatsioon viitab ühele lehele) ja panna ehituse testi **lingikontroll** (kõik sisemised lingid viivad olemasolevale lehele). Ehituse aeg (8–12 min) on enamasti allikate viisakas ooteaeg; paralleelsed päringud eri hostidele võiksid selle 2–3 minutile viia, aga Actions on tasuta, seega pole vaja.
- **Vehklemine** (omaniku otsus 2026-11-25: hiljem): uus ala `vehklemine` rühmas „Võitlusalad“ koos `voitlusspordid`-iga, üritusala. Liidu kalendri aadress ja robots.txt on kontrollimata; alguses lisab agent võistlused käsitsi.
- **Ülekannete kavad mängudena** (2026-11-25): Delfi kavast lisatakse mängud juba (`[[koduhall]]`, ulekanded.toml). Edasi: Postimehe ja Go3 kavade loetavus (Go3 on lisatud), ERR-i kava (Premium liiga, koondised) sama reegli alla, kui kava annab saali; Eesti meistriliiga meeskondade koduhallid tabelisse (Rapla, Valga, TLÜ jt) ja sama käsipallile ning võrkpallile.
- **Sõudmine, aerutamine, purjetamine**: 2027 kalendrid pole veel avaldatud (soudeliit.ee, aerutaja.ee, puri.ee); kui ilmuvad, lisab agent võistlused käsitsi ja siis tasub vaadata adapterit.
- **Kurling** ✅ (2026-11-26): adapter `kurling_ekl` (kurling.ee, Eesti MV ja MK-etapid Tondiraba jäähallis), Talialade rühmas.
- **Vastupidavusalad, suvealad**: jalgrattasport, triatlon (kergejõustik rühma), ragbi ja rannavõrkpall võistkonnaaladesse: kontrollitud 2026-11-26, 2027 hooaja kalendrid pole avaldatud ja allikad on JavaScriptis või kättesaamatud (vt SOURCES.md → Kurling ja hooajavälised alad). Vaata uuesti kevadel. Hiljem täpsusalad.

- **Päise uus kujundus** (omaniku mõte 2026-11-24, kavand [docs/paise-kavand.webp](docs/paise-kavand.webp)): ülemine riba ümber kujundada. Ülaosas on lipuvärvides triibud ja sinine pildiriba eri alade sportlastega. Selle all on suur „Elan kaasa“ ja kolm valikunuppu (spordiüritustele, kõigil aladel, üle Eesti). Teisel real on Päev/Nädal/Kuu, kuupäev noolte vahel ja nupp „Näita kaardil“. Kinnitatud kavand (2026-11-24): [docs/paise-kavand.html](docs/paise-kavand.html), arvuti- ja mobiilivaade; mobiilis pilt 30% madalam, „Elan kaasa“ kohe lipu all pildi peal, valikunupud ühel real pildi sinises alaosas, kuupäeva nupp ja nooled asenduvad kalendri ikooniga, „Näita kaardil“ peidus kuni kaardivaateni. Taustapilt on olemas: [site/paise.webp](site/paise.webp) (ChatGPT, 2000×667; ülemine kolmandik sportlased, alumine osa tühi sinine teksti ja nuppude jaoks). Kaardivaadet veel pole, see on eraldi arendus (toimumiskohtade koordinaadid on vaja lisada venues.toml-i).
- **„Võtan osa“** (omaniku mõte 2026-11-23, suurarendus): päise lause esimese valiku „Ela kaasa“ kõrvale teine valik „Võtan osa“. Sinna sobivad võistlused, kuhu minnakse osalema, mitte vaatama: murdmaasuusatamise EMV ja maratonid, rahvajooksud, klubide ratsavõistlused, kohalikud kergejõustikuvõistlused. Andmed on juba olemas peidetud tasemel 3 (suusatamine, ratsasport, kergejõustik), nii et alustada saab nendest.

- **Loapalved liitudele** (omaniku plaan 2026-11-20): kui leht on mõnda aega stabiilselt töötanud, kirjutab omanik ja küsib luba ajakava kasutamiseks või avalikku andmevoogu. Claude koostab siis kirjade mustandid.
  - **Eesti Korvpalliliit** (basket.ee, estlatbl.com): robots.txt keelab automaatse kogumise, seetõttu on lehel praegu ainult Bigbank/Kalevi mängud (klubi lehelt, adapter `korvpall_kalev`) ja Tartu Ülikool Maks & Moorits kodumängud (klubi lehelt, adapter `korvpall_ut`). Loa korral: liiga adapter (`scrapers/korvpall_...py`), `config.toml` rida ja test; korvpalli märkuse (`sport_note`) saab siis eemaldada. Taust: SOURCES.md → Korvpall.
  - **Eesti Jäähokiliit** (Unibet Hokiliiga, naiste hokiliiga): ajakava on ehs.eestihoki.ee lehel, aga brauser laadib selle hockeydata.net kommertsteenusest liidu API-võtmega. Praegu on lehel HC Vipersi kodumängud ja HC Everesti mängud (klubide lehtedelt, adapterid `jaahoki_vipers` ja `jaahoki_everest`). Küsida luba (või avalikku voogu / iCal-i), et tohiks seda kasutada. Loa korral: adapter (`scrapers/jaahoki_ehl.py`), `config.toml` rida ja test; `sport_note` jäähoki märkuse saab siis eemaldada. Taust: SOURCES.md → Täiendavate võistluste ülevaade.

- **Ülekanded** (2026-11-23 omaniku soovil, kolmes osas; taust SOURCES.md → Ülekanded):
  1. ✅ Järelvaatamise lingid allikatest (kasipall.ee, jalgpall.ee) ja liiga kaupa „Selle liiga mänge on näidanud“ (`ulekanded.toml` + mängudest õpitu).
  2. ✅ Delfi TV ülekannete kava: tulevastele mängudele „Otse: Delfi TV“ (`scrapers/kava_delfi.py`, seosed `data/ulekanded.json`).
  3. ✅ ERR telekava (ETV, ETV2, 8 päeva; `scrapers/kava_err.py`), ka ürituste alad (suusatamine, ralli …).
  4. ✅ Otsinguagent kontrollib kanaleid, kelle kava automaatselt ei loe (nt Postimees), lisab ülekanded (`[[mang]]`) ja liigadele uusi kanaleid (`[[liiga]]`); automaatne merge kontrollib (uue kanali lisab omanik).
- **Kasutajate tagasiside 2026-11-23** (omanikuga kokku lepitud järjekord):
  1. ✅ Kalender: vaade Päev / Nädal / Kuu, kuupäeva valik kuni 12 kuud ette, pühkimine vasakule-paremale (`site/kalender.js`, andmed `kalender.json` = `build.calendar_data`). Päevalehed jäävad staatiliseks (töötavad ilma JS-ita); nädala, kuu ja 14 päevast kaugemad päevad joonistab JS (aadressis `#kuupäev`).
  2. ✅ Alade rühmad menüüs (`build.SPORT_GROUPS`: võistkonnaalad, talialad, mootorsport; rühm ainult siis, kui tasemel on vähemalt 2 selle ala). Hiljem alaliigid (nt autospordis ralli, kardid, ringrada) kolmanda tasemena.
  3. Uued alad järk-järgult (vaatamist väärt võistlused); osalemisüritused eraldi „võtan osa“ ideena.
     - ✅ Reketialad (2026-11-24): tennis (`tennis_etl`), sulgpall (`sulgpall_esl`), lauatennis käsitsi. Vt SOURCES.md → Reketialad.
     - ✅ Kunstilised alad (2026-11-24): võimlemine, tantsusport, fitness, võistlused lisab otsinguagent käsitsi (allikad pole masinloetavad). Vt SOURCES.md → Kunstilised alad.
     - ✅ Veealad (2026-11-24): ujumine (`ujumine_eul`, swimming.ee), sõudmine, aerutamine (kanuu) ja purjetamine käsitsi (kalendreid pole veel avaldatud). Vt SOURCES.md → Veealad.
     - Järgmised (omanikuga kokku lepitud järjekord): vastupidavusalad (jalgrattasport, triatlon; kergejõustik rühma), suvel ragbi ja rannavõrkpall võistkonnaaladesse, kurling talialadesse, hiljem täpsusalad.
- **Piletid** (omanikuga kokku lepitud 2026-11-20): püsiinfo seadistusfailis (klubi → piletimüüja link), mängu real „Piletid ↗“. Kui allika mängulehel on piletilink juba olemas, võtta see kaasa. Mängupõhist kogumist piletimüüjatelt ei tee (hooldus, tingimused).
- Päevade ribale kuu nimi, kui riba ulatub üle kuu vahetuse.
- **Jalgpalli karikad** (omanikuga kokku lepitud „millalgi tulevikus“): Tipneri karikas, naiste karikas, superkarikas. Vaja on iCal-lugejat (vt SOURCES.md „Täiendavate võistluste ülevaade“).
- Eesti jäähoki liigad (Narva PSK, Tartu Välk 494, Viru Sputnik, naiste liiga teised mängud): vaata uuesti, kas ehis.eestihoki.ee-l on 2026/27 hooaeg. Viru Sputniku ja Välk 494 lehed on JavaScriptis. Narva PSK kodumängud on kuu kaupa PDF-is, neid lisab otsingu agent käsitsi.
- **Madalamad liigad:** esiliigad on tehtud (2026-11-20, `level = 2`), jalgpalli II–IV liiga on kolmas tase „Madalamad liigad“ (2026-11-21, `level = 3`, kaust `/madalamad/…`). Teiste alade madalamad liigad: lisa `competitions` reale `level = 3`. Taust: SOURCES.md → Madalamad liigad.
- **Noored** (`level = 4`, kaust `/noored/…`, 2026-11-21): jalgpalli vanemad klassid, saalijalgpalli U18, käsipalli TU19 ja võrkpalli U-18/U-20. Rohkem noorte liigasid lisa `competitions` reale `level = 4` (käsipalli noorte uued ID-d, kui kasipall.ee need avaldab). Taust: SOURCES.md → Noored.
- **Koondised** (`level = 5`, kaust `/koondised/…`, 2026-11-21): praegu jalgpalli ja saalijalgpalli koondised (adapterid `jalgpall_koondis`, `saalijalgpall_koondis`, ainult Eesti kodumängud). Teiste alade koondised: korvpall, käsipall ja võrkpall puuduvad, vt SOURCES.md → Koondised. `year_round = true` allikal tähendab terve aasta mänge, mis ei räägi liigahooajast.
- Saalijalgpalli esiliigat jalgpall.ee avalikult ei näita. Lisa, kui see ilmub.
