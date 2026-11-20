# Andmeallikad

Kaardistus tehtud 2026-11-20. robots.txt on kontrollitud iga domeeni puhul samal päeval.
Kasutustingimusi, mis keelaksid automaatse kogumise, ühegi allika lehtedelt ei leitud (vaadatud avalehed, jalused ja olemasolul tingimuste leht).

## Kokkuvõte

| Ala | Liiga | Allikas | Kuju | robots.txt | MVP |
|---|---|---|---|---|---|
| Jalgpall | A. Le Coq Premium liiga | jalgpall.ee | iCal (+ HTML) | lubatud, `Crawl-Delay: 5` | ✅ |
| Korvpall | FenixBet Eesti-Läti Korvpalliliiga | estlatbl.com, basket.ee | HTML | **keelatud** (`User-agent: *` / `Disallow: /`) | ❌ välja jäetud |
| Jäähoki | Optibet Hokiliiga | lhf.lv | staatiline HTML | lubatud | ✅ |
| Võrkpall | Elme Messer Balti liiga | bvl-web.dataproject.com | staatiline HTML | lubatud | ✅ |
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
- **Eripärad:** praegu (hooajaväline aeg) on iCal tühi. Adapteri testiks tuleb fixture teha iCal-i formaadi järgi ja kontrollida päris andmetega märtsis.

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
- **Eripärad:** Eesti meistriliiga (playoffid) on volley.ee järgi samuti DataProjecti süsteemis (`evf-web.dataproject.com`). Seda pole veel kontrollitud, lisame hiljem sama adapteriga. Naiste liigas Tallinna klubi pole (Rae Spordikool on Rae vallas).

## Käsipall: Meistriliiga (mehed)

- **Ajakava leht:** https://kasipall.ee/league/359 (kõik liigad: https://kasipall.ee/calendar/season/2027, päevavaade `https://kasipall.ee/calendar/YYYY-MM-DD`)
- **Kuju:** staatiline HTML: kuupäev, kell, võistkonnad ja mängu link (`/protocol/NNNN`). **Saali nimekirjas pole**, see on mängu lehel (`location_on` → nt „Viimsi kooli Spordikeskus“, link `/field/54`).
- **robots.txt:** `User-agent: *` / `Disallow:` (tühi), kõik lubatud. handball.ee-l robots.txt puudub (404).
- **Hooaeg:** 2026/27 (URL-ides `2027`). Nähtavad mängud kuni 01.01.2027, edasi „etapi mängud selgumisel“.
- **Tallinna klubi:** Tallinna Mistra. (HC Viimsi/Alexela on Viimsis, mitte Tallinnas.)
- **Eripärad:** liiga lehel on „Laadi veel“ nupp. Lihtsaim lahendus on päevavaade `/calendar/YYYY-MM-DD` 15 päeva kohta. Saali saamiseks tuleb avada iga mängu leht, aga Tallinna mänge on vähe ja leht jätab saalinime vahemällu. Balti liiga ametlikku lehte ei leitud, osa Mistra mänge võib seega puududa.

## Saalihoki: Meistriliiga + Eesti-Läti ühisliiga

- **Ajakava leht:** https://saalihoki.ee/Ajakavad.aspx (kõik tulevased mängud, filtrid liiga järgi). Liigad: Meistriliiga `Liigad/Liiga.aspx?id=9`, EST-LAT mehed `id=136`.
- **Kuju:** staatiline ASP.NET HTML-tabel: aeg, mäng koos lingiga (`Uritus.aspx?id=NNNN`) ja koht.
- **robots.txt:** keelatud ainult tehnilised kaustad (`/Bootstrap/`, `/handlers/`, `/Scripts/`, `*.axd` jm). Ajakavad ja liigade lehed on lubatud. floorball.ee suunab saalihoki.ee-le.
- **Hooaeg:** 2026/27. Ühisliiga alates 21.11.2026, meistriliiga esimene mäng 22.11.2026. Lõpp pole kirjas.
- **Tallinna klubid:** tõenäoliselt Sparta Team Automaailm (kontrollimata). Teised meistriliiga klubid on Tartust, Jõgevalt ja Märjamaalt.
- **Eripärad:** Tallinna mänge on hooaja jooksul vähe. Kuna adapter on lihtne, võtame ala sisse ja `venues.yaml` filtreerib Tallinna saalid välja.

---

## Hilisemaks (teine samm)

- Korvpall: kui liit kunagi avaldab avaliku voo või robots.txt muutub, vaatame uuesti.
- Võrkpall: Eesti meistriliiga playoffid (`evf-web.dataproject.com`).
- Esiliigad ja naiste liigad: jalgpall.ee, kasipall.ee ja saalihoki.ee kasutavad kõigi liigade jaoks sama süsteemi, seega piisab uuest liiga ID-st.
