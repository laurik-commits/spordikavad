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
- **Tartu (basket.ut.ee):** veel kontrollimata.

## Jäähoki: Optibet Hokiliiga

- **Ajakava leht:** https://www.lhf.lv/en/tournaments-list/optibet-hockey-league (ka https://www.lhf.lv/en/tournaments/optibet-hokeja-liga/schedule)
- **Kuju:** serveris renderdatud HTML: kuupäev, kell, võistkonnad, koht ja mängu link (`/en/tournaments/optibet-hokeja-liga/2026-2027/1245/schedule/hcp-kyc/20261121/35876`). JSON-it ega iCal-i ei leitud.
- **robots.txt:** `User-agent: *`, ühtegi keeldu pole.
- **Hooaeg:** algas 05.09.2026, lõpp pole lehel kirjas (eeldatavalt märts–aprill 2027 koos playoffidega).
- **Tallinna klubi:** HC Panter (kodusaal Haabersti jäähall).
- **Eripärad:** liiga on Läti liidu hallata (Eesti Jäähokiliidu oma süsteem ehis.eestihoki.ee lõpeb hooajaga 2024/25). Tallinna kodumängude koht on kirjas ainult kui „Tallina, Igaunija“. Selle jaoks tuleb `venues.yaml`-isse alias „Tallina, Igaunija“ → Haabersti jäähall.

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
