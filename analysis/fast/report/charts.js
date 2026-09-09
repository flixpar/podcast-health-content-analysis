// Minimal SVG chart helpers. All colors come from CSS variables so both themes work.
const NS = "http://www.w3.org/2000/svg";
const SERIES = ["--s1","--s2","--s3","--s4","--s5","--s6","--s7","--s8"];
const tip = document.createElement("div"); tip.className = "tip"; document.body.appendChild(tip);
function showTip(e, html){ tip.innerHTML = html; tip.style.display = "block"; moveTip(e); }
function moveTip(e){ const x = Math.min(e.clientX + 14, window.innerWidth - 330); tip.style.left = x + "px"; tip.style.top = (e.clientY + 14) + "px"; }
function hideTip(){ tip.style.display = "none"; }
function el(tag, attrs, parent){ const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; }
function txt(parent, x, y, s, attrs={}){ const t = el("text", Object.assign({x, y}, attrs), parent); t.textContent = s; return t; }
function fmt(v, d=0){ if (v === null || v === undefined) return "–"; if (Math.abs(v) >= 1e6) return (v/1e6).toFixed(1)+"M"; if (Math.abs(v) >= 1e4) return Math.round(v/1e3)+"k"; return Number(v).toLocaleString(undefined,{maximumFractionDigits:d}); }
function niceMax(v){ if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); const m = v / p; const n = m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10; return n * p; }
function esc(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;"); }

// Horizontal bars. rows: [{label, value, sub?, color?}], opts: {unit, width, digits, color}
function hbar(container, rows, opts={}){
  const c = typeof container === "string" ? document.getElementById(container) : container;
  const W = opts.width || Math.min(c.clientWidth || 900, 1000), lw = opts.labelWidth || 220, rh = opts.rowH || 22, pad = 8;
  const H = rows.length * rh + 24;
  const svg = el("svg", {viewBox:`0 0 ${W} ${H}`, width:"100%", role:"img"}, c);
  const max = niceMax(Math.max(...rows.map(r => r.value)));
  const x0 = lw, x1 = W - 70;
  const sx = v => x0 + (x1 - x0) * v / max;
  const g = el("g", {class:"grid"}, svg);
  for (let i = 0; i <= 4; i++){ const v = max * i / 4; el("line", {x1:sx(v), x2:sx(v), y1:0, y2:H-20}, g); txt(svg, sx(v), H-6, fmt(v, opts.digits||0), {"text-anchor":"middle", class:"num muted"}); }
  rows.forEach((r, i) => {
    const y = i * rh;
    txt(svg, x0 - 8, y + rh*0.68, r.label, {"text-anchor":"end", class:"lbl"});
    const rect = el("rect", {x:x0, y:y+4, width:Math.max(sx(r.value)-x0, 1), height:rh-8, rx:0, fill:`var(${r.color || opts.color || "--s1"})`}, svg);
    txt(svg, sx(r.value) + 5, y + rh*0.68, fmt(r.value, opts.digits||0) + (opts.unit||""), {class:"num"});
    if (r.sub) txt(svg, x1 + 4, y + rh*0.68, r.sub, {class:"muted num", "font-size":"10.5px"});
    rect.addEventListener("mousemove", e => showTip(e, `<b>${esc(r.label)}</b><br>${esc(r.tip || fmt(r.value, opts.digits||2) + (opts.unit||""))}`));
    rect.addEventListener("mouseleave", hideTip);
  });
  return svg;
}

// Multi-series line chart. data: {x:[labels], series:{name:[values]}}, opts:{unit, height, colors:{name:var}, highlight:[names]}
function lines(container, data, opts={}){
  const c = typeof container === "string" ? document.getElementById(container) : container;
  const W = opts.width || Math.min(c.clientWidth || 900, 1000), H = opts.height || 260;
  const m = {l:52, r:16, t:12, b:30};
  const names = Object.keys(data.series);
  const svg = el("svg", {viewBox:`0 0 ${W} ${H}`, width:"100%", role:"img"}, c);
  const allv = names.flatMap(n => data.series[n]).filter(v => v != null);
  const max = opts.max || niceMax(Math.max(...allv));
  const n = data.x.length;
  const sx = i => m.l + (W - m.l - m.r) * (n > 1 ? i/(n-1) : 0.5);
  const sy = v => m.t + (H - m.t - m.b) * (1 - v/max);
  const g = el("g", {class:"grid"}, svg);
  for (let i = 0; i <= 4; i++){ const v = max*i/4; el("line", {x1:m.l, x2:W-m.r, y1:sy(v), y2:sy(v)}, g); txt(svg, m.l-6, sy(v)+4, fmt(v, opts.digits||0), {"text-anchor":"end", class:"num muted"}); }
  const step = Math.max(1, Math.ceil(n / (opts.ticks || 10)));
  data.x.forEach((lab, i) => { if (i % step === 0 || i === n-1) txt(svg, sx(i), H-8, opts.xfmt ? opts.xfmt(lab) : lab, {"text-anchor":"middle", class:"num muted"}); });
  const colors = {};
  names.forEach((nm, i) => { colors[nm] = (opts.colors && opts.colors[nm]) || SERIES[i % 8]; });
  names.forEach(nm => {
    const vals = data.series[nm];
    const d = vals.map((v, i) => v == null ? null : `${i && vals[i-1] != null ? "L" : "M"}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`).filter(Boolean).join(" ");
    const dim = opts.highlight && !opts.highlight.includes(nm);
    el("path", {d, fill:"none", stroke:`var(${colors[nm]})`, "stroke-width": dim ? 1.2 : 2, opacity: dim ? 0.45 : 1, "stroke-linejoin":"round"}, svg);
    const last = vals.length - 1;
    if (vals[last] != null && !dim){ el("circle", {cx:sx(last), cy:sy(vals[last]), r:3.5, fill:`var(${colors[nm]})`, stroke:"var(--paper)", "stroke-width":2}, svg); }
  });
  // hover crosshair
  const cross = el("line", {x1:0, x2:0, y1:m.t, y2:H-m.b, stroke:"var(--ink-3)", "stroke-dasharray":"3 3", opacity:0}, svg);
  const hit = el("rect", {x:m.l, y:m.t, width:W-m.l-m.r, height:H-m.t-m.b, fill:"transparent"}, svg);
  hit.addEventListener("mousemove", e => {
    const r = svg.getBoundingClientRect(); const px = (e.clientX - r.left) * W / r.width;
    const i = Math.round((px - m.l) / (W-m.l-m.r) * (n-1)); if (i < 0 || i >= n) return;
    cross.setAttribute("x1", sx(i)); cross.setAttribute("x2", sx(i)); cross.setAttribute("opacity", 1);
    const rows = names.map(nm => `<span style="color:var(${colors[nm]})">■</span> ${esc(nm)}: <b>${fmt(data.series[nm][i], opts.digits||1)}${opts.unit||""}</b>`).join("<br>");
    showTip(e, `<b>${esc(data.x[i])}</b><br>${rows}`);
  });
  hit.addEventListener("mouseleave", () => { cross.setAttribute("opacity", 0); hideTip(); });
  if (opts.legend !== false){
    const lg = document.createElement("div"); lg.className = "legend";
    names.forEach(nm => { const s = document.createElement("span"); s.innerHTML = `<i style="background:var(${colors[nm]})"></i>${esc(opts.names ? (opts.names[nm]||nm) : nm)}`; lg.appendChild(s); });
    c.appendChild(lg);
  }
  return svg;
}

// Heatmap as a table. rows: [{label, vals:[]}], cols: [names]. Sequential ramp from tokens.
function heat(container, rows, cols, opts={}){
  const c = typeof container === "string" ? document.getElementById(container) : container;
  const wrap = document.createElement("div"); wrap.className = "tbl"; c.appendChild(wrap);
  const t = document.createElement("table"); t.className = "heat"; wrap.appendChild(t);
  const max = opts.max || Math.max(...rows.flatMap(r => r.vals));
  const ramp = ["--seq1","--seq2","--seq3","--seq4","--seq5","--seq6","--seq7"];
  const head = t.insertRow(); head.appendChild(document.createElement("th"));
  cols.forEach(cn => { const th = document.createElement("th"); th.textContent = cn; head.appendChild(th); });
  rows.forEach(r => {
    const tr = t.insertRow(); const td0 = tr.insertCell(); td0.className = "rowlab"; td0.textContent = r.label;
    r.vals.forEach((v, j) => {
      const td = tr.insertCell(); const q = opts.log ? Math.log1p(v)/Math.log1p(max) : v/max;
      const k = Math.min(6, Math.floor(q * 6.999));
      td.style.background = v > 0 ? `var(${ramp[k]})` : "transparent";
      td.style.color = k >= 4 ? "#fff" : "var(--ink)";
      td.textContent = opts.fmt ? opts.fmt(v) : fmt(v, 1);
      td.addEventListener("mousemove", e => showTip(e, `<b>${esc(r.label)}</b> × ${esc(cols[j])}<br>${fmt(v, 2)}${opts.unit||""}`));
      td.addEventListener("mouseleave", hideTip);
    });
  });
  return t;
}

// Small multiples of sparkline-like line charts. items: [{title, x, y, note}]
function sparks(container, items, opts={}){
  const c = typeof container === "string" ? document.getElementById(container) : container;
  const grid = document.createElement("div"); grid.style.display = "grid"; grid.style.gridTemplateColumns = `repeat(auto-fill,minmax(${opts.minw||210}px,1fr))`; grid.style.gap = "10px 18px"; c.appendChild(grid);
  items.forEach(it => {
    const box = document.createElement("div");
    const W = 220, H = opts.height || 70, m = {l:4, r:4, t:14, b:4};
    const max = opts.sharedMax ? opts.sharedMax : niceMax(Math.max(...it.y));
    const svg = el("svg", {viewBox:`0 0 ${W} ${H}`, width:"100%"}, box);
    txt(svg, 0, 10, it.title, {class:"lbl", "font-size":"11.5px", "font-weight":"600"});
    txt(svg, W, 10, it.note || "", {"text-anchor":"end", class:"muted num", "font-size":"10.5px"});
    const n = it.y.length, sx = i => m.l + (W-m.l-m.r) * i/(n-1), sy = v => m.t + (H-m.t-m.b) * (1 - v/max);
    const d = it.y.map((v,i) => `${i?"L":"M"}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`).join(" ");
    el("path", {d: d + ` L${sx(n-1).toFixed(1)},${H-m.b} L${sx(0)},${H-m.b} Z`, fill:`var(${it.color||"--s1"})`, opacity:0.15}, svg);
    el("path", {d, fill:"none", stroke:`var(${it.color||"--s1"})`, "stroke-width":1.8}, svg);
    const pk = it.y.indexOf(Math.max(...it.y));
    el("circle", {cx:sx(pk), cy:sy(it.y[pk]), r:3, fill:`var(${it.color||"--s1"})`, stroke:"var(--paper)", "stroke-width":1.5}, svg);
    const hit = el("rect", {x:0, y:0, width:W, height:H, fill:"transparent"}, svg);
    hit.addEventListener("mousemove", e => { const r = svg.getBoundingClientRect(); const i = Math.max(0, Math.min(n-1, Math.round((e.clientX-r.left)/r.width*(n-1)))); showTip(e, `<b>${esc(it.title)}</b><br>${esc(it.x[i])}: ${fmt(it.y[i], 1)}${opts.unit||""}`); });
    hit.addEventListener("mouseleave", hideTip);
    grid.appendChild(box);
  });
}

function table(container, cols, rows, opts={}){
  const c = typeof container === "string" ? document.getElementById(container) : container;
  const wrap = document.createElement("div"); wrap.className = "tbl"; c.appendChild(wrap);
  const t = document.createElement("table"); wrap.appendChild(t);
  const head = t.insertRow();
  cols.forEach(col => { const th = document.createElement("th"); th.textContent = col.h; if (col.n) th.className = "n"; head.appendChild(th); });
  rows.forEach(r => { const tr = t.insertRow(); cols.forEach(col => { const td = tr.insertCell(); const v = typeof col.k === "function" ? col.k(r) : r[col.k]; if (col.html) td.innerHTML = v; else td.textContent = col.n ? fmt(v, col.d||0) : v; if (col.n) td.className = "n"; }); });
  return t;
}
