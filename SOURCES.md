# Andmeallikad

Kaardistus tehtud 2026-11-20. robots.txt on kontrollitud iga domeeni puhul samal päeval.
Kasutustingimusi, mis keelaksid automaatse kogumise, ühegi allika lehtedelt ei leitud (vaadatud avalehed, jalused ja olemasolul tingimuste leht).

## Kokkuvõte

| Ala | Liiga | Allikas | Kuju | robots.txt | MVP |
|---|---|---|---|---|---|
| Jalgpall | A. Le Coq Premium liiga | jalgpall.ee | iCal (+ HTML) | lubatud, `Crawl-Delay: 5` | ✅ |
| Korvpall | Bigbank/Kalevi mängud (Eesti-Läti liiga, FIBA Europe Cup) | bckalev.ee (klubi koduleht) | staatiline HTML (SportPressi tabel) | lubatud (`/ajakava/`), crawl-delay'd pole | ✅ (lisatud 2026-11-21, ainult Kalev) |
| Korvpall | Liidu andmed (Eesti-Läti liiga, meistriliiga) | estlatbl.com, basket.ee | HTML | **keelatud** (`User-agent: *` / `Disallow: /`) | ❌ välja jäetud |
| Jäähoki | Optibet Hokiliiga | lhf.lv | staatiline HTML | lubatud | ✅ |
| Võrkpall | Balti liiga, Eesti meistriliiga, karikad (M+N) | bvl-web / evf-web.dataproject.com | staatiline HTML | lubatud | ✅ |
| Käsipall | Meistriliiga (mehed) | kasipall.ee | staatiline HTML | lubatud | ✅ |
| Saalihoki | Meistriliiga + Eesti-Läti ühisliiga | saalihoki.ee | staatiline HTML | lubatud | ✅ (vähe Tallinna mänge) |
| Saalijalgpall | Saalijalgpalli meistriliiga | jalgpall.ee | staatiline HTML | lubatud, `Crawl-Delay: 5` | ✅ (lisatud 2026-11-20) |

MVP-sse sobib 6 ala 7-st (korvpallist ainult Kalev).

---

## Jalgpall: A. Le Coq Premium liiga

- **Ajakava leht:** https://jalgpall.ee/voistlused/52/premium-liiga (kõik mängud: `/voistlused/52/liigad/calendar?season=2026`)
- **iCal:** https://jalgpall.ee/voistlused/download.php?type=calendar.download&action=download&league_id=52 (`text/calendar`, ajavöönd Europe/Tallinn)
- **Kuju:** iCal on eelistatud. HTML-is on kuupäev, kell, võistkonnad ja mängu link (`/voistlused/match_info/<id>`). Toimumiskohta nimekirjas pole, see tuleb kas iCal-i LOCATION väljalt (kontrollida, kui hooaeg algab) või mängu lehelt.
- **robots.txt:** `/voistlused/` pole keelatud. Keelatud on `/otsing`, `/errors/`, `/ejl/staadionid/loaders`. `Crawl-Delay: 5` → päringute vahel vähemalt 5 s.
- **Hooaeg:** märts–november. 2026. a hooaeg lõppes 07.11.2026. 2027. a algus pole veel teada (eeldatavalt märtsi algus).
- **Tallinna klubid 2026:** FCI Levadia, FC Flora, Nõmme Kalju, Nõmme United.
- **Eripärad:** praegu (hooajaväline aeg) on iCal tühi.
- **Teostus (2026-11-20):** adapter kasutab iCal-i asemel HTML-kalendrit `/voistlused/52/liigad/calendar?season=<aasta>`, sest seal on ka staadion (`data-field`) ja terve hooaeg ühe päringuga.

## Korvpall

### Liit (basket.ee, estlatbl.com) ❌

- **Lehed:** https://www.estlatbl.com/et/mangud, https://www.basket.ee/et/ajakava-ja-tulemused?action=schedule
- **robots.txt:** mõlemal domeenil `User-agent: *` / `Disallow: /`. Lubatud on ainult Googlebot, Bingbot ja Applebot. Lisaks näitab estlatbl.com robotitele turvakontrolli lehte.
- **Otsus:** liidu ja estlatbl.com lehti ei kogu. Ainus seaduslik tee oleks liidu luba või avalik voog. Seda praegu pole.
- **Plaan:** kui leht on stabiilselt töötanud, küsib omanik Korvpalliliidult luba või avalikku andmevoogu (vt README „Tulevikuideed“). Kuni loa saamiseni liidu lehtedelt midagi ei koguta. Lehe korvpalli märkus viitab endiselt basket.ee ajakavale (https://www.basket.ee/et/ajakava-ja-tulemused?action=schedule), sinna päringuid ei tehta.
- Korvpalli Meistriliiga ja naiste liiga on samal basket.ee domeenil, seega samuti välja.
- **TalTech/ALEXELA:** TalTechi enda lehel ajakava pole, see viitab estlatbl.com lehele, seega TalTechi kodumänge siia ei saa (v.a mängud Kalevi vastu, mis on Kalevi lehel).

### Bigbank/Kalev: klubi koduleht ✅ (lisatud 2026-11-21)

- **Leht:** https://bckalev.ee/ajakava/ (WordPress + SportPress). Adapter `korvpall_kalev`.
- **robots.txt (kontrollitud 2026-11-21):** `User-agent: *`. Keelatud on `/wp-admin/` (v.a `admin-ajax.php`), WooCommerce'i logid ja üleslaadimised, `?add-to-cart=` ning `?kategooria=` ja `?srch=` parameetrid. `/ajakava/` pole keelatud. Crawl-delay'd pole, kasutame viisakat 5 s (`config.toml` → `http.host_delays`), päring tehakse üks päevas.
- **Kuju:** tabel veergudega Kuupäev / Meeskonnad / Liiga / Väljak. Kõik mängud on ühes HTML-is (lehekülgedeks jagab brauser, `data-sp-rows="10"`), seega piisab ühest päringust. Masinloetav aeg on `<td class="data-date" content="2026-11-21T19:00+02:00">`, mängu link samas lahtris.
- **Hooaeg:** 2026/27, nähtavad mängud kuni märtsini 2027. Seadistuses 15.09–15.06.
- **„A vs B“ järjekord on kodu vs võõrsil.** Kontrollitud: Keila KK vs Kalev (Keila Tervisekeskus), BC Pärnu vs Kalev (Pärnu Spordihoone), Taltech/Alexela vs Kalev (TalTech Spordihoone), Valmiera Glass VIA vs Kalev (Valmieras Olimpiskais Centrs). Kalevi kodumängud on kirjas „Bigbank/Kalev vs …“.
- **Saal puudub**, kui väli on tühi või „Asukoht selgumisel“. Neid mänge lehel ei näidata, lähipäevade (15 päeva) puhul tuleb „Mängud ilma toimumiskohata“ issue.
- **Välismaa mängud** jäävad geo-filtriga välja (Kosovo, Valmieras Olimpiskais Centrs, Riga Arena, KSSH, `config.toml` → `geo.foreign`).
- **Saalid (venues.toml):** Kalevi spordihall, Unibet Arena (= Saku Suurhall), TalTechi spordihall (alias „TalTech Spordihoone“), uued: **Nord Spordihoone** (Tallinn), Keila Tervisekeskus (Keila), Pärnu Spordihoone (Pärnu). Kontrollimata: Nord Spordihoone asukoht (arvatud Tallinn, Kalevi kodumängude saal), „Pärnu Spordihoone“ ja olemasolev „Pärnu Spordihall“ võivad olla sama hoone, ja KSSH asukoht (arvatud Riia).
- **Eripärad:** ainult Kalevi mängud. Eesti-Läti liigas on ka teisi mänge, neid siit ei saa. FIBA Europe Cup on `check = false` (pikad pausid). Võistluse nimi tuleb tabeli veerust.
- **Fixture:** `tests/fixtures/korvpall_kalev.html` on lehe lähtekoodist (2026-11-21) lühendatud tabel, logopildid on välja jäetud.

### Teised klubid

- **Viimsi (kkviimsi.ee/?id=1005), kontrollitud 2026-11-21: adapterit ei tee.**
  - **robots.txt:** `User-agent: *`, keelatud ainult `/cache/noindex/`, **`Crawl-delay: 15`**. Kogumine on lubatud, päringute vahel peaks olema vähemalt 15 s.
  - **Ajakava:** leht „Kalender“ (`?id=1005`) on lähtekoodis **tühi** (sisutabel `class="content"` ilma ridadeta) ja külgriba „Mängukalender“ on samuti tühi. Mänge ei saa lugeda. Mängud on vaid uudistes (nt „ATEA kutsub: Viimsi vs BK Liepaja“, 16.11.2026), mis pole masinloetav ajakava.
  - **Järeldus:** jätta vahele. Kui kalender hiljem täitub, vaata uuesti, ja siis lisa `config.toml` `http.host_delays` alla `"kkviimsi.ee" = 15.0`. Viimsi mängud Kalevi vastu tulevad ka Kalevi lehelt.
  - Kontrollitud käsitsi kopeeritud lähtekoodist, sest seansi võrk oli selle saidi jaoks blokeeritud.
- **Pärnu (bcparnu.ee):** veel kontrollimata.
- **Tartu Ülikool Maks & Moorits (basket.ut.ee) ✅ (lisatud 2026-11-21).** Adapter `korvpall_ut`.
  - **Leht:** https://basket.ut.ee/kalender-26-27/ (WordPress, TablePress). Serveris renderdatud HTML, iga kuu oma tabel (AEG / LIIGA / KODU / KÜLALINE / KOHT / TULEMUS). Andmeid ei laeta basket.ee-st, tulemuste lingid viivad ainult estlatbl.com'i, fiba.basketball'i ja Geniuse lehtedele, neid ei kasutata.
  - **robots.txt (kontrollitud 2026-11-21):** `User-agent: *`, keelatud ainult `/wp-admin/` (`admin-ajax.php` lubatud). Crawl-delay'd pole, kasutame viisakat 5 s (`config.toml` → `http.host_delays`), päring tehakse üks päevas.
  - **Aeg:** kirjutatud eri viisil (`19:00`, `19.00`, `16,00`), võõrsil mängudel sageli puudub. Mitmepäevased read (eelhooaja turniirid, Eesti karikas 15.–20.02.2027) jäetakse välja.
  - **Ainult kodumängud (KODU = „TÜ MM“, KOHT = „TÜ sph“).** Võõrsil mängude KOHT on ainult linn („Keila“, „Riia“, „Tallinn“), mida ei saa saaliga siduda. Eestis võõrsil mängud (Keila, Pärnu, Viimsi, TalTech) jäävad seega puudu, v.a mängud Kalevi vastu (Kalevi leht). Saali alias „TÜ sph“ → Tartu Ülikooli spordihoone (`venues.toml`).
  - **Nimi:** „TÜ MM“ → „Tartu Ülikool Maks&Moorits“ (sama kirjapilt mis Kalevi lehel, et `dedupe` mäng Kalevi vastu kokku viiks).
  - **Liigad:** EST-LAT → Eesti-Läti Korvpalliliiga, FEC → FIBA Europe Cup (`check = false`), PRESEASON GAME → Eelhooaja mäng.
  - **Hooaeg:** lehe URL sisaldab hooaega (`kalender-26-27`), uuel hooajal tuleb `URL` adapteris üle vaadata.
  - **Fixture:** `tests/fixtures/korvpall_ut.html` on lehe mängutabelid (2026-11-21).

## Jäähoki: Optibet Hokiliiga

- **Ajakava leht:** https://www.lhf.lv/en/tournaments-list/optibet-hockey-league (ka https://www.lhf.lv/en/tournaments/optibet-hokeja-liga/schedule)
- **Kuju:** serveris renderdatud HTML: kuupäev, kell, võistkonnad, koht ja mängu link (`/en/tournaments/optibet-hokeja-liga/2026-2027/1245/schedule/hcp-kyc/20261121/35876`). JSON-it ega iCal-i ei leitud.
- **robots.txt:** `User-agent: *`, ühtegi keeldu pole.
- **Hooaeg:** algas 05.09.2026, lõpp pole lehel kirjas (eeldatavalt märts–aprill 2027 koos playoffidega).
- **Tallinna klubi:** HC Panter (kodusaal Haabersti jäähall).
- **Eripärad:** liiga on Läti liidu hallata (Eesti Jäähokiliidu oma süsteem ehis.eestihoki.ee lõpeb hooajaga 2024/25). Tallinna kodumängude koht on kirjas ainult kui „Tallina, Igaunija“. Selle jaoks tuleb `venues.yaml`-isse alias „Tallina, Igaunija“ → Haabersti jäähall.

## Jäähoki: Unibet Hokiliiga, HC Vipersi kodumängud ✅ (lisatud 2026-11-22)

- **Leht:** https://hcvipers.ee/?page=games&lang=et. Adapter `jaahoki_vipers`.
- **Kuju:** serveris renderdatud HTML. Iga mäng on kahes vaates: nimekirjas (`<article class="gc10-game-row">`) ja kalendriruudus (`gc10-tile`). Adapter loeb ainult nimekirja. Rea atribuutides on võistkond (`data-team="unibet"`), kuupäev (`data-date`) ja pealkiri „Kodu — Võõras“. Kellaaeg, koht ja Eesti Hoki Statistika mängulehe link on rea sees.
- **robots.txt:** puudub (404). Päring tehakse üks päevas. Liidu hockeydata.net API-võtit ei kasutata: klubi avaldab ajakava oma lehel tavalise HTML-ina.
- **Ainult kodumängud.** Koha väli on igal mängul „Tondiraba Jäähall“, ka võõrsil mängudel (nt Viru Sputnik – HC Vipers). Seetõttu võtab adapter ainult read, kus HC Vipers on esimesena (kodumeeskond). Vipersi kodusaal on Tondiraba jäähall. 2026/27 hooajal on lehel 6 tulevast kodumängu.
- **Nimi:** „HC Vipers Unibet“ → „HC Vipers“, sest liiga nimes on sponsor juba olemas.
- **Ainult tulevased mängud.** Möödunud mängud tulevad arhiivist (`archive/`), tulemusi lehel pole.
- **Välja jäetud:** noorte võistkonnad (U19 kuni U8), sest nende kodumängud võivad olla ka teistes jäähallides. Unibet Hokiliiga teiste klubide omavahelised mängud: HC Everesti omad tulevad Everesti lehelt (vt allpool), Viru Sputniku ja Välk 494 lehed on JavaScriptis.

## Jäähoki: HC Everest (Unibet Hokiliiga, naiste hokiliiga, noored) ✅ (lisatud 2026-11-22)

- **Leht:** https://hceverest.ee/ (avaleht). Adapter `jaahoki_everest`.
- **Kuju:** serveris renderdatud HTML (Bootstrap kaardid). Igal kaardil on päis liigaga (`UNIBET HOKILIIGA`, `NAISTE HOKILIIGA`, `Noored U19` …), aeg `DD.MM.YYYY HH:MM`, koht ja „Kodu - Võõras“. Lehel on ainult tulevased mängud, tulemusi pole.
- **robots.txt:** `User-agent: *` / `Disallow:` (tühi), kõik lubatud. Päring tehakse üks päevas.
- **Koht on õige** igal mängul, ka võõrsil (Narva jäähall, Tartu Astri Arena, Haabersti, Tondiraba). Seetõttu võtab adapter nii kodu- kui ka võõrsil mängud. Näiteks 16.01.2027 Everest–Vipers on Vipersi lehel kirjas Tondirabas, Everesti lehel õigesti Kohtla-Järve jäähallis.
- **Liigad:** Unibet Hokiliiga ja naiste hokiliiga (`level = 1`), U19 ja U16 (`level = 4`, nimed „U19 noorteliiga“, „U16 noorteliiga“). U12, U10 ja U8 on lastevõistlused ja jäävad välja. Kuupäevata kaardid („TBD 14:30“) jäetakse vahele.
- **Saalid** (`venues.toml`): uued on Kohtla-Järve jäähall, Narva jäähall ja Astri Arena (Tartu Lõunakeskuse jäähall). „Haabersti jäähall, A hall“ ja „Tondiraba jäähall, Hall 1“ on põhiväljakute aliased. B hall ja Hall 2 lisa eraldi saaliks, kui need ilmuvad, sest muidu võib `dedupe` ühe samaaegse mängu ära visata.
- **Topelt:** Vipersi kodumängud Everesti vastu tulevad mõlemalt lehelt. Vipersi allikas on `config.toml`-is eespool ja jääb alles.
- **ID:** noortel võib samal päeval olla kaks mängu samade võistkondade vahel (04.04.2027 U16). Siis lisatakse teise mängu ID-sse kellaaeg.
- **Fixture:** `tests/fixtures/jaahoki_everest.html` (terve avaleht, 2026-11-22).

## Jäähoki: Narva PSK, adapterit ei tee (kontrollitud 2026-11-22)

- **Leht:** Narva PSK on Narva Paemurru Spordikool (https://uus.npsk.ee/, WordPress, robots.txt keelab ainult `/wp-admin/`). Eraldi hokiklubi lehte pole.
- **Mängukava:** kalendri lehel (https://uus.npsk.ee/kalender) on iga kuu ürituste kalenderplaan PDF-ina. Seal on kõigi alade üritused, sh Narva kodumängud Narva jäähallis (Juuli 4) koos kellaajaga. Detsembris 2026 on üks Unibet Hokiliiga kodumäng (06.12 Narva PSK – HC Everest, tuleb ka Everesti lehelt), sõprusmäng 19.12 ja U13 turniir.
- **Järeldus:** automaatseks allikaks ei sobi. Põhjused: fail on PDF, aadress muutub igal kuul (`/wp-content/uploads/<üleslaadimise kuu>/<kuu>-<aasta>.pdf`) ja ette on näha ainult üks kuu. Otsingu agent loeb PDF-i (`allikad.toml`) ja lisab Narva kodumängud `kasitsi.toml`-i.
- **Kontroll:** hooaeg on `config.toml`-is 01.10–15.02, sest playoffide ajakava selgub hiljem ja siis ei tohi 0 mängu viga anda.
- **Fixture:** `tests/fixtures/jaahoki_vipers.html` (terve leht, 2026-11-22).

## Võrkpall: Elme Messer Balti liiga

- **Ajakava leht:** mehed https://bvl-web.dataproject.com/CompetitionMatches.aspx?ID=29&PID=30, naised https://bvl-web.dataproject.com/CompetitionMatches.aspx?ID=31&PID=32
- **Kuju:** serveris renderdatud HTML: kuupäev, kell, saal, võistkonnad ja mängu link (`MatchStatistics.aspx?mID=...`).
- **robots.txt:** `User-Agent: *` / `Disallow:` (tühi), kõik lubatud.
- **Hooaeg:** mehed alates 14.11.2026, nähtav kuni 06.02.2027, playoffid määramata.
- **Tallinna klubid:** Audentes/Solarstone (Audentese spordihall), Selver x TalTech (TalTechi spordihall).
- **Eripärad:** Eesti meistriliiga (playoffid) on volley.ee järgi samuti DataProjecti süsteemis (`evf-web.dataproject.com`).
- **Laiendus (omaniku otsus 2026-11-20):** algul võeti ainult meeste Balti liiga ja Tallinna mänge oli seetõttu vähe. Nüüd loeb adapter `vorkpall_dataproject` kõiki täiskasvanute tippvõistlusi, mis on loetletud `config.toml`-is (`competitions`):
  - Balti liiga, mehed `bvl-web` ID=29/PID=30 ja naised ID=31/PID=32
  - Eesti meistriliiga, mehed `evf-web` ID=96 (playoffid kevadel, praegu mänge pole) ja naised ID=97/PID=147
  - Eesti karikas, mehed `evf-web` ID=100/PID=150 ja naised ID=99/PID=149
  - `evf-web.dataproject.com/robots.txt`: `User-Agent: *` / `Disallow:` (tühi), kõik lubatud.
  - Tallinna saalid: Audentese spordihall, TalTechi spordihall, Tallinna Ülikooli spordihoone.
  - **Hooldus:** DataProjecti ID-d muutuvad igal hooajal. Augustis vaata üle `MainHome.aspx` mõlemal hostil.

## Käsipall: Meistriliiga (mehed)

- **Ajakava leht:** https://kasipall.ee/league/359 (kõik liigad: https://kasipall.ee/calendar/season/2027, päevavaade `https://kasipall.ee/calendar/YYYY-MM-DD`)
- **Kuju:** staatiline HTML: kuupäev, kell, võistkonnad ja mängu link (`/protocol/NNNN`). **Saali nimekirjas pole**, see on mängu lehel (`location_on` → nt „Viimsi kooli Spordikeskus“, link `/field/54`).
- **robots.txt:** `User-agent: *` / `Disallow:` (tühi), kõik lubatud. handball.ee-l robots.txt puudub (404).
- **Hooaeg:** 2026/27 (URL-ides `2027`). Nähtavad mängud kuni 01.01.2027, edasi „etapi mängud selgumisel“.
- **Tallinna klubi:** Tallinna Mistra. (HC Viimsi/Alexela on Viimsis, mitte Tallinnas.)
- **Eripärad:** Balti liiga ametlikku lehte ei leitud, osa Mistra mänge võib seega puududa.
- **Teostus (2026-11-20):** liiga leht näitab ka mitu nädalat ette (1 päring). Saali jaoks avatakse protokolli leht ainult järgmise 15 päeva mängude kohta (tavaliselt 4–8 päringut). Mistra kodusaal: Kalevi spordihall.

## Saalihoki: Meistriliiga + Eesti-Läti ühisliiga

- **Ajakava leht:** https://saalihoki.ee/Ajakavad.aspx (suunab aadressile https://www.saalihoki.ee/Events/Uritused.aspx; mängu lingid on kujul `https://www.saalihoki.ee/Events/Uritus.aspx?id=N`) (kõik tulevased mängud, filtrid liiga järgi). Liigad: Meistriliiga `Liigad/Liiga.aspx?id=9`, EST-LAT mehed `id=136`.
- **Kuju:** staatiline ASP.NET HTML-tabel: aeg, mäng koos lingiga (`Uritus.aspx?id=NNNN`) ja koht.
- **robots.txt:** keelatud ainult tehnilised kaustad (`/Bootstrap/`, `/handlers/`, `/Scripts/`, `*.axd` jm). Ajakavad ja liigade lehed on lubatud. floorball.ee suunab saalihoki.ee-le.
- **Hooaeg:** 2026/27. Ühisliiga alates 21.11.2026, meistriliiga esimene mäng 22.11.2026. Lõpp pole kirjas.
- **Tallinna klubid:** tõenäoliselt Sparta Team Automaailm (kontrollimata). Teised meistriliiga klubid on Tartust, Jõgevalt ja Märjamaalt.
- **Eripärad:** Tallinna mänge on hooaja jooksul vähe. Kuna adapter on lihtne, võtame ala sisse ja `venues.toml` filtreerib Tallinna saalid välja.
- **Teostus (2026-11-20):** meeste klubid (Sparta jt) mängivad kodumänge Märjamaal ja Ääsmäel, mitte Tallinnas. Seepärast on kaasas ka **naiste Eesti-Läti liiga** (lähteülesandes „teine samm“, sama allikas ja adapter): Sparta naiskond mängib Õismäe sportmängude hallis. Muud liigad (noored, M35+, Energialiiga) on välja jäetud.

---

## Täiendavate võistluste ülevaade 2026-11-20

Omaniku palvel vaadati üle kõigi alade täiskasvanute tippvõistlused.

**Lisatud:**
- Jalgpall: **naiste meistriliiga** (jalgpall.ee id 63, sama kalendrileht). Tallinnas Sportland Arena ja Lilleküla harjutusväljak I, umbes 12 mängu hooajas. Adapter on nüüd `jalgpall_ejl`, liigad on `config.toml`-is.
- Käsipall: **naiste meistriliiga** (kasipall.ee id 361; Mella, Kristiine spordihall) ja **meeste Eesti karikas** (id 362; Mistra, Mustamäe KK). Adapter on nüüd `kasipall_liigad`, võistlused on `config.toml`-is. Võistkondade nimede lõpust eemaldatakse " N" ja " K".

**Hiljem (vajab uut koodi):**
- Jalgpalli karikad: Tipneri karikas (id 137), naiste karikas (id 138), superkarikas (id 136). Kalendrilehte pole, on ainult iCal `download.php?type=calendar.download&action=download&league_id=<id>`. Mänge on peamiselt kevadel (veerandfinaalid aprillis).
- ~~Saalijalgpall~~ → lisatud uue alana (vt allpool).

## Saalijalgpall: meistriliiga (lisatud 2026-11-20 omaniku soovil)

- **Ajakava leht:** https://jalgpall.ee/voistlused/125/liigad/calendar?season=2026. Sama süsteem ja HTML mis jalgpallil (adapter `saalijalgpall_ejl` kasutab `jalgpall_ejl` parserit).
- **Eripärad:** `season` on hooaja **alguse** aasta (2026 = 2026/27, oktoober–märts). Võistkondade nimede ees on "S. ", see eemaldatakse. Playoffid (id 187) lisa `competitions` alla, kui need on avaldatud.
- **robots.txt:** sama mis jalgpall.ee (lubatud, `Crawl-Delay: 5`).
- **Tallinna klubi:** Tallinna FC Bunker Partner (Sõle spordikeskus), umbes 6 kodumängu põhiturniiril.

**Ei kasutata:**
- **Eesti jäähoki liigad** (Unibet Hokiliiga: Tallinna HC Vipers; naiste hokiliiga: Roosa Panter, Grizzlyz, Wolferines). Ajakava on ehs.eestihoki.ee-l, aga see laaditakse JavaScriptiga kommertsteenusest **hockeydata.net**, kasutades liidu enda API-võtit. Meie skriptil pole õigust seda võtit kasutada (lähteülesanne: küsitavad allikad jäta vahele). ehis.eestihoki.ee (serveri HTML, robots lubab) lõpeb hooajaga 2024/25. **Vaata uuesti**, kui ehis-is ilmub 2026/27 hooaeg.
  - **Plaan (omaniku otsus 2026-11-20):** kui leht on stabiilselt töötanud, küsib omanik koos Korvpalliliiduga ka Jäähokiliidult luba (vt README „Tulevikuideed“). Kuni loani API-võtit ei kasutata. Lehel on jäähoki filtri juures märkus.
  - **2026-11-22:** HC Vipersi kodumängud ning kõik HC Everesti mängud (Unibet Hokiliiga, naiste hokiliiga, U19, U16) tulevad nüüd klubide lehtedelt. Puudu on Narva PSK, Tartu Välk 494 ja Viru Sputniku omavahelised mängud, Vipersi võõrsil mängud (v.a Everesti vastu) ja naiste liiga mängud, kus Everest ei mängi.
- ~~Käsipalli Balti liiga~~ → leitud ja lisatud (omanik leidis baltichandball.eu), vt allpool.
- Naiste käsipallikarikas (id 363): 2026/27 mänge pole veel avaldatud. Lisa `competitions` alla, kui need ilmuvad.
- Saalihoki: naiste kodumaist liigat ega täiskasvanute karikat pole.
- Jäähoki: täiskasvanute karikat 2026/27 pole.

## Käsipall: Balti liiga ja naiste Eesti-Läti liiga (lisatud 2026-11-20)

- **Allikas:** https://baltichandball.eu/season/206/league/636/fixtures (mehed) ja `/season/206/league/637/fixtures` (naised). Omanik leidis selle.
- **robots.txt:** puudub (404), seega piiranguid pole. Kasutustingimusi lehelt ei leitud (on ainult privaatsuspoliitika).
- **Kuju:** serveri HTML. Kuu ja päeva päised, iga mängu juures võistkonnad, „HH:MM · Saal“ ja mängu link. Üks päring liiga kohta.
- **Eripärad:**
  - Tallinna Mistra Balti liiga kodumängud on **Raasiku spordihoones** (Harjumaa), mitte Kalevi spordihallis.
  - Naiste liigas on Tallinnast Mella (Kristiine spordihall).
  - Eesti klubide omavahelised Balti liiga mängud on ka kasipall.ee-s. `build.py` eemaldab topelt mängud: sama aeg ja kas samad võistkonnad või sama saal (võistkonnanimed erinevad, nt „KPK Mella“ / „Käsipalliklubi Mella“). Alles jääb kasipall.ee versioon.
  - Hooaja ja liiga ID-d (`season`, `id`) muutuvad igal hooajal.
- Adapter: `kasipall_bhl`.

## Esiliigad (eraldi kalender, lisatud 2026-11-20)

Omaniku valik: iga ala teine tase (mehed ja naised), samades süsteemides mis kõrgliigad. Seadistuses `level = 2`:

| Ala | Võistlus | ID |
|---|---|---|
| Jalgpall | Esiliiga, Esiliiga B, naiste esiliiga | jalgpall.ee 53, 186, 64 |
| Käsipall | Meeste esiliiga | kasipall.ee 360 |
| Võrkpall | Meeste ja naiste esiliiga | evf-web ID=98/PID=148, ID=106/PID=164 |
| Saalihoki | Energialiiga | saalihoki.ee eesliide „Energialiiga“ |
| Saalijalgpall | – (esiliigat jalgpall.ee-st ei leitud) | |

Lisapäringuid on umbes 6 päevas (pluss käsipalli protokollid). Lisandus ~38 uut saali/väljakut, sh NET Spordihall (Tartu, omaniku kinnitus).

## Madalamad liigad (eraldi kalender „Madalamad liigad“, `level = 3`, lisatud 2026-11-21)

Omaniku valik: madalamad liigad on esiliigadest eraldi tase (`/madalamad/…`), et tugevad liigad ei sulaks kokku väikeste liigadega.

| Ala | Liigad | Allikas |
|---|---|---|
| Jalgpall | II liiga, II liiga B (Põhi/Lääne ja Lõuna/Ida), III liiga (Põhi/Lääs, Põhi/Ida, Lõuna/Ida), IV liiga (Põhi/Ida, Põhi/Lääs) | jalgpall.ee 536, 537, 538, 549, 548, 550, 267, 268 |

- **Allikas:** sama adapter ja sama kalendrileht mis kõrgliigadel (`/voistlused/<id>/liigad/calendar?season=<aasta>`), seega koodimuudatust adapterisse ei vaja. robots.txt: `User-agent: *` keelab ainult `/errors/`, otsingu ja staadionite loaderid, `/voistlused/` on lubatud, Crawl-Delay 5 (juba `host_delays` all).
- **Kontrollitud 2026-11-21:** kõik 8 liigat andsid 2026. aasta mänge (kokku 1056, märts–november), kõik saalid läbivad Eesti filtri.
- **Hooaeg 2026 on lõppenud** (viimane mäng 07.11), uued mängud tulevad märtsist 2027. Seetõttu pole lehel enne seda madalamaid mänge näha.
- **Liiga ID-d ja nimed:** ID-d on püsivad, aga alamlehe nimekirjas on ka „võitja“ ja ülemineku turniirid (281, 559, 180, 181, 560), mida ei kogu. Piirkondade jaotus võib hooajaga muutuda, siis märgib `check` (hooaja sees 42 päeva 0 mängu) probleemi.
- **Uued saalid (43, `venues.toml`):** linn on tuletatud saali nimest või kodumeeskonnast (jalgpall.ee staadionite nimekiri ei ole serveris renderdatud). Kontrollimata: **Oru Põhikooli staadion** (FC Kose kodu, arvatud Kose), **Kotka staadion** (Tallinna meeskonnad, arvatud Tallinn), **Soe keskasula staadion** (Tõrva JK, arvatud Tõrva), **Rõuge** ja **Vastseliina** (märgitud „Võru vald“). Kui linn on vale, paranda `venues.toml`.
- **Jäetud välja:** noorteliigad (vt allpool, tehakse eraldi), naiste madalamad liigad, saalijalgpalli madalamad liigad.

## Noored (eraldi kalender „Noored“, `level = 4`, lisatud 2026-11-21)

Omaniku valik: noorteliigad on oma tase (`/noored/…`) ja kõik alad koos. Võetud on vanemad klassid, kus on tavalised kodu/võõra mängud. Mängitud turniirivormis ja U9–U13 jäävad välja.

| Ala | Liigad | Allikas |
|---|---|---|
| Jalgpall | U19 eliitliiga (esiliiga) ja finaalturniir, U17 eliitliiga (esiliiga, II liiga), U16, U15 ja U14 esiliiga | jalgpall.ee 89, 408, 239, 240, 222, 227, 231 |
| Saalijalgpall | U18 saalijalgpalli eliitliiga | jalgpall.ee 495 (hooaja algusaasta 2026) |
| Käsipall | TU19 meistrivõistlused | kasipall.ee 374 |
| Võrkpall | U-18 ja U-20 neiud ja noormehed (EMV) | evf-web ID=102/PID=152, 103/155, 105/161, 104/158 |

- **Allikad:** samad adapterid ja robots.txt-id mis vastava ala kõrgliigadel, uusi adaptereid pole. Kontrollitud 2026-11-21.
- **Jalgpall:** U19 eliitliiga talveliigad (Meistriliiga A/B, ID 406, 407, jaan–märts) on välja jäetud, sest `season` parameeter sellele ei pruugi talve üle toimida. Muud noorte liigad (U17 III liiga 376, U16 II 224, U15 II 388, U14 II 520 jne) on olemas, aga jäetud välja, et lehte mitte risustada. Lisa `config.toml`-i `level = 4` reaga. Kodu/võõra mängudeta turniiriklassid (U9–U13) ei sobi.
- **Saalijalgpall:** U18 liigas on 21 tulevast mängu (22.11.2026–21.02.2027), seega see on kohe lehel.
- **Käsipall:** 2026/27 hooajal on mänge ainult TU19 meistrivõistlustel (6 mängu, jaan–aprill 2027). Teised noorte liigad (PU19 381, PU18 389, PU17 382, TU17 375, TU16 376, PU16 383 jt) on kasipall.ee-s veel vana hooaja ID-de all, uued ID-d lisa siia, kui need ilmuvad. Saalide nimed saame alles protokollidest (lähipäevade mängud), seega võib jaanuaris tulla „tundmatu toimumiskoht“.
- **Võrkpall:** etapid on turniiriformaadis (3-päevane nädalavahetus). Seni on lehel ainult esimene etapp (okt/nov), järgmised lisanduvad hooaja jooksul, seetõttu `check = false`.
- **Korvpall:** noorteliigad on Korvpalliliidu lehtedel, mis robotid keelavad, seega ei ole.
- **Saalihoki:** noorte liigasid ei leitud. **Jäähoki:** noorteliigad pole avalikult kättesaadavad.
- **Uued saalid (11):** Bauroc Rakvere Jalgpallihall, EJL jalgpallihall (arvatud Tallinn), Karksi-Nuia Gümnaasiumi staadion (Mulgi vald), Narva Spordikeskuse spordiväljak, Pärnu Rannastaadioni harjutusväljak, Tartu Tamme kunstmuruväljak, Viljandi kunstmuruväljak, Sillamäe Spordikompleks, Valga Spordihoone, Jüri Pallihall väike saal (Rae vald), Rakvere SH. „Lähte Spordihall“ on olemasoleva „Lähte spordihoone“ alias. Kontrollimata: EJL jalgpallihall asukoht.

## Koondised (eraldi kalender „Koondised“, `level = 5`, lisatud 2026-11-21)

Omaniku valik: koondised on oma tase (`/koondised/…`). Praegu on olemas ainult jalgpalli koondised.

| Ala | Koondised | Allikas |
|---|---|---|
| Jalgpall | Mehed, U21, U19, U18, U17, U16, U15, naised, NU19, NU17, NU15 | jalgpall.ee/koondis/1, 2, 3, 4, 5, 6, 16, 7, 8, 10, 9 (adapter `jalgpall_koondis`) |
| Saalijalgpall | Meeste koondis, U19 koondis | jalgpall.ee/koondis/14, 18 (adapter `saalijalgpall_koondis`) |

- **Leht:** `https://jalgpall.ee/koondis/<id>/mangud`, serveris renderdatud. Kaks loendit: `national-upcoming-matches` (tulevased) ja `national-previous-matches`. Sama sait ja robots.txt mis kõrgliigadel (`/koondis/` on lubatud, Crawl-Delay 5, juba `host_delays` all). Kontrollitud 2026-11-21.
- **Ainult Eesti kodumängud:** võtame mängud, kus esimene võistkond on „Eesti …“, ja jätame välja väljakud, mille nimes on koma („Saal, Ungari“: NU19 turniirid välismaal, kus Eesti on formaalselt kodumeeskond). Eesti saalidel koma pole. Lisandub geo-filter. Neutraalse kodu/võõra järjekorraga Eestis peetavad mängud (nt Balti turniir, kui Eesti on kirjas teisena) võivad puududa.
- **Kellaaeg:** `00:00` loetakse „kell pole teada“ (`time_tbc`).
- **Tulevaste mängude arv:** naiste koondise lehel oli 4 tulevast ja 4 mängitud mängu, lehel on nupp „Näita järgnevaid mänge“ ja `data-total="8"`. Ma ei tea, kas kaugemad mängud on peidus (nupp tundub näitavat ainult olemasolevat loendit). Kui mänge hiljem puudu on, kontrolli seda.
- **Hooaeg:** terve aasta (`year_round = true`), `check = false`, sest mänge on vähe ja need lisanduvad ajakavasse hilja. `year_round` jätab koondised välja jalgpalli liigahooaja märkusest („Jalgpalli hooaeg algab märtsis“).
- **Hetkel tulevasi mänge** (2026-11-21): naiste koondis–(selgub) 01.12 Paide jalgpallihallis ja meeste saalijalgpalli koondis–Slovakkia 09.12 Jõhvi Spordihallis. Meeste A-koondisel järgmisi kodumänge lehel veel pole.
- **Jäetud välja:** rannajalgpall (id 15, lehel pole sellist ala), NU23 (id 560, mänge pole).
- **Teised alad, mida EI ole:**
  - **Korvpall:** koondised on Korvpalliliidu lehtedel, mis robotid keelavad.
  - **Käsipall:** kasipall.ee koondiste leht on JavaScriptil põhinev, serveris renderdatud ajakava ei leidnud.
  - **Võrkpall:** volley.ee kalender ja koondiste lehed ei andnud serveris renderdatud ajakava (robots.txt lubab). Vaata uuesti, kui klubi/liit selle avaldab.
  - **Hoki:** koondised on Jäähokiliidu lehtedel, vt „Täiendavate võistluste ülevaade“.
- **Uued saalid:** Rakvere Spordikeskus (venues.toml). Paide jalgpallihall, Pärnu Rannastaadion, Jõhvi Spordihall, A. Le Coq Arena, Tehvandi staadion olid juba olemas.

## Tulemused saalihokis ja Balti käsipalliliigas (lisatud 2026-11-22)

Mõlema allika ajakava leht näitab ainult tulevasi mänge, tulemused on eraldi lehel. Kontrollitud 2026-11-22.

- **saalihoki.ee:** https://www.saalihoki.ee/Events/Loppenud-mangud.aspx, kogu hooaja lõppenud mängud (võistlus, „Kodu vs Külalised“, tulemus, aeg, koht, link protokollile). robots.txt keelab ainult tehnilised kaustad (`/Bootstrap/`, `/handlers/` jt), seda lehte mitte. Võistluse nimed on teised kui ajakavas („EST-LAT M meistrivõistlused“ = „LAT-EST M“), seepärast loetakse lõppenud mängud eraldi, mitte ei sobitata ajakavaga. Protokolli link (`Protokoll.aspx?id=…`) on mängu seis ja statistika. Saalide lühendid „Sadolin SH“ ja „Kuusalu SH“ on aliasena `venues.toml`-is (Kuusalu seos oletatud: üks saal).
- **baltichandball.eu:** `…/season/<s>/league/<id>/results`, sama kujuga plokid kui ajakava lehel, tulemus on kaks numbrit võistkondade nimede järel. robots.txt puudub (404).
- Tulemuste leht toob ka välismaa saalid; uued saalid on `venues.toml`-is ja `geo.foreign` all (Aizkraukle, Ķekava, Spuņciems, Vilnius).
- **Kalev (bckalev.ee):** https://bckalev.ee/tulemused/ on sama SportPressi tabel mis ajakava, lisaks veerg „Tulemused“ ("83 - 81" või "-"). robots.txt lubab. Leht on suur (umbes 570 KB, sisaldab ka vanemaid hooaegu), seepärast võetakse sealt ainult mängitud mängud jooksvast hooajast (alates 1. augustist). Mängu link on klubi mängulehele. Mängitud välismaa mängudel on „saaliks“ riik või linn (Türgi, Poola, Manchester jt), need on `venues.toml`-is ja `geo.foreign` all.
- **Tartu (basket.ut.ee):** tulemus on ajakava tabeli viimases veerus ("65:41"), eraldi päringut pole vaja.
- Kui tulemuste lehte ei saa, ajakava töötab edasi (hoiatus logis).

## Käsitsi lisatud mängud ja üritused (`kasitsi.toml`, lisatud 2026-11-22)

Automaatsed allikad ei kata sõprusmänge, turniire, eriüritusi (tähtede mäng, karikafinaalid jms), võrkpalli, korvpalli ja käsipalli koondiste kodumänge ega üksikuid mänge, mida allikas mingil põhjusel ei näita. Need on failis `kasitsi.toml` (adapter `kasitsi`, `manual = true` config.toml-is).

- **Kes lisab:** otsingu agent (pilverutiin, E ja N hommikul) otsib neid veebist, hindab ja lisab kindlad leiud pull request'iga harusse `claude/otsing-<kuupäev>`. PR merge'itakse automaatselt (vt allpool „Automaatne merge“), kui kõik kontrollid läbivad, muidu vaatab omanik selle üle. Ebakindlad leiud ja puuduvad terved võistlused (uue allika vajadus) lähevad issue'na (silt `puuduv-uritus`). Kasutajate teated (issue mall „Puuduv üritus“) on agendile vihje, mitte allikas: kirje tehakse ainult siis, kui agent leiab ise ametliku kinnituse.
- **Reeglid:** iga kirje põhineb ametlikul avalikul allikal (`url`, sotsiaalmeedia pole lubatud), ainult Eestis toimuvad üritused, isikuandmeid ei lisata. Saal peab olema `venues.toml`-is. Väljad ja näited on faili päises.
- **Kontroll:** `python -m scrapers.kasitsi` (loeb faili, kontrollib saale ja prindib kirjed) ja testid. PR-i puhul jooksutab need GitHub Actions („Testid“).
- **Kalender:** tase (`level`) on igal kirjel eraldi. Turniiril ja eriüritusel võib külalismeeskonna ära jätta, siis näidatakse ainult ürituse nime. Mängu lehel on nupp „Teade allikal ↗“.
- **Topelt:** allikas on config.toml-is viimane, seega kui sama mäng tuleb hiljem automaatsest allikast (sama ala ja algusaeg ning samad võistkonnad või sama saal), jääb alles automaatse allika oma.
- **Hooaeg:** terve aasta, 0 tulevast üritust ei ole viga (ei tee „allikas“ issue'd).

### Automaatne merge (lisatud 2026-11-22, omaniku soovil)

Otsingu agendi PR (`claude/otsing-*`) läheb `main` harusse ilma omaniku ülevaatuseta, kui kõik kihid läbivad. Muidu saab PR sildi `vajab-ülevaatust` ja kommentaari põhjustega.

1. **Testid** (töövoog „Testid“): kogu testikomplekt ja `python -m scrapers.kasitsi`.
2. **Kontroll** (töövoog „Automaatne merge“, skript `scripts/automerge_check.py`). Töövoog ja skript tulevad alati `main` harust, PR-i faile loetakse ainult andmetena, nii et PR ei saa kontrolli muuta.
   - Muudetud on ainult `kasitsi.toml`, `venues.toml`, `config.toml`, `allikad.toml` ja `ulekanded.toml`. Koodi muutvad PR-id jäävad alati omanikule.
   - `config.toml`: ainult uued kohad `[geo.place]` all olemasoleva maakonnaga.
   - `venues.toml`: olemasolevad saalid muutmata, uusi kuni 5, linn Eestis.
   - `kasitsi.toml`: fail korrektne, olemasolevaid kirjeid ei muudeta, eemaldada võib ainult üle 30 päeva vanu. Uusi 1–10, algus tänasest kuni 60 päeva, `added` viimase 3 päeva sees, `note` (hinnang) olemas, saal teada ja Eestis.
3. **Allika kontroll:** GitHub Actions avab iga uue kirje `url`-i (robots.txt peab lubama). Lehel peab olema mängu kuupäev (5.12, 05.12.2026, 5. detsember, December 5 jms) ja võistkonna või ürituse nimi.
4. **Merge:** squash, ainult sama commit'iga, mille testid läbisid (`--match-head-commit`). Siis käivitatakse lehe ehitus.
5. **Järelkontroll:** nädalaplaani agent loetleb eelmise nädala automaatselt merge'itud PR-id. Vale kirje parandamiseks: kustuta see `kasitsi.toml`-ist (tavaline PR).
6. **Allikate register** (`allikad.toml`): agent võib lisada uusi allikaid (kasutus agent, vihje või keelatud) ning uuendada olemasolevatel välju `kontrollitud`, `markus`, `kuju`, `robots`, `kandidaat`. Kustutada, ümber nimetada või adapteriks märkida saab ainult omanik.
7. **Ülekanded** (`ulekanded.toml`, lisatud 2026-11-23): agent võib lisada `[[liiga]]` ridu olemasolevate kanalitega (kuni 5) ja `[[mang]]` kirjeid (kuni 10, algus tänasest kuni 21 päeva, `lisatud` viimase 3 päeva sees, `markus` olemas, link kanali saidil). Iga uue `[[mang]]` lingi kohta kontrollitakse robots.txt-i ja et lehel on mõlema võistkonna nimi (käändes sobib). Uue kanali (`[[kanal]]`) lisab või muudab ainult omanik: selline PR jääb ülevaatusele.

## Allikate register (`allikad.toml`, lisatud 2026-11-22)

Kõik kohad, kust leiab infot Eestis toimuvate mängude kohta, ühes failis: hallid ja areenid, linnade ja valdade sündmuste kalendrid, liidud, rahvusvahelised alaliidud, klubid, piletimüük ja uudised. Iga kirje kohta on url, alad, piirkond, lehe kuju (html/js), robots.txt olek, kasutus ja viimase kontrolli kuupäev.

- **Kasutus:** `adapter:<nimi>` loetakse automaatselt iga päev; `agent` käib otsingu agent igal jooksul läbi; `vihje` on vihjeallikas (uudised, piletimüük), mille põhjal otsitakse ametlik kinnitus; `keelatud` ei loeta (nt basket.ee, estlatbl.com).
- **Adapteri kandidaadid** (`kandidaat = true`): korrapärase mängukavaga allikad, millest saaks teha automaatse adapteri (praegu HC Vipersi mängude leht ja Eesti Hoki Statistika).
- **Kontroll:** `python allikad.py` (kokkuvõte ja vead), `python allikad.py --agent` (agendi kontrollnimekiri). Testid kontrollivad faili igal PR-il.
- **Esimene versioon** (50 allikat) on kontrollitud 2026-11-22: iga url vastas, robots.txt vaadatud. Kalevi spordihallil, Pärnu spordihallil ning Narva spordikeskusel ja jäähallil oma üritustekalendrit ei leitud, nende üritusi otsitakse linnade kalendritest.

## Ülekanded (`ulekanded.toml`, `ulekanded.py`, lisatud 2026-11-23)

Mängu real on ekraani ikoon ja mängu lehel nupp „Otse“ või „Vaata järele“, kui teame mängu ülekande linki (`Event.video`, `video_by`). Mängu lehel on ka rida „Selle liiga mänge on näidanud: …“. Ainult ametlikud ülekanded (liit, klubi, meediamaja).

- **Mängu link allika lehelt:** kasipall.ee liiga lehel on peetud mängul ikoon „YouTube – järelvaatamine“ või „Postimees – järelvaatamine“. jalgpall.ee liiga ja koondise lehel on peetud mängul YouTube'i nupp (`ico-btn yt`). Premium liigas viib see jalgpall.ee klikiloenduri kaudu YouTube'i (`/log/link_counter.php/?id=…&type=3`), seda linki kasutame. Tulevastel mängudel neid linke pole (kontrollitud 2026-11-23). kasipall.ee peetud mängul pole saali (saal on ainult lähipäevade protokollis), seega mäng ise andmetesse ei jää ja tuleb lehele arhiivist. Tema link salvestatakse faili `data/ulekanded.json` ja lisatakse arhiivist tulevale mängule.
- **Liiga kaupa:** käsitsi kontrollitud info (`ulekanded.toml` [[liiga]]) ja mängudest õpitu: iga mäng, millel on `video_by`, lisab selle kanali oma liigale (arhiivist viimased 180 päeva). Nimekiri on ka „Meist“ lehel.
- **Kontrollitud 2026-11-23:** Delfi TV näitab võrkpalli Balti liigat ja Eesti-Läti korvpalliliigat (tv.delfi.ee ülekannete kava). ERR näitab Premium liigast üht mängu voorus ja meeste koondise mänge. Postimees näitab käsipalli meistriliigat.
- **Delfi TV kava** ✅ (adapter `scrapers/kava_delfi.py`, `ulekanded.toml` → `kava = "delfi"`): `portal-feeds.api.delfi.ee/portal-feeds-proxy/v1/stream-schedule` (JSON, sama, mida tv.delfi.ee kava leht kasutab; api hostil robots.txt puudub, tv.delfi.ee robots lubab). Umbes kaks nädalat ette: kuupäev, kellaaeg (UTC), ala (`label`) ja „Kodu - Võõras“. Kava read seotakse olemasolevate mängudega (ala, kellaaeg ±45 min, mõlema võistkonna nimes ühine eristav sõna); kahe võrdse kandidaadi korral jäetakse vahele. Seosed hoitakse failis `data/ulekanded.json` (mängu id → link, 180 päeva), nii jääb link ka möödunud päevale ja õppimisele. 2026-11-23: 15 kava mängust 11 seoti, ülejäänud 4 on korvpallimängud, mida lehel pole (TÜ leht maas, teiste klubide omavahelised mängud). Kava ridu mängudena ei lisata.
- **ERR telekava** ✅ (adapter `scrapers/kava_err.py`, `kava = "err"`): err.ee telekava lehe JSON `www.err.ee/api/tvSchedule/getTimelineSchedule?day=&month=&year=&channel=etv|etv2` (robots.txt keelab ainult nimelised robotid, `User-agent: *` gruppi pole). Loeme ETV ja ETV2 8 päeva (16 päringut). Spordiülekanne tuntakse ära nime algusest („Korvpalli …“, „Laskesuusatamise …“); pallimängul on pärast esimest punkti „Kodu - Võõras“, tärniga nimi on kordus ja jäetakse välja. Link viib saate Jupiteri lehele. Ürituse aladel (suusatamine, ralli, uisutamine …) seotakse nime sõnade järgi: ülekande päev ürituse päevade sees ja vähemalt 2 ühist sõna (käänded lubatud, „Otepää“ = „Otepääl“). 2026-11-23: ETV2 27.11 kell 18.45 „Korvpalli MM-valikmäng. Eesti - Prantsusmaa“ seoti käsitsi lisatud koondisemänguga.
- **Postimees** teatab ülekandest uudises alles mängupäeval („TÄNA OTSEÜLEKANNE“), RSS katab umbes ühe päeva ja leht ehitatakse hommikul. Seepärast seda automaatselt ei loe: liiga kaupa on Postimees teada (käsipalli meistriliiga järelvaatamise lingid).
- **Otsinguagent** (E ja N): kontrollib kanaleid, mille kava automaatselt ei loeta (Postimees, klubide ja liitude YouTube), ning lisab teadaolevad ülekanded `[[mang]]` kirjetena. Need seotakse mängudega samamoodi nagu kava read, seega vale nimi lehele ei jõua. Kui agent leiab liigale uue ülekandja, lisab ta `[[liiga]]` rea (olemasolev kanal) või teeb ettepaneku uue kanali kohta (omanik kinnitab).
- **Kontroll:** `python ulekanded.py` (faili vead). Testid kontrollivad faili igal PR-il.

## Reketialad: tennis ✅, sulgpall ✅, lauatennis käsitsi (lisatud 2026-11-24 omaniku soovil)

Menüüs rühm „Reketialad“ (`build.SPORT_GROUPS`).
- **Tennis** (`scrapers/tennis_etl.py`, tennis.ee/kalender/, robots.txt lubab): aasta pealkirja („VÕISTLUSKALENDER 2027“) all tabel: algus, lõpp, kategooria (M,N / T18 / P12 / TP14 / NL…), nimi, linn, klubi. Täiskasvanute MV, Masters ja rahvusvahelised → 1, Eesti GP → 2, noorte MV ja rahvusvahelised noorteturniirid (ITF, Tennis Europe „TE14“) → 4, noorte GP ja noorteliiga → 3 (peidetud). Koht „Klubi, Linn“ (venues.toml aliased), „ETL“ → „Linn, koht täpsustamisel“. Sama nimega turniire on samal päeval mitu (vanuseklassid), seepärast on id-s kategooria ja koht. Kalendris oli trükiviga „3o.01“ (o → 0). WTA Tallinn Open, Davis Cupi ja BJK Cupi kodumängud lisab agent käsitsi.
- **Sulgpall** (`scrapers/sulgpall_esl.py`, badminton.ee võistluskalender, robots.txt lubab): plokid nime, kuupäeva („05.12.2026“, „10. --- 12.12.2026“, üle kuu „31. --- 01.11.2026“), saali ja juhendi lingiga. Rahvusvahelised (International, European … Championships), Eesti MV, klubide karikas → 1, GP-sari → 2, noorte MV ja rahvusvahelised noorteturniirid → 4, noorte GP ja harrastajate turniirid → 3, seeniorid ja edasi lükatud välja. Esimene suur: badmintoni segavõistkondade EM Kalevi spordihallis 6.–10.01.2027.
- **Lauatennis**: kalender on allalaaditavas failis (uus.lauatennis.ee), meistriliiga ja tulemused eltl.ee/voistlused. Praegu lisab meistriliiga mängud ja Eesti MV otsinguagent käsitsi; adapteri kandidaat.
- **Squash ja padel**: peamiselt harrastajate liigad (padel.ee iCal, squash.ee Events Calendar API on olemas), sobivad hiljem „võtan osa“ juurde.

## Kunstilised alad: võimlemine, tantsusport, fitness, käsitsi (lisatud 2026-11-24 omaniku soovil)

Menüüs rühm „Kunstilised alad“. Automaatset lugejat praegu pole, võistlused lisab otsinguagent (`kasitsi.toml`):
- **Võimlemine** (iluvõimlemine, sportvõimlemine, rühmvõimlemine): kalender.eevl.ee on JavaScripti rakendus, toores HTML-is sündmusi pole ja avalikku andmeaadressi ei leitud. Suurim: Miss Valentine Tartus igal veebruaril (missvalentine.eu; 2026: 25.02–1.03 Tartu Ülikooli spordihoones, 2027 kuupäevad teadmata).
- **Tantsusport**: dancesport.ee aasta kalendris on ainult kuupäev ja nimi (~5 võistlust, nt 20.03.2027 „EMV ST&LA + Tallinn Trophy“), kohta pole: koht juhendist või uudisest.
- **Fitness ja kulturism**: kulturism.ee on Events Calendar (iCal ja REST API, robots Crawl-delay 3), aga Eestis toimuvaid võistlusi on vähe (Eesti MV ja Estonian Open Cup, peamiselt kevadel), IFBB rahvusvahelised on enamasti välismaal ja ilma kohata.
- Kui mõni allikas muutub loetavaks (nt võimlemisliidu kalender saab avaliku voo), saab teha adapteri.

## Veealad: ujumine, sõudmine, aerutamine, purjetamine (lisatud 2026-11-24 omaniku soovil)

Menüüs rühm „Veealad“.
- **Ujumine** ✅ adapter `ujumine_eul`: swimming.ee/kalender/ (robots.txt lubab kõike). Nimekirjavaade `?view=list&swimming_ajax=1&swimming_ppp=300` annab kogu tuleviku ühe päringuga (tavaline `paged=` lehitsemine töötab ainult saidi JS-iga). Kellaaega pole. Koolitused jäävad välja, duplikaadid liidetakse, välismaa võistlused langevad välja geo.foreign kaudu (uus välismaa koht tuleb sinna lisada). Tase: Eesti MV → 1, Open/Cup/karikad → 2, noorte ja laste sarjad → 4, klubide võistlused → 3 (peidetud).
- **Sõudmine** (soudeliit.ee), **aerutamine/kanuu** (aerutaja.ee, rajaaerutamise karikasari, Paala sprint, Pühajärve regatt) ja **purjetamine** (puri.ee, Garmin Sailing Series): 2027 kalendreid pole veel avaldatud ja hooaeg on suvel, seega võistlused lisab otsinguagent `kasitsi.toml`-i, kui kalender ilmub. Kõigi kolme robots.txt lubab lugemist.

## Pistekontroll 2026-11-20

Iga allika kohta üks mäng lehel olevatest andmetest, võrreldud allika enda mängulehega:

| Mäng | Kuupäev, kell | Tulemus |
|---|---|---|
| HC Panter – Rīgas HS/Dinaburga (jäähoki) | 25.11 19:00 | ✅ (allikas näitab kohana ainult „Tallina“) |
| Audentes/Solarstone – Barrus Võru VK (võrkpall) | 27.11 19:00 | ✅ |
| Tallinna Mistra – Põlva Serviti (käsipall) | 25.11 19:00 | ✅ |
| Sparta – Rubene (saalihoki) | 12.12 14:30 | ✅ andmed õiged, **link oli 404** → parandatud (`/Events/` kaust) |
| Tallinna FCI Levadia – Nõmme Kalju FC (jalgpall) | 07.11 12:30 | ✅ |

## Hilisemaks (teine samm)

- Korvpall: kui liit kunagi avaldab avaliku voo või robots.txt muutub, vaatame uuesti. Viimsi kalender on tühi (vt Korvpall), Pärnu ja Tartu klubilehed on kontrollimata.
- Võrkpall: Eesti meistriliiga playoffid (`evf-web.dataproject.com`).
- Esiliigad ja naiste liigad: jalgpall.ee, kasipall.ee ja saalihoki.ee kasutavad kõigi liigade jaoks sama süsteemi, seega piisab uuest liiga ID-st.

## Kergejõustik: Eesti Kergejõustikuliidu kalender ✅ (lisatud 2026-11-23)
- Allikas: https://www.ekjl.ee/kalender/ (robots.txt lubab, keelab ainult ühe pluginafaili). Adapter `kergejoustik_ekjl`.
- Kogu hooaeg ühel serveris renderdatud lehel: nimi, kuupäev(ad), valikuline kellaaeg, koht, kategooria (World Athletics A–F, GL/GW/OW, Muu, Koolitus). Kontaktisikute modaalaknaid ei loeta.
- Tase: noored → 4, A–E ja Eesti MV/KV → 1, ülejäänud kohalikud → 3 (peidetud). Välismaa võistlustel on koha asemel linn, need jäävad välja `geo.foreign` kaudu.

## Motosport: Eesti Mootorrattaspordi Föderatsiooni kalender ✅ (lisatud 2026-11-23)
- Allikas: https://msport.ee/?mec-ical-feed=1 (iCal, robots.txt lubab). Adapter `motosport_emf`.
- Pluginal on ajavööndi viga: terve päeva üritus on kujul `T200000Z` eelmisel päeval (vt adapteri kirjeldus).
- Koht on iCal-is harva, aga ürituse nimes ("Kiltsi lennuväli", "Karksi-Nuia"): `config.toml` → `venue_hints`. Ilma kohata üritus ilmub lähipäevadel aruandesse („Mängud ilma toimumiskohata“).
- Autosport (autosport.ee) on sama kalendripluginaga, aga iCal pole seal sisse lülitatud ja kalender laeb JavaScriptiga, nii et see ei ole veel lisatud.

## Suusatamine: Eesti Suusaliidu kalender ✅ (lisatud 2026-11-23)
- Allikas: https://www.suusaliit.ee/et/voistlused (robots.txt lubab, Crawl-delay 15; meil üks päring päevas). Adapter `suusatamine_esl`.
- Serveris renderdatud tabel tänasest hooaja lõpuni: kuupäev(ad) ilma aastata (aasta tuletatakse), ala, nimi, koht ja riik, kategooria (MK, MM, FIS, EMV, EMS, MA, NoSu, NS, OTHER).
- Tase (ainult vaatamist väärt): MK, MM, Tartu Maraton ja showalad (hüpped, kahevõistlus, freestyle, lumelaud) → 1, showalade noortesari → 4, ülejäänud (murdmaa EMV, maratonid, karikad, noortesarjad) → 3 (peidetud). „Muu“ (laagrid jms) ja välismaa võistlused jäävad välja. Riik võib olla kohas ka tavalise tekstina („Tromsö, Norra, Eesti“).

## Ratsasport: Eesti Ratsaspordi Liidu kalender ✅ (lisatud 2026-11-23)
- Allikas: https://ratsanet.ee/events (robots.txt lubab /events; keelab hobuste, isikute jms lehed). Adapter `ratsasport_ratsanet`.
- Serveris renderdatud tabel: kuupäevad, ala lühend (TS, KS, PKS, 3V, KR, RS, V), nimi, koht, riik (EST jt), tase (takistuste kõrgus või koolisõidu klass), staatus.
- Tase: rahvusvahelised (RV, CSI/CDI/CHI/CEI), Eesti (sise)meistrivõistlused ja takistussõit ≥ 130 cm → 1; ülejäänud klubide võistlused → 3 (peidetud). Välismaa ja tühistatud jäävad välja.

## Uisutamine: Eesti Uisuliidu iluuisutamise kalenderplaan ✅ (lisatud 2026-11-23)
- Allikas: https://www.uisuliit.ee/iluuisutamine/voistlused → hooaja leht `eul-kalenderplaan-<aasta>-<aasta>` (robots.txt lubab; `/files/` keelatud, PDF-e ei loeta). Adapter `uisutamine_eul`.
- Serveris renderdatud tabel: kuupäevad, võistlus, koht, korraldaja, kategooria. Kuupäevata (TBA) jääb välja.
- Tase: ISU kalenderplaani võistlused (Tallinn Trophy, Tallinn Open, Lõunakeskus Trophy, Tallink Hotels Cup, Crystal Skate Spring) ja Eesti MV → 1, noorte MV ja Novice/Kids → 4, klubide Interclub → 3 (peidetud).
- Kiiruisutamise lehel on ainult eelmine hooaeg ja Härma ovaali väikesed võistlused, seda ei loeta.

## Võitlusspordid ✅ judo, käsitsi poks ja maadlus (lisatud 2026-11-23)
- **Judo:** https://judo.ee/voistlused/ külgriba „Upcoming events“ (robots.txt lubab). Adapter `voitlusspordid_judo`. Täielik kalender on PDF-is ja ürituste lehtedel; järgmise aasta üritused lisab liit veebruaris. Tase: rahvusvahelised ja täiskasvanute Eesti MV → 1, noorte MV → 4, klubide turniirid → 3.
- **Poks:** eestipoksiliit.ee „võistluskalender“ on aastaid vana (Moskva EM, Singapuri noorte olümpia), automaatseks allikaks ei sobi. Juhendid on PDF-ina. Otsinguagent (`allikad.toml`) lisab Eesti MV ja suuremad turniirid `kasitsi.toml`-i.
- **Maadlus:** maadlusliit.ee kalender laeb JavaScriptiga, WordPressi API ei vasta. Agent nagu poksis.
- **Kikk- ja taipoks, MMA galad:** liitudel kalendrit pole; agent otsib korraldajate ja piletimüügi lehtedelt.

## Autosport: käsitsi ✅ (lisatud 2026-11-23)
- autosport.ee kalender laeb JavaScriptiga, iCal pole sisse lülitatud (sama MEC plugin kui msport.ee-l). Ürituste lehed on loetavad ja nimekiri on `mec-events-sitemap.xml`-is, aga 2027. aasta etappe veel pole.
- WRC Rally Estonia 22.–25.07.2027 on `kasitsi.toml`-is. Suuremad etapid (ralli EMV, talverallid) lisab agent.

