// Alafilter: peidab teiste alade read. Valik jäetakse meelde ka järgmistel päevadel.
// Välise lingiga ala (korvpall) nupp näitab mängude asemel selgitust ja linki.
(function () {
  var KEY = "spordikavad-ala";
  var buttons = document.querySelectorAll(".filters button");
  var rows = document.querySelectorAll(".games li");
  var empty = document.querySelector(".empty-filter");
  var none = document.querySelector(".none");
  var notes = document.querySelectorAll(".extnote");

  // päevade ribal too valitud päev nähtavale
  var cur = document.querySelector('.days [aria-current="page"]');
  if (cur && cur.parentNode.previousElementSibling) cur.scrollIntoView({ block: "nearest", inline: "center" });

  function apply(sport) {
    var btn = document.querySelector('.filters button[data-filter="' + sport + '"]');
    var ext = !!(btn && btn.dataset.ext);
    var shown = 0;
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.filter === sport)); });
    notes.forEach(function (n) { n.classList.toggle("show", ext && n.dataset.note === sport); });
    rows.forEach(function (r) {
      var hide = ext || (sport !== "" && r.dataset.sport !== sport);
      r.hidden = hide;
      if (!hide) shown++;
    });
    if (empty) empty.hidden = ext || shown > 0 || rows.length === 0;
    if (none) none.hidden = ext;
    var list = document.querySelector(".games");
    if (list) list.hidden = ext;
  }

  var saved = "";
  try { saved = localStorage.getItem(KEY) || ""; } catch (e) {}
  var savedBtn = saved && document.querySelector('.filters button[data-filter="' + saved + '"]');
  // välise lingi valikut ei jäeta meelde: järgmisel avamisel näeb jälle mänge
  if (!savedBtn || savedBtn.dataset.ext) saved = "";
  apply(saved);

  buttons.forEach(function (b) {
    b.addEventListener("click", function () {
      apply(b.dataset.filter);
      if (!b.dataset.ext) {
        try { localStorage.setItem(KEY, b.dataset.filter); } catch (e) {}
      }
    });
  });
})();
