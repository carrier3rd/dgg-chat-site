(() => {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const nf = new Intl.NumberFormat("en");
  const cf = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
  const pct = (v, d = 1) => (v == null ? "—" : (+v).toFixed(d) + "%");
  const $ = (s) => document.querySelector(s);
  const tip = $("#tip");

  // ---------- tabs
  const tabs = [...document.querySelectorAll(".tabs button")];
  const show = (name) => {
    tabs.forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
    document.querySelectorAll(".tab").forEach((s) => { s.hidden = s.id !== "tab-" + name; });
    if (location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
    redraw();
  };
  tabs.forEach((b) => b.addEventListener("click", () => show(b.dataset.tab)));
  const fromHash = () => { const t = (location.hash || "#live").slice(1).replace(/[^a-z]/g, ""); return ["live", "glossary", "archive", "about"].includes(t) ? t : "live"; };
  window.addEventListener("hashchange", () => { if (D.meta !== undefined) show(fromHash()); });

  // ---------- data
  const files = ["glossary", "meta", "live_days", "live_hours", "live_emotes", "live_terms", "archive_overlap", "archive_channels",
    "archive_dgg_years", "archive_dgg_emotes", "archive_politics", "archive_hasan_monthly", "archive_badbunny_monthly",
    "scorecard"];
  const D = {};
  Promise.all(files.map((f) => fetch("data/" + f + ".json", { cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : null)).catch(() => null).then((j) => { D[f] = j; })))
    .then(() => { fillStatic(); show(fromHash()); });

  // ---------- svg helpers
  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };
  const svgIn = (box, h) => {
    box.replaceChildren();
    const w = Math.max(280, box.clientWidth || 600);
    const s = el("svg", { viewBox: `0 0 ${w} ${h}`, width: "100%", role: "img" }, box);
    return [s, w];
  };
  const text = (parent, x, y, str, attrs = {}) => { const t = el("text", { x, y, ...attrs }, parent); t.textContent = str; return t; };
  const textW = (svg, str, cls) => { const t = text(svg, 0, 0, str, cls ? { class: cls } : {}); const w = t.getComputedTextLength(); t.remove(); return w; };
  const niceMax = (v) => { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); const m = v / p; return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p; };
  const ticks = (max, n = 4) => { const step = niceMax(max / n); const out = []; for (let v = 0; v <= max + 1e-9; v += step) out.push(+v.toFixed(6)); return out; };
  const showTip = (ev, lines) => {
    tip.replaceChildren(...lines.map((l, i) => { const d = document.createElement("div"); if (i === 0) d.className = "k"; d.textContent = l; return d; }));
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    tip.style.left = Math.min(window.innerWidth - r.width - 8, ev.clientX + 12) + "px";
    tip.style.top = Math.max(8, ev.clientY - r.height - 10) + "px";
  };
  const hideTip = () => { tip.hidden = true; };

  // Horizontal bars, one or two series per row.
  function hbars(box, rows, series, fmt) {
    const rowH = series.length > 1 ? 30 : 22;
    const [s, w] = svgIn(box, rows.length * rowH + 22);
    const left = Math.min(w * 0.45, Math.max(...rows.map((r) => textW(s, r.label, "lbl"))) + 10);
    const max = niceMax(Math.max(...rows.flatMap((r) => series.map((k) => r[k.key] ?? 0))) * 1.05);
    const x = (v) => left + (w - left - 48) * v / max;
    for (const t of ticks(max)) {
      el("line", { x1: x(t), x2: x(t), y1: 0, y2: rows.length * rowH, stroke: "var(--grid)" }, s);
      text(s, x(t), rows.length * rowH + 15, fmt(t), { "text-anchor": "middle" });
    }
    rows.forEach((r, i) => {
      const y0 = i * rowH;
      text(s, left - 8, y0 + rowH / 2, r.label, { class: "lbl", "text-anchor": "end", "dominant-baseline": "middle" });
      const bh = (rowH - 6) / series.length;
      series.forEach((k, j) => {
        const v = r[k.key];
        if (v == null) return;
        el("rect", { x: left, y: y0 + 3 + j * bh, width: Math.max(1, x(v) - left), height: bh - 1, rx: 2, fill: `var(${k.color})` }, s);
      });
      const vals = series.map((k) => r[k.key]).filter((v) => v != null);
      text(s, x(Math.max(...vals, 0)) + 4, y0 + rowH / 2, series.map((k) => (r[k.key] == null ? "–" : fmt(r[k.key]))).join(" / "), { "dominant-baseline": "middle" });
      const hit = el("rect", { x: 0, y: y0, width: w, height: rowH, fill: "transparent" }, s);
      hit.addEventListener("pointermove", (ev) => showTip(ev, [r.label, ...series.map((k) => `${k.name}: ${r[k.key] == null ? "n/a" : fmt(r[k.key])}`)]));
      hit.addEventListener("pointerleave", hideTip);
    });
  }

  // Line chart over dates; series of {key, name, color}.
  function lines(box, rows, xKey, series, yFmt, xFmt) {
    const H = 220, m = { l: 36, r: 10, t: 10, b: 24 };
    const [s, w] = svgIn(box, H);
    const xs = rows.map((r) => +new Date(r[xKey]));
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const max = niceMax(Math.max(...rows.flatMap((r) => series.map((k) => r[k.key] ?? 0))) * 1.05);
    const X = (t) => m.l + (w - m.l - m.r) * (x1 === x0 ? 0.5 : (t - x0) / (x1 - x0));
    const Y = (v) => H - m.b - (H - m.t - m.b) * v / max;
    for (const t of ticks(max)) {
      el("line", { x1: m.l, x2: w - m.r, y1: Y(t), y2: Y(t), stroke: "var(--grid)" }, s);
      text(s, m.l - 6, Y(t), yFmt(t), { "text-anchor": "end", "dominant-baseline": "middle" });
    }
    const n = Math.max(2, Math.min(6, Math.floor(w / 110)));
    for (let i = 0; i < n; i++) { const t = x0 + (x1 - x0) * i / (n - 1); text(s, X(t), H - 6, xFmt(new Date(t)), { "text-anchor": i === 0 ? "start" : i === n - 1 ? "end" : "middle" }); }
    series.forEach((k) => {
      const pts = rows.map((r, i) => r[k.key] == null ? null : `${X(xs[i])},${Y(r[k.key])}`).filter(Boolean);
      el("polyline", { points: pts.join(" "), fill: "none", stroke: `var(${k.color})`, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, s);
    });
    const dots = series.map((k) => el("circle", { r: 4, fill: `var(${k.color})`, opacity: 0 }, s));
    const hit = el("rect", { x: m.l, y: 0, width: w - m.l - m.r, height: H, fill: "transparent" }, s);
    hit.addEventListener("pointermove", (ev) => {
      const b = s.getBoundingClientRect(); const px = (ev.clientX - b.left) * w / b.width;
      let i = 0, best = Infinity; xs.forEach((t, j) => { const d = Math.abs(X(t) - px); if (d < best) { best = d; i = j; } });
      series.forEach((k, j) => { const v = rows[i][k.key]; dots[j].setAttribute("cx", X(xs[i])); dots[j].setAttribute("cy", Y(v ?? 0)); dots[j].setAttribute("opacity", v == null ? 0 : 1); });
      showTip(ev, [xFmt(new Date(xs[i])), ...series.map((k) => `${k.name}: ${rows[i][k.key] == null ? "n/a" : yFmt(rows[i][k.key])}`)]);
    });
    hit.addEventListener("pointerleave", () => { hideTip(); dots.forEach((d) => d.setAttribute("opacity", 0)); });
  }

  // Vertical bars.
  function vbars(box, rows, labelKey, valKey, fmt, labelFmt, tipFmt, sparse) {
    const H = 220, m = { l: 40, r: 6, t: 16, b: 24 };
    const [s, w] = svgIn(box, H);
    const max = niceMax(Math.max(...rows.map((r) => r[valKey])) * 1.08);
    const bw = (w - m.l - m.r) / rows.length;
    const Y = (v) => H - m.b - (H - m.t - m.b) * v / max;
    for (const t of ticks(max)) {
      el("line", { x1: m.l, x2: w - m.r, y1: Y(t), y2: Y(t), stroke: "var(--grid)" }, s);
      text(s, m.l - 6, Y(t), fmt(t), { "text-anchor": "end", "dominant-baseline": "middle" });
    }
    const every = Math.max(1, Math.ceil(rows.length / Math.floor((w - m.l) / 46)));
    rows.forEach((r, i) => {
      const x = m.l + i * bw, gap = Math.min(bw * 0.25, 6), v = r[valKey];
      el("rect", { x: x + gap / 2, y: Y(v), width: Math.max(1, Math.min(32, bw - gap)), height: Math.max(0, Y(0) - Y(v)), rx: bw > 6 ? 2 : 0, fill: "var(--s2)" }, s);
      const lab = labelFmt(r[labelKey]);
      if (sparse ? lab : i % every === 0) text(s, x + Math.min(32, bw - gap) / 2 + gap / 2, H - 6, labelFmt(r[labelKey]), { "text-anchor": sparse ? "start" : "middle" });
      const hit = el("rect", { x, y: 0, width: bw, height: H, fill: "transparent" }, s);
      hit.addEventListener("pointermove", (ev) => showTip(ev, [tipFmt ? tipFmt(r[labelKey]) : labelFmt(r[labelKey]), fmt(v, true)]));
      hit.addEventListener("pointerleave", hideTip);
    });
  }

  const fillTable = (sel, rows, cols) => {
    const tb = $(sel + " tbody"); if (!tb) return;
    tb.replaceChildren(...rows.map((r) => {
      const tr = document.createElement("tr");
      for (const [k, kind] of cols) {
        const td = document.createElement("td"); const v = typeof k === "function" ? k(r) : r[k];
        if (kind === "num") { td.className = "num"; td.textContent = v == null ? "—" : nf.format(v); }
        else if (kind === "pct") { td.className = "num"; td.textContent = pct(v); }
        else if (kind === "dec") { td.className = "num"; td.textContent = v == null ? "—" : (+v).toFixed(1); }
        else if (kind === "res") { td.textContent = v; td.className = /^Held/.test(v) ? "ok" : /Missed/.test(v) ? "bad" : "warn"; }
        else td.textContent = v == null ? "" : String(v);
        tr.appendChild(td);
      }
      return tr;
    }));
  };


  // ---------- glossary
  let glFilter = "all";
  const kindLabel = { emote: "emote", word: "word", phrase: "phrase", nickname: "nickname", meme: "meme",
    reference: "reference", person: "person", event: "event", other: "term" };
  const srcLabel = (e) => e.definition_source === "Claude" ? `Written by Claude from recent chat, ${e.definition_date}, unreviewed`
    : e.definition_source ? `From the ${e.definition_source}` : "";
  function spark(trend) {
    const vals = trend.map((d) => d.per_10k);
    const w = 300, h = 34, max = Math.max(1, ...vals.filter((v) => v != null));
    const s = el("svg", { viewBox: `0 0 ${w} ${h}`, class: "spark", preserveAspectRatio: "none", role: "img" });
    const step = w / Math.max(1, vals.length - 1);
    const pts = vals.map((v, i) => v == null ? null : `${i * step},${h - 2 - (h - 4) * v / max}`).filter(Boolean);
    if (pts.length > 1) el("polyline", { points: pts.join(" "), fill: "none", stroke: "var(--s2)", "stroke-width": 2, "stroke-linejoin": "round", "vector-effect": "non-scaling-stroke" }, s);
    else if (pts.length === 1) { const [x, y] = pts[0].split(","); el("circle", { cx: x, cy: y, r: 3, fill: "var(--s2)" }, s); }
    const t = document.createElementNS(NS, "title"); t.textContent = "Uses per 10k messages, last 14 days"; s.prepend(t);
    return s;
  }
  const div = (cls, txt) => { const d = document.createElement("div"); if (cls) d.className = cls; if (txt != null) d.textContent = txt; return d; };
  function glCard(e) {
    const c = div("card gl-card");
    const head = div("gl-head");
    head.append(div("gl-term", e.term));
    const chips = div("gl-co");
    if (e.status === "trending") chips.append(Object.assign(div("chip hot", `trending ${e.lift >= 100 ? "new" : e.lift + "x"}`)));
    chips.append(div("chip", kindLabel[e.kind] || "term"));
    head.append(chips); c.append(head);
    const p = document.createElement("p");
    p.className = "gl-def" + (e.definition ? "" : " pending");
    p.textContent = e.definition || "Definition pending.";
    c.append(p);
    if (e.definition) c.append(div("gl-src", srcLabel(e)));
    c.append(div("gl-stats", `${nf.format(e.messages_24h)} messages from ${nf.format(e.chatters_24h)} chatters in the last 24 hours · ${e.per_10k_24h} per 10k`));
    c.append(spark(e.trend || []));
    const a = e.archive;
    c.append(div("gl-stats", a ? `In 2014-2020 DGG chat: first seen ${a.first_year}, peaked ${a.peak_year}, ${a.rate_2019_per100k} per 100k messages in 2019` : "Not seen in 2014-2020 DGG chat"));
    if (e.co_terms && e.co_terms.length) {
      const co = div("gl-co"); co.append(div("gl-stats", "Seen with:"));
      e.co_terms.forEach((t) => co.append(div("chip", t))); c.append(co);
    }
    (e.quotes || []).forEach((q) => {
      const b = document.createElement("blockquote"); b.className = "gl-q"; b.textContent = q.text + " ";
      const sp = document.createElement("span"); sp.textContent = `sent by ${q.chatters} chatters`; b.append(sp); c.append(b);
    });
    return c;
  }
  function renderGlossary() {
    const g = D.glossary;
    const list = $("#gl-list"); if (!list) return;
    if (!g || !g.entries) { $("#gl-status").textContent = "The glossary hasn't been built yet."; list.replaceChildren(); return; }
    $("#gl-status").textContent = `${g.entries.length} terms · ${nf.format(g.messages_24h)} messages in the last 24 hours · updated ${new Date(g.generated).toLocaleString()}`;
    const q = ($("#gl-q").value || "").trim().toLowerCase();
    const rows = g.entries.filter((e) => {
      if (glFilter === "trending" && e.status !== "trending") return false;
      if (glFilter === "emote" && e.kind !== "emote") return false;
      if (glFilter === "word" && e.kind === "emote") return false;
      return !q || e.term.toLowerCase().includes(q) || (e.definition || "").toLowerCase().includes(q);
    });
    list.replaceChildren(...rows.map(glCard));
    $("#gl-empty").hidden = rows.length > 0;
  }
  $("#gl-q") && $("#gl-q").addEventListener("input", renderGlossary);
  document.querySelectorAll(".gl-filter button").forEach((b) => b.addEventListener("click", () => {
    glFilter = b.dataset.f;
    document.querySelectorAll(".gl-filter button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderGlossary();
  }));

  // ---------- static fills (tables and tiles)
  function fillStatic() {
    renderGlossary();
    const meta = D.meta || {};
    const days = D.live_days || [];
    const today = days[days.length - 1];
    if (today) {
      $("#t-msgs").textContent = nf.format(today.messages);
      $("#t-msgs-lab").textContent = `Messages on ${today.day} (UTC)${today.partial ? ", so far" : ""}`;
      $("#t-users").textContent = nf.format(today.chatters);
      $("#t-emote").textContent = pct(100 * today.emote_only_share, 0);
    }
    $("#t-7d").textContent = meta.live_messages_7d == null ? "—" : nf.format(meta.live_messages_7d);
    const st = $("#live-status"); st.replaceChildren();
    const dot = document.createElement("span"); dot.className = "dot" + (meta.logger_connected ? " on" : "");
    const gen = meta.generated ? new Date(meta.generated) : null;
    st.append(dot, document.createTextNode(`Logger ${meta.logger_connected ? "connected" : "offline"} at last update · updated ${gen ? gen.toLocaleString() : "—"} · refreshes every 15 min`));
    fillTable("#tb-days", days.slice().reverse(), [["day"], ["messages", "num"], ["chatters", "num"],
      [(r) => r.emote_only_share == null ? null : 100 * r.emote_only_share, "pct"], ["median_words", "num"],
      [(r) => r.connected_minutes == null ? "" : (r.connected_minutes / 60).toFixed(1) + " h", "txt"]]);
    $("#tb-days tbody").querySelectorAll("td:last-child").forEach((td) => { td.className = "num"; });
    const terms = D.live_terms || [];
    fillTable("#tb-terms", terms, [["term"], ["messages", "num"], ["per_10k", "dec"]]);
    $("#terms-empty").hidden = terms.length > 0;

    const chans = D.archive_channels || [];
    $("#a-total").textContent = meta.archive_messages ? cf.format(meta.archive_messages) : "—";
    $("#a-chats").textContent = meta.archive_channels ?? "—";
    const dgg = chans.find((c) => c.key === "Destinygg");
    $("#a-dgg").textContent = dgg ? cf.format(dgg.messages) : "—";
    const hm = (D.archive_hasan_monthly || []).filter((r) => r.month >= "2019-01");
    if (hm.length) $("#a-hasan").textContent = pct(hm.reduce((a, r) => a + r.shared, 0) / hm.reduce((a, r) => a + r.destiny_regulars, 0) * 100, 0);
    fillTable("#tb-emotes", D.archive_dgg_emotes || [], [["year"], [(r) => r.top5.join(", ")], ["PEPE", "num"], ["YEE", "num"]]);
    fillTable("#tb-pol", D.archive_politics || [], [["channel"], ["year"], ["electoral_per_10k", "dec"], ["culture_war_per_10k", "dec"]]);
    fillTable("#tb-chans", chans.slice().sort((a, b) => b.messages - a.messages), [["channel"], ["group"], ["messages", "num"], ["first_month"], ["last_month"], ["median_words", "num"], ["top_short_message"]]);
    fillTable("#tb-score", D.scorecard || [], [["n"], ["prediction"], ["result", "res"], ["evidence"]]);
    if (meta.generated) $("#about-gen").textContent = `Data generated ${new Date(meta.generated).toLocaleString()}.`;
  }

  // ---------- charts (redrawn on tab switch and resize)
  const monthFmt = (d) => d.toLocaleDateString("en", { month: "short", year: "numeric", timeZone: "UTC" });
  function redraw() {
    const live = !$("#tab-live").hidden, arch = !$("#tab-archive").hidden;
    if (live && D.live_hours && D.live_hours.length) {
      vbars($("#c-hours"), D.live_hours, "hour", "messages", (v, full) => (full ? nf.format(v) + " messages" : cf.format(v)),
        (h) => { const d = new Date(h); return d.getHours() === 0 ? d.toLocaleDateString("en", { weekday: "short" }) : ""; },
        (h) => new Date(h).toLocaleString("en", { weekday: "short", hour: "numeric" }), true);
    }
    if (live && D.live_emotes) {
      if (D.live_emotes.length) hbars($("#c-emotes"), D.live_emotes.slice(0, 15).map((r) => ({ label: r.emote, v: 100 * r.share })), [{ key: "v", name: "Share of messages", color: "--s2" }], (v) => v.toFixed(1) + "%");
      else $("#c-emotes").textContent = "Not enough messages yet.";
    }
    if (arch && D.archive_overlap) {
      const rows = D.archive_overlap.map((r) => ({ label: r.channel, tw: r.pct_in_destiny_twitch, dg: r.pct_in_dgg })).sort((a, b) => (b.tw ?? 0) - (a.tw ?? 0));
      hbars($("#c-overlap"), rows, [{ key: "tw", name: "In Destiny's Twitch chat", color: "--s1" }, { key: "dg", name: "In DGG", color: "--s2" }], (v) => Math.round(v) + "%");
    }
    if (arch && D.archive_hasan_monthly) lines($("#c-hasan"), D.archive_hasan_monthly.map((r) => ({ ...r, month: r.month + "-01" })), "month",
      [{ key: "pct_of_channel", name: "Share of Hasan's regulars", color: "--s1" }, { key: "pct_of_destiny", name: "Share of Destiny's regulars", color: "--s2" }], (v) => Math.round(v) + "%", monthFmt);
    if (arch && D.archive_badbunny_monthly) lines($("#c-bb"), D.archive_badbunny_monthly.map((r) => ({ ...r, month: r.month + "-01" })), "month",
      [{ key: "pct_of_channel", name: "Share in Destiny's Twitch chat", color: "--s2" }], (v) => Math.round(v) + "%", monthFmt);
    if (arch && D.archive_dgg_years) vbars($("#c-dgg"), D.archive_dgg_years, "year", "messages_per_month", (v, full) => (full ? nf.format(v) + " a month" : cf.format(v)), (y) => y);
  }
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(redraw, 150); });
})();
