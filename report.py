"""Render results as one self-contained HTML page, in the spirit of the
Backdoor demo: a grid of every company tinted by chance, a detail panel
with the per-signal meters, and the shortlist.

Colour is one sequential hue (blue, light to dark) because the only thing
encoded is magnitude. Mismatch is a state, so it gets a glyph and a label,
never colour alone. Favicons load from Google's s2 endpoint when the page is
opened, so the page needs network for logos; everything else is inline.
"""

from __future__ import annotations

import html
import json

# dataviz reference palette, sequential blue steps 100..700
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
        "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]

SIGNAL_LABELS = {
    "domain_fit": ("domain", "same kind of product"),
    "role_fit": ("role", "a role they hire for"),
    "stage_fit": ("stage", "worked at this stage"),
    "would_interview": ("reply", "recruiter would reach out"),
    "location_ok": ("place", "location works"),
}

MISMATCH_LABELS = {
    "domain": "wrong industry",
    "discipline": "wrong discipline",
    "seniority": "seniority off",
    "stage": "wrong stage",
    "location": "location rules it out",
}


def _candidate_name(resume: str) -> str:
    for line in resume.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:60]
    return "Candidate"


def render_html(summary: dict, results: list[dict], resume: str, photo: str | None = None) -> str:
    payload = json.dumps(
        {"summary": summary, "results": results, "candidate": _candidate_name(resume), "photo": photo,
         "ramp": RAMP, "labels": SIGNAL_LABELS, "mismatch_labels": MISMATCH_LABELS},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload).replace("__TITLE__", html.escape(_candidate_name(resume)))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>jobbyjev: __TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--surface:#f6f5f2;--card:#ffffff;--ink:#1a1a1a;--ink2:#5a5a57;--ink3:#8c8b86;--line:#e6e4df;--tile:#ecebe7;--warn:#b4531a;--hot:#d63b2f}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",sans-serif}
header{display:flex;align-items:flex-end;justify-content:space-between;padding:22px 28px 14px;gap:24px;flex-wrap:wrap}
.me{display:flex;align-items:center;gap:14px}
.avatar{width:56px;height:56px;border-radius:50%;object-fit:cover;border:1px solid var(--line);background:var(--tile)}
h1{font-size:22px;font-weight:600;margin:0;letter-spacing:-.01em}
h1 small{display:block;font-size:12px;color:var(--ink3);font-weight:500;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px}
.stats{display:flex;gap:28px}
.stat{min-width:84px}
.stat .k{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3)}
.stat .v{font-size:26px;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.stat .v span{font-size:14px;color:var(--ink3);font-weight:500}
main{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:20px;padding:0 28px 28px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(44px,1fr));gap:6px;align-content:start}
.tile{position:relative;aspect-ratio:1;border-radius:8px;background:var(--tile);display:flex;align-items:center;justify-content:center;cursor:pointer;border:2px solid transparent;transition:transform .08s}
.tile:hover{transform:scale(1.12);z-index:2}
.tile.hot{border-color:var(--hot)}
.tile.sel{border-color:var(--ink)}
.tile img{width:22px;height:22px;border-radius:4px;object-fit:contain}
.tile .ini{font-size:11px;font-weight:600;color:var(--ink2)}
.tile.mm::after{content:"×";position:absolute;top:1px;right:4px;font-size:10px;line-height:1;color:var(--ink2)}
.tile.hi img,.tile.hi .ini{filter:none}
.legend{grid-column:1;display:flex;align-items:center;gap:10px;font-size:12px;color:var(--ink3);margin-top:6px}
.legend .bar{height:6px;width:140px;border-radius:3px;background:linear-gradient(90deg,#cde2fb,#0d366b)}
.legend .ring{display:inline-block;width:10px;height:10px;border-radius:3px;border:2px solid var(--hot);vertical-align:-1px;margin-right:4px}
aside{display:flex;flex-direction:column;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.card h2{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);margin:0 0 10px;font-weight:600}
.who{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.who .name{font-size:18px;font-weight:600}
.who .meta{color:var(--ink2);font-size:13px}
.big{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.02em;text-align:right}
.big small{display:block;font-size:11px;color:var(--ink3);letter-spacing:.08em;text-transform:uppercase;font-weight:600}
.sig{display:grid;grid-template-columns:52px 150px 1fr 34px;align-items:center;gap:10px;padding:5px 0;font-size:13px}
.sig .k{color:var(--ink3)}
.sig .d{color:var(--ink2)}
.meter{height:4px;border-radius:2px;background:var(--line);position:relative}
.meter i{position:absolute;left:0;top:0;bottom:0;border-radius:2px;background:#256abf}
.sig .n{text-align:right;font-variant-numeric:tabular-nums;color:var(--ink)}
.mm-label{margin-top:10px;font-size:13px;color:var(--warn)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.chip{font-size:12px;background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:2px 9px;color:var(--ink2)}
.short{display:flex;gap:8px;overflow-x:auto;overscroll-behavior-x:contain;scroll-snap-type:x proximity;scroll-behavior:smooth;padding:2px 2px 10px;scrollbar-width:thin;scrollbar-color:var(--line) transparent}
.short::-webkit-scrollbar{height:6px}
.short::-webkit-scrollbar-thumb{background:var(--line);border-radius:3px}
.short .s{flex:0 0 92px;scroll-snap-align:start;background:var(--surface);border:2px solid var(--line);border-radius:10px;padding:10px 6px;text-align:center;cursor:pointer;font-size:12px;min-width:0}
.short .s.hot{border-color:var(--hot)}
.short .s.sel{border-color:var(--ink)}
.short-meta{font-size:12px;color:var(--ink3);margin:-4px 0 8px}
.short .s img{width:20px;height:20px;border-radius:4px;margin-bottom:4px}
.short .s b{display:block;font-size:16px;font-variant-numeric:tabular-nums}
.short .s span{display:block;color:var(--ink3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--line)}
th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);font-weight:600}
td.n{text-align:right}
tr{cursor:pointer}
tr.sel td{background:#f0efec}
details summary{cursor:pointer;color:var(--ink2);font-size:13px}
.tip{position:fixed;pointer-events:none;background:var(--ink);color:#fff;font-size:12px;padding:6px 9px;border-radius:6px;display:none;z-index:9;max-width:260px}
@media (max-width:980px){main{grid-template-columns:1fr}}
</style></head>
<body>
<header>
  <div class="me"><img class="avatar" id="avatar" alt="" hidden><h1><small>Picking the best company using Jev</small><span id="cand"></span></h1></div>
  <div class="stats" id="stats"></div>
</header>
<main>
  <section>
    <div class="grid" id="grid" aria-label="Companies, tinted by chance"></div>
    <div class="legend"><span>less likely</span><span class="bar"></span><span>more likely</span><span style="margin-left:14px"><i class="ring"></i> over 50%</span><span style="margin-left:14px">× = mismatch flagged</span></div>
    <details style="margin-top:18px"><summary>Ranked table (all companies)</summary>
      <table id="tbl"><thead><tr><th>#</th><th>Company</th><th>HQ</th><th>Stage</th><th class="n">Chance</th><th class="n">Conf</th><th>Mismatch</th></tr></thead><tbody></tbody></table>
    </details>
  </section>
  <aside>
    <div class="card" id="detail"></div>
    <div class="card"><h2>High probability of interviewing</h2><div class="short-meta" id="shortmeta"></div><div class="short" id="short"></div></div>
  </aside>
</main>
<div class="tip" id="tip"></div>
<script>
const D = __DATA__;
const R = D.results, S = D.summary;
const $ = s => document.querySelector(s);
const fav = d => d ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(d)}&sz=64` : "";
const ini = n => n.split(/\s+/).slice(0,2).map(w=>w[0]).join("").toUpperCase();
const pct = x => Math.round(x*100);
const tint = c => D.ramp[Math.min(D.ramp.length-1, Math.floor(c*D.ramp.length))];
const mix = (hex, a) => { // blend ramp colour over the neutral tile so low chance recedes
  const n = parseInt(hex.slice(1),16), r=n>>16, g=(n>>8)&255, b=n&255;
  const base=[236,235,231];
  return `rgb(${Math.round(base[0]+(r-base[0])*a)},${Math.round(base[1]+(g-base[1])*a)},${Math.round(base[2]+(b-base[2])*a)})`;
};
let sel = null;
const HOT = 0.5;                       // ring threshold, also the shortlist cut
const SHORT_MIN = 5, SHORT_MAX = 40;   // shortlist always shows at least 5, at most 40

$("#cand").textContent = D.candidate;
if (D.photo) { const a = $("#avatar"); a.src = D.photo; a.hidden = false; }
$("#stats").innerHTML = [
  ["checked", `${S.checked}<span>/${S.total}</span>`],
  ["likely interview", S.likely_interview],
  ["mismatch", S.mismatched],
  ["avg. chance", S.avg_chance.toFixed(2)],
  ["time", `${S.elapsed_s}<span>s</span>`],
  ["cost", `$${S.cost_usd.toFixed(5)}`],
].map(([k,v])=>`<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");

const logo = r => `<img src="${fav(r.domain)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ini',textContent:'${ini(r.name)}'}))">`;

const grid = $("#grid");
R.forEach(r => {
  const t = document.createElement("div");
  t.className = "tile" + (r.mismatch ? " mm" : "") + (r.chance >= HOT ? " hot" : "");
  t.style.background = mix(tint(r.chance), 0.25 + 0.75*r.chance);
  t.dataset.id = r.id;
  t.innerHTML = logo(r);
  t.onclick = () => select(r.id);
  t.onmousemove = e => { const tip=$("#tip"); tip.style.display="block"; tip.style.left=(e.clientX+12)+"px"; tip.style.top=(e.clientY+12)+"px";
    tip.textContent = `${r.name} · ${pct(r.chance)}%` + (r.mismatch ? ` · ${D.mismatch_labels[r.mismatch]}` : ""); };
  t.onmouseleave = () => $("#tip").style.display="none";
  grid.appendChild(t);
});

const hotCount = R.filter(r => r.chance >= HOT).length;
const shortN = Math.min(SHORT_MAX, Math.max(SHORT_MIN, hotCount));
$("#shortmeta").textContent = hotCount > shortN ? `${hotCount} over ${pct(HOT)}%, showing the top ${shortN}, scroll sideways`
  : hotCount ? `${hotCount} over ${pct(HOT)}%, scroll sideways` : `none over ${pct(HOT)}%, showing the top ${shortN}`;
$("#short").innerHTML = R.slice(0, shortN).map(r => `<div class="s${r.chance >= HOT ? " hot" : ""}" data-id="${r.id}" title="${r.name}" onclick="select('${r.id}')">${logo(r)}<b>${pct(r.chance)}%</b><span>${r.name}</span></div>`).join("");
// wheel over the strip scrolls it sideways, so a trackpad or mouse wheel both work
$("#short").addEventListener("wheel", e => { if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { e.preventDefault(); e.currentTarget.scrollLeft += e.deltaY; } }, {passive:false});

$("#tbl tbody").innerHTML = R.map(r => `<tr data-id="${r.id}" onclick="select('${r.id}')"><td>${r.rank}</td><td>${r.name}</td><td>${r.hq||""}</td><td>${r.stage||""}</td><td class="n">${r.chance.toFixed(2)}</td><td class="n">${r.confidence.toFixed(2)}</td><td>${r.mismatch ? D.mismatch_labels[r.mismatch] : ""}</td></tr>`).join("");

function select(id){
  sel = id;
  const r = R.find(x => x.id === id);
  document.querySelectorAll("[data-id]").forEach(el => el.classList.toggle("sel", el.dataset.id === id));
  const card = document.querySelector(`.short .s[data-id="${id}"]`);
  if (card) card.scrollIntoView({behavior:"smooth", block:"nearest", inline:"center"});
  const sigs = [
    ["domain_fit", r.signals.domain_fit.value, r.signals.domain_fit.confidence],
    ["role_fit", r.signals.role_fit.value, r.signals.role_fit.confidence],
    ["stage_fit", r.signals.stage_fit.value, r.signals.stage_fit.confidence],
    ["would_interview", r.would_interview, null],
    ["location_ok", r.location_ok, null],
  ];
  $("#detail").innerHTML = `
    <div class="who">
      <div>${logo(r)}<div class="name">${r.name}</div>
        <div class="meta">${r.hq||""} · ${r.stage||""} · ${r.size||""} · ${r.category||""}${r.founder_led ? " · founder-led" : ""}</div></div>
      <div class="big"><small>chance</small>${pct(r.chance)}%<small style="margin-top:6px">confidence ${r.confidence.toFixed(2)}</small></div>
    </div>
    <h2 style="margin-top:16px">Interview signals</h2>
    ${sigs.map(([k,v,c]) => `<div class="sig"><span class="k">${D.labels[k][0]}</span><span class="d">${D.labels[k][1]}</span><div class="meter" title="${c!=null?`confidence ${c.toFixed(2)}`:""}"><i style="width:${pct(v)}%"></i></div><span class="n">${pct(v)}</span></div>`).join("")}
    ${r.mismatch ? `<div class="mm-label">× mismatch: ${D.mismatch_labels[r.mismatch]} (${pct(r.mismatch_probs[r.mismatch]||0)}%)</div>` : `<div class="mm-label" style="color:var(--ink3)">no mismatch flagged</div>`}
    <h2 style="margin-top:14px">They hire for</h2>
    <div class="chips">${(r.hiring_for||[]).map(h=>`<span class="chip">${h}</span>`).join("")}</div>`;
}
if (R.length) select(R[0].id);
</script>
</body></html>
"""
