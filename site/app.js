// Alavalik (päise rippmenüü): peidab teiste alade read. Valik jäetakse meelde ka järgmistel päevadel.
// Välise lingiga ala (korvpall) nupp näitab mängude asemel selgitust ja linki.
(function () {
  var KEY = "spordikavad-ala";
  // ala või alade rühm (data-group = rühma alad); rühma avamise nool (.gtog) pole valik
  var buttons = document.querySelectorAll(".filters button[data-filter]");
  var rows = document.querySelectorAll(".games li");
  var empty = document.querySelector(".empty-filter");
  var none = document.querySelector(".none");
  var notes = document.querySelectorAll(".extnote");

  // linna- ja tasemevalik: jäta valik meelde; avalehel (Kogu Eesti, kõik liigad, täna) suuna meelde jäetud valikule
  var CITY = "spordikavad-linn", LEVEL = "spordikavad-tase";
  var body = document.body;
  function get(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  if (body.dataset.index && body.dataset.region === body.dataset.default &&
      body.dataset.level === body.dataset.defaultLevel) {
    var city = get(CITY), level = get(LEVEL);
    var prefixes = {};
    try { prefixes = JSON.parse(body.dataset.levels || "{}"); } catch (e) {}
    var path = (level && level in prefixes) ? prefixes[level] : "";
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

  // jagamine: telefonis süsteemi jagamisaken, mujal kopeeritakse link (tekst + aadress)
  document.querySelectorAll(".share[data-url]").forEach(function (b) {
    b.addEventListener("click", function () {
      var d = { title: b.dataset.title, text: b.dataset.text, url: b.dataset.url };
      if (navigator.share) { navigator.share(d).catch(function () {}); return; }
      function done() {
        b.classList.add("copied");
        setTimeout(function () { b.classList.remove("copied"); }, 2000);
      }
      var line = d.text + " " + d.url;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(line).then(done, function () { window.prompt("Kopeeri link:", d.url); });
      } else {
        window.prompt("Kopeeri link:", d.url);
      }
    });
  });

  // päevade ribal too valitud päev nähtavale
  var cur = document.querySelector('.days [aria-current="page"]');
  if (cur && cur.parentNode.previousElementSibling) cur.scrollIntoView({ block: "nearest", inline: "center" });

  function apply(sport) {
    var btn = document.querySelector('.filters button[data-filter="' + sport + '"]');
    var ext = !!(btn && btn.dataset.ext);
    var members = btn && btn.dataset.group ? btn.dataset.group.split(" ") : null;  // alade rühm
    function matches(s) { return sport === "" || (members ? members.indexOf(s) !== -1 : s === sport); }
    var shown = 0;
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.filter === sport)); });
    // päise lauses näita valitud ala ("jalgpallis") või rühma ("talialadel") koos värvitäppidega
    var cur = document.querySelector(".sport summary .cur");
    if (cur && btn) {
      cur.textContent = btn.dataset.word || btn.dataset.label;
      if (members) {
        var dots = document.createElement("span");
        dots.className = "gdots";
        members.forEach(function (s) { var i = document.createElement("i"); i.className = "s-" + s; dots.appendChild(i); });
        cur.insertBefore(dots, cur.firstChild);
      } else if (sport) {
        var dot = document.createElement("i");
        dot.className = "dot s-" + sport;
        cur.insertBefore(dot, cur.firstChild);
      }
    }
    // valitud ala rühm on menüüs lahti
    var inGroup = btn && btn.closest(".gsub");
    if (inGroup) toggleGroup(inGroup.parentNode, true);
    // välise lingi ala (korvpall): märkus mängude asemel; tavalise ala märkus (nt hoki): märkus mängude kohal (rühmal mitte)
    notes.forEach(function (n) { n.classList.toggle("show", sport !== "" && !members && n.dataset.note === sport); });
    rows.forEach(function (r) {
      var hide = ext || !matches(r.dataset.sport);
      r.hidden = hide;
      if (!hide) shown++;
    });
    // ala ilma mängudeta (hall nupp): oma teade on juba näha, üldist "mänge pole" teksti ei korrata
    var nogames = !!(btn && btn.dataset.none);
    if (empty) empty.hidden = ext || nogames || shown > 0 || rows.length === 0;
    if (none) none.hidden = ext || nogames;
    // päevade riba: valitud ala korral on paksud ainult päevad, kus selle ala mänge on
    document.querySelectorAll(".days a[data-sports]").forEach(function (a) {
      var list = a.dataset.sports ? a.dataset.sports.split(" ") : [];
      var has = sport === "" ? list.length > 0 : list.some(matches);
      a.classList.toggle("empty", !has);
    });
    var list = document.querySelector(".games");
    if (list) list.hidden = ext;
  }

  // rühma nool: avab või sulgeb rühma alad (menüü jääb lahti)
  function toggleGroup(grp, open) {
    var tog = grp.querySelector(".gtog"), sub = grp.querySelector(".gsub");
    if (!tog || !sub) return;
    var name = grp.querySelector("[data-group]").dataset.label;
    tog.setAttribute("aria-expanded", String(open));
    tog.setAttribute("aria-label", (open ? "Peida" : "Näita") + " rühma " + name + " alad");
    sub.hidden = !open;
  }
  document.querySelectorAll(".filters .gtog").forEach(function (t) {
    t.addEventListener("click", function () { toggleGroup(t.closest(".grp"), t.getAttribute("aria-expanded") !== "true"); });
  });

  var saved = "";
  try { saved = localStorage.getItem(KEY) || ""; } catch (e) {}
  var savedBtn = saved && document.querySelector('.filters button[data-filter="' + saved + '"]');
  // välise lingi valikut ei jäeta meelde: järgmisel avamisel näeb jälle mänge
  if (!savedBtn || savedBtn.dataset.ext) saved = "";
  apply(saved);

  buttons.forEach(function (b) {
    b.addEventListener("click", function () {
      apply(b.dataset.filter);
      var menu = b.closest("details");
      if (menu) menu.removeAttribute("open");
      if (!b.dataset.ext) {
        try { localStorage.setItem(KEY, b.dataset.filter); } catch (e) {}
      }
    });
  });
})();
