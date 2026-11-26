// Kalender: vaate valik (päev / nädal / kuu), kuupäeva valik kuni aasta ette ja pühkimine vasakule-paremale.
// Leht on staatiline (päevalehed 14 päeva tagasi ja ette, töötavad ka ilma JS-ita). See fail joonistab nimekirja
// ümber, kui vahetad vaadet, valid kalendrist päeva, vajutad ◀ ▶ või pühid mängude alal. Andmed: kalender.json
// (build.calendar_data). Ala valik on app.js-is: siin loetakse valitud nuppu ja joonistatakse uuesti, kui see muutub.
(function () {
  "use strict";
  var body = document.body;
  var views = document.querySelector(".views");
  var list = document.getElementById("list");
  if (!views || !list) return;

  /* @sports:js */
  /* @sports:end */
  var WD = ["esmaspäev", "teisipäev", "kolmapäev", "neljapäev", "reede", "laupäev", "pühapäev"];
  var WDS = ["E", "T", "K", "N", "R", "L", "P"];
  var MON = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober",
    "november", "detsember"];
  var MONS = ["jaan", "veebr", "märts", "apr", "mai", "juuni", "juuli", "aug", "sept", "okt", "nov", "dets"];
  var WATCH = {tv: "Teleülekanne", veeb: "Otseülekanne", jarel: "Järelvaatamine"};
  var VIEW_KEY = "elakaasa-vaade";
  var SHARE_ICON = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/></svg>';

  // --- kuupäevad (UTC keskööna, et ajavöönd ei nihutaks päeva) ---
  function D(s) { var p = s.split("-"); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); }
  function iso(d) { return d.toISOString().slice(0, 10); }
  function add(d, n) { return new Date(d.getTime() + n * 864e5); }
  function wdi(d) { return (d.getUTCDay() + 6) % 7; }
  function diff(a, b) { return Math.round((D(b) - D(a)) / 864e5); }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function human(d) { return WD[wdi(d)] + ", " + d.getUTCDate() + ". " + MON[d.getUTCMonth()]; }
  function games(n) { return n === 1 ? "1 mäng" : n + " mängu"; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c];
    });
  }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) {} return null; }

  var pageDay = body.dataset.day;
  var now = "";
  try { now = new Intl.DateTimeFormat("sv-SE", {timeZone: "Europe/Tallinn"}).format(new Date()); } catch (e) {}
  var TODAY = now && now > (body.dataset.built || "") ? now : (body.dataset.built || pageDay);
  var level = +body.dataset.level;
  var state = {view: "day", date: pageDay, client: false};
  var saved = store(VIEW_KEY);
  if (saved === "week" || saved === "month") state.view = saved;
  if (/^#\d{4}-\d{2}-\d{2}$/.test(location.hash)) state.date = location.hash.slice(1);

  var data = null, byDay = null, loading = null;
  function load() {
    if (!loading) {
      loading = fetch(body.dataset.root + "kalender.json").then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      }).then(function (d) { data = d; index(); return d; });
    }
    return loading;
  }

  function index() {
    byDay = {};
    data.events.forEach(function (ev) {
      var start = ev.t.slice(0, 10), last = ev.e || start, total = diff(start, last) + 1;
      for (var i = 0, d = start; i < total; i++, d = iso(add(D(d), 1))) {
        (byDay[d] = byDay[d] || []).push({ev: ev, n: i + 1, total: total});
      }
    });
    Object.keys(byDay).forEach(function (k) {
      byDay[k].sort(function (a, b) {
        var ka = [a.ev.tbc || a.n > 1 ? 1 : 0, a.n > 1 ? "" : a.ev.t.slice(11), a.ev.s, a.ev.h].join("|");
        var kb = [b.ev.tbc || b.n > 1 ? 1 : 0, b.n > 1 ? "" : b.ev.t.slice(11), b.ev.s, b.ev.h].join("|");
        return ka < kb ? -1 : ka > kb ? 1 : 0;
      });
    });
  }

  // --- filtrid: tase ja piirkond lehe järgi, ala app.js-i valikust ---
  function sportFilter() {
    var b = document.querySelector('.filters button[data-filter][aria-pressed="true"]');
    if (!b) return {key: "", ext: false, word: "", members: null};
    return {key: b.dataset.filter || "", ext: !!b.dataset.ext, word: b.dataset.filter ? b.dataset.word : "",
            members: b.dataset.group ? b.dataset.group.split(" ") : null};  // alade rühm
  }
  function visible(ev, sport) {
    if (sport.ext) return false;
    if (level === 0 ? data.hidden.indexOf(ev.lv) !== -1 : ev.lv !== level) return false;
    if (body.dataset.regionKind !== "all" && ev.rg !== body.dataset.region) return false;
    if (!sport.key) return true;
    return sport.members ? sport.members.indexOf(ev.s) !== -1 : ev.s === sport.key;
  }
  function dayList(day, sport) {
    return (byDay[day] || []).filter(function (x) { return visible(x.ev, sport); });
  }
  function words(sport) { return [sport.word, body.dataset.in].filter(Boolean).join(" "); }

  // --- mängu rida: sama kuju nagu site/day.html ---
  function icon(kind) {
    var inner = kind === "tv" ? '<path d="M8 1.8l4 3.2 4-3.2M8 21.5h8"/>'
      : kind === "veeb" ? '<path d="M10 8.6v5.8l4.8-2.9z" fill="currentColor" stroke-width="1.5"/><circle class="live" cx="20" cy="5" r="3.2" stroke="none"/>'
      : '<path d="M10 8.6v5.8l4.8-2.9z" fill="currentColor" stroke-width="1.5"/><circle cx="19" cy="5.5" r="4.6" fill="currentColor" stroke="none"/><path class="mark" d="M19 3.4a2.1 2.1 0 1 1-2.1 2.1" stroke-width="1.3"/><path class="markfill" d="M16.9 3.4l2.3-1.5v3z"/>';
    return '<svg class="wi wi-' + kind + '" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="13" rx="2.5"/>' + inner + "</svg>";
  }
  function row(x, past) {
    var ev = x.ev, later = x.n > 1;
    var time = later ? x.n + "./" + x.total + ". päev" : ev.tbc ? "—:—" : ev.t.slice(11, 16);
    var match = ev.a ? esc(ev.h) + " – " + esc(ev.a) : esc(ev.h);
    var score = ev.r ? ' <b class="score" title="Tulemus">' + esc(ev.r.replace("-", ":")) + "</b>" : "";
    var city = body.dataset.regionKind !== "city" && ev.c && ev.c !== ev.v ? (ev.v ? ", " : " · ") + esc(ev.c) : "";
    var meta = (ev.sp ? esc(ev.sp) + " · " : "") + esc(ev.l) + (ev.v ? " · " + esc(ev.v) : "") + city
      + (ev.tbc && !ev.e ? " · <em>kellaaeg täpsustamisel</em>" : "")
      + (ev.n ? " · <em>" + esc(ev.n) + "</em>" : "");
    var html = '<li data-sport="' + ev.s + '"><a href="' + esc(ev.u) + '" rel="noopener"><time class="s-' + ev.s + '">'
      + "<b" + (later ? ' class="dayno"' : "") + ">" + time + "</b><small>" + (BLOCK[ev.s] || SPORTS[ev.s] || "") + "</small></time>"
      + '<span class="info"><span class="match">' + match + score + '</span><span class="meta">' + meta + "</span></span></a>";
    if (ev.vid) {
      var kind = past ? "jarel" : ev.vk, label = WATCH[kind] + ": " + esc(ev.vb);
      var vhref = /^m\//.test(ev.vid) ? body.dataset.root + ev.vid : ev.vid;
      html += '<a class="watch ' + kind + '" href="' + esc(vhref) + '" rel="noopener" title="' + label + '" aria-label="' + label + ", " + match + '">' + icon(kind) + "</a>";
    }
    // mängu leht /m/<id>/ on olemas ainult staatiliste päevade vahemikus
    var start = ev.t.slice(0, 10), last = ev.e || start;
    if (start <= data.last && last >= data.first) {
      html += '<button type="button" class="share" data-k="1" data-url="' + esc(body.dataset.base + "m/" + ev.id + "/") + '" data-title="'
        + match + '" data-text="' + esc(ev.sh) + '" aria-label="Jaga: ' + match + '" title="Jaga">' + SHARE_ICON + "</button>";
    }
    return html + "</li>";
  }
  function block(day, sport, head) {
    var items = dayList(day, sport), past = day < TODAY;
    var h = head ? '<h2 class="dayhead"><span>' + cap((day === TODAY ? "täna, " : "") + human(D(day))) + '</span><span class="cnt">'
      + (items.length ? games(items.length) : "") + "</span></h2>" : "";
    if (!items.length) return head ? '<section class="dayblock" id="p' + day + '">' + h + '<p class="noday">Mänge pole</p></section>' : "";
    return '<section class="dayblock' + (past ? " past" : "") + '" id="p' + day + '">' + h + '<ol class="games">'
      + items.map(function (x) { return row(x, past); }).join("") + "</ol></section>";
  }
  function nextWithGames(from, sport) {
    var days = Object.keys(byDay).filter(function (d) { return d > from && d >= TODAY && dayList(d, sport).length; }).sort();
    return days[0];
  }

  // --- joonistamine ---
  var label = document.querySelector(".datelabel");
  var dateBtn = document.querySelector(".datebtn");
  var main = document.querySelector("main");
  var strip = document.querySelector(".days");

  function title() {
    var d = D(state.date), year = function (dd) { return iso(dd).slice(0, 4) !== TODAY.slice(0, 4) ? " " + dd.getUTCFullYear() : ""; };
    if (state.view === "day") return cap((state.date === TODAY ? "täna, " : "") + human(d)) + year(d);
    if (state.view === "week") {
      var mon = add(d, -wdi(d)), sun = add(mon, 6);
      return (mon.getUTCMonth() === sun.getUTCMonth()
        ? mon.getUTCDate() + ".–" + sun.getUTCDate() + ". " + MON[sun.getUTCMonth()]
        : mon.getUTCDate() + ". " + MONS[mon.getUTCMonth()] + " – " + sun.getUTCDate() + ". " + MONS[sun.getUTCMonth()]) + year(sun);
    }
    return cap(MON[d.getUTCMonth()]) + " " + d.getUTCFullYear();
  }

  function render(anim) {
    var sport = sportFilter(), d = D(state.date), html = "";
    if (state.view === "day") {
      html = block(state.date, sport, false);
      if (!html) {
        var nxt = nextWithGames(state.date, sport);
        html = '<div class="none"><p>' + (state.date === TODAY ? "Täna" : "Sel päeval") + " ei ole " + esc(words(sport)) + " ühtegi mängu.</p>"
          + (nxt ? '<p><button type="button" class="go" data-go="' + nxt + '">Järgmised mängud: ' + human(D(nxt)) + " →</button></p>" : "") + "</div>";
      }
    } else if (state.view === "week") {
      var mon = add(d, -wdi(d)), total = 0, body7 = "";
      for (var i = 0; i < 7; i++) { var k = iso(add(mon, i)); total += dayList(k, sport).length; body7 += block(k, sport, true); }
      html = '<p class="summary">Sel nädalal ' + games(total) + " " + esc(words(sport)) + ".</p>" + body7;
    } else {
      var first = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1));
      var lastDay = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0));
      var sum = 0, active = 0, blocks = "";
      for (var x = first; x <= lastDay; x = add(x, 1)) {
        var n = dayList(iso(x), sport).length;
        if (n) { sum += n; active++; blocks += block(iso(x), sport, true); }
      }
      html = '<p class="summary">' + cap(MON[d.getUTCMonth()]) + ": " + games(sum) + " " + active + " päeval " + esc(words(sport)) + ".</p>"
        + (diff(TODAY, iso(first)) > 45 ? '<p class="farnote">Kaugemate kuude kava on veel poolik: liigad avaldavad mänge tavaliselt mõni nädal ette, praegu on siin peamiselt suuremad võistlused.</p>' : "")
        + (blocks || '<div class="none"><p>Selles kuus pole veel ühtegi teadaolevat mängu.</p></div>');
    }
    list.innerHTML = html;
    state.client = true;
    var t = title();
    label.textContent = t;
    dateBtn.setAttribute("aria-label", "Vali kuupäev: " + t);
    views.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.view === state.view)); });
    var pastDay = state.view === "day" && state.date < TODAY;
    if (main) main.classList.toggle("pastday", pastDay);
    document.querySelectorAll(".pastnote").forEach(function (p) { p.hidden = !pastDay; });
    renderStrip(sport);
    // „kahe nädala jooksul pole“ märkus kehtib ainult päeva vaates
    document.querySelectorAll(".extnote[data-none]").forEach(function (p) { p.style.display = state.view === "day" ? "" : "none"; });
    fixLinks();
    var hash = state.view === "day" && state.date === pageDay ? "" : "#" + state.date;
    try { history.replaceState(null, "", location.pathname + location.search + hash); } catch (e) {}
    if (anim) {
      list.classList.remove("swipe-next", "swipe-prev");
      void list.offsetWidth;  // animatsioon uuesti
      list.classList.add(anim > 0 ? "swipe-next" : "swipe-prev");
    }
    if (state.scrollTo) {
      var el = document.getElementById("p" + state.scrollTo);
      if (el) el.scrollIntoView({block: "start"});
      state.scrollTo = null;
    }
  }

  // taseme ja koha valiku lingid viivad sama päeva lehele (väljaspool 14 päeva: lähim leht + #kuupäev)
  function fixLinks() {
    var near = state.date < data.first ? data.first : state.date > data.last ? data.last : state.date;
    document.querySelectorAll(".tier a[href], .city a[href]").forEach(function (a) {
      var h = a.getAttribute("href").replace(/#.*$/, "");
      if (!/\d{4}-\d{2}-\d{2}\/$/.test(h)) return;
      a.setAttribute("href", h.replace(/\d{4}-\d{2}-\d{2}\/$/, near + "/") + (near !== state.date ? "#" + state.date : ""));
    });
  }

  function renderStrip(sport) {
    if (!strip) return;
    strip.hidden = state.view !== "day";
    if (strip.hidden) return;
    var d = D(state.date), here = body.dataset.index ? "" : "../", html = "";
    for (var i = -10; i <= 10; i++) {
      var dd = add(d, i), k = iso(dd), n = dayList(k, sport).length;
      var href = k >= data.first && k <= data.last ? here + k + "/" : "#" + k;
      html += '<li><a href="' + href + '" data-go="' + k + '" class="' + (n ? "" : "empty") + (k < TODAY ? " past" : "") + '"'
        + (k === state.date ? ' aria-current="page"' : "") + ' title="' + human(dd) + ": " + (n ? games(n) : "mänge pole") + '">'
        + '<span class="wd">' + WDS[wdi(dd)] + '</span><span class="dn">' + dd.getUTCDate() + "</span></a></li>";
    }
    var ol = strip.querySelector("ol");
    ol.innerHTML = html;
    var cur = ol.querySelector("[aria-current]");
    if (cur) cur.scrollIntoView({block: "nearest", inline: "center"});
  }

  function show(anim) {
    load().then(function () { render(anim); }, function () {
      if (state.view !== "day") list.innerHTML = '<div class="none"><p>Kalendrit ei õnnestunud laadida. Värskenda lehte.</p></div>';
    });
  }
  function go(day, view) {
    state.date = day;
    if (view) setView(view, false);
    window.scrollTo(0, 0);
    show();
  }
  function setView(v, draw) {
    state.view = v;
    store(VIEW_KEY, v === "day" ? "" : v);
    if (draw !== false) show();
  }
  function step(dir, swipe) {
    var d = D(state.date);
    if (state.view === "day") state.date = iso(add(d, dir));
    else if (state.view === "week") state.date = iso(add(d, 7 * dir));
    else state.date = iso(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + dir, 1)));
    show(swipe ? dir : 0);
  }

  // --- kalendri leht ---
  var sheet = document.createElement("div");
  sheet.className = "sheet";
  sheet.hidden = true;
  sheet.innerHTML = '<div class="panel" role="dialog" aria-modal="true" aria-labelledby="calTitle">'
    + '<div class="panel-head"><b id="calTitle">Vali kuupäev</b><button type="button" class="close" data-close="1">Sulge</button></div>'
    + '<div class="quick"><button type="button" data-q="today">Täna</button><button type="button" data-q="tomorrow">Homme</button>'
    + '<button type="button" data-q="weekend">Nädalavahetus</button><button type="button" data-q="week">See nädal</button></div>'
    + '<p class="label">Kuu</p><div class="months"></div><p class="label cal-label"></p><div class="cal"></div>'
    + '<div class="calfoot"><span>Täpp = sel päeval on mänge (värv = ala)</span><button type="button" class="wholemonth" data-whole="1">Vaata kogu kuud</button></div></div>';
  document.body.appendChild(sheet);
  var calMonth = state.date.slice(0, 7);

  function renderSheet() {
    var sport = sportFilter(), start = D(TODAY.slice(0, 8) + "01"), mhtml = "";
    for (var i = 0; i < 12; i++) {
      var m = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + i, 1));
      var end = new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth() + 1, 0)), n = 0;
      for (var d = m; d <= end; d = add(d, 1)) n += dayList(iso(d), sport).length;
      var key = iso(m).slice(0, 7);
      mhtml += '<button type="button" data-month="' + key + '" class="' + (n ? "" : "zero") + '" aria-pressed="' + (calMonth === key) + '">'
        + '<span class="m">' + MONS[m.getUTCMonth()] + '</span><span class="y">' + m.getUTCFullYear() + '</span><span class="c">' + (n || "–") + "</span></button>";
    }
    sheet.querySelector(".months").innerHTML = mhtml;
    var mm = D(calMonth + "-01"), last = new Date(Date.UTC(mm.getUTCFullYear(), mm.getUTCMonth() + 1, 0));
    sheet.querySelector(".cal-label").textContent = cap(MON[mm.getUTCMonth()]) + " " + mm.getUTCFullYear();
    var chtml = WDS.map(function (w) { return '<span class="h">' + w + "</span>"; }).join("") + new Array(wdi(mm) + 1).join("<span></span>");
    for (var x = mm; x <= last; x = add(x, 1)) {
      var k = iso(x), items = dayList(k, sport), seen = {}, dots = "";
      items.forEach(function (it) { if (!seen[it.ev.s] && Object.keys(seen).length < 3) { seen[it.ev.s] = 1; dots += '<i class="s-' + it.ev.s + '"></i>'; } });
      var cls = [items.length ? "" : "empty", k < TODAY ? "past" : "", k === TODAY ? "today" : ""].join(" ").trim();
      chtml += '<button type="button" data-pick="' + k + '" class="' + cls + '"' + (k === state.date ? ' aria-current="date"' : "")
        + ' aria-label="' + human(x) + ": " + (items.length ? games(items.length) : "mänge pole") + '"><span class="num">' + x.getUTCDate()
        + '</span><span class="dots">' + dots + "</span></button>";
    }
    sheet.querySelector(".cal").innerHTML = chtml;
  }
  function openSheet() {
    calMonth = state.date.slice(0, 7);
    load().then(function () { renderSheet(); sheet.hidden = false; sheet.querySelector(".close").focus(); });
  }
  function closeSheet() { sheet.hidden = true; dateBtn.focus(); }

  // --- sündmused ---
  views.hidden = false;
  views.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.view === state.view)); });
  views.addEventListener("click", function (e) {
    var b = e.target.closest("button[data-view]");
    if (b && b.dataset.view !== state.view) setView(b.dataset.view);
  });
  dateBtn.addEventListener("click", openSheet);
  // ◀ ▶ liiguvad päeva, nädala või kuu kaupa ka staatiliste päevade vahemikust välja
  document.querySelectorAll(".daynav .step").forEach(function (el) {
    var dir = el.getAttribute("rel") === "prev" || el.textContent.indexOf("◀") !== -1 ? -1 : 1;
    var b = document.createElement("button");
    b.type = "button";
    b.className = "step";
    b.textContent = dir < 0 ? "◀" : "▶";
    b.setAttribute("aria-label", dir < 0 ? "Eelmine" : "Järgmine");
    b.addEventListener("click", function () { step(dir); });
    el.parentNode.replaceChild(b, el);
  });
  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-go], .filters button[data-filter], .share[data-k]");
    if (!t) return;
    if (t.matches(".filters button")) { if (state.client) render(); return; }  // app.js vahetas ala või rühma
    if (t.matches(".share[data-k]")) { share(t); return; }
    e.preventDefault();
    if (state.view === "week") state.scrollTo = t.dataset.go;
    go(t.dataset.go, state.view === "month" ? "day" : null);
  });
  sheet.addEventListener("click", function (e) {
    if (e.target === sheet) { closeSheet(); return; }
    var b = e.target.closest("button");
    if (!b) return;
    var td = D(TODAY);
    if (b.dataset.close) closeSheet();
    else if (b.dataset.month) { calMonth = b.dataset.month; renderSheet(); }
    else if (b.dataset.pick) {
      closeSheet();
      if (state.view === "week") state.scrollTo = b.dataset.pick;
      go(b.dataset.pick, state.view === "month" ? "day" : null);
    } else if (b.dataset.whole) { closeSheet(); go(calMonth + "-01", "month"); }
    else if (b.dataset.q) {
      closeSheet();
      if (b.dataset.q === "today") go(TODAY, "day");
      else if (b.dataset.q === "tomorrow") go(iso(add(td, 1)), "day");
      else if (b.dataset.q === "week") go(TODAY, "week");
      else { var sat = iso(add(td, wdi(td) >= 5 ? 0 : 5 - wdi(td))); state.scrollTo = sat; go(sat, "week"); }
    }
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !sheet.hidden) closeSheet(); });

  // jagamine (uued read; staatilised seob app.js)
  function share(b) {
    var d = {title: b.dataset.title, text: b.dataset.text, url: b.dataset.url};
    if (navigator.share) { navigator.share(d).catch(function () {}); return; }
    var line = d.text + " " + d.url;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(line).then(function () {
        b.classList.add("copied");
        setTimeout(function () { b.classList.remove("copied"); }, 2000);
      }, function () { window.prompt("Kopeeri link:", d.url); });
    } else {
      window.prompt("Kopeeri link:", d.url);
    }
  }

  // pühkimine mängude alal: vasakule = järgmine, paremale = eelmine (päev, nädal või kuu)
  var touch = null;
  if (main) {
    main.addEventListener("touchstart", function (e) {
      touch = e.touches.length === 1 ? {x: e.touches[0].clientX, y: e.touches[0].clientY, t: Date.now()} : null;
    }, {passive: true});
    main.addEventListener("touchend", function (e) {
      if (!touch) return;
      var p = e.changedTouches[0], dx = p.clientX - touch.x, dy = p.clientY - touch.y, ms = Date.now() - touch.t;
      touch = null;
      if (Math.abs(dx) < 60 || Math.abs(dx) < 2 * Math.abs(dy) || ms > 800) return;
      step(dx < 0 ? 1 : -1, true);
    }, {passive: true});
  }

  // nädala/kuu vaade või teine päev (aadressis #kuupäev) kohe; muidu laadi andmed vaikselt ette
  if (state.view !== "day" || state.date !== pageDay) show();
  else setTimeout(load, 1500);
})();
