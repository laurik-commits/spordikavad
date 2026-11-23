# Uued alad: grupid, andmeallikad ja kuidas need tabelisse sobivad

Analüüs 23.11.2026.

**Tehtud 23.11.2026:** ürituse kuju (`end` = viimane päev, mitmepäevane üritus on igal oma päeval, kellaplokis „2./3. päev“) ning kaks ala: **kergejõustik** (`kergejoustik_ekjl`, ekjl.ee) ja **motosport** (`motosport_emf`, msport.ee iCal). Motospordi koht tuleb ürituse nimest (`config.toml` → `venue_hints`). Käsitsi lisatud kirjetel (`kasitsi.toml`) on samuti `end` väli ja liik „võistlus“. Järgmised kandidaadid on all.

**Tehtud 23.11.2026 (teine samm):** **suusatamine** (`suusatamine_esl`, suusaliit.ee: murdmaa- ja mäesuusatamine, kahevõistlus, hüpped, freestyle, lumelaud) ja **ratsasport** (`ratsasport_ratsanet`, ratsanet.ee). Ratsaspordis on tasemel 1 rahvusvahelised, Eesti (sise)meistrivõistlused ja takistussõit ≥ 130 cm; klubide võistlused on peidetud tasemel 3. Ala valik on juba päises rippmenüü („Kõik alad ▾“), nii et alasid saab juurde panna ilma, et leht läheks segaseks.

Iga allika robots.txt on kontrollitud. Kõik allpool nimetatud lehed lubavad lugemist. Erand on sport.ee (EOK), mis keelab ClaudeBoti, nii et otsinguagent seda lehte ei kasuta.

## Põhierinevus: mängud ja üritused

Praegu on igal real **mäng**: kodu- ja võõrmeeskond, üks kellaaeg ja üks saal. Uutel aladel on enamasti **üritus**:

| | Mäng (praegu) | Üritus (uus) |
|---|---|---|
| Real | „Kalev – Tartu“ | „Saaremaa Ralli“, „Eesti MV poksis“ |
| Aeg | kellaaeg | sageli terve päev või mitu päeva, kellaaeg vahel puudub |
| Koht | saal | saal, staadion, rajatis või terve maakond (ralli) |
| Sagedus | iga nädal | mõni kord kuus, suvel tihedamalt |
| Seire | „42 päeva pole mänge = allikas katki“ | ei sobi, sest pikad vahed on normaalsed |

### Kuidas üritus tabelisse sobitub

- **Mudel.** Eventile tuleb juurde `kind = "event"`, `title` (ürituse nimi) ja `end` (viimane päev). Kodu- ja võõrmeeskonna väljad jäävad tühjaks.
- **Rida.** Mängu asemel on ürituse nimi. Hall rida on sama: sari või võistlus (`league`, näiteks „Eesti MV“), koht ja linn. Kellaplokis on alguse kellaaeg, „terve päev“ või „—:—“.
- **Mitmepäevane üritus** on nähtav igal oma päeval ja kellaplokis on näiteks „2./3. päev“. Jagamislink on üks.
- **Koht ja linn.** Saalid lähevad `venues.toml` faili nagu praegu. Ralli ja muu laialt toimuv üritus seotakse linna või maakonnaga (`[geo] places`), näiteks „Saaremaa“ → Saare maakond.
- **Tase.** Täiskasvanute MV, MK ja EM etapid ning suured rahvusvahelised üritused on tasemel 1. Karikasarjad ja etapid on tasemel 2, noored tasemel 4. Nimi „Kõrgliigad“ ei sobi üritustele hästi. Kui üritusi tuleb palju, võiks taseme nimeks panna näiteks „Tippvõistlused“.
- **Seire.** Ürituste allikatel on `check = false` nagu karikasarjadel praegu, nii et „allikas katki“ teade tuleb ainult siis, kui lehte ei saa lugeda või see on tühi.
- **Filtreerimine.** Liitude kalendrites on palju muud: koolitused, galad, trennipäevad, lastevõistlused ja välismaa võistlused. Iga allika juures on märksõnad või kategooriad, mida võtta ja mida jätta. Välismaa võistlused välja jätta on juba olemas (`only_estonia`).
- **Alavalikus** võivad olla gruppide pealkirjad (Pallimängud, Võitlusspordid, Motosport …) nagu linnavalikus on maakonnad.

## Alade grupid

Hinnang: ✅ allikas on masinloetav ja korralik, 🟡 allikat saab lugeda, aga vajab rohkem tööd, 🔴 allikat pole või see on keeruline.

### 1. Kergejõustik ja jooks
- **Kergejõustik** ✅ ekjl.ee/kalender. HTML-kalendris on kuupäev, kellaaeg, koht ja kategooria, näiteks „25.11.2026 (11:00) · Ahtme Spordihall“. Seal on palju lastevõistlusi (TV10 OS), mis lähevad „Noored“ alla või jäävad välja. Täiskasvanute EMV ja sisehooaja võistlused sobivad hästi.
- **Jooksud** 🟡 jooksukalender.ee (robots lubab). Enamik on osalemiseks, mitte vaatamiseks. Võtta ainult suured: Tallinna maraton, Tartu linnajooks, EMV.
- Hooaeg: talvel sisehallid (Lasnamäe, Tartu), suvel staadionid.

### 2. Motosport
- **Mootorrattasport** ✅ msport.ee pakub **iCal-voogu** (`?mec-ical-feed=1`, 484 üritust, kategooriatega: Motokross, Enduro …). See on parim allikas: andmed tulevad standardkujul ja HTML-i parsida ei ole vaja. Koht ei ole voos alati kirjas, aga ürituse lehel on.
- **Autosport (ralli, ringrada, krossiralli, autokross)** 🟡 autosport.ee/kalender. Sama kalendriplugin (MEC), aga iCal ei ole sisse lülitatud ja kalender laeb JavaScriptiga. Ürituse lehed on loetavad. Võib-olla saab liidult paluda iCal-voo sisselülitamist.
- **Rally Estonia (WRC/ERC)** ✅ rallyestonia.com (robots lubab, Crawl-delay 2). See on üks üritus aastas, nii et sobib `kasitsi.toml` faili.
- Hooaeg: põhiliselt mai kuni oktoober, talvel jäärajad ja Adrenalin Arena Cup.

### 3. Võitlusspordid
- **Poks** ✅ eestipoksiliit.ee/voistluskalender. Tabelis on kuupäevad, nimi, linn ja tase (näiteks „26.03–28.03 · J. Kudrjašovi memoriaal · Sillamäe“). Kellaaega pole, nii et kellaplokis oleks „—:—“.
- **Judo** 🟡 judo.ee. Kalender on PDF-is, üksikud üritused on eraldi lehtedel (`/event/…`).
- **Maadlus** 🟡 maadlusliit.ee/kalender (robots lubab). Kalender laeb tõenäoliselt JavaScriptiga, kuju veel kontrollimata.
- **Kikkpoks, karate, taekwondo** 🔴 liidu lehti ei õnnestunud lugeda või neil kalendrit ei ole.
- **Profipoksi ja MMA galad** 🔴 neid liitude lehtedel pole. Leiab ainult otsinguagent korraldajate lehtedelt ja piletimüügist.
- Kokku kümmekond kuni paarkümmend üritust aastas Eestis.

### 4. Tantsu- ja kunstilised alad
- **Tantsusport** 🟡 dancesport.ee/voistlused-ja-edetabelid/kalender-2026/. Nimekirjas on kuupäev ja nimi (EMV, EKV etapid). Koht on ürituse lehel. Üritusi on umbes 10 aastas, nii et need võiks lisada otsinguagent.
- **Iluuisutamine** ✅ uisuliit.ee kalenderplaan 2026/2027. Tabelis on kuupäevad ja nimed (Tallinn Trophy, Crystal Skate, Talveunistus Trophy). Kiiruisutamisel on sama lehe all oma kalender.
- **Iluvõimlemine** ei ole veel kontrollitud.

### 5. Talialad
- **Suusatamine ja kahevõistlus** ✅ suusaliit.ee/et/voistlused. Tabelis on kuupäev, ala, nimi, koht ja kategooria (näiteks „12.12–13.12 · Murdmaasuusatamine · Vello Liliumi karikavõistlus · Alutaguse, Pannjärve · EMS“). Seal on ka välismaa võistlused, mis jäävad välja. robots.txt nõuab Crawl-delay 15, mis on meie kord päevas päringute juures lihtne täita.
- **Laskesuusatamine** 🟡 biathlon.ee (robots lubab), kalender kontrollimata. Otepää MK etapp sobib `kasitsi.toml` faili.
- **Tartu Maraton, Otepää MK** on suured üksikud üritused, mis sobivad `kasitsi.toml` faili.

### 6. Vesi ja ratsasport
- **Ratsasport** ✅ ratsanet.ee/events. Tabelis on kuupäevad, nimi, ala, koht ja riik (EST või välismaa). Sobib hästi, välismaa võistlused jäävad välja.
- **Ujumine** 🟡 swimming.ee/kalender. Seal on segamini võistlused ja koolitused, nii et vaja on märksõnade filtrit.

### 7. Võistkonnaalad, mis sobivad praeguse kujuga (mängud)
- **Ragby** ✅ rugby.ee. Kalendriplugin on avatud API ja iCal-iga (`/events/?ical=1`), praegu hooajaväline (0 üritust).
- **Kurling** ✅ kurling.ee, samuti avatud API. Enamik üritusi on välismaal, Eestis vähe.
- **Lauatennis, sulgpall, tennis (klubide MV)**: kontrollimata, aga need on mängud ja sobiksid tabelisse kõige lihtsamalt.

## Soovitus, millest alustada

1. **Mudel ja rida ürituste jaoks** (`kind`, `title`, `end`, mitmepäevane kuvamine, alavalik gruppidega). Seda on vaja ükskõik millise grupi jaoks.
2. **Motosport (msport.ee iCal)** ja **kergejõustik (ekjl.ee)**: korralikud allikad, palju üritusi ja eri hooajad (suvi ja talv).
3. **Talialad (suusaliit.ee)** ja **ratsasport (ratsanet.ee)**: korralikud tabelid.
4. Ülejäänud (poks, tantsusport, iluuisutamine, suured üksikud üritused) lisab otsinguagent `kasitsi.toml` faili kaudu. Neid on vähe ja nende lehed on ebaühtlased.
