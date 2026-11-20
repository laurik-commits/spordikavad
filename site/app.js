// Alafilter: peidab teiste alade read. Valik jäetakse meelde ka järgmistel päevadel.
// Välise lingiga ala (korvpall) nupp näitab mängude asemel selgitust ja linki.
(function () {
  var KEY = "spordikavad-ala";
  var buttons = document.querySelectorAll(".filters button");
  var rows = document.querySelectorAll(".games li");
  var empty = document.querySelector(".empty-filter");
  var none = document.querySelector(".none");
  var notes = document.querySelectorAll(".extnote");

  // linna- ja tasemevalik: jäta valik meelde; avalehel (Tallinn, kõrgliigad, täna) suuna meelde jäetud valikule
  var CITY = "spordikavad-linn", LEVEL = "spordikavad-tase";
  var body = document.body;
  function get(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  if (body.dataset.index && body.dataset.region === body.dataset.default && body.dataset.level === "1") {
    var city = get(CITY), level = get(LEVEL);
    var path = "";
    if (level === "2") path += "esiliigad/";
    if (city && city !== body.dataset.default && document.querySelector('.city a[data-region="' + city + '"]')) {
      path += city + "/";
    }
    if (path) { location.replace(body.dataset.root + path); return; }
  }
  document.querySelectorAll(".city a[data-region]").forEach(function (a) {
    a.addEventListener("click", function () { set(CITY, a.dataset.region); });
  });
  document.querySelectorAll(".tier a[data-level]").forEach(function (a) {
    a.addEventListener("click", function () { set(LEVEL, a.dataset.level); });
  });
  // avatud menüü sulgub, kui klõpsad mujale; korraga on lahti ainult üks
  document.addEventListener("click", function (ev) {
    document.querySelectorAll(".pick-menu[open]").forEach(function (d) {
      if (!d.contains(ev.target)) d.removeAttribute("open");
    });
  });

  // kui igapäevane uuendus on seiskunud, ütle seda (leht on ehitatud rohkem kui 1 päev tagasi)
  var built = body.dataset.built;
  if (built) {
    var now = new Date();
    var today = now.getFullYear() + "-" + ("0" + (now.getMonth() + 1)).slice(-2) + "-" + ("0" + now.getDate()).slice(-2);
    var ageDays = (Date.parse(today) - Date.parse(built)) / 864e5;
    var stale = document.querySelector(".stale");
    if (stale && ageDays >= 2) stale.hidden = false;
  }

  // päevade ribal too valitud päev nähtavale
  var cur = document.querySelector('.days [aria-current="page"]');
  if (cur && cur.parentNode.previousElementSibling) cur.scrollIntoView({ block: "nearest", inline: "center" });

  function apply(sport) {
    var btn = document.querySelector('.filters button[data-filter="' + sport + '"]');
    var ext = !!(btn && btn.dataset.ext);
    var shown = 0;
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.filter === sport)); });
    // välise lingi ala (korvpall): märkus mängude asemel; tavalise ala märkus (nt hoki): märkus mängude kohal
    notes.forEach(function (n) { n.classList.toggle("show", sport !== "" && n.dataset.note === sport); });
    rows.forEach(function (r) {
      var hide = ext || (sport !== "" && r.dataset.sport !== sport);
      r.hidden = hide;
      if (!hide) shown++;
    });
    if (empty) empty.hidden = ext || shown > 0 || rows.length === 0;
    if (none) none.hidden = ext;
    // päevade riba: valitud ala korral on paksud ainult päevad, kus selle ala mänge on
    document.querySelectorAll(".days a[data-sports]").forEach(function (a) {
      var list = a.dataset.sports ? a.dataset.sports.split(" ") : [];
      var has = sport === "" ? list.length > 0 : list.indexOf(sport) !== -1;
      a.classList.toggle("empty", !has);
    });
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
