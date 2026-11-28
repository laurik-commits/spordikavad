// Spordikaart: ringid toimumiskohtades (suurus = mängude arv ajaaknas, värv = peamine ala). Andmed: andmed.json (analuus/kaart.py), mängude tekstid: tekstid.json.
// Kaks vaadet: kindel kuupäev (terve päev, mängude nimekiri kellaaja järgi) ja tüüpiline nädal (nädalapäev × kellaaeg, keskmine aktiivsete nädalate kohta).
// Seis on URL-is (?v=…&d=…&t=…&a=…&l=…&c=lat,lon&z=suum): link taastab sama vaate. Algvaade: terve Eesti (linnalehe nupp lisab ?linn=…, siis avaneb see linn).
(function () {
  "use strict";
  var mapEl = document.getElementById("map");
  var ctl = document.getElementById("kontrollid");
  if (!mapEl || !ctl || !window.L) return;

  var BASE = Date.UTC(2026, 0, 1);
  var AKEN = 180;
  var DEFAULT_START = 18 * 60;
  var EESTI = [58.65, 25.3];                      // terve Eesti: keskpunkt; suum sõltub kaardi laiusest (kitsas ekraan 6, lai 7)
  function eestiSuum() { return mapEl.clientWidth >= 600 ? 7 : 6; }
  var WD = ["esmaspäev", "teisipäev", "kolmapäev", "neljapäev", "reede", "laupäev", "pühapäev"];
  var MON = ["jaan", "veebr", "märts", "apr", "mai", "juuni", "juuli", "aug", "sept", "okt", "nov", "dets"];
  var TASE = {1: "Tipp", 2: "Esiliigad", 4: "Noored", 5: "Koondised"};
  var ATTR = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMapi</a> kaasautorid';
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function dayOf(y, m, d) { return Math.round((Date.UTC(y, m, d) - BASE) / 86400000); }
  function ymd(day) { var t = new Date(BASE + day * 86400000); return t.getUTCFullYear() + "-" + pad(t.getUTCMonth() + 1) + "-" + pad(t.getUTCDate()); }
  function dmy(day) { var t = new Date(BASE + day * 86400000); return t.getUTCDate() + ". " + MON[t.getUTCMonth()]; }
  function weekday(day) { return (((day + 3) % 7) + 7) % 7; }          // 2026-01-01 on neljapäev
  function hm(min) { return pad(Math.floor(min / 60)) + ":" + pad(min % 60); }
  function nowTallinn() {
    var o = {};
    new Intl.DateTimeFormat("en-GB", {timeZone: "Europe/Tallinn", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit",
      minute: "2-digit", hour12: false}).formatToParts(new Date()).forEach(function (x) { o[x.type] = x.value; });
    return {d: dayOf(+o.year, +o.month - 1, +o.day), m: (+o.hour % 24) * 60 + +o.minute};
  }
  function el(tag, props, text) {
    var e = document.createElement(tag);
    if (props) Object.keys(props).forEach(function (k) { e.setAttribute(k, props[k]); });
    if (text != null) e.textContent = text;
    return e;
  }
  function q(id) { return document.getElementById(id); }
  function store(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } }

  var params = new URLSearchParams(location.search);
  var hasView = params.has("c") && params.has("z");
  // kaart ja aluskaardi plaadid luuakse kohe (algvaade terve Eesti), andmed laaditakse paralleelselt: LCP ei oota JSON-i
  var start = [EESTI[0], EESTI[1], eestiSuum()];
  if (hasView) { var cc = params.get("c").split(","); if (cc.length === 2 && isFinite(+cc[0]) && isFinite(+cc[1])) start = [+cc[0], +cc[1], +params.get("z") || 12]; else hasView = false; }
  var map = L.map(mapEl, {minZoom: 6, maxZoom: 17, zoomControl: true}).setView([start[0], start[1]], start[2]);
  // aluskaart: OpenStreetMapi standardplaadid (CARTO „light_all“ nõuab 2026. aastast API võtit); CSS teeb need heledaks (style.css .kaart .leaflet-tile-pane)
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 19, attribution: ATTR}).addTo(map);
  var T = null;           // tekstid.json: [pealkiri, liiga] mängude ridade järjekorras (laetakse hiljem)
  var redraw = function () {};
  fetch("andmed.json").then(function (r) { return r.json(); }).then(init).catch(function () {
    q("kaardimark").textContent = "Kaardi andmeid ei õnnestunud laadida.";
    q("kaardimark").hidden = false;
    document.querySelector("main.kaart").classList.remove("laeb");
    q("selgitus").textContent = "";
  });
  fetch("tekstid.json").then(function (r) { return r.json(); }).then(function (t) { T = t; redraw(); }).catch(function () {});

  function init(D) {
    var days = D.mangud.map(function (g) { return g[1]; });
    var minDay = Math.min.apply(null, days), maxDay = Math.max.apply(null, days);
    var st = {mode: "paev", day: null, wd: 4, start: DEFAULT_START, tbc: true, sports: {}, levels: {}};
    var levels = [];
    D.mangud.forEach(function (g) { if (levels.indexOf(g[4]) < 0) levels.push(g[4]); });
    levels.sort();
    function allOn() {
      D.alad.forEach(function (a, i) { st.sports[i] = true; });
      levels.forEach(function (l) { st.levels[l] = true; });
    }
    allOn();

    var layer = L.layerGroup().addTo(map);
    var markers = {}, active = null, applying = true, ready = false;

    // vaikimisi päev: täna, kui sel päeval on mänge, muidu järgmine mängupäev
    var now = nowTallinn();
    var sorted = days.slice().sort(function (a, b) { return a - b; });
    var defaultDay = sorted.filter(function (d) { return d >= now.d; })[0];
    if (defaultDay == null) defaultDay = maxDay;
    st.day = defaultDay;

    var kuup = q("kuup"), kell = q("kell"), main = document.querySelector("main.kaart");
    kuup.min = ymd(minDay); kuup.max = ymd(maxDay);

    // ---- alade ja tasemete valikud ----
    function chip(parent, label, color, on, onclick) {
      var b = el("button", {type: "button", "aria-pressed": on ? "true" : "false"});
      if (color) { var d = el("i", {"class": "dot"}); d.style.background = color; b.appendChild(d); }
      b.appendChild(document.createTextNode(label));
      b.addEventListener("click", function () { onclick(b); });
      parent.appendChild(b);
      return b;
    }
    function toggle(set, key) {
      var keys = Object.keys(set), every = keys.every(function (k) { return set[k]; });
      if (key === "k") keys.forEach(function (k) { set[k] = true; });
      else if (every) keys.forEach(function (k) { set[k] = k === String(key); });     // kõik sees: vali ainult see
      else set[key] = !set[key];
      if (!keys.some(function (k) { return set[k]; })) keys.forEach(function (k) { set[k] = true; });
      refreshChips(); changed(true);
    }
    var chipEls = [];
    var kokku = [
      [st.sports, chip(q("alad"), "Kõik", null, true, function () { toggle(st.sports, "k"); })],
      [st.levels, chip(q("tasemed"), "Kõik", null, true, function () { toggle(st.levels, "k"); })]];
    D.alad.forEach(function (a, i) { chipEls.push([st.sports, i, chip(q("alad"), a.n, a.c, true, function () { toggle(st.sports, i); })]); });
    levels.forEach(function (l) { chipEls.push([st.levels, l, chip(q("tasemed"), TASE[l] || ("Tase " + l), null, true, function () { toggle(st.levels, l); })]); });
    function refreshChips() {
      kokku.forEach(function (c) { c[1].setAttribute("aria-pressed", Object.keys(c[0]).every(function (k) { return c[0][k]; }) ? "true" : "false"); });
      chipEls.forEach(function (c) { c[2].setAttribute("aria-pressed", c[0][c[1]] ? "true" : "false"); });
    }
    function ok(g) { return st.sports[g[3]] && st.levels[g[4]]; }
    function subset(set) { return Object.keys(set).some(function (k) { return !set[k]; }); }

    // ---- filtrite riba (mobiil) ----
    var toggleBtn = q("filtritoggle");
    function activeCount() {
      var n = 0;
      if (st.mode === "nadal") n++;
      else if (st.day !== defaultDay) n++;
      if (st.mode === "nadal" && st.start !== DEFAULT_START) n++;
      if (!st.tbc) n++;
      if (subset(st.sports)) n++;
      if (subset(st.levels)) n++;
      return n;
    }
    function setPanel(open) { main.classList.toggle("suletud", !open); toggleBtn.setAttribute("aria-expanded", open ? "true" : "false"); }
    toggleBtn.addEventListener("click", function () { setPanel(main.classList.contains("suletud")); });
    setPanel(false);

    // ---- URL ----
    function encode() {
      var p = new URLSearchParams();
      p.set("v", st.mode);
      p.set("d", ymd(st.day));
      if (st.mode === "nadal") { p.set("t", String(st.start)); p.set("w", String(st.wd)); }
      if (subset(st.sports)) p.set("a", D.alad.filter(function (a, i) { return st.sports[i]; }).map(function (a) { return a.k; }).join(","));
      if (subset(st.levels)) p.set("l", levels.filter(function (l) { return st.levels[l]; }).join(","));
      if (!st.tbc) p.set("tbc", "0");
      var c = map.getCenter();
      p.set("c", c.lat.toFixed(4) + "," + c.lng.toFixed(4));
      p.set("z", String(map.getZoom()));
      return "?" + p.toString();
    }
    function writeUrl(push) {
      if (applying || !ready) return;
      var u = encode();
      if (u === location.search) return;
      try { history[push ? "pushState" : "replaceState"](null, "", location.pathname + u); } catch (e) {}
    }
    function decode(p, resetMissing) {
      if (resetMissing) { allOn(); st.mode = "paev"; st.day = defaultDay; st.wd = 4; st.start = DEFAULT_START; st.tbc = true; }
      if (p.get("v") === "nadal" || p.get("v") === "paev") st.mode = p.get("v");
      var d = (p.get("d") || "").split("-");
      if (d.length === 3 && isFinite(+d[0])) st.day = Math.min(maxDay, Math.max(minDay, dayOf(+d[0], +d[1] - 1, +d[2])));
      if (p.has("t") && isFinite(+p.get("t"))) st.start = Math.min(1380, Math.max(0, Math.round(+p.get("t") / 30) * 30));
      if (p.has("w") && +p.get("w") >= 0 && +p.get("w") <= 6) st.wd = Math.round(+p.get("w"));
      if (p.get("tbc") === "0") st.tbc = false;
      if (p.has("a")) {
        var keys = p.get("a").split(","), any = false;
        D.alad.forEach(function (a, i) { var on = keys.indexOf(a.k) >= 0; st.sports[i] = on; any = any || on; });
        if (!any) D.alad.forEach(function (a, i) { st.sports[i] = true; });
      }
      if (p.has("l")) {
        var ls = p.get("l").split(",").map(Number), anyl = false;
        levels.forEach(function (l) { var on = ls.indexOf(l) >= 0; st.levels[l] = on; anyl = anyl || on; });
        if (!anyl) levels.forEach(function (l) { st.levels[l] = true; });
      }
    }
    function syncControls() {
      kuup.value = ymd(st.day);
      q("nadalapaev").value = String(st.wd);
      kell.value = String(st.start);
      q("tbc").checked = st.tbc;
      Array.prototype.forEach.call(document.querySelectorAll('input[name="vaade"]'), function (r) { r.checked = r.value === st.mode; });
      q("paevarida").hidden = st.mode !== "paev"; q("nadalarida").hidden = st.mode !== "nadal"; q("kellarida").hidden = st.mode !== "nadal";
      refreshChips();
    }
    function changed(push) { draw(); writeUrl(push); }

    // ---- arvutus ----
    // {res: {paik: {n, s:{ala:arv}}}, games: [mängu rea indeksid] (ainult kindel kuupäev), tbc, nw, total, lo, hi}
    function compute() {
      var lo = st.mode === "paev" ? 0 : st.start, hi = st.mode === "paev" ? 1440 : Math.min(st.start + AKEN, 1440), res = {}, games = [];
      var weeks = {}, nw = 0, tbc = 0, total = 0;
      function add(g, idx) { var r = res[g[0]] || (res[g[0]] = {n: 0, s: {}}); r.n++; r.s[g[3]] = (r.s[g[3]] || 0) + 1; total++; if (st.mode === "paev") games.push(idx); }
      D.mangud.forEach(function (g, idx) {
        if (!ok(g)) return;
        if (st.mode === "paev") {
          if (g[1] !== st.day) return;
          if (g[2] < 0) { if (st.tbc) { add(g, idx); tbc++; } }
          else if (g[2] >= lo && g[2] < hi) add(g, idx);
        } else {
          if (g[2] < 0) return;
          var w = Math.floor((g[1] + 3) / 7);
          if (!weeks[w]) { weeks[w] = 1; nw++; }
          if (weekday(g[1]) === st.wd && g[2] >= lo && g[2] < hi) add(g, idx);
        }
      });
      if (st.mode === "nadal" && nw) Object.keys(res).forEach(function (k) {
        res[k].n = res[k].n / nw; Object.keys(res[k].s).forEach(function (s) { res[k].s[s] /= nw; });
      });
      return {res: res, games: games, tbc: tbc, nw: nw, total: total, lo: lo, hi: hi};
    }
    function dominant(s) { var best = null; Object.keys(s).forEach(function (k) { if (best == null || s[k] > s[best]) best = k; }); return +best; }
    function radius(n) { return Math.max(5, 7 + 9 * Math.sqrt(n)); }
    function fmt(n) { return st.mode === "paev" ? String(Math.round(n)) : (n < 10 ? n.toFixed(1).replace(".", ",") : String(Math.round(n))); }
    function title(idx) { return T && T[idx] ? T[idx][0] : D.alad[D.mangud[idx][3]].n; }

    function popup(i, r) {
      var k = D.kohad[i], box = el("div", {"class": "popup"});
      box.appendChild(el("strong", null, k.n));
      box.appendChild(el("div", {"class": "meta"}, k.l + (k.t !== "tapne" ? " · asukoht " + (k.t === "umbes" ? "ligikaudne" : "on linna keskpunkt") : "")));
      var ul = el("ul");
      Object.keys(r.s).sort(function (a, b) { return r.s[b] - r.s[a]; }).forEach(function (s) {
        ul.appendChild(el("li", null, D.alad[s].n + ": " + fmt(r.s[s]) + (st.mode === "nadal" ? " nädalas" : "")));
      });
      box.appendChild(ul);
      var best = null;
      D.mangud.forEach(function (g, idx) {
        if (g[0] !== i || !ok(g) || !(g[1] > now.d || (g[1] === now.d && (g[2] < 0 || g[2] >= now.m)))) return;
        if (best == null || g[1] < D.mangud[best][1] || (g[1] === D.mangud[best][1] && g[2] < D.mangud[best][2])) best = idx;
      });
      if (best != null) {
        var g = D.mangud[best];
        var p = el("div", {"class": "next"}, "Järgmine mäng: " + dmy(g[1]) + (g[2] >= 0 ? " " + hm(g[2]) : "") + ", ");
        p.appendChild(el("a", {href: "../m/" + g[5] + "/"}, title(best)));
        if (T && T[best]) p.appendChild(document.createTextNode(" (" + T[best][1] + ")"));
        box.appendChild(p);
      }
      return box;
    }

    // ---- esiletõstmine ringi ja nimekirja vahel ----
    var ol = q("nimekiri");
    function rowsOf(i) { return ol.querySelectorAll('li[data-p="' + i + '"]'); }
    function highlight(i, on) {
      Array.prototype.forEach.call(rowsOf(i), function (li) { li.classList.toggle("esile", on); });
      var m = markers[i];
      if (m) { m.setStyle(on ? {weight: 5, fillOpacity: 0.85} : {weight: 2, fillOpacity: 0.5}); if (on) m.bringToFront(); }
    }
    function selectVenue(i) {
      Array.prototype.forEach.call(ol.querySelectorAll("li.aktiivne"), function (li) { li.classList.remove("aktiivne"); });
      active = i;
      var rows = rowsOf(i);
      Array.prototype.forEach.call(rows, function (li) { li.classList.add("aktiivne"); });
      if (rows.length) ol.scrollTo({top: Math.max(0, rows[0].offsetTop - 4), behavior: REDUCED ? "auto" : "smooth"});
    }
    function pointOf(li) { var p = li && li.getAttribute("data-p"); return p == null ? null : +p; }
    ol.addEventListener("mouseover", function (e) { var li = e.target.closest("li"); if (li) highlight(pointOf(li), true); });
    ol.addEventListener("mouseout", function (e) { var li = e.target.closest("li"); if (li) highlight(pointOf(li), false); });
    ol.addEventListener("focusin", function (e) { var li = e.target.closest("li"); if (li) highlight(pointOf(li), true); });
    ol.addEventListener("focusout", function (e) { var li = e.target.closest("li"); if (li) highlight(pointOf(li), false); });
    ol.addEventListener("click", function (e) {
      if (e.target.closest("a")) return;                               // mängu link avab mängu lehe
      var li = e.target.closest("li"), i = pointOf(li);
      if (i == null || !markers[i]) return;
      map.setView([D.kohad[i].la, D.kohad[i].lo], Math.max(map.getZoom(), 12));
      markers[i].fire("click");
    });

    function draw() {
      var c = compute();
      layer.clearLayers(); markers = {};
      var order = Object.keys(c.res).sort(function (a, b) { return c.res[b].n - c.res[a].n; });
      order.slice().reverse().forEach(function (key) {            // suured all, väikesed peal
        var i = +key, r = c.res[key], k = D.kohad[i], col = D.alad[dominant(r.s)].c;
        var m = L.circleMarker([k.la, k.lo], {radius: radius(r.n), color: col, weight: 2, fillColor: col, fillOpacity: 0.5,
          dashArray: k.t === "tapne" ? null : "4 3"});
        m.on("click", function () { m.bindPopup(popup(i, r), {maxWidth: 280}).openPopup(); selectVenue(i); });
        m.on("mouseover", function () { highlight(i, true); });
        m.on("mouseout", function () { highlight(i, false); });
        m.addTo(layer); markers[i] = m;
      });
      var kellaTekst = hm(c.lo) + "–" + hm(c.hi);
      q("kellatekst").textContent = kellaTekst;
      var t;
      if (st.mode === "paev") {
        t = "Mänge kuupäeval " + dmy(st.day) + " (" + WD[weekday(st.day)] + "): " + Math.round(c.total) + ", kohti " + order.length +
          (c.tbc ? ", sh " + c.tbc + " kellaajata üritust" : "") + ".";
      } else {
        var sum = order.reduce(function (s, k) { return s + c.res[k].n; }, 0);
        t = "Tüüpiline " + WD[st.wd] + " kell " + kellaTekst + ": keskmiselt " + fmt(sum) + " mängu nädalas, kohti " + order.length + ". Keskmine on jagatud " + c.nw +
          " aktiivse nädalaga (nädalad, kus valitud aladel oli vähemalt üks kellaajaga mäng). Aluseks on kõik andmetes olevad mängud, möödunud ja tulevased; kellaajata üritusi ei arvestata.";
      }
      q("selgitus").textContent = t;
      toggleBtn.textContent = "Filtrid (" + activeCount() + " aktiivset)";

      while (ol.firstChild) ol.removeChild(ol.firstChild);
      if (!order.length) { ol.appendChild(el("li", {"class": "tyhi"}, "Valitud aknas mänge pole. Muuda kuupäeva, kellaaega või valikuid.")); return; }
      if (st.mode === "paev") {
        // kindel kuupäev: mängud kellaaja järgi (kellaajata lõpus), iga rida viib mängu lehele
        var rows = c.games.slice().sort(function (a, b) {
          var ma = D.mangud[a][2], mb = D.mangud[b][2];
          return (ma < 0 ? 9999 : ma) - (mb < 0 ? 9999 : mb) || title(a).localeCompare(title(b), "et");
        });
        rows.slice(0, 400).forEach(function (idx) {
          var g = D.mangud[idx], k = D.kohad[g[0]], li = el("li", {"data-p": String(g[0]), "class": "mang"});
          li.appendChild(el("span", {"class": "kell"}, g[2] < 0 ? "terve päev" : hm(g[2])));
          li.appendChild(el("a", {href: "../m/" + g[5] + "/"}, title(idx)));
          var sub = el("span", {"class": "rida2"}), dot = el("i", {"class": "dot"});
          dot.style.background = D.alad[g[3]].c;
          sub.appendChild(dot);
          sub.appendChild(document.createTextNode(D.alad[g[3]].n + " · " + k.n + ", " + k.l + (T && T[idx] ? " · " + T[idx][1] : "")));
          li.appendChild(sub);
          ol.appendChild(li);
        });
      } else {
        // tüüpiline nädal: kellaaegu pole (keskmine paljude nädalate kohta), seega kohad mängude arvu järgi
        order.slice(0, 40).forEach(function (key) {
          var i = +key, li = el("li", {"data-p": String(i)});
          li.appendChild(el("button", {type: "button"}, D.kohad[i].n + " (" + D.kohad[i].l + "): " + fmt(c.res[key].n) + " mängu nädalas"));
          ol.appendChild(li);
        });
      }
      if (active != null) Array.prototype.forEach.call(rowsOf(active), function (li) { li.classList.add("aktiivne"); });
    }
    redraw = draw;

    // ---- juhtnupud ----
    function setDay(d) { st.day = Math.min(maxDay, Math.max(minDay, d)); kuup.value = ymd(st.day); changed(true); }
    kuup.addEventListener("change", function () {
      var p = kuup.value.split("-"); if (p.length === 3) setDay(dayOf(+p[0], +p[1] - 1, +p[2]));
    });
    q("eelmine").addEventListener("click", function () { setDay(st.day - 1); });
    q("jargmine").addEventListener("click", function () { setDay(st.day + 1); });
    q("tana").addEventListener("click", function () { setDay(now.d); });
    q("tbc").addEventListener("change", function (e) { st.tbc = e.target.checked; changed(true); });
    q("nadalapaev").addEventListener("change", function (e) { st.wd = +e.target.value; changed(true); });
    kell.addEventListener("input", function () { st.start = +kell.value; draw(); writeUrl(false); });   // lohistamine ei täida ajalugu
    Array.prototype.forEach.call(document.querySelectorAll('input[name="vaade"]'), function (r) {
      r.addEventListener("change", function () {
        st.mode = r.value;
        q("paevarida").hidden = st.mode !== "paev"; q("nadalarida").hidden = st.mode !== "nadal"; q("kellarida").hidden = st.mode !== "nadal";
        changed(true);
      });
    });
    q("kogu").addEventListener("click", function () { map.setView(EESTI, eestiSuum()); });
    var moveTimer = null;
    map.on("moveend", function () { clearTimeout(moveTimer); moveTimer = setTimeout(function () { writeUrl(false); }, 250); });
    window.addEventListener("popstate", function () {
      applying = true;
      var p = new URLSearchParams(location.search);
      decode(p, true); syncControls();
      var cc = (p.get("c") || "").split(",");
      if (cc.length === 2 && isFinite(+cc[0]) && isFinite(+cc[1])) map.setView([+cc[0], +cc[1]], +p.get("z") || map.getZoom(), {animate: false});
      draw();
      setTimeout(function () { applying = false; }, 400);
    });

    // ---- algseis: URL (c, z) → muidu ?linn= (linnalehelt tulnud) → muidu terve Eesti ----
    decode(params, false);
    syncControls();
    if (!hasView) {
      var slug = params.get("linn");
      var city = (D.linnad || []).filter(function (x) { return x.s === slug; })[0];
      if (city) map.setView([city.la, city.lo], city.z, {animate: false});
    }
    draw();
    main.classList.remove("laeb");
    setTimeout(function () { applying = false; ready = true; }, 500);   // algvaate liikumine ei kirjuta URL-i
  }
})();
