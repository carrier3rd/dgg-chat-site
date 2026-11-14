// Lookup tab (Nov 13 2026): scores one Reddit account in the visitor's browser.
// Fetches the account's history straight from Arctic Shift (same paging and 1,000-per-kind cap as
// socialscope/arctic.py pull_user_histories), then runs socialscope/lookup_core.py in Pyodide with the exported
// v7.1 trees (lookup/model.json). Nothing is sent to this site or stored; the username stays out of the URL.
// CLAUDE.md rule 5, "Lookup tab".
(() => {
  "use strict";
  const BASE = "https://arctic-shift.photon-reddit.com/api/";
  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
  const PY_FILES = ["__init__.py", "signals.py", "hijack.py", "prewindow.py", "history.py", "lookup_core.py", "salt.py", "sources.py", "vocab.txt"];
  const CAP = 1000;
  // Nov 13 2026: an optional "Sign in with Reddit" (official API) was built here and removed the same day. Reddit
  // requires approval before any API use, and the user chose to stay on Arctic Shift only.
  const $ = (s) => document.querySelector(s);
  const form = $("#lk-form"), input = $("#lk-user"), go = $("#lk-go"), status = $("#lk-status"), out = $("#lk-result");
  if (!form) return;
  go.disabled = false;   // the button starts disabled in index.html until this script is ready

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const bar = document.getElementById("lk-bar"), fill = document.getElementById("lk-fill"), barTxt = document.getElementById("lk-bartxt");
  const say = (t) => { status.textContent = t; };
  // Loading bar: posts fill 0-30%, comments 30-88%, account age 88-92%, detector load 92-96%, scoring 96-100%.
  const prog = (pct, text) => {
    bar.hidden = false;
    fill.style.width = Math.max(2, Math.min(100, pct)).toFixed(1) + "%";
    bar.setAttribute("aria-valuenow", Math.round(pct));
    barTxt.textContent = text;
  };
  const RANGE = { posts: [0, 30], comments: [30, 88] };

  // ---------- Python (loaded once, on the first lookup)
  let pyReady = null;
  function loadPy() {
    if (pyReady) return pyReady;
    pyReady = (async () => {
      await new Promise((ok, bad) => {
        const s = document.createElement("script");
        s.src = PYODIDE + "pyodide.js"; s.onload = ok; s.onerror = () => bad(new Error("could not load Pyodide"));
        document.head.appendChild(s);
      });
      const py = await window.loadPyodide({ indexURL: PYODIDE });
      py.FS.mkdirTree("/home/pyodide/socialscope");
      await Promise.all(PY_FILES.map(async (f) => {
        const r = await fetch("py/socialscope/" + f);
        if (!r.ok) throw new Error("missing " + f);
        py.FS.writeFile("/home/pyodide/socialscope/" + f, await r.text());
      }));
      const model = await (await fetch("lookup/model.json")).text();
      py.globals.set("MODEL_JSON", model);
      py.runPython("import sys, json\nsys.path.insert(0, '/home/pyodide')\nfrom socialscope import lookup_core as LC\nM = json.loads(MODEL_JSON)\ndel MODEL_JSON");
      return py;
    })();
    pyReady.catch(() => { pyReady = null; });
    return pyReady;
  }

  // ---------- Arctic Shift
  class Busy extends Error {}
  async function get(endpoint, params, tries = 6) {
    const url = BASE + endpoint + "?" + new URLSearchParams(params).toString();
    let delay = 5000;
    for (let a = 0; a < tries; a++) {
      try {
        const r = await fetch(url);
        const txt = await r.text();
        const busy = [429, 500, 502, 503, 504, 520, 522, 524].includes(r.status) || /timeout|slow down/i.test(txt);
        if (r.ok && !busy) {
          const j = JSON.parse(txt);
          if (j && j.error) throw new Error(String(j.error));
          return j && j.data !== undefined ? j.data : j;
        }
        if (!busy) throw new Error("Arctic Shift said " + r.status + ": " + txt.slice(0, 120));
        if (a === tries - 1) throw new Busy("Arctic Shift is busy; try again in a few minutes");
        say("Arctic Shift is busy, waiting " + delay / 1000 + " s…");
      } catch (e) {
        if (e instanceof Busy || (e instanceof Error && !(e instanceof TypeError))) throw e;
        if (a === tries - 1) throw new Error("could not reach Arctic Shift");
      }
      await sleep(delay);
      delay = Math.min(delay * 2, 60000);
    }
  }

  // Newest first, up to CAP items, same edge handling as arctic._page_all(order="desc").
  async function pageAll(kind, user, label) {
    const items = [];
    let hi = null, seen = new Set(), limit = "auto";
    const [a0, a1] = RANGE[kind];
    prog(a0, `Searching ${label}… (Arctic Shift can take 10 s or more per page)`);
    while (items.length < CAP) {
      const q = { author: user, sort: "desc", limit };
      if (hi !== null) q.before = hi;
      let page;
      try { page = await get(kind + "/search", q, limit === "auto" ? 3 : 6); }
      catch (e) { if (e instanceof Busy && limit === "auto") { limit = 100; continue; } throw e; }
      const fresh = page.filter((r) => !seen.has(r.id));
      if (!fresh.length) {
        if (page.length < 100) break;
        hi = (hi !== null ? hi : Math.floor(+page[0].created_utc) + 1) - 1; seen = new Set();
        continue;
      }
      const take = fresh.slice(0, CAP - items.length);
      items.push(...take);
      const edgeT = Math.floor(+take[take.length - 1].created_utc);
      const edge = new Set(take.filter((r) => Math.floor(+r.created_utc) === edgeT).map((r) => r.id));
      const boundary = hi !== null ? hi - 1 : null;
      seen = edgeT === boundary ? new Set([...edge, ...seen]) : edge;
      hi = edgeT + 1;
      prog(a0 + (a1 - a0) * items.length / CAP, `Searching ${label}: ${items.length.toLocaleString()} found so far (reads up to ${CAP.toLocaleString()})`);
      if (page.length < 100) break;
      await sleep(800);
    }
    return items;
  }

  async function oldestTime(user) {
    const t = [];
    for (const kind of ["posts", "comments"]) {
      try {
        let page;
        try { page = await get(kind + "/search", { author: user, sort: "asc", limit: 1, fields: "id,created_utc" }, 3); }
        catch (e) { page = await get(kind + "/search", { author: user, sort: "asc", limit: 1 }, 3); }
        if (page && page[0]) t.push(+page[0].created_utc);
      } catch (e) { /* optional, as in arctic.py */ }
    }
    return t.length ? Math.min(...t) : null;
  }

  // ---------- card
  const pc = (v, d = 0) => (100 * v).toFixed(d) + "%";
  const off = (o) => "UTC" + (o >= 0 ? "+" : "−") + Math.abs(o);
  function card(user, R) {
    const th = R.thresholds, rh = R.rhythm, de = R.desc;
    const lp = (x) => Math.max(0, Math.min(100, 25 * (Math.log10(Math.max(x, 1e-4)) + 4)));
    const ticks = [["5", th["5%"]], ["7", th["2%"]], ["9", th["1%"]]]
      .map(([k, t]) => `<div class="lk-tk" style="left:${lp(t).toFixed(1)}%"><span>${k}</span></div>`).join("");
    let tz, rtxt;
    if (rh.status === "clear rhythm") {
      tz = `fits ${off(rh.band[0])} to ${off(rh.band[1])}`;
      const q = rh.quiet_start;
      rtxt = `${pc(rh.quiet_share, 1)} of items fall in the quietest 6 hours (${String(q).padStart(2, "0")}:00-${String((q + 6) % 24).padStart(2, "0")}:00 UTC).`;
    } else if (rh.status === "no clear rhythm") {
      tz = "no estimate";
      rtxt = `No clear rest period: ${pc(rh.quiet_share, 1)} of items fall even in the quietest 6 hours. Round-the-clock posting fits a shared or automated account.`;
    } else { tz = "no estimate"; rtxt = `Too few items (${rh.n}) to read a rhythm.`; }
    const us = pc(de.us_share);
    const sig = [
      [R.default_name ? "warn" : "ok", R.default_name ? "Reddit-style default name" : "Chosen name",
        R.default_name ? "Pattern Word-Word-1234. Many real users keep it, so it's only a weak signal." : "Not the default pattern."],
      [rh.status === "clear rhythm" ? "ok" : "warn", "Day-night rhythm", rtxt],
      [R.mismatch ? "warn" : "ok", "Time zone vs. where it presents",
        R.mismatch ? `Presents as US (${us} of items in US subs), but its active hours fit ${tz}. Only a lead: shift workers, people abroad and scheduling tools look the same.`
          : R.us_presenting ? `${us} of items in US subs, active hours ${tz}. No mismatch.` : `Not US-presenting (${us} of items in US subs), active hours ${tz}.`],
      [R.solicit_handle ? "warn" : "ok", "Contact-handle template", R.solicit_handle ? "Posts push a contact handle." : "None found."],
      [R.solicit_broad ? "warn" : "ok", "Turn to NSFW or solicitation", R.solicit_broad ? "A normal history that turned to NSFW or solicitation posting." : "None found."],
    ].map(([k, t, d]) => `<li class="${k}"><b>${esc(t)}</b><span>${esc(d)}</span></li>`).join("");
    const rows = (pairs) => pairs.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${pc(v)}</td></tr>`).join("");
    const mx = Math.max(1, ...rh.hist);
    const q = rh.quiet_start;
    const bars = rh.hist.map((c, h) => `<div class="lk-hb${q != null && (h - q + 24) % 24 < 6 ? " q" : ""}" style="height:${(4 + 56 * c / mx).toFixed(0)}px" title="${String(h).padStart(2, "0")}:00 UTC: ${c} items"></div>`).join("");
    const age = R.age_days != null ? (R.age_days / 365.25).toFixed(1) + " years" : "unknown";
    const day = (t) => new Date(t * 1000).toISOString().slice(0, 10);
    return `
<div class="card lk-head">
  <div class="lk-top"><div><h2>u/${esc(user)}</h2>
    <p class="note">${R.n_items.toLocaleString()} items (${R.n_posts.toLocaleString()} posts, ${R.n_comments.toLocaleString()} comments), ${day(R.first_item)} to ${day(R.last_item)}. Account age ${age}.</p></div>
    <div class="lk-rating lk-${R.tone}"><span class="big">${esc(R.rating_text)}</span><span class="lab">out of 10</span></div></div>
  <div class="lk-meter">${ticks}<div class="lk-dot" style="left:${lp(R.score).toFixed(1)}%"></div></div>
  <div class="lk-ends"><span>Ordinary</span><span>Flag lines at 5, 7 and 9</span><span>Strict flag</span></div>
  <p class="lk-v lk-${R.tone}">${esc(R.verdict)}</p>
  <p class="note">Detector score ${R.score.toFixed(4)}: higher than ${pc(R.control_pct)} of ${R.control_n} ordinary accounts in our test set. Rule flags: ${esc(R.flag_list || "none")}.</p>
</div>
<div class="grid">
  <div class="card"><h2>Signals</h2><ul class="lk-s">${sig}</ul><p class="note">Only the detector score sets the rating. These signals are for you to weigh.</p></div>
  <div class="card"><h2>Top subreddits</h2><table class="tbl lk-t">${rows(de.top_subs.map(([k, v]) => ["r/" + k, v]))}</table></div>
  <div class="card"><h2>Active hours (UTC)</h2><div class="lk-hrs">${bars}</div><div class="lk-hl"><span>00</span><span>06</span><span>12</span><span>18</span><span>23</span></div>
    <p class="note">Lighter bars are the quietest 6 hours. Time-zone estimate: <b>${esc(tz)}</b>.</p></div>
  <div class="card"><h2>Location clues (estimate)</h2><dl class="lk-dl"><dt>Active hours</dt><dd>${esc(tz)}</dd>
    <dt>US local subs</dt><dd>${esc(de.local_us.map((k) => "r/" + k).join(", ") || "none")}</dd>
    <dt>Non-US place subs</dt><dd>${esc(de.local_abroad.map(([k, c]) => `r/${k} (${c})`).join(", ") || "none")}</dd>
    <dt>Language</dt><dd>${de.english_share != null ? "English " + pc(de.english_share) + " of texts" : "no text"}</dd></dl>
    <p class="note">A rough guess from posting times and place subreddits. Reddit doesn't show where an account is based.</p></div>
  <div class="card"><h2>Top keywords</h2><table class="tbl lk-t">${rows(de.keywords)}</table><p class="note">Share of texts that use the word.</p></div>
</div>`;
  }

  // ---------- run
  let running = false;
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (running) return;
    const typed = input.value.trim().replace(/^\/?u\//i, "");
    if (!/^[A-Za-z0-9_-]{3,20}$/.test(typed)) { say("That isn't a valid Reddit username."); return; }
    running = true; go.disabled = true; out.innerHTML = "";
    const py = loadPy();
    try {
      say("");
      prog(0, "Starting…");
      const posts = await pageAll("posts", typed, "posts");
      const comments = await pageAll("comments", typed, "comments");
      const all = posts.concat(comments);
      if (!all.length) { bar.hidden = true; say("Arctic Shift has no posts or comments for that name."); return; }
      const user = all[0].author && all[0].author.toLowerCase() === typed.toLowerCase() ? all[0].author : typed;
      prog(88, `Found ${posts.length.toLocaleString()} posts and ${comments.length.toLocaleString()} comments. Checking account age…`);
      const oldest = await oldestTime(user);
      prog(92, "Loading the detector (first time only, a few seconds)…");
      const P = await py;
      prog(96, `Scoring ${all.length.toLocaleString()} items…`);
      await sleep(30);   // let the bar paint before Python blocks the page
      P.globals.set("ITEMS_JSON", JSON.stringify(all));
      P.globals.set("USER", user);
      P.globals.set("OLDEST", oldest);
      const res = JSON.parse(P.runPython("r = json.dumps(LC.analyze(USER, json.loads(ITEMS_JSON), OLDEST, M))\ndel ITEMS_JSON\nr"));
      if (res.error) { bar.hidden = true; say("Nothing to score for that name."); return; }
      prog(100, "Done");
      bar.hidden = true;
      out.innerHTML = card(user, res);
      say(`Done. Data from Arctic Shift, read ${new Date().toISOString().slice(0, 16).replace("T", " ")} UTC.`);
    } catch (e) {
      bar.hidden = true;
      say("Lookup failed: " + (e && e.message ? String(e.message).split("\n").filter(Boolean).pop() : e));
    } finally { running = false; go.disabled = false; }
  });
})();
