# Andmeallikad

Kaardistus tehtud 2026-11-20. robots.txt on kontrollitud iga domeeni puhul samal päeval.
Kasutustingimusi, mis keelaksid automaatse kogumise, ühegi allika lehtedelt ei leitud (vaadatud avalehed, jalused ja olemasolul tingimuste leht).

## Kokkuvõte

| Ala | Liiga | Allikas | Kuju | robots.txt | MVP |
|---|---|---|---|---|---|
| Jalgpall | A. Le Coq Premium liiga | jalgpall.ee | iCal (+ HTML) | lubatud, `Crawl-Delay: 5` | ✅ |
| Korvpall | FenixBet Eesti-Läti Korvpalliliiga | estlatbl.com, basket.ee | HTML | **keelatud** (`User-agent: *` / `Disallow: /`) | ❌ välja jäetud |
| Jäähoki | Optibet Hokiliiga | lhf.lv | staatiline HTML | lubatud | ✅ |
| Võrkpall | Balti liiga, Eesti meistriliiga, karikad (M+N) | bvl-web / evf-web.dataproject.com | staatiline HTML | lubatud | ✅ |
| Käsipall | Meistriliiga (mehed) | kasipall.ee | staatiline HTML | lubatud | ✅ |
| Saalihoki | Meistriliiga + Eesti-Läti ühisliiga | saalihoki.ee | staatiline HTML | lubatud | ✅ (vähe Tallinna mänge) |

MVP-sse sobib 5 ala 6-st.

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

## Korvpall: FenixBet Eesti-Läti Korvpalliliiga ❌

- **Lehed:** https://www.estlatbl.com/et/mangud, https://www.basket.ee/et/ajakava-ja-tulemused?action=schedule
- **robots.txt:** mõlemal domeenil `User-agent: *` / `Disallow: /`. Lubatud on ainult Googlebot, Bingbot ja Applebot. Lisaks näitab estlatbl.com robotitele turvakontrolli lehte.
- **Otsus:** jäetud välja vastavalt lähteülesandele (automaatne kogumine on keelatud). Ainus seaduslik tee oleks liidu luba või avalik voog. Seda praegu pole.
- **Omaniku otsus 2026-11-20:** andmeid ei koguta, aga alafiltris on nupp „Korvpall“, mis on tavaline väline link basket.ee ajakavale (https://www.basket.ee/et/ajakava-ja-tulemused?action=schedule). Lehe ehitamisel basket.ee poole päringuid ei tehta.
- **Tallinna klubid:** Bigbank/Kalev, TalTech/ALEXELA. (Kahju, sest need on populaarsed mängud.)
- Ka Korvpalli Meistriliiga ja naiste liiga on samal basket.ee domeenil, seega samuti välja.

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
- Saalijalgpall (futsal) meistriliiga (jalgpall.ee id 125, Tallinna FC Bunker Partner). See oleks uus ala.

**Ei kasutata:**
- **Eesti jäähoki liigad** (Unibet Hokiliiga: Tallinna HC Vipers; naiste hokiliiga: Roosa Panter, Grizzlyz, Wolferines). Ajakava on ehs.eestihoki.ee-l, aga see laaditakse JavaScriptiga kommertsteenusest **hockeydata.net**, kasutades liidu enda API-võtit. Meie skriptil pole õigust seda võtit kasutada (lähteülesanne: küsitavad allikad jäta vahele). ehis.eestihoki.ee (serveri HTML, robots lubab) lõpeb hooajaga 2024/25. **Vaata uuesti**, kui ehis-is ilmub 2026/27 hooaeg.
- Käsipalli Balti liiga (Mistra): mänge ei leitud ei kasipall.ee-st ega mujalt.
- Naiste käsipallikarikas (id 363): 2026/27 mänge pole veel avaldatud. Lisa `competitions` alla, kui need ilmuvad.
- Saalihoki: naiste kodumaist liigat ega täiskasvanute karikat pole.
- Jäähoki: täiskasvanute karikat 2026/27 pole.

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

- Korvpall: kui liit kunagi avaldab avaliku voo või robots.txt muutub, vaatame uuesti.
- Võrkpall: Eesti meistriliiga playoffid (`evf-web.dataproject.com`).
- Esiliigad ja naiste liigad: jalgpall.ee, kasipall.ee ja saalihoki.ee kasutavad kõigi liigade jaoks sama süsteemi, seega piisab uuest liiga ID-st.
