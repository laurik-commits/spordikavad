// Alafilter: peidab teiste alade read. Valik jäetakse meelde ka järgmistel päevadel.
(function () {
  var KEY = "spordikavad-ala";
  var buttons = document.querySelectorAll(".filters button");
  var rows = document.querySelectorAll(".games li");
  var empty = document.querySelector(".empty-filter");

  // päevade ribal too valitud päev nähtavale
  var cur = document.querySelector('.days [aria-current="page"]');
  if (cur && cur.parentNode.previousElementSibling) cur.scrollIntoView({ block: "nearest", inline: "center" });

  function apply(sport) {
    var shown = 0;
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.filter === sport)); });
    rows.forEach(function (r) {
      var hide = sport !== "" && r.dataset.sport !== sport;
      r.hidden = hide;
      if (!hide) shown++;
    });
    if (empty) empty.hidden = shown > 0 || rows.length === 0;
  }

  var saved = "";
  try { saved = localStorage.getItem(KEY) || ""; } catch (e) {}
  if (saved && !document.querySelector('.filters button[data-filter="' + saved + '"]')) saved = "";
  apply(saved);

  buttons.forEach(function (b) {
    b.addEventListener("click", function () {
      apply(b.dataset.filter);
      try { localStorage.setItem(KEY, b.dataset.filter); } catch (e) {}
    });
  });
})();
