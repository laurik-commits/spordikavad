// Alafilter: peidab teiste alade read. Valik jäetakse meelde ka järgmistel päevadel.
// Välise lingiga ala (korvpall) nupp näitab mängude asemel selgitust ja linki.
(function () {
  var KEY = "spordikavad-ala";
  var buttons = document.querySelectorAll(".filters button");
  var rows = document.querySelectorAll(".games li");
  var empty = document.querySelector(".empty-filter");
  var none = document.querySelector(".none");
  var notes = document.querySelectorAll(".extnote");

  // linnavalik: jäta valik meelde; avalehel (vaikelinna tänane leht) suuna meelde jäetud linna
  var CITY = "spordikavad-linn";
  var body = document.body;
  if (body.dataset.index && body.dataset.region === body.dataset.default) {
    var city = "";
    try { city = localStorage.getItem(CITY) || ""; } catch (e) {}
    if (city && city !== body.dataset.default) {
      var target = document.querySelector('.city a[data-region="' + city + '"]');
      // tänase päeva leht selles linnas = linna kausta avaleht
      if (target) { location.replace(target.getAttribute("href").replace(/\d{4}-\d{2}-\d{2}\/$/, "")); return; }
    }
  }
  document.querySelectorAll(".city a[data-region]").forEach(function (a) {
    a.addEventListener("click", function () {
      try { localStorage.setItem(CITY, a.dataset.region); } catch (e) {}
    });
  });
  document.addEventListener("click", function (ev) {
    var d = document.querySelector(".city[open]");
    if (d && !d.contains(ev.target)) d.removeAttribute("open");
  });

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
