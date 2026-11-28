// Spordikaart: ringid toimumiskohtades (suurus = mängude arv ajaaknas, värv = peamine ala). Andmed: andmed.json (analuus/kaart.py), mängude tekstid: tekstid.json.
// Kaks vaadet: päev (valitud kuupäeva mängud) ja nädal (7 päeva alates valitud kuupäevast); nimekiri kellaaja järgi, nädalal päevade kaupa. Filtrid kehtivad terve valitud vahemiku peale.
// Seis on URL-is (?v=paev|nadal&d=…&a=…&l=…&tbc=0&c=lat,lon&z=suum): link taastab sama vaate. Algvaade: terve Eesti (linnalehe nupp lisab ?linn=…, siis avaneb see linn).
(function () {
  "use strict";
  var mapEl = document.getElementById("map");
  var ctl = document.getElementById("kontrollid");
  if (!mapEl || !ctl || !window.L) return;

  var BASE = Date.UTC(2026, 0, 1);
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
    var st = {mode: "paev", day: null, tbc: true, sports: {}, levels: {}};
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

    var kuup = q("kuup"), main = document.querySelector("main.kaart");
    kuup.min = ymd(minDay); kuup.max = ymd(maxDay);

    // ---- alade ja tasemete valikud (nupul on mängude arv valitud vahemikus; tühjad hallid ja lõpus) ----
    function chip(parent, label, color, onclick) {
      var b = el("button", {type: "button", "aria-pressed": "true"});
      if (color) { var d = el("i", {"class": "dot"}); d.style.background = color; b.appendChild(d); }
      b.appendChild(document.createTextNode(label));
      var n = el("span", {"class": "n"}); b.appendChild(n);
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
      changed(true);
    }
    var chipEls = [];
    var kokku = [
      [st.sports, chip(q("alad"), "Kõik", null, function () { toggle(st.sports, "k"); }), q("alad")],
      [st.levels, chip(q("tasemed"), "Kõik", null, function () { toggle(st.levels, "k"); }), q("tasemed")]];
    D.alad.forEach(function (a, i) { chipEls.push([st.sports, i, chip(q("alad"), a.n, a.c, function () { toggle(st.sports, i); }), q("alad")]); });
    levels.forEach(function (l) { chipEls.push([st.levels, l, chip(q("tasemed"), TASE[l] || ("Tase " + l), null, function () { toggle(st.levels, l); }), q("tasemed")]); });
    function inRange(g) { var hi = st.mode === "nadal" ? st.day + 6 : st.day; return g[1] >= st.day && g[1] <= hi && (g[2] >= 0 || st.tbc); }
    function refreshChips() {
      // mängude arv valitud vahemikus: alanupul arvestatakse taseme valikut, tasemenupul alade valikut
      var cs = {}, cl = {};
      D.mangud.forEach(function (g) {
        if (!inRange(g)) return;
        if (st.levels[g[4]]) cs[g[3]] = (cs[g[3]] || 0) + 1;
        if (st.sports[g[3]]) cl[g[4]] = (cl[g[4]] || 0) + 1;
      });
      kokku.forEach(function (c) {
        var every = Object.keys(c[0]).every(function (k) { return c[0][k]; });
        c[1].setAttribute("aria-pressed", every ? "true" : "false");
      });
      var every = {sports: Object.keys(st.sports).every(function (k) { return st.sports[k]; }), levels: Object.keys(st.levels).every(function (k) { return st.levels[k]; })};
      chipEls.forEach(function (c) {
        var isSport = c[0] === st.sports, n = (isSport ? cs : cl)[c[1]] || 0;
        c[2].querySelector(".n").textContent = " " + n;
        c[2].setAttribute("aria-pressed", c[0][c[1]] ? "true" : "false");
        // tühi nupp on välja lülitatud, välja arvatud juba valitud nupp alamhulga režiimis (et seda saaks tühistada)
        var off = n === 0 && ((isSport ? every.sports : every.levels) || !c[0][c[1]]);
        c[2].disabled = off;
        c[2].classList.toggle("tyhi", n === 0);
      });
      // tühjad nupud lõppu (algjärjekord jääb muus osas samaks)
      [q("alad"), q("tasemed")].forEach(function (box) {
        var list = chipEls.filter(function (c) { return c[3] === box; });
        list.filter(function (c) { return !c[2].classList.contains("tyhi"); }).concat(list.filter(function (c) { return c[2].classList.contains("tyhi"); }))
          .forEach(function (c) { box.appendChild(c[2]); });
      });
    }
    function ok(g) { return st.sports[g[3]] && st.levels[g[4]]; }
    function subset(set) { return Object.keys(set).some(function (k) { return !set[k]; }); }

    // ---- filtrite riba (mobiil) ----
    var toggleBtn = q("filtritoggle");
    function activeCount() {
      var n = 0;
      if (st.day !== defaultDay) n++;
      if (!st.tbc) n++;
      if (subset(st.sports)) n++;
      if (subset(st.levels)) n++;
      return n;
    }
    function setPanel(open) {
      main.classList.toggle("suletud", !open); toggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
      setTimeout(function () { map.invalidateSize(); }, 60);       // kaart muudab kõrgust (mobiilis jääb filtreid avades nähtavale)
    }
    toggleBtn.addEventListener("click", function () { setPanel(main.classList.contains("suletud")); });
    setPanel(false);

    // ---- URL ----
    function encode() {
      var p = new URLSearchParams();
      p.set("v", st.mode);
      p.set("d", ymd(st.day));
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
      if (resetMissing) { allOn(); st.mode = "paev"; st.day = defaultDay; st.tbc = true; }
      if (p.get("v") === "nadal" || p.get("v") === "paev") st.mode = p.get("v");
      var d = (p.get("d") || "").split("-");
      if (d.length === 3 && isFinite(+d[0])) st.day = Math.min(maxDay, Math.max(minDay, dayOf(+d[0], +d[1] - 1, +d[2])));
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
      q("tbc").checked = st.tbc;
      Array.prototype.forEach.call(document.querySelectorAll('input[name="vaade"]'), function (r) { r.checked = r.value === st.mode; });
      modeUi();
    }
    function modeUi() {
      var w = st.mode === "nadal";
      q("kuuplabel").textContent = w ? "Nädala algus" : "Kuupäev";
      q("eelmine").setAttribute("aria-label", w ? "Eelmine nädal" : "Eelmine päev");
      q("jargmine").setAttribute("aria-label", w ? "Järgmine nädal" : "Järgmine päev");
    }
    function changed(push) { draw(); writeUrl(push); }

    // ---- arvutus ----
    // {res: {paik: {n, s:{ala:arv}, d:{päev:arv}}}, games: [mängu rea indeksid], tbc, total, lo, hi}; vahemik = valitud päev või 7 päeva alates sellest
    function compute() {
      var lo = st.day, hi = st.mode === "nadal" ? st.day + 6 : st.day, res = {}, games = [], tbc = 0, total = 0;
      D.mangud.forEach(function (g, idx) {
        if (g[1] < lo || g[1] > hi || !ok(g)) return;
        if (g[2] < 0) { if (!st.tbc) return; tbc++; }
        var r = res[g[0]] || (res[g[0]] = {n: 0, s: {}, d: {}});
        r.n++; r.s[g[3]] = (r.s[g[3]] || 0) + 1; r.d[g[1]] = (r.d[g[1]] || 0) + 1; total++; games.push(idx);
      });
      return {res: res, games: games, tbc: tbc, total: total, lo: lo, hi: hi};
    }
    function dominant(s) { var best = null; Object.keys(s).forEach(function (k) { if (best == null || s[k] > s[best]) best = k; }); return +best; }
    function radius(n) { return Math.max(5, 7 + 9 * Math.sqrt(n)); }
    function fmt(n) { return String(Math.round(n)); }
    function title(idx) { return T && T[idx] ? T[idx][0] : D.alad[D.mangud[idx][3]].n; }

    function popup(i, r) {
      var k = D.kohad[i], box = el("div", {"class": "popup"});
      box.appendChild(el("strong", null, k.n));
      box.appendChild(el("div", {"class": "meta"}, k.l + (k.t !== "tapne" ? " · asukoht " + (k.t === "umbes" ? "ligikaudne" : "on linna keskpunkt") : "")));
      var ul = el("ul");
      Object.keys(r.s).sort(function (a, b) { return r.s[b] - r.s[a]; }).forEach(function (s) {
        ul.appendChild(el("li", null, D.alad[s].n + ": " + fmt(r.s[s])));
      });
      box.appendChild(ul);
      if (st.mode === "nadal") {
        var ds = Object.keys(r.d).map(Number).sort(function (a, b) { return a - b; });
        box.appendChild(el("div", {"class": "meta"}, "Päevad: " + ds.map(function (d) { return WD[weekday(d)].slice(0, 3) + " " + dmy(d) + " (" + r.d[d] + ")"; }).join(", ")));
      }
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
    ol.addEventListener("mouseover", function (e) { var li = e.target.closest("li"); if (li && pointOf(li) != null) highlight(pointOf(li), true); });
    ol.addEventListener("mouseout", function (e) { var li = e.target.closest("li"); if (li && pointOf(li) != null) highlight(pointOf(li), false); });
    ol.addEventListener("focusin", function (e) { var li = e.target.closest("li"); if (li && pointOf(li) != null) highlight(pointOf(li), true); });
    ol.addEventListener("focusout", function (e) { var li = e.target.closest("li"); if (li && pointOf(li) != null) highlight(pointOf(li), false); });
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
      var t = "Mänge " + (st.mode === "nadal" ? dmy(c.lo) + " – " + dmy(c.hi) : dmy(st.day) + " (" + WD[weekday(st.day)] + ")") + ": " + c.total + ", kohti " + order.length +
        (c.tbc ? ", sh " + c.tbc + " kellaajata üritust" : "") + ".";
      q("selgitus").textContent = t;
      toggleBtn.textContent = "Filtrid (" + activeCount() + " aktiivset)";
      refreshChips();

      while (ol.firstChild) ol.removeChild(ol.firstChild);
      if (!order.length) { ol.appendChild(el("li", {"class": "tyhi"}, "Valitud ajavahemikus mänge pole. Muuda kuupäeva või valikuid.")); return; }
      // mängud päeva ja kellaaja järgi (kellaajata päeva lõpus); nädalavaates päevapealkirjad; iga rida viib mängu lehele
      var rows = c.games.slice().sort(function (a, b) {
        var ga = D.mangud[a], gb = D.mangud[b];
        return ga[1] - gb[1] || (ga[2] < 0 ? 9999 : ga[2]) - (gb[2] < 0 ? 9999 : gb[2]) || title(a).localeCompare(title(b), "et");
      });
      var lastDay = null;
      rows.slice(0, 600).forEach(function (idx) {
        var g = D.mangud[idx], k = D.kohad[g[0]];
        if (st.mode === "nadal" && g[1] !== lastDay) {
          lastDay = g[1];
          ol.appendChild(el("li", {"class": "paevakiri"}, WD[weekday(g[1])].charAt(0).toUpperCase() + WD[weekday(g[1])].slice(1) + ", " + dmy(g[1])));
        }
        var li = el("li", {"data-p": String(g[0]), "class": "mang"});
        li.appendChild(el("span", {"class": "kell"}, g[2] < 0 ? "terve päev" : hm(g[2])));
        li.appendChild(el("a", {href: "../m/" + g[5] + "/"}, title(idx)));
        var sub = el("span", {"class": "rida2"}), dot = el("i", {"class": "dot"});
        dot.style.background = D.alad[g[3]].c;
        sub.appendChild(dot);
        sub.appendChild(document.createTextNode(D.alad[g[3]].n + " · " + k.n + ", " + k.l + (T && T[idx] ? " · " + T[idx][1] : "")));
        li.appendChild(sub);
        ol.appendChild(li);
      });
      if (active != null) Array.prototype.forEach.call(rowsOf(active), function (li) { li.classList.add("aktiivne"); });
    }
    redraw = draw;

    // ---- juhtnupud ----
    function setDay(d) { st.day = Math.min(maxDay, Math.max(minDay, d)); kuup.value = ymd(st.day); changed(true); }
    kuup.addEventListener("change", function () {
      var p = kuup.value.split("-"); if (p.length === 3) setDay(dayOf(+p[0], +p[1] - 1, +p[2]));
    });
    q("eelmine").addEventListener("click", function () { setDay(st.day - (st.mode === "nadal" ? 7 : 1)); });
    q("jargmine").addEventListener("click", function () { setDay(st.day + (st.mode === "nadal" ? 7 : 1)); });
    q("tana").addEventListener("click", function () { setDay(now.d); });
    q("tbc").addEventListener("change", function (e) { st.tbc = e.target.checked; changed(true); });
    Array.prototype.forEach.call(document.querySelectorAll('input[name="vaade"]'), function (r) {
      r.addEventListener("change", function () {
        st.mode = r.value;
        modeUi();
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
