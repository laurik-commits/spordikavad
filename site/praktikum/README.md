# Praktikumi leht (elakaasa.ee/praktikum)

Pane materjalid kausta `materjalid/` (GitHubis: **Add file → Upload files**, brauseriga kuni 25 MB faili kohta, suuremad `git`-iga, kuni 100 MB). Pärast merge'i
ehitatakse leht ise: `elakaasa.ee/praktikum/` loetleb failid (nimi ja suurus) ja neid saab alla laadida. Alamkaust `materjalid/` sees on lehel pealkiri
(nt `materjalid/1. praktikum/slaidid.pdf`). Kui kaustas pole ühtegi faili, lehte ei tehta.

Valikuline `praktikum.toml` (sama kaustas, siin kaustas `site/praktikum/`):

    title = "ChatGPT Edu praktikum"
    intro = "Siin on praktikumi materjalid."

    [[fail]]
    nimi = "slaidid.pdf"            # või alamkausta fail: "1. praktikum/slaidid.pdf"
    kirjeldus = "Sissejuhatuse slaidid"

**Tähelepanu:** GitHub Pages on avalik. Leht on `noindex, nofollow`, sitemapis ja kuskilt lingitud pole, aga igaüks, kellel on link (või failiaadress),
näeb ja laadib faile. Ära pane siia midagi, mis ei tohi avalik olla (autoriõigus, õpilaste isikuandmed, hinded, pääsukoodid).
