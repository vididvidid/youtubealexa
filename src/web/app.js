var TOK = "";
var TAB = "status";
var TIMER = 0;
var CFG = {};
var DOCS = [];
var DOCSEL = "";

var CFG_HELP = {
  "host": "bind address, keep 127.0.0.1",
  "port": "local port the tunnel points at",
  "public_hosts": "allowed hostnames, one per line",
  "skill_id": "alexa skill id, amzn1.ask.skill....",
  "verify_sig": "1 to verify alexa signatures",
  "locale": "hi-IN or en-IN",
  "cache_max_mb": "audio cache ceiling in MB",
  "log_keep": "log rows kept in sqlite",
  "audio_mode": "local or proxy",
  "audio_origin": "phone base url when mode is proxy",
  "queue_len": "radio tracks queued per search",
  "prefetch": "1 to pre-pull the next track",
  "url_ttl": "signed audio url life in seconds",
  "search_region": "two letter region for search",
  "search_lang": "language code for search"
};


function el(id) {
  return document.getElementById(id);
}


function mk(tag, cls, txt) {
  var n = document.createElement(tag);
  if (cls) { n.className = cls; }
  if (txt !== undefined) { n.textContent = txt; }
  return n;
}


function tok_load() {
  try {
    return window.localStorage.getItem("yta_tok") || "";
  } catch (e) {
    return "";
  }
}


function tok_save(t) {
  try {
    window.localStorage.setItem("yta_tok", t);
  } catch (e) {
    return;
  }
}


function tok_drop() {
  try {
    window.localStorage.removeItem("yta_tok");
  } catch (e) {
    return;
  }
}


function api(path, meth, body, done) {
  var o = {};
  o.method = meth;
  o.headers = { "X-Admin-Token": TOK };
  if (body !== null) {
    o.headers["Content-Type"] = "application/json";
    o.body = JSON.stringify(body);
  }
  fetch(path, o).then(function (r) {
    if (r.status === 401) {
      done(-1, null);
      return;
    }
    return r.json().then(function (j) { done(r.status, j); });
  }).catch(function () {
    done(-2, null);
  });
}


function dot_set(st) {
  var d = el("dot");
  d.className = "dot " + st;
}


function secs_fmt(n) {
  if (n < 60) { return n + "s"; }
  if (n < 3600) {
    return Math.floor(n / 60) + "m " + (n % 60) + "s";
  }
  var h = Math.floor(n / 3600);
  var m = Math.floor((n % 3600) / 60);
  if (h < 24) { return h + "h " + m + "m"; }
  return Math.floor(h / 24) + "d " + (h % 24) + "h";
}


function card_add(wrap, k, v) {
  var c = mk("div", "kv", undefined);
  c.appendChild(mk("div", "k", k));
  c.appendChild(mk("div", "v", v));
  wrap.appendChild(c);
}


function status_draw(st) {
  el("vers").textContent = "v" + st.ver;
  var w = el("cards");
  w.textContent = "";
  card_add(w, "uptime", secs_fmt(st.uptime));
  card_add(w, "bind", st.host + ":" + st.port);
  card_add(w, "locale", st.locale);
  card_add(w, "audio mode", st.audio_mode);
  card_add(w, "log rows", String(st.logs));
  card_add(w, "cache", st.cache_mb + " / " +
           st.cache_max_mb + " MB");
  card_add(w, "skill id", st.skill_id ? "set" : "not set");
  var hosts = "none";
  if (st.public_hosts.length > 0) {
    hosts = String(st.public_hosts.length);
  }
  card_add(w, "public hosts", hosts);

  var f = el("feats");
  f.textContent = "";
  var i = 0;
  while (i < st.feat.length) {
    var it = st.feat[i];
    i = i + 1;
    var row = mk("div", "feat", undefined);
    row.appendChild(mk("span", "mono dim", it.id));
    row.appendChild(mk("span", "", it.name));
    var sp = mk("span", "spacer", undefined);
    row.appendChild(sp);
    var p = mk("span", it.on ? "pill on" : "pill",
               it.on ? "live" : "todo");
    row.appendChild(p);
    f.appendChild(row);
  }
}


function status_load() {
  api("/api/status", "GET", null, function (code, j) {
    if (code === -1) { gate_show("token rejected"); return; }
    if (code !== 200 || !j) { dot_set("down"); return; }
    dot_set("up");
    status_draw(j);
  });
}


function logs_draw(rows) {
  var b = el("logbody");
  b.textContent = "";
  var i = 0;
  while (i < rows.length) {
    var r = rows[i];
    i = i + 1;
    var tr = mk("tr", "", undefined);
    tr.appendChild(mk("td", "", r.at));
    tr.appendChild(mk("td", "l-" + r.lvl, r.lvl));
    tr.appendChild(mk("td", "", r.tag));
    tr.appendChild(mk("td", "msg", r.msg));
    b.appendChild(tr);
  }
  if (rows.length === 0) {
    var tr2 = mk("tr", "", undefined);
    var td = mk("td", "dim", "no rows");
    td.colSpan = 4;
    tr2.appendChild(td);
    b.appendChild(tr2);
  }
}


function logs_load() {
  var n = el("nlines").value;
  var lvl = el("lvl").value;
  var url = "/api/logs?n=" + n + "&lvl=" + lvl;
  api(url, "GET", null, function (code, j) {
    if (code === -1) { gate_show("token rejected"); return; }
    if (code !== 200 || !j) { dot_set("down"); return; }
    dot_set("up");
    logs_draw(j.rows);
  });
}


function logs_wipe() {
  api("/api/logs/clear", "POST", {}, function () {
    logs_load();
  });
}


function row_add(wrap, key, val) {
  var row = mk("div", "row", undefined);
  var lab = mk("div", "lab", undefined);
  lab.appendChild(document.createTextNode(key));
  var h = CFG_HELP[key];
  if (h) { lab.appendChild(mk("span", "", h)); }
  row.appendChild(lab);

  var inp;
  if (Array.isArray(val)) {
    inp = mk("textarea", "", undefined);
    inp.value = val.join("\n");
    inp.setAttribute("data-kind", "list");
  } else {
    inp = mk("input", "", undefined);
    inp.type = "text";
    inp.value = String(val);
    if (typeof val === "number") {
      inp.setAttribute("data-kind", "int");
    } else {
      inp.setAttribute("data-kind", "str");
    }
  }
  inp.id = "cf-" + key;
  inp.setAttribute("data-key", key);
  row.appendChild(inp);
  wrap.appendChild(row);
}


function cfg_draw(c) {
  CFG = c;
  var w = el("form");
  w.textContent = "";
  var keys = Object.keys(c).sort();
  var i = 0;
  while (i < keys.length) {
    row_add(w, keys[i], c[keys[i]]);
    i = i + 1;
  }
  hosts_draw(c.public_hosts);
}


function hosts_draw(list) {
  var w = el("hostlist");
  w.textContent = "";
  if (!list || list.length === 0) {
    w.appendChild(mk("div", "dim",
                     "no custom hostnames configured"));
    return;
  }
  var i = 0;
  while (i < list.length) {
    w.appendChild(mk("div", "host", list[i]));
    i = i + 1;
  }
}


function cfg_load() {
  api("/api/config", "GET", null, function (code, j) {
    if (code === -1) { gate_show("token rejected"); return; }
    if (code !== 200 || !j) { return; }
    cfg_draw(j.cfg);
  });
}


function lines_split(txt) {
  var raw = txt.split("\n");
  var out = [];
  var i = 0;
  while (i < raw.length) {
    var s = raw[i].trim();
    i = i + 1;
    if (s !== "") { out.push(s); }
  }
  return out;
}


function cfg_save() {
  var patch = {};
  var keys = Object.keys(CFG);
  var i = 0;
  while (i < keys.length) {
    var k = keys[i];
    i = i + 1;
    var n = el("cf-" + k);
    if (!n) { continue; }
    var kind = n.getAttribute("data-kind");
    if (kind === "list") {
      patch[k] = lines_split(n.value);
    } else if (kind === "int") {
      var v = parseInt(n.value, 10);
      if (isNaN(v)) { continue; }
      patch[k] = v;
    } else {
      patch[k] = n.value.trim();
    }
  }
  el("cfgmsg").textContent = "saving";
  api("/api/config", "POST", patch, function (code, j) {
    if (code !== 200 || !j) {
      el("cfgmsg").textContent = "save failed";
      return;
    }
    cfg_draw(j.cfg);
    if (j.bad.length > 0) {
      el("cfgmsg").textContent = "saved, ignored: " +
                                 j.bad.join(", ");
    } else {
      el("cfgmsg").textContent = "saved";
    }
  });
}


function docs_draw() {
  var ul = el("docnames");
  ul.textContent = "";
  var i = 0;
  while (i < DOCS.length) {
    var name = DOCS[i];
    i = i + 1;
    var li = mk("li", name === DOCSEL ? "on" : "", name);
    li.setAttribute("data-f", name);
    li.onclick = function (ev) {
      doc_open(ev.target.getAttribute("data-f"));
    };
    ul.appendChild(li);
  }
}


function doc_open(name) {
  DOCSEL = name;
  docs_draw();
  api("/api/doc?f=" + encodeURIComponent(name), "GET", null,
      function (code, j) {
    if (code !== 200 || !j) {
      el("doctext").textContent = "read failed";
      return;
    }
    el("docttl").textContent = j.name;
    el("doctext").textContent = j.text;
  });
}


function docs_load() {
  api("/api/docs", "GET", null, function (code, j) {
    if (code === -1) { gate_show("token rejected"); return; }
    if (code !== 200 || !j) { return; }
    DOCS = j.files;
    docs_draw();
    if (DOCSEL === "" && DOCS.length > 0) {
      doc_open(DOCS[0]);
    }
  });
}


function ck_draw(ck) {
  var w = el("ckcards");
  w.textContent = "";
  card_add(w, "present", ck.present ? "yes" : "no");
  card_add(w, "logged in", ck.ok ? "yes" : "no");
  card_add(w, "youtube rows", String(ck.yt));
  if (ck.present) {
    card_add(w, "expires in", ck.days + " days");
  }
  if (ck.missing && ck.missing.length > 0) {
    card_add(w, "missing", ck.missing.join(" "));
  }
}


function ck_load() {
  api("/api/cookies", "GET", null, function (code, j) {
    if (code === -1) { gate_show("token rejected"); return; }
    if (code !== 200 || !j) { return; }
    ck_draw(j.cookie);
  });
}


function ck_save() {
  var t = el("cktext").value;
  if (t.trim() === "") {
    el("ckmsg").textContent = "nothing pasted";
    return;
  }
  el("ckmsg").textContent = "checking";
  api("/api/cookies", "POST", { text: t }, function (code, j) {
    if (code !== 200 || !j || !j.ok) {
      el("ckmsg").textContent = "rejected: " +
        (j ? j.err : "failed");
      return;
    }
    el("cktext").value = "";
    el("ckmsg").textContent = "loaded";
    ck_draw(j.cookie);
  });
}


function ck_drop() {
  api("/api/cookies/clear", "POST", {}, function (code, j) {
    if (code !== 200 || !j) { return; }
    el("ckmsg").textContent = "removed";
    ck_draw(j.cookie);
  });
}


function cache_draw(j) {
  el("cacheinfo").textContent = j.files.length + " files, " +
    j.mb + " of " + j.max_mb + " MB";
  var b = el("cachebody");
  b.textContent = "";
  var i = 0;
  while (i < j.files.length) {
    var r = j.files[i];
    i = i + 1;
    var tr = mk("tr", "", undefined);
    tr.appendChild(mk("td", "", r.vid));
    tr.appendChild(mk("td", "", r.kib + " KiB"));
    tr.appendChild(mk("td", "", r.at));
    b.appendChild(tr);
  }
  if (j.files.length === 0) {
    var tr2 = mk("tr", "", undefined);
    var td = mk("td", "dim", "cache empty");
    td.colSpan = 3;
    tr2.appendChild(td);
    b.appendChild(tr2);
  }
}


function cache_load() {
  api("/api/cache", "GET", null, function (code, j) {
    if (code === -1) { gate_show("token rejected"); return; }
    if (code !== 200 || !j) { return; }
    cache_draw(j);
  });
}


function cache_evict() {
  api("/api/cache/evict", "POST", {}, function () {
    cache_load();
  });
}


function cache_wipe() {
  api("/api/cache/clear", "POST", {}, function () {
    cache_load();
  });
}


function s_draw(rows) {
  var b = el("sbody");
  b.textContent = "";
  var i = 0;
  while (i < rows.length) {
    var r = rows[i];
    i = i + 1;
    var tr = mk("tr", "", undefined);
    tr.appendChild(mk("td", "", String(r.score)));
    tr.appendChild(mk("td", "", String(r.rel)));
    tr.appendChild(mk("td", "", r.dur));
    var td = mk("td", "msg", r.title + "  —  " + r.chan);
    tr.appendChild(td);
    var act = mk("td", "", undefined);
    var btn = mk("button", "ghost", r.cached ? "cached" : "fetch");
    btn.setAttribute("data-v", r.vid);
    btn.onclick = function (ev) {
      var n = ev.target;
      n.textContent = "...";
      api("/api/fetch", "POST",
          { vid: n.getAttribute("data-v") },
          function (code, j) {
        n.textContent = (code === 200 && j && j.ok) ?
                        "cached" : "failed";
      });
    };
    act.appendChild(btn);
    tr.appendChild(act);
    b.appendChild(tr);
  }
  if (rows.length === 0) {
    var tr3 = mk("tr", "", undefined);
    var td3 = mk("td", "dim", "nothing usable found");
    td3.colSpan = 5;
    tr3.appendChild(td3);
    b.appendChild(tr3);
  }
}


function s_go() {
  var q = el("sq").value.trim();
  if (q === "") { return; }
  el("sbody").textContent = "";
  var tr = mk("tr", "", undefined);
  var td = mk("td", "dim", "searching");
  td.colSpan = 5;
  tr.appendChild(td);
  el("sbody").appendChild(tr);
  api("/api/search", "POST", { q: q }, function (code, j) {
    if (code !== 200 || !j || !j.ok) {
      s_draw([]);
      return;
    }
    s_draw(j.rows);
  });
}


function media_load() {
  ck_load();
  cache_load();
}


function tick_stop() {
  if (TIMER !== 0) {
    window.clearInterval(TIMER);
    TIMER = 0;
  }
}


function tick_start() {
  tick_stop();
  TIMER = window.setInterval(function () {
    if (TAB === "status") { status_load(); return; }
    if (TAB === "logs" && el("auto").checked) { logs_load(); }
  }, 4000);
}


function tab_show(name) {
  TAB = name;
  var tabs = document.querySelectorAll(".tab");
  var i = 0;
  while (i < tabs.length) {
    var t = tabs[i];
    i = i + 1;
    if (t.getAttribute("data-t") === name) {
      t.classList.add("on");
    } else {
      t.classList.remove("on");
    }
  }
  var panes = ["status", "logs", "media", "config",
                "docs"];
  i = 0;
  while (i < panes.length) {
    var p = el("p-" + panes[i]);
    i = i + 1;
    p.classList.add("hide");
  }
  el("p-" + name).classList.remove("hide");
  if (name === "status") { status_load(); }
  if (name === "logs") { logs_load(); }
  if (name === "media") { media_load(); }
  if (name === "config") { cfg_load(); }
  if (name === "docs") { docs_load(); }
}


function gate_show(msg) {
  tick_stop();
  el("app").classList.add("hide");
  el("gate").classList.remove("gate-off");
  el("gate").classList.remove("hide");
  el("gateerr").textContent = msg || "";
}


function app_show() {
  el("gate").classList.add("hide");
  el("app").classList.remove("hide");
  tab_show("status");
  tick_start();
}


function try_unlock(t) {
  TOK = t;
  api("/api/status", "GET", null, function (code, j) {
    if (code !== 200 || !j) {
      gate_show("token rejected");
      return;
    }
    tok_save(t);
    app_show();
  });
}


function wire() {
  el("tokgo").onclick = function () {
    var t = el("tok").value.trim();
    if (t === "") { el("gateerr").textContent = "empty"; return; }
    try_unlock(t);
  };
  el("tok").onkeydown = function (ev) {
    if (ev.key === "Enter") { el("tokgo").click(); }
  };
  el("lock").onclick = function () {
    tok_drop();
    TOK = "";
    gate_show("locked");
  };
  var tabs = document.querySelectorAll(".tab");
  var i = 0;
  while (i < tabs.length) {
    tabs[i].onclick = function (ev) {
      tab_show(ev.target.getAttribute("data-t"));
    };
    i = i + 1;
  }
  el("refresh").onclick = logs_load;
  el("wipe").onclick = logs_wipe;
  el("lvl").onchange = logs_load;
  el("nlines").onchange = logs_load;
  el("cksave").onclick = ck_save;
  el("ckdrop").onclick = ck_drop;
  el("evict").onclick = cache_evict;
  el("wipecache").onclick = cache_wipe;
  el("sgo").onclick = s_go;
  el("sq").onkeydown = function (ev) {
    if (ev.key === "Enter") { s_go(); }
  };
  el("save").onclick = cfg_save;
  el("reload").onclick = cfg_load;
}


function main() {
  wire();
  var t = tok_load();
  if (t === "") { gate_show(""); return; }
  try_unlock(t);
}


main();
