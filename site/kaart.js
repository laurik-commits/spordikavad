// Spordikaart: ringid toimumiskohtades (suurus = mängude arv ajaaknas, värv = peamine ala). Andmed: andmed.json (analuus/kaart.py).
// Kaks vaadet: kindel kuupäev (3 tunni aken) ja tüüpiline nädal (nädalapäev × kellaaeg, keskmine aktiivsete nädalate kohta).
(function () {
  "use strict";
  var mapEl = document.getElementById("map");
  var ctl = document.getElementById("kontrollid");
  if (!mapEl || !ctl || !window.L) return;

  var BASE = Date.UTC(2026, 0, 1);
  var AKEN = 180;
  var WD = ["esmaspäev", "teisipäev", "kolmapäev", "neljapäev", "reede", "laupäev", "pühapäev"];
  var MON = ["jaan", "veebr", "märts", "apr", "mai", "juuni", "juuli", "aug", "sept", "okt", "nov", "dets"];
  var TASE = {1: "Tipp", 2: "Esiliigad", 4: "Noored", 5: "Koondised"};
  var ATTR = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMapi</a> kaasautorid';

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

  // kaart ja aluskaardi plaadid luuakse kohe, andmed (andmed.json) laaditakse paralleelselt: LCP ei oota JSON-i
  var map = L.map(mapEl, {minZoom: 6, maxZoom: 17, zoomControl: true}).setView([58.65, 25.3], 7);
  // aluskaart: OpenStreetMapi standardplaadid (CARTO „light_all“ nõuab 2026. aastast API võtit); CSS teeb need heledaks (style.css .kaart .leaflet-tile-pane)
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 19, attribution: ATTR}).addTo(map);
  fetch("andmed.json").then(function (r) { return r.json(); }).then(init).catch(function () {
    document.getElementById("kaardimark").textContent = "Kaardi andmeid ei õnnestunud laadida. Tabel allpool töötab ilma kaardita.";
    q("selgitus").textContent = "";
  });
  function q(id) { return document.getElementById(id); }

  function init(D) {
    document.getElementById("kaardimark").textContent = "";
    var days = D.mangud.map(function (g) { return g[1]; });
    var minDay = Math.min.apply(null, days), maxDay = Math.max.apply(null, days);
    var st = {mode: "paev", day: null, wd: 4, start: 18 * 60, tbc: true, sports: {}, levels: {}};
    D.alad.forEach(function (a, i) { st.sports[i] = true; });
    var levels = [];
    D.mangud.forEach(function (g) { if (levels.indexOf(g[4]) < 0) levels.push(g[4]); });
    levels.sort().forEach(function (l) { st.levels[l] = true; });

    var layer = L.layerGroup().addTo(map);
    var markers = {};

    // vaikimisi päev: täna, kui sel päeval on mänge, muidu järgmine mängupäev
    var now = nowTallinn();
    var sorted = days.slice().sort(function (a, b) { return a - b; });
    st.day = sorted.filter(function (d) { return d >= now.d; })[0];
    if (st.day == null) st.day = maxDay;

    var kuup = q("kuup"), kell = q("kell");
    kuup.min = ymd(minDay); kuup.max = ymd(maxDay);

    // alade ja tasemete valikud
    function chip(parent, label, color, on, onclick) {
      var b = el("button", {type: "button", "aria-pressed": on ? "true" : "false"});
      if (color) { var d = el("i", {"class": "dot"}); d.style.background = color; b.appendChild(d); }
      b.appendChild(document.createTextNode(label));
      b.addEventListener("click", function () { onclick(b); });
      parent.appendChild(b);
      return b;
    }
    function toggle(set, key, b) {
      var keys = Object.keys(set), allOn = keys.every(function (k) { return set[k]; });
      if (key === "k") keys.forEach(function (k) { set[k] = true; });
      else if (allOn) keys.forEach(function (k) { set[k] = k === String(key); });     // kõik sees: vali ainult see
      else set[key] = !set[key];
      if (!keys.some(function (k) { return set[k]; })) keys.forEach(function (k) { set[k] = true; });
      refreshChips(); draw();
    }
    var chipEls = [];
    var kokku = [
      [st.sports, chip(q("alad"), "Kõik", null, true, function () { toggle(st.sports, "k"); })],
      [st.levels, chip(q("tasemed"), "Kõik", null, true, function () { toggle(st.levels, "k"); })]];
    D.alad.forEach(function (a, i) { chipEls.push([st.sports, i, chip(q("alad"), a.n, a.c, true, function (b) { toggle(st.sports, i, b); })]); });
    levels.forEach(function (l) { chipEls.push([st.levels, l, chip(q("tasemed"), TASE[l] || ("Tase " + l), null, true, function (b) { toggle(st.levels, l, b); })]); });
    function refreshChips() {
      kokku.forEach(function (c) { c[1].setAttribute("aria-pressed", Object.keys(c[0]).every(function (k) { return c[0][k]; }) ? "true" : "false"); });
      chipEls.forEach(function (c) { c[2].setAttribute("aria-pressed", c[0][c[1]] ? "true" : "false"); });
    }

    function ok(g) { return st.sports[g[3]] && st.levels[g[4]]; }

    // ühe ajaakna arvutus: {counts: {paik: {kokku, ala:{}}}, kellajata, nadalaid}
    function compute() {
      var lo = st.start, hi = Math.min(st.start + AKEN, 1440), res = {};
      var weeks = {}, nw = 0, tbc = 0, total = 0;
      function add(g) { var r = res[g[0]] || (res[g[0]] = {n: 0, s: {}}); r.n++; r.s[g[3]] = (r.s[g[3]] || 0) + 1; total++; }
      D.mangud.forEach(function (g) {
        if (!ok(g)) return;
        if (st.mode === "paev") {
          if (g[1] !== st.day) return;
          if (g[2] < 0) { if (st.tbc) { add(g); tbc++; } }
          else if (g[2] >= lo && g[2] < hi) add(g);
        } else {
          if (g[2] < 0) return;
          var w = Math.floor((g[1] + 3) / 7);
          if (!weeks[w]) { weeks[w] = 1; nw++; }
          if (weekday(g[1]) === st.wd && g[2] >= lo && g[2] < hi) add(g);
        }
      });
      if (st.mode === "nadal" && nw) Object.keys(res).forEach(function (k) {
        res[k].n = res[k].n / nw; Object.keys(res[k].s).forEach(function (s) { res[k].s[s] /= nw; });
      });
      return {res: res, tbc: tbc, nw: nw, total: total, lo: lo, hi: hi};
    }
    function dominant(s) { var best = null; Object.keys(s).forEach(function (k) { if (best == null || s[k] > s[best]) best = k; }); return +best; }
    function radius(n) { return Math.max(5, 7 + 9 * Math.sqrt(n)); }
    function pct(x) { return String(x).replace(".", ","); }
    function fmt(n) { return st.mode === "paev" ? String(Math.round(n)) : (n < 10 ? n.toFixed(1).replace(".", ",") : String(Math.round(n))); }

    function popup(i, r) {
      var k = D.kohad[i], box = el("div", {"class": "popup"});
      box.appendChild(el("strong", null, k.n));
      box.appendChild(el("div", {"class": "meta"}, k.l + (k.t !== "tapne" ? " · asukoht " + (k.t === "umbes" ? "ligikaudne" : "on linna keskpunkt") : "")));
      var ul = el("ul");
      Object.keys(r.s).sort(function (a, b) { return r.s[b] - r.s[a]; }).forEach(function (s) {
        ul.appendChild(el("li", null, D.alad[s].n + ": " + fmt(r.s[s]) + (st.mode === "nadal" ? " nädalas" : "")));
      });
      box.appendChild(ul);
      var nxt = D.tulevased.filter(function (t) { return t.p === i && ok([0, 0, 0, t.s, t.l]) && (t.d > now.d || (t.d === now.d && (t.m < 0 || t.m >= now.m))); })
        .sort(function (a, b) { return a.d - b.d || a.m - b.m; })[0];
      if (nxt) {
        var a = el("a", {href: "../m/" + nxt.id + "/"}, nxt.t);
        var p = el("div", {"class": "next"}, "Järgmine mäng: " + dmy(nxt.d) + (nxt.m >= 0 ? " " + hm(nxt.m) : "") + ", ");
        p.appendChild(a); p.appendChild(document.createTextNode(" (" + nxt.lg + ")"));
        box.appendChild(p);
      }
      if (k.hv) box.appendChild(el("div", {"class": "meta"}, "Kodu võidud: " + pct(k.hv[1]) + "% (ootus " + pct(k.hv[2]) + "%, " + k.hv[0] + " mängu, " + k.hv[3] + " kodumeeskonda)"));
      return box;
    }

    function draw() {
      var c = compute();
      layer.clearLayers(); markers = {};
      var order = Object.keys(c.res).sort(function (a, b) { return c.res[b].n - c.res[a].n; });
      order.slice().reverse().forEach(function (key) {            // suured all, väikesed peal
        var i = +key, r = c.res[key], k = D.kohad[i], col = D.alad[dominant(r.s)].c;
        var m = L.circleMarker([k.la, k.lo], {radius: radius(r.n), color: col, weight: 2, fillColor: col, fillOpacity: 0.5,
          dashArray: k.t === "tapne" ? null : "4 3"});
        m.on("click", function () { m.bindPopup(popup(i, r), {maxWidth: 280}).openPopup(); });
        m.addTo(layer); markers[i] = m;
      });
      var kell = hm(c.lo) + "–" + hm(c.hi === 1440 ? 1440 : c.hi);
      q("kellatekst").textContent = kell;
      var t;
      if (st.mode === "paev") {
        t = "Mänge kuupäeval " + dmy(st.day) + " (" + WD[weekday(st.day)] + ") kell " + kell + ": " + Math.round(c.total) + ", kohti " + order.length +
          (c.tbc ? ", sh " + c.tbc + " kellaajata üritust" : "") + ".";
      } else {
        var sum = order.reduce(function (s, k) { return s + c.res[k].n; }, 0);
        t = "Tüüpiline " + WD[st.wd] + " kell " + kell + ": keskmiselt " + fmt(sum) + " mängu nädalas, kohti " + order.length + ". Keskmine on jagatud " + c.nw +
          " aktiivse nädalaga (nädalad, kus valitud aladel oli vähemalt üks kellaajaga mäng). Aluseks on kõik andmetes olevad mängud, möödunud ja tulevased; kellaajata üritusi ei arvestata.";
      }
      q("selgitus").textContent = t;
      var ol = q("nimekiri");
      while (ol.firstChild) ol.removeChild(ol.firstChild);
      if (!order.length) ol.appendChild(el("li", null, "Valitud aknas mänge pole. Muuda kuupäeva, kellaaega või valikuid."));
      order.slice(0, 15).forEach(function (key) {
        var i = +key, r = c.res[key], li = el("li");
        var b = el("button", {type: "button"}, D.kohad[i].n + " (" + D.kohad[i].l + "): " + fmt(r.n) + (st.mode === "nadal" ? " mängu nädalas" : " mängu"));
        b.addEventListener("click", function () { map.setView([D.kohad[i].la, D.kohad[i].lo], Math.max(map.getZoom(), 12)); markers[i].fire("click"); });
        li.appendChild(b); ol.appendChild(li);
      });
    }

    function setDay(d) { st.day = Math.min(maxDay, Math.max(minDay, d)); kuup.value = ymd(st.day); draw(); }
    kuup.value = ymd(st.day);
    kuup.addEventListener("change", function () {
      var p = kuup.value.split("-"); if (p.length === 3) setDay(dayOf(+p[0], +p[1] - 1, +p[2]));
    });
    q("eelmine").addEventListener("click", function () { setDay(st.day - 1); });
    q("jargmine").addEventListener("click", function () { setDay(st.day + 1); });
    q("tana").addEventListener("click", function () { setDay(now.d); });
    q("tbc").addEventListener("change", function (e) { st.tbc = e.target.checked; draw(); });
    q("nadalapaev").value = String(st.wd);
    q("nadalapaev").addEventListener("change", function (e) { st.wd = +e.target.value; draw(); });
    kell.value = String(st.start);
    kell.addEventListener("input", function () { st.start = +kell.value; draw(); });
    Array.prototype.forEach.call(document.querySelectorAll('input[name="vaade"]'), function (r) {
      r.addEventListener("change", function () {
        st.mode = r.value;
        q("paevarida").hidden = st.mode !== "paev"; q("nadalarida").hidden = st.mode !== "nadal";
        draw();
      });
    });
    draw();
  }
})();
