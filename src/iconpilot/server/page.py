"""Review page — Vue 3 (vendored ESM, no build step), responsive, interactive."""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iconpilot review</title>
<link id="fav" rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3C/svg%3E">
<script>
(function () {
  var th = null;
  try { th = localStorage.getItem('iconpilot.theme'); } catch (e) {}
  if (!th) th = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  document.documentElement.dataset.theme = th;
})();
</script>
<style>
:root {
  /* light — tinted neutrals, hue 150; see DESIGN.md */
  --bg: oklch(0.975 0.004 150);
  --card: oklch(0.995 0.002 150);
  --card-2: oklch(0.955 0.005 150);
  --ink: oklch(0.250 0.012 155);
  --muted: oklch(0.500 0.015 155);
  --line: oklch(0.905 0.006 150);
  --accent: oklch(0.500 0.125 152);
  --accent-ink: oklch(0.995 0.002 150);
  --warn: oklch(0.620 0.130 70);
  --danger: oklch(0.550 0.170 25);
  --star: oklch(0.750 0.150 85);
  --chip: color-mix(in oklab, var(--line) 45%, var(--card));
  --focus: oklch(0.600 0.110 152);
  --shadow: 0 1px 3px oklch(0.25 0.02 155 / 0.10);
  --shadow-lg: 0 12px 40px oklch(0.20 0.02 155 / 0.22);
  color-scheme: light;
}
:root[data-theme="dark"] {
  --bg: oklch(0.165 0.008 155);
  --card: oklch(0.205 0.009 155);
  --card-2: oklch(0.245 0.010 155);
  --ink: oklch(0.930 0.008 150);
  --muted: oklch(0.700 0.012 150);
  --line: oklch(0.300 0.012 155);
  --accent: oklch(0.720 0.135 152);
  --accent-ink: oklch(0.150 0.025 152);
  --warn: oklch(0.780 0.125 75);
  --danger: oklch(0.680 0.160 25);
  --star: oklch(0.800 0.140 85);
  --chip: color-mix(in oklab, var(--line) 40%, var(--card));
  --focus: oklch(0.760 0.115 152);
  --shadow: 0 1px 3px oklch(0 0 0 / 0.35);
  --shadow-lg: 0 12px 40px oklch(0 0 0 / 0.50);
  color-scheme: dark;
}
* { box-sizing: border-box; }
.dialog .row > label.muted { flex:0 0 110px; min-width:0; }
input, select, textarea {
  font: inherit; color: var(--ink); background: var(--card);
  border: 1px solid var(--line); border-radius: 8px;
  padding: 6px 10px; min-height: 32px;
}
select, input:not([type="checkbox"]):not([type="color"]):not([type="range"]) { height:32px; box-sizing:border-box; }
.topbar select { height:28px; }
select { cursor: pointer; }
input[type="color"] { min-height: 28px; padding: 0 2px; }
input[type="range"] { min-height: 0; padding: 0; }
:is(button, input, select, textarea, summary):focus-visible {
  outline: 2px solid var(--focus); outline-offset: 1px;
}
button, .card, .iconbtn, .histhumb, .stylestrip summary, .chip { transition: border-color .12s ease-out, background-color .12s ease-out, color .12s ease-out; }
button:disabled { opacity:.45; cursor:not-allowed; }
.ab-apply:disabled { background:var(--card); color:var(--muted); border-color:var(--line); }
body { margin:0; font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
       background:var(--bg); color:var(--ink); }
/* one-line sticky top bar — identity left, tabs center, actions right */
.topbar { position:sticky; top:0; z-index:30; background:var(--card); border-bottom:1px solid var(--line);
          box-shadow:var(--shadow); }
.topbar-row { display:flex; align-items:stretch; gap:12px; padding:0 16px; min-height:52px; }
.tb-left  { flex:1 1 0; min-width:0; display:flex; align-items:center; gap:8px; }
.tb-right { flex:1 1 0; min-width:0; display:flex; align-items:center; justify-content:flex-end; gap:8px; }
.topbar h1 { font-size:1rem; margin:0; font-weight:650; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.topbar .meta.rev { color:var(--muted); font-size:.8rem; white-space:nowrap; }

/* centered tabs — full-height, underline flush with the bar's bottom border */
.tabs { display:flex; gap:4px; flex:0 0 auto; align-items:stretch; }
.tabs button { border:none; border-bottom:2px solid transparent; border-radius:0; background:none;
               color:var(--muted); padding:0 14px; font-weight:600; display:inline-flex; gap:6px; align-items:center;
               height:auto; align-self:stretch; }  /* exempt from the 32px cap — reach the bar bottom */
.tabs button:hover { color:var(--ink); }
.tabs button.on { color:var(--accent); border-bottom-color:var(--accent); }

/* inline AI status chip — zero rows, truncates, full text in title */
.aistatwrap { position:relative; display:inline-flex; min-width:0; }
.aistat { display:inline-flex; align-items:center; gap:6px; min-width:28px; height:32px; max-width:240px;
          font-size:.8rem; padding:0 10px; border-radius:99px; border:none; cursor:pointer; }
.aistat-pop { position:absolute; top:calc(100% + 8px); right:0; z-index:60; background:var(--card);
              border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow);
              padding:8px 12px; font-size:.8rem; color:var(--ink); max-width:min(300px, 80vw);
              white-space:normal; line-height:1.4; }
.aistat .dot { width:8px; height:8px; border-radius:50%; background:currentColor; flex:none; }
.aistat-txt { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.aistat.working { color:var(--warn); background:color-mix(in srgb, var(--warn) 14%, transparent); }
.aistat.working .dot { animation:pulse 1.6s infinite; }
.aistat.ready   { color:var(--accent); background:color-mix(in srgb, var(--accent) 12%, transparent); }
:root[data-theme="dark"] .aistat.working { background:color-mix(in srgb, var(--warn) 24%, transparent);
          color:color-mix(in srgb, var(--warn) 55%, white); }

/* full-area waiting state (pick tab, agent drafting, nothing to rate yet) */
.waitstate { display:flex; justify-content:center; padding:48px 16px 64px; }
.waitcard { text-align:center; max-width:520px; background:var(--card); border:1px solid var(--line);
            border-radius:14px; box-shadow:var(--shadow); padding:28px 24px 24px; }
.waitcard h2 { margin:14px 0 6px; font-size:1.15rem; }
.waitcard p { margin:4px 0; }
.waiticon { width:48px; height:48px; margin:0 auto; border-radius:12px;
            background:color-mix(in srgb, var(--warn) 14%, transparent);
            display:flex; align-items:center; justify-content:center; }
.waitpulse { animation:pulse 1.6s infinite; color:var(--warn); }
.waitpulse svg { width:24px; height:24px; }
.waittargets { display:flex; flex-wrap:wrap; gap:5px; justify-content:center; margin:12px 0 4px; }
.waitskeleton { display:flex; gap:8px; justify-content:center; margin:14px 0 6px; }
.skcell { width:56px; height:56px; border-radius:10px; border:1px dashed var(--line);
          background:var(--card-2); animation:pulse 2.2s infinite; }
.skcell:nth-child(2) { animation-delay:.2s; } .skcell:nth-child(3) { animation-delay:.4s; }
.skcell:nth-child(4) { animation-delay:.6s; } .skcell:nth-child(5) { animation-delay:.8s; }
.skcell:nth-child(6) { animation-delay:1s; }

/* breakpoint ladder */
@media (max-width:1199px) { .tb-left .meta.rev { display:none; } .aistat { max-width:160px; } }
@media (max-width:1023px) { .tabs .tab-label { display:none; } .aistat-txt { display:none; }
                            .aistat { padding:3px 6px; } .tb-right .refresh { display:none; } }
@media (max-width:640px) {
  .topbar-row { flex-wrap:wrap; align-items:center; min-height:0; padding:0 12px; }
  .tb-left, .tb-right { flex:1 1 auto; padding:8px 0; }
  .tabs { order:3; flex:1 0 100%; border-top:1px solid var(--line); }
  .tabs button { flex:1; justify-content:center; min-height:44px; padding:0; }
  .nextpass .np-label { display:none; }
  .tb-right select { max-width:92px; }
}
.spacer { flex:1; }
.banner { width:100%; padding:6px 12px; border-radius:8px; font-size:.85rem; display:flex; gap:8px; align-items:center; }
.ic { display:inline-flex; vertical-align:-2px; }
.ic svg { width:14px; height:14px; }
.ic-lg svg { width:18px; height:18px; vertical-align:-4px; }
.dotnew { width:7px; height:7px; border-radius:50%; background:var(--warn); display:inline-block; margin-left:2px; }
.chip.new { background:var(--warn); color:var(--bg); font-size:.65rem; padding:1px 6px; font-weight:600; }
.suggestbox { position:absolute; top:100%; left:0; right:0; z-index:30; background:var(--card);
             border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow-lg); max-height:200px; overflow-y:auto; }
.focusgrid { border-collapse:collapse; width:100%; }
.focusgrid th, .focusgrid td { padding:4px 6px; text-align:center; border-bottom:1px solid var(--line); }
.focusgrid td:first-child, .focusgrid th:first-child { text-align:left; font-weight:600; }
.focusgrid input[type=checkbox] { min-height:0; }
.stylestrip { margin: 0 0 12px; }
.stylestrip summary { cursor:pointer; color:var(--muted); padding:6px 10px; border:1px solid var(--line);
                      border-radius:10px; background:var(--card); display:inline-flex; gap:8px; align-items:center;
                      user-select:none; }
.stylestrip summary:hover { color:var(--ink); border-color:var(--accent); }
@keyframes spin { to { transform: rotate(360deg); } }

.spin { width:16px; height:16px; border:2px solid var(--line); border-top-color: var(--accent);
  border-radius:50%; display:inline-block; animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
progress { flex:1; height:6px; accent-color: var(--accent); }
.progressrow { display:flex; gap:16px; align-items:center; margin-top:12px; }
.progressrow progress { flex:1; margin-left:8px; }
.chip.fit { display:inline-block; width:auto; align-self:center; }
.dropzone { outline: 2px dashed var(--accent); outline-offset: 4px; border-radius: 8px; }
.selmatrix { border-collapse:collapse; font-size:.78rem; }
.selmatrix .sh { position:sticky; left:0; background:var(--card); text-align:left; padding:2px 8px 2px 0; border-bottom:1px solid var(--line); white-space:nowrap; }
.selmatrix .ih { padding:2px 6px; border-bottom:1px solid var(--line); }
.selmatrix .cell { padding:2px 6px; border-bottom:1px solid var(--line); vertical-align:middle; }
.selmatrix .cell:empty { background:var(--card-2); }
.only-wide { display:block; }
.only-narrow { display:none; }
@media (max-width:700px) {
  .only-wide { display:none; }
  .only-narrow { display:block; }
}
.selchip { display:inline-flex; align-items:center; gap:4px; min-height:36px; padding:0 12px;
           border-radius:99px; border:1px solid var(--line); background:var(--card);
           color:var(--muted); font-size:.78rem; cursor:pointer; }
.selchip.on { border-color:var(--accent); color:var(--accent); font-weight:600;
              background:color-mix(in srgb, var(--accent) 10%, transparent); }
@media (max-width:480px) { .actionbar .statustext { display:none; } }
@media (max-width:640px) {
  button, button.subtle, .iconbtn, .iconbtn-lg, .aistat { height:40px; }
  select, input:not([type="checkbox"]):not([type="color"]) { height:40px; }
}
.tabs button { border:none; border-bottom:2px solid transparent; border-radius:8px 8px 0 0; background:none;
               color:var(--muted); padding:8px 14px; font-weight:600; display:inline-flex; gap:6px; align-items:center; }
.tabs button.on { color:var(--accent); border-bottom-color:var(--accent); }
.tabs .tab-label { display:inline; }
@media (max-width: 640px) { .tabs .tab-label { display:none; } .tabs { padding:0 12px; }
.tabs button { padding:10px 12px; min-height:44px; } }
.refcell { margin:0; width:56px; display:inline-flex; flex-direction:column; align-items:center; gap:2px; position:relative; }
.refcell img { border-radius:8px; background:#fff; display:block; }
.stylecard { width:110px; padding:10px 8px; border:1px solid var(--line); border-radius:10px;
             display:inline-flex; flex-direction:column; align-items:center; gap:6px; cursor:pointer; background:var(--card); }
.stylecard:hover { border-color:var(--accent); }
.stylepick { width:92px; flex-direction:column; display:inline-flex; align-items:center; gap:4px; padding:8px 6px; }
.refcell .armed-x { position:absolute; top:-6px; right:-6px; padding:0 5px; }
.palchip { width:44px; height:32px; border-radius:8px; border:1px solid var(--line); position:relative;
           display:inline-flex; align-items:center; justify-content:center; overflow:hidden; }
.palchip input[type=color] { position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%; min-height:0; padding:0; border:none; }
.palchip .palx { position:absolute; top:-1px; right:-1px; padding:0 3px; font-size:.7rem; background:var(--card); border:1px solid var(--line); border-radius:0 0 0 6px; }
.paladd { border-style:dashed; color:var(--muted); }
.palrow { display:inline-flex; gap:3px; align-items:center; }
.chip.rule { background:color-mix(in oklab, var(--accent) 10%, var(--card)); }
.paldot.pick { cursor: pointer; outline: 2px solid transparent; outline-offset: 1px; }
.paldot.pick.sel { outline-color: var(--accent); }
.paldot { width:12px; height:12px; border-radius:50%; display:inline-block; border:1px solid var(--line); }
.chat { max-height:300px; overflow-y:auto; border:1px solid var(--line); border-radius:10px; padding:10px; margin-bottom:10px;
       background:color-mix(in oklab, var(--bg) 60%, var(--card)); display:flex; flex-direction:column; gap:6px; }
.chat-head { font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); text-align:center; margin:6px 0 2px; }
.chat-head:first-child { margin-top:0; }
.bubble { display:flex; align-items:baseline; gap:8px; padding:5px 10px; border-radius:12px; max-width:88%; font-size:.88rem; }
.bubble.user { align-self:flex-end; background:color-mix(in oklab, var(--accent) 14%, var(--card)); }
.bubble.agent { align-self:flex-start; background:color-mix(in oklab, var(--warn) 12%, var(--card)); }
.bubble.agent .bubble-text { color:var(--ink); }
.r-archived .bubble { opacity:.75; }
.bubble-text { flex:1; overflow-wrap:anywhere; }
.bubble-time { font-size:.75rem; color:var(--muted); white-space:nowrap; }
.scope { font-size:.75rem; }
.chip.agent { background:color-mix(in srgb, var(--warn) 18%, transparent); }
.chip.user { background:color-mix(in srgb, var(--line) 40%, transparent); }
.chip.done { background:color-mix(in srgb, var(--accent) 18%, transparent); }
.iconbtn.busy, button.busy { opacity:.45; pointer-events:none; }
.banner.working { background:color-mix(in srgb, var(--warn) 15%, transparent); color:var(--warn); }
:root[data-theme="dark"] .banner.working { background:color-mix(in srgb, var(--warn) 26%, transparent); color:color-mix(in srgb, var(--warn) 55%, white); }
.banner.ready  { background:color-mix(in srgb, var(--accent) 14%, transparent); color:var(--accent); }
.dot { width:8px; height:8px; border-radius:50%; background:currentColor; animation:pulse 1.6s infinite; }
.banner.ready .dot { animation:none; }
@keyframes pulse { 50% { opacity:.3; } }
main { max-width:1200px; margin:0 auto; padding:16px; }
section h2 { font-size:.85rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:22px 0 10px; }
.group { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; margin:10px 0; box-shadow:var(--shadow); }
.group > .ghead { display:flex; align-items:center; gap:10px; margin-bottom:8px; flex-wrap:wrap; }
.group b { font-size:1.15rem; letter-spacing:-0.01em; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:12px; }
.card { background:var(--card); border:1px solid transparent; border-radius:12px; padding:10px; text-align:center;
        display:flex; flex-direction:column; gap:8px; }
.card:hover { border-color:var(--line); }
.card .thumb { cursor:zoom-in; align-self:center; border-radius:8px; background:#fff; }
.card .name { font-size:.85rem; font-weight:600; }
.rating { display:flex; align-items:center; gap:10px; justify-content:center; }
.rating button { padding:4px 8px; font-size:.9rem; }
.rating input[type=range] { flex:1; min-width:60px; accent-color:var(--accent); }
button { font:inherit; padding:0 12px; height:32px; border-radius:8px; border:1px solid var(--line);
         background:var(--card); color:var(--ink); cursor:pointer;
         display:inline-flex; align-items:center; justify-content:center; gap:6px; }
button:hover { border-color:var(--accent); }
button.primary { background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }
button.subtle { font-size:.8rem; padding:0 8px; height:32px; color:var(--muted); }
button.armed { border-color:var(--accent); color:var(--accent); font-weight:600; }
button.armed-x { border-color:var(--warn); color:var(--warn); font-weight:600; }
.chip { display:inline-block; padding:1px 8px; border-radius:99px; font-size:.75rem; background:var(--chip); color:var(--muted); }
.chip.approved { background:var(--accent); color:var(--accent-ink); }
.chip.in_review, .chip.stale { background:var(--warn); color:var(--bg); }
textarea { font:13px/1.5 ui-monospace,Menlo,Consolas,monospace; width:100%; min-height:64px; padding:8px;
           border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--ink); resize:vertical; }
textarea[readonly] { color:var(--muted); }
.composer { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; margin:14px 0; }
.row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.composer .row { margin-top:8px; }
.err { color:var(--danger); font-size:.85rem; white-space:pre-wrap; margin:4px 0; }
.ok { color:var(--accent); font-size:.85rem; }
/* dialog */
.overlay { position:fixed; inset:0; background:oklch(0.15 0.01 155 / 0.48); display:flex; align-items:center;
           justify-content:center; z-index:50; padding:16px; }
.dialog { background:var(--card); border:1px solid var(--line); border-radius:14px; max-width:560px; width:100%;
          max-height:92vh; overflow:auto; padding:16px; box-shadow:var(--shadow-lg); }
.dialog h3 { margin:0 0 8px; font-size:1rem; display:flex; justify-content:space-between; align-items:center; }
.dialog .controls { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:8px 0; }
.dialog .controls label { font-size:.78rem; color:var(--muted); min-width:74px; }
.seg { display:flex; gap:4px; }
.seg button { padding:4px 10px; font-size:.85rem; }
.seg button.on { background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }
.swatch { width:26px; height:26px; border-radius:8px; border:2px solid var(--line); cursor:pointer; padding:0; }
.swatch.on { border-color:var(--accent); }
input[type=color] { width:34px; height:28px; padding:0 2px; border:1px solid var(--line); border-radius:8px; background:none; }
.matrix { display:flex; gap:12px; margin:10px 0; flex-wrap:wrap; }
.matrix .col { flex:1; min-width:200px; }
.matrix .colhead { font-size:.75rem; letter-spacing:.08em; color:var(--muted); margin-bottom:4px; }
.matrix .stage { border-radius:10px; display:flex; align-items:flex-end; justify-content:space-around;
                 padding:14px 8px; gap:8px; min-height:130px; }
.matrix .sizes { font-size:.7rem; color:var(--muted); text-align:center; margin-top:4px; }
.ratebtn { min-width:64px; font-weight:600; }
.sheet .sheetbox { position:fixed; bottom:0; left:0; right:0; max-width:560px; margin:0 auto;
                   background:var(--card); border:1px solid var(--line); border-bottom:none;
                   border-radius:16px 16px 0 0; padding:16px 16px calc(16px + env(safe-area-inset-bottom));
                   box-shadow:var(--shadow-lg); }
.sheet .sheetbox h3 { display:flex; justify-content:space-between; align-items:center; margin:0 0 10px; font-size:.95rem; }
.sheetstage { display:flex; align-items:flex-end; justify-content:center; gap:20px; padding:12px 0 16px; }
.stars { display:flex; gap:2px; }
.stars button { flex:1; font-size:30px; line-height:1.3; padding:10px 0; color:var(--line); border:none; background:none; }
.stars button.on { color: var(--star); }
.sheetrow { display:flex; justify-content:space-between; margin-top:10px; gap:8px; }
@media (min-width: 700px) {
  .sheet .sheetbox { position:relative; bottom:auto; border-radius:16px; border-bottom:1px solid var(--line); }
}
.stylebox { background:var(--chip); border-radius:10px; padding:10px; font-size:.82rem; margin-top:10px; }
.stylebox select { font:inherit; padding:4px 8px; border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--ink); }
.kv { display:grid; grid-template-columns:auto 1fr; gap:2px 12px; margin-top:6px; color:var(--muted); }
.kv b { color:var(--ink); font-weight:600; }
.muted { color:var(--muted); font-size:.82rem; }
footer { text-align:center; color:var(--muted); font-size:.75rem; padding:20px 0 96px; }
/* sticky action bar */
.actionbar { position:fixed; bottom:0; left:0; right:0; z-index:20; display:flex; align-items:center;
             gap:12px; padding:10px 16px calc(10px + env(safe-area-inset-bottom));
             background:var(--card); border-top:1px solid var(--line); box-shadow:var(--shadow-lg); }
.actionbar.ready { border-top-color:color-mix(in srgb, var(--accent) 40%, transparent); }
.ab-status { flex:1; font-size:.85rem; color:var(--muted); display:flex; align-items:center; gap:8px; min-width:0; }
.actionbar.ready .ab-status { color:var(--accent); font-weight:600; }
.dot.green { background:var(--accent); }
.dot.amber { background:var(--warn); animation:pulse 1.6s infinite; }
.dot.gray { background:var(--line); }
.ab-apply { min-width:120px; font-weight:700; letter-spacing:.02em; }
.ab-status.flash-ok { color:var(--accent); font-weight:650; }
.ab-status.flash-err { color:var(--danger); font-weight:650; }
/* group meta row (brief + color + style) */
.gmeta { display:flex; align-items:center; gap:8px; margin:-2px 0 10px; flex-wrap:wrap; }
.gmeta .brief { flex:1 1 160px; cursor:text; min-width:120px; font-size:.85rem; }
.brief-input { flex:1 1 160px; font:inherit; font-size:.85rem; padding:4px 8px; border-radius:8px;
               border:1px solid var(--accent); background:var(--card); color:var(--ink); min-width:120px; }
.colorchip { width:20px; height:20px; flex:none; border-radius:6px; border:1px solid var(--line); cursor:pointer; padding:0; background:none; }
.gmeta select { font:inherit; font-size:.8rem; padding:4px 6px; border-radius:8px;
                border:1px solid var(--line); background:var(--card); color:var(--ink); max-width:140px; }
.vargrid { display:flex; flex-direction:column; gap:10px; }
.vargroup { border:1px solid var(--line); background: color-mix(in oklab, var(--card-2) 55%, var(--card));
            border-radius:10px; padding:8px 10px; }
.varhead { column-gap: 6px;  display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.compare-grid { display:flex; gap:16px; }
.compare-col { flex:1; text-align:center; }
.compare-label { font-weight:600; margin-bottom:8px; }
.compare-sizes { display:flex; justify-content:center; gap:12px; align-items:flex-end; margin-top:8px; }
.card.kbactive { outline: 3px solid var(--accent); outline-offset: 2px; }
.iconbtn-lg { padding:0 9px; height:32px; display:inline-flex; align-items:center; justify-content:center; }
.iconbtn .ic.filled svg { fill: currentColor; }
.histstrip { margin:0 0 8px; font-size:.8rem; }
.histstrip summary { cursor:pointer; color:var(--muted); display:inline-flex; gap:6px; align-items:center;
                     padding:2px 6px; border-radius:6px; user-select:none; }
.histstrip summary:hover { background:var(--chip); color:var(--ink); }
.histgrid { display:flex; flex-wrap:wrap; gap:10px; padding:8px 0 4px; }
.histcell { margin:0; text-align:center; }
.histcell img { display:block; margin:0 auto; border-radius:6px; }
.histhumb { padding:0; border:1px solid var(--line); border-radius:8px; background:var(--card); cursor:zoom-in; }
.histhumb:hover { border-color:var(--accent); }
.histcell figcaption { font-size:.75rem; }
.thumb.missing { width:64px; height:64px; display:flex; align-items:center; justify-content:center;
                 color:var(--muted); border:1px dashed var(--line); border-radius:8px; }
.iconbtn { padding:0 7px; height:32px; font-size:.85rem; border:none; background:none; cursor:pointer;
             color:var(--muted); border-radius:6px; display:inline-flex; align-items:center; justify-content:center; }
.iconbtn:hover { color:var(--ink); background:var(--chip); }
.iconbtn.on { color:var(--accent); font-weight:700; }
.varstyle { font:inherit; font-size:.75rem; padding:2px 4px; border-radius:6px;
            border:1px solid var(--line); background:var(--card); color:var(--ink); }
@media (max-width: 640px) {
  main { padding:12px; }
  input, select, textarea { min-height:40px; }
  .grid { grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:10px; }
  .rating button, .ratebtn { min-height:48px; min-width:48px; }   /* thumb targets */
  .ab-apply { min-height:48px; flex:1; max-width:220px; }
  .card .subtle { min-height:44px; }
  .ghead { gap:6px; }
}
</style>
</head>
<body>
<div id="loader" style="display:flex; align-items:center; justify-content:center; min-height:50vh; flex-direction:column; gap:12px;">
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--accent, #2f855a)" stroke-width="2.5" stroke-linecap="round" style="animation:spin 1s linear infinite">
    <path d="M21 12a9 9 0 1 1-6.2-8.5"/>
  </svg>
  <span style="color:var(--muted, #66707a); font-size:.85rem">loading pack…</span>
</div>
<div id="app" style="visibility:hidden">
  <header class="topbar">
    <div class="topbar-row">
      <div class="tb-left">
        <h1>{{ S.pack.name || 'iconpilot' }}</h1>
        <span class="meta rev">rev {{ S.rev }}</span>
      </div>
      <nav class="tabs" role="tablist">
        <button :class="{ on: S.tab === 'round' }" @click="setTab('round')" role="tab" aria-label="pick"><span class="ic" v-html="IC.star"></span><span class="tab-label">pick</span></button>
        <button :class="{ on: S.tab === 'pack' }" @click="setTab('pack')" role="tab" aria-label="icons"><span class="ic" v-html="IC.grid"></span><span class="tab-label">icons</span></button>
        <button :class="{ on: S.tab === 'styles' }" @click="setTab('styles')" role="tab" aria-label="styles"><span class="ic" v-html="IC.palette"></span><span class="tab-label">styles</span></button>
        <button :class="{ on: S.tab === 'settings' }" @click="setTab('settings')" role="tab" aria-label="settings"><span class="ic" v-html="IC.gear"></span><span class="tab-label">settings</span></button>
      </nav>
      <div class="tb-right">
        <span v-if="S.ai.text" class="aistatwrap">
          <button class="aistat" :class="S.ai.active ? 'working' : 'ready'" @click.stop="S.aistatOpen = !S.aistatOpen"
                  :aria-label="'agent status: ' + S.ai.text" :aria-expanded="!!S.aistatOpen">
            <span class="dot"></span><span class="aistat-txt">{{ S.ai.text }}</span>
          </button>
          <div v-if="S.aistatOpen" class="aistat-pop" @click.stop>{{ S.ai.text }}</div>
        </span>
        <button class="subtle iconbtn-lg" @click="toggleTheme"
                :title="S.theme === 'dark' ? 'switch to light' : 'switch to dark'"
                :aria-label="S.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'">
          <span class="ic" v-html="S.theme === 'dark' ? IC.sun : IC.moon"></span>
        </button>
        <select v-if="S.rounds.length" :value="S.viewRound || S.latest" @change="switchRound($event.target.value)"
                class="subtle" style="padding:4px 6px" title="browse any pass — latest is the live one">
          <option v-for="r in S.rounds" :key="r" :value="r">{{ r }}{{ r === S.latest ? ' (live)' : '' }}</option>
        </select>
        <button class="subtle" :class="{ on: fbFor('pack').length }"
                title="feedback for the whole draft" aria-label="feedback for the whole draft" @click="openFb('pack')">
          <span class="ic" v-html="IC.comment"></span> {{ fbFor('pack').length || '' }}
          <span v-if="fbNew('pack')" class="chip new">{{ fbNew('pack') }} new</span>
        </button>
        <button class="primary nextpass" @click="openNextDlg()"
                title="apply first, then start the next pass — history is kept">
          <span class="ic" v-html="IC.plus"></span> <span class="np-label">next pass</span></button>
        <button class="subtle refresh" @click="load(true)" title="refresh" aria-label="refresh"><span class="ic" v-html="IC.refresh"></span></button>
      </div>
    </div>
  </header>

  <main>
<div v-show="S.tab === 'round'">
    <div v-if="S.msg" :class="S.msgClass">{{ S.msg }}</div>

    <section v-if="S.appliedRound === S.round && !isViewing()">
      <div class="banner ready" style="margin:8px 0">
        <span class="dot green"></span> pass {{ S.round }} applied — decisions are in. Start the next pass (optionally focused) when ready.
        <button class="subtle" @click="openNextDlg()">next pass…</button>
      </div>
    </section>
    <section v-if="S.viewRound && S.viewRound !== S.latest">
      <div class="banner working" style="margin:8px 0">
        viewing {{ S.viewRound }} (history — read only). <button class="subtle" @click="switchRound(S.latest)">back to {{ S.latest }}</button>
      </div>
    </section>
    <section v-if="waitingForAgent()" class="waitstate">
      <div class="waitcard">
        <div class="waiticon"><span class="ic-lg waitpulse" v-html="IC.spark"></span></div>
        <h2>agent is drafting pass {{ S.round || '—' }}</h2>
        <p class="muted">{{ S.ai.text }}</p>
        <div class="waittargets" v-if="waitTargets().length">
          <span class="chip" v-for="tg in waitTargets()" :key="tg">{{ tg }}</span>
        </div>
        <div class="waitskeleton" aria-hidden="true">
          <span v-for="n in 6" :key="n" class="skcell"></span>
        </div>
        <p class="muted" style="font-size:.8rem">candidates appear here automatically — rate them when they land.</p>
        <div class="row" style="justify-content:center; margin-top:10px">
          <button v-if="S.recraftReady || S.debug" class="subtle" @click="openBatchDlg()"
                  title="draft every open icon with Recraft instead — same icons on every sheet, one take per sheet">
            <span class="ic" v-html="IC.bolt"></span> seed with Recraft instead
          </button>
        </div>
      </div>
    </section>
    <section v-else-if="S.grouped.length">
      <div class="row" style="justify-content:space-between; align-items:baseline">
        <h2 style="margin:0">{{ S.viewRound && S.viewRound !== S.latest ? 'Archived pass ' + S.viewRound : 'Current pass — rate, then decide' }}</h2>
        <button v-if="(S.recraftReady || S.debug) && !isViewing()" class="subtle" @click="openBatchDlg()"
                title="Recraft pack draft: same icons on every sheet, one different take per sheet (≤9 icons per 3×3 sheet) — review before anything is written">
          <span class="ic" v-html="IC.bolt"></span> draft pack</button>
        <button v-if="(S.recraftReady || S.debug) && !isViewing()" class="subtle" @click="openRefineDlg(null)"
                title="Recraft refine: every open variant's best take + round feedback → improved variants (image-to-image)">
          <span class="ic" v-html="IC.spark"></span> refine pack</button>
      </div>
      <div class="group" v-for="(g, gi) in S.grouped" :key="g.key">
        <div class="ghead">
          <b>{{ g.icon }}</b>
          <span class="muted">{{ g.cands.length }} candidates across variants</span>
          <span class="spacer"></span>
          <button v-if="S.recraftReady || S.debug" class="subtle" :class="{ busy: S.drafting.startsWith(g.icon + '/') }"
                  title="Recraft: seed 4 drafts for every open variant of this icon"
                  @click="recraftIcon(g)"><span class="ic" v-html="IC.bolt"></span> draft</button>
          <button v-if="S.recraftReady || S.debug" class="subtle" @click="openRefineDlg(g.icon)"
                  title="Recraft refine: best take of each variant + your round feedback → improved variants (image-to-image)">
            <span class="ic" v-html="IC.spark"></span> refine</button>
          <button class="subtle" :class="{ 'armed-x': S.rejectArm === g.icon }" @click="rejectAllIcon(g)"
                  title="reject every candidate for this icon (click twice)">reject all</button>
        </div>
        <div class="gmeta">
          <span class="muted brief">{{ packBriefIcon(g) }}</span>
          <button class="iconbtn" :class="{ on: hasNote(g) }"
                  title="feedback for this glyph" aria-label="feedback for this glyph" @click="openFb('icon', g.icon)">
            <span class="ic" v-html="IC.comment"></span><span v-if="fbNew('icon', g.icon)" class="dotnew"></span>
          </button>
          <input type="color" class="colorchip" :value="mainColorIcon(g) || '#89919a'"
                 title="main color" aria-label="main color"
                 @input="saveMainColorIcon(g, $event.target.value)">
        </div>
        <details class="histstrip" @toggle="e => e.target.open && loadIconHist(g)">
          <summary><span class="ic" v-html="IC.history"></span> earlier passes</summary>
          <div v-if="(S.iconHist[g.icon] || []).length" class="histgrid">
            <figure v-for="hc in S.iconHist[g.icon]" :key="hc.round + hc.variant + hc.cand" class="histcell">
              <button class="histhumb" @click="S.histView = hc" :title="'view ' + hc.round + ' ' + hc.variant + '/' + hc.cand">
                <img loading="lazy" width="40" height="40"
                     :src="render(hc.path, 40, '#f6f9f7', mainColorIcon(g))">
              </button>
              <figcaption class="muted">{{ hc.round }} · {{ hc.variant }}/{{ hc.cand }}</figcaption>
            </figure>
          </div>
          <p v-else class="muted">no earlier drafts</p>
        </details>
        <div class="vargrid">
          <div class="vargroup" v-for="(vg, vi) in variantGroups(g)" :key="vg.variant">
            <div class="varhead">
              <span class="chip" :class="{ done: isLocked(g.icon, vg.variant) }">{{ vg.variant }}<span v-if="isLocked(g.icon, vg.variant)" class="ic" v-html="IC.lock"></span></span>
              <button v-if="isLocked(g.icon, vg.variant)" class="iconbtn" title="reopen for the next pass (approved file stays in history)" aria-label="reopen"
                      @click="reopen(g.icon, vg.variant)"><span class="ic" v-html="IC.unlock"></span></button>
              <button v-if="!isLocked(g.icon, vg.variant)" class="iconbtn" :class="{ on: isPostponed(g.icon, vg.variant) }"
                      :title="isPostponed(g.icon, vg.variant) ? 'resume — include in future passes' : 'postpone — keep open but skip future passes'"
                      aria-label="postpone" @click="togglePostpone(g.icon, vg.variant)"><span class="ic" v-html="IC.pause"></span></button>
              <span v-if="isPostponed(g.icon, vg.variant)" class="chip">postponed</span>
              <button class="iconbtn" :class="{ on: fbFor('variant', g.icon, vg.variant).length }"
                      title="feedback for this variant" aria-label="feedback for this variant" @click="openFb('variant', g.icon, vg.variant)">
                <span class="ic" v-html="IC.comment"></span><span v-if="fbNew('variant', g.icon, vg.variant)" class="dotnew"></span>
              </button>
              <button class="iconbtn" title="copy a complete LLM hint for this variant — paste into any model, bring SVGs back"
                      @click="copyPrompt(g.icon, vg.variant)"><span class="ic" v-html="IC.copy"></span></button>
              <button v-if="S.recraftReady || S.debug" class="iconbtn" :class="{ on: S.drafting === g.icon + '/' + vg.variant }"
                      :title="S.debug && !S.recraftReady ? 'preview the Recraft request (no call)' : 'Recraft: seed 4 drafts for this variant (~$0.18-0.20)'" aria-label="Recraft draft"
                      @click="showDebug(g.icon, vg.variant)"><span class="ic" v-html="IC.bolt"></span></button>
            </div>
            <div v-if="!vg.cands.length" class="card empty" style="border-style:dashed; display:flex; justify-content:space-between; align-items:center; gap:8px; padding:6px 10px">
              <span class="muted" style="font-size:.8rem">open — no drafts yet</span>
              <span class="row" style="gap:6px; flex:none">
                <button v-if="S.recraftReady || S.debug" class="subtle" style="padding:3px 8px; font-size:.75rem" @click="showDebug(g.icon, vg.variant)"><span class="ic" v-html="IC.bolt"></span> seed</button>
                <button class="subtle" style="padding:3px 8px; font-size:.75rem" @click="copyPrompt(g.icon, vg.variant)"><span class="ic" v-html="IC.spark"></span> LLM hint</button>
              </span>
            </div>
            <div class="grid">
              <div class="card" v-for="(c, ci) in vg.cands" :key="c.cand"
                   :class="{ kbactive: S.kbUsed && gi === S.kbFocus && vi === S.kbVariant && ci === S.kbCand && !isViewing() }">
                <img class="thumb" loading="lazy" width="64" height="64"
                     :src="render(c.path, 64, '#f6f9f7', mainColorIcon(g))" @click="open(c)">
            <div class="name">{{ c.cand }}
            </div>
            <div class="rating">
              <button :class="{ 'armed-x': item(c)?.t?.startsWith(c.cand + ' no') }"
                      title="drop (rate 0)" @click="drop(c)">✕</button>
              <button class="ratebtn" :class="{ armed: hasRating(c) }"
                      @click="openSheet(c)" :title="'rate ' + c.cand" aria-label="rate">
                <template v-if="hasRating(c)">★ {{ rating(c) }}</template>
                <template v-else>rate</template>
              </button>
              <button :class="{ armed: item(c)?.t === c.cand + ' ok' }"
                      title="approve — final" @click="approve(c)">✓</button>
            </div>
            <button class="iconbtn" title="compare" aria-label="compare" @click="toggleCompare(c)">⇄</button>
          </div>
            </div>
          </div>
        </div>
      </div>
    </section>
    <section v-else>
      <h2>Current round</h2>
      <p class="muted">no candidates in {{ S.viewRound || S.round || 'this pass' }} — the status above shows agent progress.</p>
    </section>

    <div class="composer" v-show="!waitingForAgent()">
      <details>
        <summary>Decision text · {{ S.lines.length }} lines</summary>
        <p class="muted" style="margin:6px 0">
          ok = <b>approve final</b> · rate 1–9 = refine · rate 0 / ✕ = drop. Unrated candidates carry over implicitly.
          Free-text editable; the generated line list stays underneath.
        </p>
        <textarea v-model="S.decisionEdit" @input="markDirty"
                  placeholder="hut/mono: a2 ok · b1 rate 7 · more 2"></textarea>
        <input v-model="S.instructions" style="margin-top:6px"
               placeholder="instructions for the agent with this apply (optional) — e.g. 'try a2 with a steeper roof'">
        <div class="row">
          <button class="subtle" @click="S.showGen = !S.showGen">{{ S.showGen ? 'hide' : 'show' }} generated</button>
          <button class="subtle" @click="markDirty(); S.decisionEdit = S.decisionText">reset to generated</button>
          <button @click="copy">copy JSON</button>
        </div>
        <div class="row" style="margin-top:6px">
          <span class="muted">keys: ←→ move · [ ] group · 1 ok · 2 drop · 0 rate · enter apply · esc close</span>
        </div>
        <div class="row" style="margin-top:6px">
          <span class="muted">batch:</span>
          <button class="subtle" @click="batchApprove(7)" title="approve all rated ≥7">✓ all ≥7</button>
          <button class="subtle" @click="batchApprove(8)" title="approve all rated ≥8">✓ all ≥8</button>
          <button class="subtle armed-x" @click="batchReject(3)" title="reject all rated ≤3">✕ all ≤3</button>
          <button class="subtle armed-x" @click="batchReject(0)" title="reject all unrated (rated 0)">✕ unrated</button>
        </div>
        <textarea v-if="S.showGen" readonly :value="S.decisionText"></textarea>
      </details>
    </div>

    <section>
      <details>
        <summary>Round history · {{ S.history.length }} rounds · ≈${{ totalCost().toFixed(2) }} recraft</summary>
        <div v-for="h in S.history" :key="h.round" class="group" style="margin:6px 0">
          <div class="ghead">
            <b>{{ h.round }}</b>
            <span class="muted">{{ h.decided ? 'decided' : h.candidates + ' drafted' }}</span>
            <span v-if="h.cost_usd" class="chip" title="recraft seeds in this pass">$ {{ h.cost_usd }}</span>
            <span v-if="h.instructions" class="chip" title="apply-time instructions"><span class="ic" v-html="IC.comment"></span> {{ h.instructions.slice(0, 40) }}{{ h.instructions.length > 40 ? '…' : '' }}</span>
            <span v-if="h.feedback && h.feedback.length" class="chip"><span class="ic" v-html="IC.comment"></span> {{ h.feedback.length }}</span>
          </div>
          <div v-if="h.feedback && h.feedback.length" class="chat" style="margin:4px 0">
            <div v-for="f in h.feedback" :key="h.round + f.text" class="bubble" :class="f.author">
              <span class="chip" :class="f.author">{{ f.author }}</span>
              <span class="muted scope">{{ f.scope === 'pack' ? '' : (f.icon || '') + (f.variant ? '#' + f.variant : '') }}</span>
              <span class="bubble-text">{{ f.text }}</span>
              <span class="muted bubble-time">{{ relTime(f.created) }}</span>
            </div>
          </div>
          <div v-if="h.decided" class="muted" style="font-size:.8rem">
            <template v-for="(dec, key) in h.icons" :key="key">
              {{ key }}: {{ dec.items.map(i => i.t).join(' · ') }}
            </template>
          </div>
        </div>
        <p v-if="!S.history.length" class="muted">no rounds yet</p>
      </details>
    </section>

</div>

<div v-show="S.tab === 'pack'">
    <section>
      <h2>Icons — the set</h2>
      <div class="group" v-for="(icon, id) in S.pack.icons" :key="id">
        <div class="ghead">
          <b>{{ id }}</b>
          <i v-if="icon.main_color" class="paldot" :style="{background: icon.main_color}" :title="'main color ' + icon.main_color"></i>
          <span v-if="(icon.colors || []).length" class="row" style="gap:3px">
            <i v-for="c in icon.colors" :key="c" class="paldot" :style="{background:c}" :title="c"></i>
          </span>
          <div v-if="S.editing === id" style="display:flex; gap:6px; flex:1">
            <input style="flex:1; min-width:100px" :value="icon.brief"
                   placeholder="describe the icon — human and agent read the same text"
                   @keydown.enter="saveIcon(id, $event.target.value)" @blur="saveIcon(id, $event.target.value)">
          </div>
          <span v-else class="muted" style="flex:1; cursor:text" @click="S.editing = id">{{ icon.brief }}</span>
          <details style="margin-left:auto">
            <summary class="muted" title="this icon's own colors — a subset of the style palette">colors</summary>
            <div class="row" style="gap:5px; padding:6px 0">
              <i v-for="c in iconStylePalette(id)" :key="c" class="paldot pick"
                 :class="{ sel: (icon.colors || []).includes(c) }"
                 :style="{background:c}" :title="c" @click="toggleIconColor(id, c)"></i>
              <button v-if="(icon.colors || []).length" class="subtle" @click="toggleIconColor(id, null)">clear</button>
            </div>
          </details>
          <button class="subtle" @click="S.editing = S.editing === id ? null : id">edit</button>
        </div>
        <div class="grid">
          <div class="card" v-for="(v, vid) in icon.variants" :key="vid">
            <img v-if="!v.link && S.svgFiles[id + '/' + vid]" class="thumb" loading="lazy" width="64" height="64"
                 :src="render('icons/' + id + '/' + vid + '.svg', 64, '#ffffff')"
                 @click="openIcon(id, vid, v)">
            <div v-else-if="!v.link" class="thumb missing" title="not drafted yet">—</div>
            <div class="name">{{ vid }}</div>
            <span class="chip fit" :class="v.status">{{ v.link ? '→ ' + v.link : v.status }}</span>
            <div v-if="(v.status === 'approved' && !v.link) || v.status === 'stale' || edited(id, vid)"
                 class="row" style="justify-content:center; gap:4px; margin-top:2px">
              <button v-if="v.status === 'approved' && !v.link" class="iconbtn"
                      :class="{ on: isPinned(id, vid) }" :title="isPinned(id, vid) ? 'unpin' : 'pin as style reference'"
                      aria-label="pin as style reference"
                      @click="togglePin(id, vid)"><span class="ic" :class="{ filled: isPinned(id, vid) }" v-html="IC.pin"></span></button>
              <button v-if="v.status === 'approved' && !v.link && !isViewing()" class="iconbtn"
                      title="add to the next pass again — the approved file stays in history" aria-label="add to next pass"
                      @click="reopen(id, vid)"><span class="ic" v-html="IC.unlock"></span></button>
              <span v-if="v.status === 'stale' || edited(id, vid)" class="muted" style="font-size:.7rem">needs re-review</span>
            </div>
          </div>
        </div>
      </div>
    </section>
    </div>

<div v-show="S.tab === 'styles'">
    <section>
      <h2>Styles — the pack's look, references and rules</h2>
      <p class="muted" style="margin:-6px 0 12px">references: bundled defaults + own uploads (own shown first)</p>

      <!-- used styles: cards with refs, rules, model -->
      <div class="group" v-for="sid in usedStyles()" :key="sid">
        <div class="ghead">
          <b @click="styleDetail(sid)" style="cursor:pointer">{{ sid }}</b>
          <span class="chip" title="glyphs using this style">{{ styleUsageCount(sid) }} glyphs</span>
          <span class="chip rule" v-for="ru in styleRules(sid)" :key="ru" :title="ruleTitle(ru)">{{ ru }}</span>
          <span class="palrow" v-if="stylePalette(sid).length" title="style palette"><i v-for="c in stylePalette(sid)" :key="c" class="paldot" :style="{background: c}" :title="c"></i></span>
          <span class="spacer"></span>
          <button class="iconbtn" @click="editStyle(sid)" title="edit style rules and model" aria-label="edit style"><span class="ic" v-html="IC.gear"></span></button>
          <button class="iconbtn" :class="{ on: S.removeArm === sid }" @click="removeStyle(sid)" title="remove from every glyph" aria-label="remove style"><span class="ic" v-html="IC.trash"></span></button>
        </div>
        <div class="row" style="flex-wrap:wrap">
          <figure v-for="ic in (S.styleRefs[sid]?.own || []).concat(S.styleRefs[sid]?.bundled || [])"
                  :key="sid + (ic.own ? 'o' : 'b') + ic.name" class="refcell"
                  :style="isOwnRef(sid, ic.name) ? '' : 'opacity:.7'">
            <img width="48" height="48" loading="lazy"
                 :src="'/api/style-ref-file?style=' + encodeURIComponent(sid) + '&name=' + encodeURIComponent(ic.name)"
                 :alt="ic.name">
            <figcaption class="muted">{{ ic.name }}</figcaption>
            <button v-if="isOwnRef(sid, ic.name)" class="subtle armed-x" @click="removeRef(sid, ic.name)"
                    title="remove own reference" aria-label="remove reference">✕</button>
          </figure>
          <figure v-for="pn in (S.styleDetail?.[sid]?.pinned || [])" :key="'p' + pn.icon" class="refcell">
            <img width="48" height="48" loading="lazy"
                 :src="render('icons/' + pn.icon + '/' + pn.variant + '.svg', 48, '#ffffff')">
            <figcaption class="muted">{{ pn.icon }}</figcaption>
          </figure>
          <button class="subtle stylepick" @click="pickRefFile(sid)" title="upload an own SVG reference"><span class="ic" v-html="IC.plus"></span> upload</button>
        </div>
      </div>

      <!-- add styles: card per available style -->
      <div class="group">
        <div class="ghead"><b>add a style</b></div>
        <div class="row" style="flex-wrap:wrap; gap:10px">
          <div v-for="(st, sid) in S.styles" :key="sid" v-show="!usedStyles().includes(sid)"
               class="stylecard" @click="styleDetail(sid)">
            <div class="row" style="gap:4px">
              <img v-for="ic in ((S.styleRefs[sid]?.bundled || S.styleRefs[sid]?.own || []).slice(0, 3))"
                   :key="ic.name" width="36" height="36" loading="lazy" style="border-radius:6px; background:#fff"
                   :src="'/api/style-ref-file?style=' + encodeURIComponent(sid) + '&name=' + encodeURIComponent(ic.name)">
            </div>
            <div class="muted" style="font-size:.8rem">{{ sid }}</div>
            <div class="muted" style="font-size:.7rem">{{ styleSummary(sid) }}</div>
          </div>
          <div class="stylecard" @click="editCustomStyle()" style="border-style:dashed">
            <span class="ic-lg" v-html="IC.plus"></span>
            <div class="muted" style="font-size:.8rem">custom style</div>
            <div class="muted" style="font-size:.7rem">define your own</div>
          </div>
        </div>
      </div>
    </section>

    <!-- style detail (read-only) dialog -->
    <div v-if="S.styleView && !S.styleEdit" class="overlay" @click.self="S.styleView = null">
      <div class="dialog" style="max-width:640px">
        <h3><span>{{ S.styleView.id }}</span>
            <span class="row" style="gap:4px">
              <button v-if="S.recraftReady || S.debug" class="iconbtn" @click="openStyleRc(S.styleView.id)" title="Recraft style: create the custom style (bakes look + palette), inspect the exact request, or paste a UUID" aria-label="recraft style"><span class="ic" v-html="IC.bolt"></span></button>
              <button class="iconbtn" @click="editStyle(S.styleView.id)" title="edit rules and model" aria-label="edit"><span class="ic" v-html="IC.gear"></span></button>
              <button class="subtle" @click="S.styleView = null" aria-label="Close">✕</button>
            </span></h3>
        <div class="row" style="flex-wrap:wrap; gap:6px; margin-bottom:10px">
          <img v-for="ic in (S.styleRefs[S.styleView.id]?.own || []).concat(S.styleRefs[S.styleView.id]?.bundled || [])"
               :key="ic.name" width="48" height="48" style="border-radius:8px; background:#fff"
               :src="'/api/style-ref-file?style=' + encodeURIComponent(S.styleView.id) + '&name=' + encodeURIComponent(ic.name)">
        </div>
        <div class="kv">
          <b>construction</b><span>{{ S.styleView.def.construction }}</span>
          <b>color mode</b><span>{{ S.styleView.def.color_mode }}</span>
          <b v-if="S.styleView.def.stroke">stroke</b><span v-if="S.styleView.def.stroke">{{ S.styleView.def.stroke.width }}px {{ S.styleView.def.stroke.linecap }}</span>
          <b v-if="S.styleView.def.size">grid</b><span v-if="S.styleView.def.size">{{ S.styleView.def.size }}px</span>
          <b>min gap</b><span>{{ S.styleView.def.min_gap }}</span>
          <b>max nodes</b><span>{{ S.styleView.def.max_nodes }}</span>
          <b v-if="S.styleView.def.palette">palette</b>
          <span v-if="S.styleView.def.palette"><i v-for="c in S.styleView.def.palette" :key="c" class="paldot" :style="{background:c}" :title="c"></i></span>
          <b v-if="S.styleView.def.style_words">words</b><span v-if="S.styleView.def.style_words">{{ S.styleView.def.style_words.join(', ') }}</span>
          <b v-if="S.styleView.def.avoid">avoid</b><span v-if="S.styleView.def.avoid">{{ S.styleView.def.avoid.join(', ') }}</span>
          <b v-if="S.styleView.def.gate">gate off</b><span v-if="S.styleView.def.gate">{{ Object.entries(S.styleView.def.gate).filter(([,v2]) => !v2).map(([k]) => k).join(', ') }}</span>
          <b v-if="S.styleView.model">Recraft model</b><span v-if="S.styleView.model">{{ S.styleView.model }}</span>
          <b v-if="S.styleView.recraftStyleId">Recraft style</b><span v-if="S.styleView.recraftStyleId" class="muted" style="font-size:.75rem">{{ S.styleView.recraftStyleId }}</span>
        </div>
        <div class="row" v-if="!usedStyles().includes(S.styleView.id)" style="margin-top:10px">
          <button class="primary" @click="addStyleToPack(S.styleView.id); S.styleView = null;">add to every glyph</button>
        </div>
      </div>
    </div>

    <!-- style EDITOR dialog -->
    <div v-if="S.styleEdit" class="overlay" @click.self="S.styleEdit = null">
      <div class="dialog" style="max-width:620px">
        <h3><span>edit · {{ S.styleEdit.id }}</span>
            <button class="subtle" @click="S.styleEdit = null" aria-label="Close">✕</button></h3>
        <div class="stylegrid" style="display:flex; flex-direction:column; align-items:stretch; gap:6px">
          <div class="row"><label class="muted" style="flex:0 0 96px">label</label><input v-model="S.styleEdit.label" style="flex:1"></div>
          <div class="row"><label class="muted" style="flex:0 0 96px" title="canvas size the icons are drawn on (24 or 48 typical)">grid px</label><input v-model="S.styleEdit.size" type="number" style="flex:1; min-width:0">
            <label class="muted" style="flex:0 0 96px" title="outline stroke thickness">stroke width</label><input v-model="S.styleEdit.strokeWidth" type="number" step="0.5" style="flex:1; min-width:0"></div>
          <div class="row"><label class="muted" style="flex:0 0 96px" title="minimum spacing between separate strokes — near-misses fail the gate">min gap</label><input v-model="S.styleEdit.minGap" type="number" step="0.5" style="flex:1; min-width:0">
            <label class="muted" style="flex:0 0 96px" title="complexity budget: total path points">max nodes</label><input v-model="S.styleEdit.maxNodes" type="number" style="flex:1; min-width:0"></div>
          <div class="row" style="align-items:flex-start"><label class="muted" style="flex:0 0 96px" title="allowed colors — only these pass the gate">palette</label>
            <div class="row" style="flex:1; flex-wrap:wrap; gap:6px">
              <label v-for="(c, i) in S.styleEdit.paletteList" :key="i" class="palchip" :style="{background: c}">
                <input type="color" :value="c" @input="S.styleEdit.paletteList[i] = $event.target.value" :aria-label="'color ' + (i+1)">
                <button class="palx" @click="S.styleEdit.paletteList.splice(i, 1)" :aria-label="'remove color ' + (i+1)">✕</button>
              </label>
              <label class="palchip paladd"><input type="color" value="#2b6cb0" @input="S.styleEdit.paletteList.push($event.target.value)" aria-label="add color"><span>＋</span></label>
            </div>
          </div>
          <div class="row"><label class="muted" style="flex:0 0 96px" title="vocabulary injected into every drafting brief">style words</label><input v-model="S.styleEdit.words" placeholder="comma separated" style="flex:1"></div>
          <div class="row"><label class="muted" style="flex:0 0 96px" title="negative vocabulary — never appears in drafts">avoid</label><input v-model="S.styleEdit.avoid" placeholder="comma separated" style="flex:1"></div>
          <div class="row" style="align-items:flex-start"><label class="muted" title="deterministic gate checks — uncheck to disable per style">gate checks</label>
            <div style="flex:1; display:flex; flex-direction:column; gap:6px; font-size:.8rem">
              <label v-for="g in GATE_HELP" :key="g.k" style="display:flex; gap:8px; align-items:baseline">
                <input type="checkbox" :checked="!(S.styleEdit.gateOff || []).includes(g.k)" @change="toggleGate(g.k)" style="min-height:0">
                <span><b>{{ g.k }}</b> <span class="muted">— {{ g.h }}</span></span>
              </label>
            </div>
          </div>
          <div class="row"><label class="muted" style="flex:0 0 96px" title="Freeform instructions the drafting agent reads before drawing — e.g. 'if a detail needs a second stroke to read, drop it'">guidance</label><input v-model="S.styleEdit.guidance" style="flex:1"></div>
          <div class="row"><label class="muted" style="flex:0 0 96px" title="Curated V2 style name (cheaper: $0.044/img vs $0.05+ for V4)">V2 style name</label>
            <select v-model="S.styleEdit.curatedStyle" style="flex:1">
              <option value="">auto (from style family)</option>
              <option v-for="name in curatedNames()" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
          <div class="row"><label class="muted" style="flex:0 0 96px" title="Recraft model preferred for this style (auto uses the suggestion)">Recraft model</label>
            <select v-model="S.styleEdit.recraftModel" style="flex:1">
              <option value="">auto</option>
              <option v-for="m in vectorModels()" :key="m" :value="m">{{ m }} (${{ (S.recraftModels.prices || {})[m] || '?' }}/img)</option>
            </select>
            <span v-if="S.recraftModels.suggestions?.[S.styleEdit.id]" class="muted">→ {{ S.recraftModels.suggestions[S.styleEdit.id] }}</span>
          </div>
        </div>
        <div class="row" style="margin-top:10px">
          <button class="primary" @click="saveStyleRules">save</button>
          <button class="subtle" @click="S.styleEdit = null" aria-label="Close">cancel</button>
        </div>
      </div>
    </div>
</div>

<div v-show="S.tab === 'settings'">
  <section>
    <h2>Settings — {{ S.pack.name }}</h2>
    <div class="group">
<div class="controls"><label>version</label>
        <input v-model="S.set.version"></div>
      <div class="controls" style="align-items:flex-start"><label>description</label>
        <textarea v-model="S.set.description" placeholder="durable docs: what this collection is for — shown to humans, exports, READMEs"></textarea></div>
      <div class="controls" style="align-items:flex-start"><label>global note</label>
        <textarea v-model="S.set.note" placeholder="FEEDBACK to the agent, every draft — e.g. 'no chimneys anywhere'. Clear when resolved."></textarea></div>
      <div class="controls" style="align-items:flex-start"><label>rules</label>
        <textarea v-model="S.set.rules" placeholder="one rule per line — injected into every drafting context"></textarea></div>
      <!-- removed: style management moved to styles tab -->
      <div class="controls" style="align-items:flex-start"><label>custom style</label>
        <div class="row" style="flex-direction:column; align-items:stretch; gap:4px">
          <div class="row"><input v-model="S.set.csId" placeholder="style id (e.g. outline-color)" style="flex:1">
          <select v-model="S.set.csBase"><option v-for="(st, sid) in S.styles" :key="sid" :value="sid">extends {{ sid }}</option></select></div>
          <div class="row"><input v-model="S.set.csSize" type="number" placeholder="grid px" style="width:110px">
          <input v-model="S.set.csPalette" placeholder="palette hex, comma-separated" style="flex:1"></div>
          <button class="subtle" @click="addCustomStyle">define + add to every glyph</button>
        </div></div>
      <div class="controls"><label>Recraft</label>
        <div class="row">
          <select v-model="S.set.rcModel"><option v-for="m in vectorModels()" :key="m" :value="m">{{ m }} (${{ (S.recraftModels.prices || {})[m] || '?' }}/img)</option></select>
          <input v-model="S.set.rcN" type="number" min="1" max="6" style="width:64px" title="images per request">
          <button class="subtle" @click="saveRecraftDefaults(S.set.rcModel, +S.set.rcN)">save</button>
        </div></div>
      <div class="controls"><label>stroke width</label>
        <input v-model="S.set.strokeWidth" type="number" step="0.5" min="0.5" style="width:90px"></div>
      <div class="controls"><label>caps/joins</label>
        <select v-model="S.set.linecap"><option>round</option><option>butt</option><option>square</option></select>
        <select v-model="S.set.linejoin"><option>round</option><option>miter</option><option>bevel</option></select></div>
      <div class="controls"><label>live padding</label>
        <input v-model="S.set.padding" type="number" step="0.5" min="0" style="width:90px"></div>
      <div class="controls"><label>precision</label>
        <input v-model="S.set.precision" type="number" step="0.25" min="0.25" style="width:90px"></div>
      <div class="controls" v-if="S.set.palette"><label>palette</label>
        <span class="swatch" v-for="c in S.set.palette" :key="c" :style="{background: c}" :title="c"></span></div>
      <p class="muted">Every write bumps the pack rev — a waiting agent picks changes up via <code>iconpilot wait</code>.</p>
      <div class="row" style="margin-top:10px">
        <button class="primary" @click="saveSettings">Save settings</button>
        <button class="subtle" @click="S.settingsDlg = false">cancel</button>
      </div>
      <div v-if="S.set.errors" class="err">{{ S.set.errors }}</div>
    </div>
  </section>
</div>

<footer>iconpilot review v{{ S.version }} · flock-serialized writes · approval is always yours</footer>
  </main>

  <div class="actionbar" v-show="S.tab === 'round' && !waitingForAgent()" :class="{ ready: S.actionBar.ready }">
    <span class="ab-status" :class="{ 'flash-ok': S.flash && S.flashOk, 'flash-err': S.flash && !S.flashOk }">
      <template v-if="S.flash">{{ S.flash }}</template>
      <template v-else>
        <span v-if="S.actionBar.working" class="dot amber"></span>
        <span v-else-if="S.actionBar.ready" class="dot green"></span>
        <span v-else class="dot gray"></span>
        <span class="statustext">{{ S.actionBar.text }}</span>
      </template>
    </span>
    <button class="subtle" @click="undo" title="undo last apply" aria-label="undo"><span class="ic" v-html="IC.undo"></span></button>
    <button class="primary ab-apply" @click="applyAndNext()"
            :disabled="!S.decisionEdit.trim() || S.applying">apply ▸ next pass</button>
        <button class="subtle" @click="apply()" v-if="S.decisionEdit.trim() && !S.applying"
                title="record decisions without starting the next pass">apply only</button>
  </div>


  <div v-if="S.fbDlg" class="overlay" @click.self="S.fbDlg = null">
    <div class="dialog">
      <h3><span><span class="ic-lg" v-html="IC.comment"></span> {{ fbTitle() }}</span>
          <button class="subtle" @click="S.fbDlg = null">✕</button></h3>
      <p class="muted" style="margin:0 0 8px">Per-round feedback — guides the next draft, then dies with its round (history keeps it). Generally valid? The agent promotes it into the standing note via CLI.</p>
      <textarea ref="fbInput" v-model="S.fbDlg.text" rows="2"
                placeholder="what to change in the next draft — Enter to add, Shift+Enter for a new line"
                @keydown.enter.exact.prevent="addFeedback"></textarea>
      <div class="row" style="margin:8px 0">
        <button class="primary" @click="addFeedback">Add</button>
        <span class="muted">guidance lives until resolved · the agent promotes durable points itself</span>
      </div>
      <div class="chat" ref="fbChatEl" aria-live="polite">
        <template v-for="r in fbChat()" :key="r.round + (r.archived ? '-a' : '-l')">
          <div class="chat-head" :class="{ 'r-archived': r.archived }">{{ r.round }}{{ r.archived ? ' · archived' : ' · live' }}</div>
          <div v-for="i in r.items" :key="r.round + i.id" class="bubble" :class="i.author"
               :title="i.author + ' · ' + (i.created || '')">
            <span class="bubble-text">{{ i.text }}</span>
            <span v-if="isNew(i)" class="chip new">new</span>
            <span class="bubble-time">{{ relTime(i.created) }}</span>
            <button v-if="!r.archived" class="subtle armed-x" title="resolve (done / addressed)" @click="resolveFeedback(i)">✕</button>
          </div>
        </template>
        <p v-if="!fbChat().length" class="muted">no comments yet for this scope</p>
      </div>
      <div class="row" style="margin-top:8px">
        <button class="subtle" @click="S.fbDlg = null" aria-label="Close">close</button>
      </div>
    </div>
  </div>

  <div v-if="S.nextDlg" class="overlay" @click.self="S.nextDlg = null">
    <div class="dialog" style="max-width:640px">
      <h3><span>Focus for the next pass</span><button class="subtle" @click="S.nextDlg = null" aria-label="Close">✕</button></h3>
      <p class="muted" style="margin:0 0 8px">Preselected = previous pass. Toggle a whole column, or single cells.</p>
      <div style="max-height:340px; overflow-y:auto">
        <table class="focusgrid">
          <thead>
            <tr>
              <th></th>
              <th v-for="c in S.nextDlg.cols" :key="c">
                <button class="subtle" :class="{ armed: colState(c) === 'all' }" @click="toggleCol(c)"
                        :title="'toggle all ' + c">{{ c }}</button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in S.nextDlg.rows" :key="r">
              <td class="muted">{{ r }}</td>
              <td v-for="c in S.nextDlg.cols" :key="c">
                <input v-if="S.nextDlg.cells.includes(r + '#' + c)" type="checkbox"
                       v-model="S.nextDlg.sel[r + '#' + c]" :aria-label="r + ' ' + c">
                <span v-else class="muted">·</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="only-narrow">
        <div class="row" style="gap:6px; margin-bottom:8px">
          <button class="subtle" style="height:36px" @click="batchSelAll(true)">all</button>
          <button class="subtle" style="height:36px" @click="batchSelAll(false)">none</button>
          <span class="muted" style="font-size:.75rem; align-self:center">{{ batchSelCount() }}/{{ batchTotal() }} selected</span>
        </div>
        <div v-for="row in batchMatrix().styles" :key="row.style" style="margin-bottom:10px">
          <div class="row" style="justify-content:space-between; margin-bottom:4px">
            <button class="subtle" style="height:36px; font-weight:600" :class="{ on: batchRowAll(row) }" @click="batchToggleRow(row)">{{ row.style }}</button>
            <span class="muted" style="font-size:.75rem">{{ batchRowTargets(row).filter(tg => S.batchDlg.sel[tg]).length }}/{{ batchRowTargets(row).length }}</span>
          </div>
          <div class="row" style="flex-wrap:wrap; gap:6px">
            <button v-for="tg in batchRowTargets(row)" :key="tg" class="selchip" :class="{ on: S.batchDlg.sel[tg] }"
                    @click="S.batchDlg.sel[tg] = !S.batchDlg.sel[tg]" :aria-pressed="!!S.batchDlg.sel[tg]">
              {{ tg.replace('#', ' · ') }}
            </button>
          </div>
        </div>
      </div>
      <div class="row" style="margin-top:10px; align-items:flex-start">
        <div style="flex:1; position:relative">
          <input v-model="S.nextDlg.newIcon" placeholder="add a new icon — name — brief, e.g. 'sunset — orange sun over horizon'"
                 @input="iconSuggest()" @keydown.enter.prevent="addNewIcon()"
                 style="width:100%" aria-label="add new icon">
          <div v-if="S.nextDlg.suggestions && S.nextDlg.suggestions.length" class="suggestbox">
            <button v-for="s in S.nextDlg.suggestions" :key="s.key" class="subtle"
                    @click="pickSuggestion(s)" style="display:block; width:100%; text-align:left">
              {{ s.label }}
            </button>
          </div>
        </div>
        <button class="subtle" @click="addNewIcon()"><span class="ic" v-html="IC.plus"></span> add</button>
      </div>
      <div class="row" v-if="S.nextDlg.pending && S.nextDlg.pending.length" style="margin-top:6px">
        <span class="muted">to add:</span>
        <span v-for="(pn, i) in S.nextDlg.pending" :key="pn" class="chip">{{ pn }}
          <button class="subtle" @click="S.nextDlg.pending.splice(i, 1)" aria-label="remove">✕</button>
        </span>
      </div>
      <div class="row" style="margin-top:10px">
        <button class="primary" @click="startRoundWithNew()">start pass</button>
        <button class="subtle" @click="toggleAll(true)">select all</button>
        <button class="subtle" @click="toggleAll(false)">none</button>
        <button class="subtle" @click="S.nextDlg = null" aria-label="Close">✕</button>
      </div>
    </div>
  </div>

  <div v-if="S.debugDlg" class="overlay" @click.self="!S.debugDlg.generating && (S.debugDlg = null)">
    <div class="dialog" style="max-width:640px">
      <h3><span><span class="ic-lg" v-html="IC.bolt"></span> Recraft · {{ S.debugDlg.icon }}#{{ S.debugDlg.variant }}</span>
          <button class="subtle" @click="S.debugDlg = null" aria-label="Close" :disabled="S.debugDlg.generating">✕</button></h3>

      <!-- generating spinner -->
      <div v-if="S.debugDlg.generating" style="display:flex; align-items:center; gap:12px; padding:24px 0; justify-content:center">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" style="animation:spin 1s linear infinite">
          <path d="M21 12a9 9 0 1 1-6.2-8.5"/>
        </svg>
        <span class="muted">generating {{ S.debugDlg.n }} versions via {{ S.debugDlg.model }}…</span>
      </div>

      <div v-if="S.debugDlg.error" class="err" style="margin-bottom:8px; padding:8px; border-radius:8px; background:color-mix(in oklab, var(--danger) 10%, var(--card))">
        {{ S.debugDlg.error }}
      </div>

      <template v-else>
          <label class="muted" style="flex:0 0 60px">model</label>
          <select v-model="S.debugDlg.model" @change="showDebug(S.debugDlg.icon, S.debugDlg.variant, S.debugDlg.model, +S.debugDlg.n, +S.debugDlg.grid)">
            <option v-for="m in S.debugDlg.models" :key="m" :value="m">{{ m }}</option>
          </select>
          <label class="muted" style="margin-left:10px" title="1×1 = separate images, 2×2+ = one sheet">grid</label>
          <select v-model="S.debugDlg.grid" @change="showDebug(S.debugDlg.icon, S.debugDlg.variant, null, +S.debugDlg.n, +S.debugDlg.grid)">
            <option v-for="g in [1,2,3,4,5]" :key="g" :value="g">{{ g }}×{{ g }}</option>
          </select>
          <label class="muted" style="margin-left:10px" title="total number of icon versions to generate">versions</label>
          <input v-model.number="S.debugDlg.n" type="number" min="1"
                 :max="S.debugDlg.grid * S.debugDlg.grid === 1 ? 6 : S.debugDlg.grid * S.debugDlg.grid"
                 style="width:52px"
                 @change="showDebug(S.debugDlg.icon, S.debugDlg.variant, null, +S.debugDlg.n, +S.debugDlg.grid)">
          <select v-if="S.debugDlg.variants && S.debugDlg.variants.length > 1" v-model="S.debugDlg.variant" @change="showDebug(S.debugDlg.icon, S.debugDlg.variant)">
            <option v-for="vd in S.debugDlg.variants" :key="vd" :value="vd">{{ vd }}</option>
          </select>
          <span class="chip">{{ S.debugDlg.style }}</span>
        </div>

        <div class="row" style="justify-content:space-between; margin-bottom:8px">
          <span class="muted">{{ S.debugDlg.refs }} style ref(s) · {{ S.debugDlg.promptChars }}/{{ S.debugDlg.promptLimit }} chars</span>
          <span class="chip rule" title="estimated cost">≈ ${{ S.debugDlg.cost }}</span>
        </div>

        <details style="margin-bottom:8px">
          <summary class="muted" style="cursor:pointer; font-size:.8rem">request JSON</summary>
          <textarea :value="S.debugDlg.request" readonly rows="10" style="font-size:.78rem; margin-top:6px"></textarea>
        </details>

        <div class="row">
          <button class="primary" @click="recraftGenerate()">
            <span class="ic" v-html="IC.bolt"></span> generate {{ S.debugDlg.n }} versions
          </button>
          <button class="subtle" @click="debugCopy('full')" title="copy the full drafting hint">copy hint</button>
          <button class="subtle" @click="S.debugDlg = null" aria-label="Close">cancel</button>
        </div>
      </template>
    </div>
  </div>

  <div v-if="S.styleRc" class="overlay" @click.self="S.styleRc = null">
    <div class="dialog" style="max-width:640px">
      <h3><span><span class="ic-lg" v-html="IC.bolt"></span> Recraft style — {{ S.styleRc.id }}</span>
          <button class="subtle" @click="S.styleRc = null" aria-label="Close">✕</button></h3>
      <div class="kv">
        <b>cached style id</b><span>{{ S.styleRc.cached || '—' }} <span v-if="S.styleRc.fresh" class="chip done">fresh</span><span v-else-if="S.styleRc.cached" class="chip rule">stale refs</span></span>
        <b>references</b><span>{{ S.styleRc.refs }} SVG → data URLs</span>
        <b>cost</b><span>${{ S.styleRc.cost }} one-time · cached until refs change</span>
      </div>
      <details open style="margin-top:8px">
        <summary class="muted">exact request (look + palette baked into the style)</summary>
        <pre style="max-height:240px; overflow:auto; font-size:.72rem; white-space:pre-wrap">POST {{ S.styleRc.endpoint }}
{{ S.styleRc.reqs }}</pre>
      </details>
      <div class="row" style="margin-top:10px">
        <button class="primary" :class="{ busy: S.styleRc.busy }" @click="styleRcCreate()">
          <span class="ic" v-html="IC.bolt"></span> create style · ${{ S.styleRc.cost }}
        </button>
        <button class="subtle" @click="copyText('POST ' + S.styleRc.endpoint + String.fromCharCode(10) + S.styleRc.reqs, '')">copy request</button>
      </div>
      <div class="row" style="margin-top:8px">
        <input v-model="S.styleRc.uuid" placeholder="or paste a Recraft style UUID (created manually)" style="flex:1">
        <button class="subtle" @click="styleRcSave()">save uuid</button>
      </div>
      <p v-if="S.styleRc.err" class="err">{{ S.styleRc.err }}</p>
    </div>
  </div>

  <div v-if="S.adoptDlg" class="overlay" @click.self="S.adoptDlg = null">
    <div class="dialog" style="max-width:680px">
      <h3><span><span class="ic-lg" v-html="IC.check || IC.star"></span> adopt — {{ S.adoptDlg.icon }}#{{ S.adoptDlg.variant }} {{ S.adoptDlg.cand ? '· ' + S.adoptDlg.cand : '' }}</span>
          <button class="subtle" @click="S.adoptDlg = null" aria-label="Close">✕</button></h3>
      <div class="row" style="gap:16px; align-items:flex-start">
        <div style="text-align:center">
          <img :src="S.adoptDlg.svg_data" width="120" height="120" style="border-radius:10px; background:#fff; border:1px solid var(--line)">
          <div class="muted" style="font-size:.75rem; margin-top:2px">adopted</div>
        </div>
        <div style="flex:1; min-width:0">
          <b style="font-size:.85rem">applied fixes</b>
          <ul style="margin:4px 0 10px; padding-left:18px; font-size:.8rem">
            <li v-for="f in S.adoptDlg.fixes" :key="f">{{ f }}</li>
          </ul>
          <b style="font-size:.85rem" :style="{color: S.adoptDlg.gate_errors.length ? 'var(--warn)' : 'var(--accent)'}">
            gate: {{ S.adoptDlg.gate_errors.length ? S.adoptDlg.gate_errors.length + ' open issue(s)' : 'clean pass' }}</b>
          <ul v-if="S.adoptDlg.gate_errors.length" style="margin:4px 0; padding-left:18px; font-size:.78rem; color:var(--warn)">
            <li v-for="e in S.adoptDlg.gate_errors" :key="e">{{ e.slice(0, 110) }}</li>
          </ul>
        </div>
      </div>
      <div class="row" style="margin-top:12px">
        <button class="primary" :class="{ busy: S.adoptDlg.busy }" @click="adoptCommit()">
          {{ S.adoptDlg.gate_errors.length ? 'adopt anyway' : 'adopt' }} — make this the {{ S.adoptDlg.variant }} icon
        </button>
        <button class="subtle" @click="S.adoptDlg = null">cancel</button>
      </div>
      <p v-if="S.adoptDlg.err" class="err">{{ S.adoptDlg.err }}</p>
    </div>
  </div>

  <div v-if="S.refineDlg" class="overlay" @click.self="S.refineDlg = null">
    <div class="dialog" style="max-width:640px">
      <h3><span><span class="ic-lg" v-html="IC.spark"></span> refine — {{ refineActive().length }} variant(s)</span>
          <button class="subtle" @click="S.refineDlg = null" aria-label="Close">✕</button></h3>
      <p class="muted" style="margin:0 0 10px">Best take of each variant + your feedback → improved variants via image-to-image. Feedback is required — it IS the change instruction.</p>
      <div style="overflow-x:auto; margin-bottom:6px">
        <table class="selmatrix">
          <thead>
            <tr>
              <th class="sh">
                <button class="subtle" style="padding:0 6px; font-size:.72rem" @click="refineSetAll(true)">all</button>
                <button class="subtle" style="padding:0 6px; font-size:.72rem" @click="refineSetAll(false)">none</button>
              </th>
              <th v-for="ic in refineMatrix().icons" :key="ic" class="ih">
                <button class="subtle" style="padding:0 4px; font-size:.72rem" :class="{ on: refineColAll(ic) }" @click="refineToggleCol(ic)">{{ ic }}</button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in refineMatrix().styles" :key="row.style">
              <th class="sh">
                <button class="subtle" style="padding:0 6px; font-size:.75rem" :class="{ on: refineRowAll(row) }" @click="refineToggleRow(row)">{{ row.style }}</button>
              </th>
              <td v-for="ic in refineMatrix().icons" :key="ic" class="cell" style="min-width:180px">
                <div v-for="it in (row.cells[ic] || [])" :key="it.icon + '#' + it.variant"
                     class="row" style="gap:5px; align-items:center"
                     :style="{ opacity: it.skip ? '.45' : '1' }">
                  <input type="checkbox" :checked="!it.skip" @change="it.skip = !it.skip" :aria-label="'include ' + it.icon + ' ' + it.variant">
                  <span class="muted" style="font-size:.7rem; flex:none" :title="it.icon + '#' + it.variant">{{ it.variant }}</span>
                  <input v-model="it.feedback" style="flex:1; min-width:120px; height:28px; font-size:.78rem"
                         :placeholder="it.skip ? 'skipped' : 'what to change — e.g. flame too heavy'">
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="only-narrow">
        <div v-for="it in S.refineDlg.items" :key="it.icon + '#' + it.variant" style="margin-bottom:8px">
          <div class="row" style="gap:6px; margin-bottom:3px">
            <button class="selchip" :class="{ on: !it.skip }" @click="it.skip = !it.skip">{{ it.icon }} · {{ it.variant }}</button>
          </div>
          <input v-if="!it.skip" v-model="it.feedback" style="width:100%; height:36px; font-size:.82rem"
                 :placeholder="'what to change in ' + it.icon + ' ' + it.variant">
        </div>
        <div class="row" style="gap:6px; margin-bottom:8px">
          <button class="subtle" style="height:36px" @click="refineSetAll(true)">all</button>
          <button class="subtle" style="height:36px" @click="refineSetAll(false)">none</button>
        </div>
      </div>
      <div class="row" style="margin-top:8px; gap:10px">
        <label class="muted">strength</label>
        <input type="range" min="0" max="1" step="0.05" v-model.number="S.refineDlg.strength" style="flex:1">
        <span class="chip">{{ S.refineDlg.strength }}</span>
        <span class="muted" style="font-size:.75rem">0 = identical · 1 = reinvent</span>
      </div>
      <div class="row" style="margin-top:6px; gap:8px">
        <label class="muted">takes</label>
        <select v-model.number="S.refineDlg.takes"><option v-for="tk in [1,2,3,4,5,6]" :key="tk" :value="tk">{{ tk }}</option></select>
        <label class="muted">model</label>
        <select v-model="S.refineDlg.model">
          <option v-for="m in ['recraftv4_vector', 'recraftv4_1_vector']" :key="m" :value="m">{{ m }} (${{ (S.recraftModels.prices || {})[m] || '?' }}/img)</option>
        </select>
        <span class="chip rule">≈ ${{ refineEst() }}</span>
      </div>
      <div class="row" style="margin-top:12px">
        <button class="primary" :class="{ busy: S.refineDlg.busy }" :disabled="!refineReady()" @click="refineGenerate()">
          <span class="ic" v-html="IC.spark"></span> refine {{ refineActive().length * S.refineDlg.takes }} variants · ~${{ refineEst() }}
        </button>
      </div>
      <p v-if="S.refineDlg.err" class="err">{{ S.refineDlg.err }}</p>
    </div>
  </div>

  <div v-if="S.batchDlg" class="overlay" @click.self="S.batchDlg = null">
    <div class="dialog" style="max-width:680px">
      <h3><span><span class="ic-lg" v-html="IC.bolt"></span> draft pack — {{ batchSelCount() }} icons × {{ S.batchDlg.takes }} takes</span>
          <button class="subtle" @click="S.batchDlg = null" aria-label="Close">close</button></h3>
      <p class="muted" style="margin:0 0 10px">One Recraft request per style: <b>same icons on every 3×3 sheet</b> (≤9 icons per sheet, one icon per cell), <b>one different take per sheet</b>. You review every take before anything is written.</p>
      <div class="only-wide" style="overflow-x:auto; margin-bottom:6px">
        <table class="selmatrix">
          <thead>
            <tr>
              <th class="sh"><button class="subtle" style="padding:0 6px; font-size:.72rem" @click="batchSelAll(true)">all</button> <button class="subtle" style="padding:0 6px; font-size:.72rem" @click="batchSelAll(false)">none</button></th>
              <th v-for="ic in batchMatrix().icons" :key="ic" class="ih">
                <button class="subtle" style="padding:0 4px; font-size:.72rem" :class="{ on: batchColAll(ic) }" @click="batchToggleCol(ic)">{{ ic }}</button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in batchMatrix().styles" :key="row.style">
              <th class="sh">
                <button class="subtle" style="padding:0 6px; font-size:.75rem" :class="{ on: batchRowAll(row) }" @click="batchToggleRow(row)" :title="row.style">{{ row.style }}</button>
              </th>
              <td v-for="ic in batchMatrix().icons" :key="ic" class="cell">
                <label v-for="tg in (row.cells[ic] || [])" :key="tg" style="display:inline-flex; gap:3px; align-items:center; cursor:pointer; margin:1px">
                  <input type="checkbox" v-model="S.batchDlg.sel[tg]"> <span style="font-size:.7rem">{{ tg.split('#')[1] }}</span>
                </label>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="only-narrow">
        <div class="row" style="gap:6px; margin-bottom:8px">
          <button class="subtle" style="height:36px" @click="batchSelAll(true)">all</button>
          <button class="subtle" style="height:36px" @click="batchSelAll(false)">none</button>
          <span class="muted" style="font-size:.75rem; align-self:center">{{ batchSelCount() }}/{{ batchTotal() }} selected</span>
        </div>
        <div v-for="row in batchMatrix().styles" :key="row.style" style="margin-bottom:10px">
          <div class="row" style="justify-content:space-between; margin-bottom:4px">
            <button class="subtle" style="height:36px; font-weight:600" :class="{ on: batchRowAll(row) }" @click="batchToggleRow(row)">{{ row.style }}</button>
            <span class="muted" style="font-size:.75rem">{{ batchRowTargets(row).filter(tg => S.batchDlg.sel[tg]).length }}/{{ batchRowTargets(row).length }}</span>
          </div>
          <div class="row" style="flex-wrap:wrap; gap:6px">
            <button v-for="tg in batchRowTargets(row)" :key="tg" class="selchip" :class="{ on: S.batchDlg.sel[tg] }"
                    @click="S.batchDlg.sel[tg] = !S.batchDlg.sel[tg]" :aria-pressed="!!S.batchDlg.sel[tg]">
              {{ tg.replace('#', ' · ') }}
            </button>
          </div>
        </div>
      </div>
      <div class="row" style="margin-top:8px; gap:8px">
        <label class="muted">takes per icon</label>
        <select v-model.number="S.batchDlg.takes"><option v-for="tk in [1,2,3,4,5,6]" :key="tk" :value="tk">{{ tk }}</option></select>
        <label class="muted" style="margin-left:6px">max grid</label>
        <select v-model.number="S.batchDlg.maxGrid" @change="planCheck()">
          <option :value="0">auto</option>
          <option v-for="g in [2,3,4,5]" :key="g" :value="g">{{ g }}×{{ g }}</option>
        </select>
        <span class="muted" style="font-size:.75rem">smaller grids = more sheets, higher fidelity per icon</span>
      </div>
      <div class="row" style="margin-top:6px; gap:8px">
        <label class="muted">model</label>
        <select v-model="S.batchDlg.model" @change="planCheck()">
          <option value="">auto</option>
          <option v-for="m in vectorModels()" :key="m" :value="m">{{ m }} (${{ (S.recraftModels.prices || {})[m] || '?' }}/img)</option>
        </select>
        <span v-if="S.batchDlg.warn" class="chip rule" :title="S.batchDlg.warn">{{ S.batchDlg.warn }}</span>
      </div>
      <p style="margin:10px 0 0; display:flex; gap:6px; flex-wrap:wrap">
        <span class="chip">{{ batchSelCount() }}/{{ batchTotal() }} icons</span>
        <span class="chip">{{ batchSheets() }} sheet(s) × {{ S.batchDlg.takes }} take(s)</span>
        <span class="chip">{{ batchSelCount() * S.batchDlg.takes }} candidates</span>
        <span class="chip rule" title="estimated cost">≈ ${{ batchEst() }}</span>
      </p>
      <details v-if="S.debug" style="margin-top:8px">
        <summary class="muted">debug: exact request JSON</summary>
        <button class="subtle" @click="batchDebug()">fetch from server</button>
        <pre v-if="S.batchDlg.reqs" style="max-height:260px; overflow:auto; font-size:.7rem; white-space:pre-wrap">{{ S.batchDlg.reqs }}</pre>
      </details>
      <div v-if="S.batchDlg.busy" class="progressrow" style="margin-top:12px">
        <span class="spin"></span>
        <span>{{ S.batchDlg.phase }} · {{ batchElapsed() }}s</span>
        <progress max="100" :value="batchProgress()"></progress>
      </div>
      <div class="row" style="margin-top:12px">
        <button class="primary" :class="{ busy: S.batchDlg.busy }" :disabled="!batchSelCount()" @click="batchGenerate()">
          <span class="ic" v-html="IC.bolt"></span> generate {{ batchSelCount() * S.batchDlg.takes }} candidates
        </button>
      </div>
      <p v-if="S.batchDlg.err" class="err">{{ S.batchDlg.err }}</p>
    </div>
  </div>

  <div v-if="S.resultDlg" class="overlay" @click.self="S.resultDlg = null">
    <div class="dialog" style="max-width:720px">
      <h3 v-if="!S.resultDlg.batch"><span><span class="ic-lg" v-html="IC.bolt"></span> {{ S.resultDlg.icon }}#{{ S.resultDlg.variant }} — {{ (S.resultDlg.results || []).filter(r => r.keep).length }}/{{ (S.resultDlg.results || []).length }} kept</span>
          <button class="subtle" @click="S.resultDlg = null" aria-label="Close">✕</button></h3>
      <h3 v-if="S.resultDlg.batch"><span><span class="ic-lg" v-html="IC.bolt"></span> pack draft — {{ S.resultDlg.items.length }} icons × {{ S.resultDlg.takes }} takes · {{ keptCount() }}/{{ totalCount() }} kept</span>
          <button class="subtle" @click="S.resultDlg = null" aria-label="Close">✕</button></h3>
      <p class="muted" style="margin:0 0 10px">{{ S.resultDlg.model }} · ${{ S.resultDlg.cost }} · click to toggle, ✓ = keep</p>
      <p class="muted" style="margin:-6px 0 10px; font-size:.75rem">drag a take onto another icon of the same variant to reassign it</p>
      <div v-if="S.resultDlg.batch">
        <div v-for="it in S.resultDlg.items" :key="it.icon + '#' + it.variant" style="margin-bottom:12px"
             :class="{ dropzone: S.resultDlg.drag && S.resultDlg.drag.variant === it.variant && S.resultDlg.drag.icon !== it.icon }"
             @dragover.prevent @drop="dropResult(it)">
          <div class="row" style="justify-content:space-between">
            <b>{{ it.icon }}#{{ it.variant }}</b>
            <span class="muted">{{ (it.results || []).filter(r => r.keep).length }}/{{ (it.results || []).length }}</span>
          </div>
          <div class="row" style="flex-wrap:wrap; gap:8px">
            <div v-for="r in it.results" :key="r.uid"
                 draggable="true"
                 @dragstart="S.resultDlg.drag = { icon: it.icon, variant: it.variant, uid: r.uid }"
                 @dragend="S.resultDlg.drag = null"
                 @click="r.keep = !r.keep"
                 :style="{ cursor:'grab', border: r.keep ? '2px solid var(--accent)' : '2px dashed var(--line)', borderRadius:'10px', padding:'6px', opacity: r.keep ? '1' : '.4' }">
              <img :src="r.svg_data" width="64" height="64" style="border-radius:6px; background:#fff" draggable="false">
              <div style="text-align:center; font-size:.7rem; margin-top:2px">
                {{ r.keep ? '✓' : '✕' }} {{ r.gate_pass ? 'pass' : 'gate' }}
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="row" style="flex-wrap:wrap; gap:10px">
        <div v-for="r in S.resultDlg.results" :key="r.id"
             @click="r.keep = !r.keep"
             :style="{ cursor:'pointer', border: r.keep ? '2px solid var(--accent)' : '2px dashed var(--line)', borderRadius:'10px', padding:'6px', opacity: r.keep ? '1' : '.4' }">
          <img :src="r.svg_data" width="72" height="72" style="border-radius:6px; background:#fff">
          <div style="text-align:center; font-size:.7rem; margin-top:2px">
            {{ r.keep ? '✓' : '✕' }} {{ r.gate_pass ? 'pass' : 'gate' }}
          </div>
        </div>
      </div>
      <div class="row" style="margin-top:12px">
        <button class="primary" @click="commitResults()">
          add {{ keptCount() }} to round
        </button>
        <button class="subtle" @click="keepAll(true)">select all</button>
        <button class="subtle" @click="S.resultDlg = null">discard all</button>
      </div>
    </div>
  </div>

  <div v-if="S.histView" class="overlay" @click.self="S.histView = null">
    <div class="dialog">
      <h3><span>{{ S.histView.icon }} / {{ S.histView.variant }} · {{ S.histView.cand }} <span class="chip">{{ S.histView.round }}</span></span>
          <button class="subtle" @click="S.histView = null" aria-label="Close">✕</button></h3>
      <div class="sheetstage">
        <img width="96" height="96" :src="render(S.histView.path, 96, '#f6f9f7', mainColorIcon({icon: S.histView.icon}))">
        <img width="48" height="48" :src="render(S.histView.path, 48, '#22292e', '#f2f7f4')">
        <img width="24" height="24" :src="render(S.histView.path, 24, '#f6f9f7', mainColorIcon({icon: S.histView.icon}))">
      </div>
      <div class="row">
        <button class="subtle" @click="copyPath(S.histView.icon, S.histView.variant, S.histView.cand)"><span class="ic" v-html="IC.copy"></span> path</button>
        <button class="subtle" @click="toggleCompare({...S.histView, hist: true}); S.histView = null">⇄ compare</button>
      </div>
    </div>
  </div>

  <div v-if="S.compare && S.compare.length === 2" class="overlay" @click.self="S.compare = null">
    <div class="dialog" style="max-width:700px">
      <h3><span>Compare: {{ S.compare[0].cand }} vs {{ S.compare[1].cand }}</span>
          <button class="subtle" @click="S.compare = null">✕</button></h3>
      <div class="compare-grid">
        <div v-for="c in S.compare" :key="(c.round || '') + c.icon + '/' + c.variant + '/' + c.cand" class="compare-col">
          <div class="compare-label">{{ c.icon }} / {{ cmpLabel(c) }}{{ c.hist ? ' (history)' : '' }}</div>
          <div class="stage" style="background:#f6f9f7">
            <img :width="96" :height="96" :src="render(c.path, 96, '#f6f9f7')">
          </div>
          <div class="stage" style="background:#22292e">
            <img :width="96" :height="96" :src="render(c.path, 96, '#22292e', '#f2f7f4')">
          </div>
          <div class="compare-sizes">
            <img :width="48" :height="48" :src="render(c.path, 48, '#f6f9f7')">
            <img :width="24" :height="24" :src="render(c.path, 24, '#f6f9f7')">
            <img :width="16" :height="16" :src="render(c.path, 16, '#f6f9f7')">
          </div>
          <div class="rating" style="margin-top:6px" v-if="!c.hist">
            <button :class="{ armed: item(c)?.t === c.cand + ' ok' }" @click="approve(c)">✓</button>
            <button class="ratebtn" @click="openSheet(c)"><template v-if="hasRating(c)">★ {{ rating(c) }}</template><template v-else>rate</template></button>
            <button :class="{ 'armed-x': item(c)?.t?.startsWith(c.cand + ' no') }" @click="drop(c)">✕</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-if="S.sheet" class="overlay sheet" @click.self="S.sheet = null">
    <div class="sheetbox">
      <h3>{{ S.sheet.c.icon }} / {{ S.sheet.c.variant }} · {{ S.sheet.c.cand }}
          <button class="subtle" @click="S.sheet = null">✕</button></h3>
      <div class="sheetstage">
        <img width="96" height="96" :src="render(S.sheet.c.path, 96, '#f6f9f7')">
        <img width="48" height="48" :src="render(S.sheet.c.path, 48, '#22292e', '#f2f7f4')">
        <img width="24" height="24" :src="render(S.sheet.c.path, 24, '#f6f9f7')">
      </div>
      <div class="stars">
        <button v-for="n in 10" :key="n" :class="{ on: n <= rating(S.sheet.c) }"
                @click="rate(S.sheet.c, n); S.sheet = null;">★</button>
      </div>
      <div class="sheetrow">
        <button class="subtle" @click="copyPath(S.sheet.c.icon, S.sheet.c.variant, S.sheet.c.cand)"
                title="copy this SVG path (open in Inkscape)"><span class="ic" v-html="IC.copy"></span> path</button>
        <button class="subtle" @click="copyPrompt(S.sheet.c.icon, S.sheet.c.variant)"
                title="copy a complete LLM hint for this variant"><span class="ic" v-html="IC.spark"></span> LLM hint</button>
        <button class="armed-x" @click="drop(S.sheet.c); S.sheet = null">drop (0)</button>
        <button class="subtle" @click="S.sheet = null">cancel</button>
      </div>
    </div>
  </div>

  <div v-if="S.dlg" class="overlay" @click.self="S.dlg = null">
    <div class="dialog">
      <h3><span>{{ S.dlg.icon }} / {{ S.dlg.variant }} <span class="muted">{{ S.dlg.cand || '' }}</span></span>
          <span class="row" style="gap:6px">
            <button v-if="S.recraftReady || S.debug" class="primary" @click="adoptPreview()"
                    title="deterministic post-process this seed into a pack icon: bake transforms, snap colors/palette, rescale to the style grid, simplify — gate issues are shown, never blocking">
              <span class="ic" v-html="IC.check || IC.star"></span> adopt</button>
            <button class="subtle" @click="S.dlg = null">close ✕</button>
          </span></h3>
      <div class="matrix">
        <div class="col" v-for="bgc in S.dlg.bgs2" :key="bgc.hex">
          <div class="colhead">{{ bgc.name }}</div>
          <div class="stage" :style="{background: bgc.hex}">
            <img v-for="s in [96, 48, 24, 16]" :key="s" :width="s" :height="s"
                 :src="render(S.dlg.path, s * 2, bgc.hex, bgc.iconColor)">
          </div>
          <div class="sizes">96 · 48 · 24 · 16</div>
        </div>
      </div>
      <div class="controls">
        <label>icon color · light bg</label>
        <input type="color" :value="S.dlg.bgs2[0].iconColor"
               @input="S.dlg.bgs2[0].iconColor = $event.target.value">
        <label style="margin-left:12px">icon on dark</label>
        <input type="color" :value="S.dlg.bgs2[1].iconColor"
               @input="S.dlg.bgs2[1].iconColor = $event.target.value">
        <label style="margin-left:12px">dark bg</label>
        <input type="color" :value="S.dlg.bgs2[1].hex"
               @input="S.dlg.bgs2[1].hex = $event.target.value">
      </div>
      <div class="stylebox" v-if="S.dlg.styleId">
        <b>{{ styleLabel(S.dlg.styleId) }}</b>
        <div class="kv">
          <template v-if="S.styles[S.dlg.styleId]">
            <span>grid</span><b>{{ S.styles[S.dlg.styleId].size || 'S.pack' }}px</b>
            <span>stroke</span><b>{{ S.styles[S.dlg.styleId].stroke?.width || '—' }}</b>
            <span>mode</span><b>{{ S.styles[S.dlg.styleId].construction }} / {{ S.styles[S.dlg.styleId].color_mode }}</b>
            <span>budget</span><b>≤ {{ S.styles[S.dlg.styleId].max_nodes }} nodes · gap {{ S.styles[S.dlg.styleId].min_gap }}</b>
            <span v-if="S.styles[S.dlg.styleId].palette">palette</span>
            <b v-if="S.styles[S.dlg.styleId].palette">{{ S.styles[S.dlg.styleId].palette.join(' ') }}</b>
          </template>
        </div>
        <div class="controls" style="margin-top:8px">
          <label>switch style</label>
          <select :value="S.dlg.styleId" @change="switchStyle(S.dlg, $event.target.value)">
            <option v-for="(s, sid) in S.styles" :key="sid" :value="sid">{{ sid }} — {{ s.label }}</option>
          </select>
        </div>
      </div>
    </div>
  </div>
</div>

<script type="module">
import { createApp, reactive, computed, onMounted } from '/static/vue.esm-browser.prod.js';

const S = reactive({
  pack: { icons: {} }, rev: 0, round: null, latest: null, candidates: [], locked: {}, drafting: '',
  viewRound: null, rounds: [],
  styles: {}, ai: { text: '', active: false }, version: '',
  decisions: {}, manual: false, manualText: '',
  msg: '', msgClass: 'muted', editing: null,
  dlg: null, sheet: null, fbDlg: null, settingsDlg: false,
  decisionEdit: '', showGen: false, editingBrief: null,
  flash: '', flashOk: true, applying: false, instructions: '',
  tab: (location.hash || '#round').slice(1) || 'round',
  kbFocus: 0, kbVariant: 0, kbCand: 0, kbUsed: false, compare: null, histView: null,
  recraftReady: false, debug: new URLSearchParams(location.search).has('debug'), debugDlg: null, nextDlg: null, resultDlg: null, batchDlg: null, refineDlg: null, adoptDlg: null, styleRc: null, aistatOpen: false,
  appliedRound: null,
  recraftModels: {}, styleRefs: {}, styleDetail: {}, styleEdit: null, styleView: null, removeArm: null, theme: 'light', iconHist: {}, svgFiles: {}, rejectArm: null,
  history: [], showHistory: false,
  set: { version: '', rules: '', strokeWidth: 2, linecap: 'round', linejoin: 'round', padding: 2, precision: 0.5, palette: null, errors: '' },
  bgs: [
    { name: 'white', hex: '#ffffff' }, { name: 'paper', hex: '#f6f9f7' },
    { name: 'night', hex: '#112119' }, { name: 'ink', hex: '#1c1c1c' },
  ],
});

const api = async (url, opts) => {
  const r = await fetch(url, opts);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(d.error || JSON.stringify(d.errors) || r.status), { d });
  return d;
};
const esc = s => String(s ?? '');

// inline icon set (16px, stroke currentColor — no emoji)
const IC = {
  comment: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  bolt: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>',
  undo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-15-6.7L3 13"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36L21 8"/><path d="M21 3v5h-5"/></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1z"/></svg>',
  unlock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"/></svg>',
  history: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>',
  spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6l1.4 1.4m10 10 1.4 1.4m0-12.8-1.4 1.4m-10 10-1.4 1.4"/><path d="M12 8.5 13.5 12 12 15.5 10.5 12z"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>',
  star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l2.7 5.6 6.3.9-4.5 4.3 1 6.2-5.5-3-5.5 3 1-6.2L3 9.5l6.3-.9z"/></svg>',
  palette: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r="1.2"/><circle cx="17.5" cy="10.5" r="1.2"/><circle cx="8.5" cy="7.5" r="1.2"/><circle cx="6.5" cy="12.5" r="1.2"/><path d="M12 2a10 10 0 0 0 0 20c1.1 0 2-.9 2-2 0-.5-.2-1-.5-1.3-.3-.4-.5-.8-.5-1.3 0-1.1.9-2 2-2h2.5A4.5 4.5 0 0 0 22 11c0-5-4.5-9-10-9z"/></svg>',
  grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
};
function relTime(iso) {
  if (!iso) return '';
  const d = new Date(/Z$|[+-][0-9][0-9]:[0-9][0-9]$/.test(iso) ? iso : iso + 'Z');
  if (isNaN(d)) return '';
  const s = Math.max(0, (Date.now() - d.getTime()) / 1000);
  if (s < 60) return 'now';
  if (s < 3600) return Math.floor(s / 60) + 'm';
  if (s < 86400) return Math.floor(s / 3600) + 'h';
  return Math.floor(s / 86400) + 'd';
}
function seenKey() { return 'iconpilot.seen.' + (S.pack.name || ''); }
const GATE_HELP = [
  { k: 'min_gap', h: 'no near-miss spacing — strokes must join or keep clear distance (off for broken lines)' },
  { k: 'grid', h: 'coordinates snapped to the 0.5 design grid' },
  { k: 'live_area', h: 'artwork stays inside the padded live area' },
  { k: 'max_nodes', h: 'path complexity budget per icon' },
  { k: 'palette', h: 'only colors from the style palette are allowed' },
];
const FAV = {
  // phase → [bg, glyph-path, title-suffix]
  agent:  ['#b7791f', 'M13 2 3 14h9l-1 8 10-12h-9l1-8z', 'agent drafting'],
  review: ['#2f855a', 'M12 2l2.9 6.3 6.9.8-5.1 4.7 1.4 6.8-6.1-3.4-6.1 3.4 1.4-6.8L2.2 9.1l6.9-.8z', 'your turn — rate'],
  applied:['#2b6cb0', 'M20 6 9 17l-5-5', 'applied — start next pass'],
  idle:   ['#718096', 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'idle'],
};
function setFavicon(phase) {
  const [bg, glyph, label] = FAV[phase] || FAV.idle;
  const svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>"
    + "<rect width='24' height='24' rx='6' fill='" + bg + "'/>"
    + "<path d='" + glyph + "' fill='none' stroke='#fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>";
  const link = document.getElementById('fav');
  if (link) link.href = 'data:image/svg+xml,' + encodeURIComponent(svg);
  document.title = label + ' · iconpilot review';
}
function applyTheme(th) {
  S.theme = th;
  document.documentElement.dataset.theme = th;
  try { localStorage.setItem('iconpilot.theme', th); } catch {}
}
function initTheme() {
  let th = null;
  try { th = localStorage.getItem('iconpilot.theme'); } catch {}
  applyTheme(th || (matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
}
function toggleTheme() { applyTheme(S.theme === 'dark' ? 'light' : 'dark'); }
function setTab(tb) {
  if (S.aistatOpen) S.aistatOpen = false;
  S.tab = tb;
  history.replaceState(null, '', '#' + tb);
  if (tb === 'settings') loadSettings();
}
function markSeen() { try { localStorage.setItem(seenKey(), new Date().toISOString()); } catch {} }
function seenTs() { try { return localStorage.getItem(seenKey()) || ''; } catch { return ''; } }
function isNew(i) { return !!i.created && i.created + 'Z' > seenTs(); }

S.grouped = computed(() => {
  const m = new Map();
  for (const c of S.candidates) {
    if (!m.has(c.icon)) m.set(c.icon, { key: c.icon, icon: c.icon, cands: [] });
    m.get(c.icon).cands.push(c);
  }
  // open work comes from pack state, not just candidates: unlocked icons
  // reappear immediately, even before new drafts exist
  if (!S.viewRound || S.viewRound === S.latest) {
    for (const [iid, icon] of Object.entries(S.pack.icons || {})) {
      const hasOpen = Object.entries(icon.variants || {})
        .some(([vid, v]) => !v.link && !S.locked[iid + '/' + vid]);
      if (hasOpen && !m.has(iid)) m.set(iid, { key: iid, icon: iid, cands: [] });
    }
  }
  return [...m.values()];
});
async function copyText(text, okMsg) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(ta); ta.focus(); ta.select();
      const ok = document.execCommand('copy'); ta.remove();
      if (!ok) throw new Error('execCommand denied');
    }
    flash(okMsg, true);
  } catch (e) { flash('copy blocked — select the composer textarea and paste manually', false); }
}
async function copyPath(icon, variant, cand) {
  const q = new URLSearchParams({ icon, variant });
  if (cand) q.set('cand', cand);
  try {
    const r = await api('/api/svg-path?' + q);
    await copyText(r.path, 'path copied: ' + r.path);
  } catch (e) { flash('copy failed', false); }
}
async function copyPrompt(icon, variant) {
  try {
    const r = await api('/api/prompt?icon=' + encodeURIComponent(icon) + '&variant=' + encodeURIComponent(variant));
    await copyText(r.prompt, 'LLM hint copied for ' + icon + '#' + variant + ' — paste it anywhere, bring the SVGs back');
  } catch (e) { flash('hint: ' + e.message, false); }
}
function variantGroups(g) {
  const m = new Map();
  const put = (vid, style) => { if (!m.has(vid)) m.set(vid, { variant: vid, cands: [], style }); };
  for (const c of g.cands) { put(c.variant, c.style); m.get(c.variant).cands.push(c); }
  if (!isViewing()) {
    for (const [vid, v] of Object.entries(S.pack.icons?.[g.icon]?.variants || {})) {
      if (!v.link && !S.locked[g.icon + '/' + vid]) put(vid, v.style);
    }
  }
  return [...m.values()];
}
function packBriefIcon(g) {
  return S.pack.icons?.[g.icon]?.brief || '';
}
function iconStylePalette(iid) {
  const icon = S.pack.icons?.[iid];
  const vids = Object.keys(icon?.variants || {});
  if (!vids.length) return [];
  const st = icon.variants[vids[0]].style;
  return (S.pack.styles?.[st]?.def?.palette) || [];
}
async function toggleIconColor(iid, c) {
  const icon = S.pack.icons?.[iid];
  if (!icon) return;
  let colors = (icon.colors || []).slice();
  if (c === null) colors = [];
  else if (colors.includes(c)) colors = colors.filter(x => x !== c);
  else if (colors.length >= 10) { flash('max 10 colors per icon', false); return; }
  else colors.push(c);
  try {
    await api('/api/icon', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: iid, colors }) });
    await load();
  } catch (e) { flash('colors: ' + (e.d?.error || e.message), false); }
}
function mainColorIcon(g) {
  return S.pack.icons?.[g.icon]?.main_color;
}
async function saveMainColorIcon(g, color) {
  try {
    const r = await api('/api/icon', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: g.icon, main_color: color }) });
    S.msg = `main color saved (rev ${r.rev})`; S.msgClass = 'ok'; await load();
  } catch (e) { S.msg = e.message; S.msgClass = 'err'; }
}
async function togglePin(icon, variant) {
  const current = S.pack.icons?.[icon]?.variants?.[variant]?.pinned;
  try {
    const r = await api('/api/variant', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon, variant, pinned: !current }) });
    S.msg = `${!current ? 'pinned' : 'unpinned'} ${icon}/${variant} (rev ${r.rev})`;
    S.msgClass = 'ok'; await load();
  } catch (e) { S.msg = e.message; S.msgClass = 'err'; }
}
function isPinned(icon, variant) {
  return !!S.pack.icons?.[icon]?.variants?.[variant]?.pinned;
}
function fbNew(scope, icon, vid) {
  return fbFor(scope, icon, vid).filter(isNew).length;
}
function fbFor(scope, icon, vid) {
  return (S.pack.feedback || []).filter(i =>
    i.scope === scope && (scope === 'pack' || i.icon === icon) &&
    (scope !== 'variant' || i.variant === vid));
}
function fbTitle() {
  const d = S.fbDlg || {};
  return 'feedback: ' + (d.scope === 'pack' ? 'whole draft' : d.icon + (d.variant ? ' / ' + d.variant : ''));
}
function fbItems() { const d = S.fbDlg || {}; return d.scope ? fbFor(d.scope, d.icon, d.variant) : []; }
function openFb(scope, icon, vid) {
  S.fbDlg = { scope, icon, variant: vid, text: '' };
  markSeen();
  focusDialog();
  chatToBottom();
}
function chatToBottom() {
  requestAnimationFrame(() => {
    const el = document.querySelector('.chat');
    if (el) el.scrollTop = el.scrollHeight;
  });
}
function fbChat() {
  const d = S.fbDlg;
  if (!d || !d.scope) return [];
  const match = i =>
    i.scope === d.scope &&
    (d.scope === 'pack' || i.icon === d.icon) &&
    (d.scope !== 'variant' || i.variant === d.variant);
  const out = [];
  for (const h of S.history || []) {
    const items = (h.feedback || []).filter(match);
    if (items.length) out.push({ round: h.round, archived: true, items });
  }
  const live = fbFor(d.scope, d.icon, d.variant);
  if (live.length) out.push({ round: S.round || 'live', archived: false, items: live });
  return out;
}
async function addFeedback() {
  const d = S.fbDlg; if (!d || !d.text || !d.text.trim()) return;
  try {
    await api('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope: d.scope, icon: d.icon, variant: d.variant, text: d.text.trim(), author: 'user' }) });
    d.text = ''; await load(); chatToBottom();
  } catch (e) { flash('feedback: ' + e.message, false); }
}
async function resolveFeedback(i) {
  try {
    await api('/api/feedback/resolve', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: i.id }) });
    await load();
  } catch (e) { flash('resolve: ' + e.message, false); }
}
function batchApprove(minScore) {
  // approve all candidates rated >= minScore
  for (const g of S.grouped) {
    for (const vg of variantGroups(g)) {
      for (const c of vg.cands) {
        if (rating(c) >= minScore) approve(c);
      }
    }
  }
  flash('batch: approved all rated ≥ ' + minScore, true);
}
function batchReject(maxScore) {
  // reject all candidates rated <= maxScore (0 = reject unrated/unrejected)
  for (const g of S.grouped) {
    for (const vg of variantGroups(g)) {
      for (const c of vg.cands) {
        const r = rating(c);
        const hasDecision = !!item(c);
        if (maxScore === 0) {
          // reject unrated = no explicit decision yet
          if (!hasDecision) drop(c);
        } else if (r > 0 && r <= maxScore) {
          drop(c);
        }
      }
    }
  }
  flash('batch: rejected ' + (maxScore === 0 ? 'unrated' : 'all rated ≤ ' + maxScore), true);
}
function waitTargets() {
  return [...new Set((S.grouped || []).map(g => g.icon))];
}
function waitingForAgent() {
  return S.tab === 'round' && !isViewing() && S.ai.active && !S.candidates.length;
}
function isViewing() { return !!(S.viewRound && S.viewRound !== S.latest); }
function ruleTitle(ru) {
  if (ru.startsWith('stroke')) return 'stroke width in px';
  if (ru.endsWith('px')) return 'design grid size';
  if (ru.startsWith('gap')) return 'minimum spacing between strokes (near-miss check)';
  if (ru.includes('nodes')) return 'path complexity budget';
  if (ru.endsWith(' off')) return 'gate check disabled for this style';
  return ru;
}
function curatedNames() {
  return [...new Set(Object.values(S.recraftModels?.suggestions || {}))].sort();
}
function vectorModels() {
  const prices = S.recraftModels?.prices || {};
  return Object.keys(prices).filter(m => m.includes('vector'));
}
async function styleDetail(sid) {
  try {
    const d = await api('/api/style-detail?style=' + encodeURIComponent(sid));
    S.styleDetail = { ...S.styleDetail, [sid]: d };
    const snap = d.snapshot || {};
    S.styleView = { id: sid, def: d.def, model: snap.recraft_model || (S.recraftModels.suggestions || {})[sid] || 'auto', recraftStyleId: snap.recraft_style_id || (S.pack.recraft?.style_ids || {})[sid] || '' };
    focusDialog();
  } catch (e) { flash('style detail: ' + e.message, false); }
}
function editCustomStyle() {
  S.styleEdit = {
    id: '', label: '', size: '', strokeWidth: '', minGap: 1.5, maxNodes: 40,
    paletteList: [], words: '', avoid: '', guidance: '', gateOff: [],
    recraftModel: '', extends: 'mono-line',
  };
  focusDialog();
}
function styleUsageCount(sid) {
  let n = 0;
  for (const icon of Object.values(S.pack.icons || {}))
    for (const v of Object.values(icon.variants || {}))
      if (v.style === sid && !v.link) n += 1;
  return n;
}
function styleRules(sid) {
  const st = S.styles[sid]; if (!st) return [];
  const r = [];
  if (st.stroke) r.push('stroke ' + st.stroke.width);
  if (st.size) r.push(st.size + 'px');
  r.push('gap ≥ ' + st.min_gap);
  r.push('≤ ' + st.max_nodes + ' nodes');
  if (st.gate) r.push(...Object.entries(st.gate).filter(([, off]) => !off).map(([k]) => k + ' off'));
  return r;
}
function stylePalette(sid) { return (S.styles[sid]?.palette) || []; }
function styleSummary(sid) {
  const st = S.styles[sid]; if (!st) return '';
  const bits = [st.construction, st.color_mode];
  if (st.stroke) bits.push('stroke ' + st.stroke.width);
  if (st.size) bits.push(st.size + 'px grid');
  return bits.join(' · ');
}
function isOwnRef(sid, name) { return (S.styleDetail?.[sid]?.refs || []).some(r => r.name === name && r.own); }
async function editStyle(sid) {
  S.styleView = null;
  try {
    const d = await api('/api/style-detail?style=' + encodeURIComponent(sid));
    S.styleDetail = { ...S.styleDetail, [sid]: d };
    const def = d.def || {};
    const gateOff = Object.entries(def.gate || {}).filter(([, off]) => off === false).map(([k]) => k);
    S.styleEdit = {
      id: sid,
      label: def.label || sid,
      size: def.size || '',
      strokeWidth: def.stroke ? def.stroke.width : '',
      minGap: def.min_gap,
      maxNodes: def.max_nodes,
      paletteList: (def.palette || []).slice(),
      words: (def.style_words || []).join(', '),
      avoid: (def.avoid || []).join(', '),
      guidance: def.guidance || '',
      gateOff,
      extends: (d.snapshot || {}).extends,
    };
    focusDialog();
  } catch (e) { flash('style detail: ' + e.message, false); }
}
function toggleGate(gk) {
  const go = S.styleEdit.gateOff || [];
  S.styleEdit.gateOff = go.includes(gk) ? go.filter(k => k !== gk) : [...go, gk];
}
async function saveStyleRules() {
  const e = S.styleEdit;
  if (!e.id?.trim()) {
    e.id = e.label?.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-') || 'custom-style';
  }
  const sdef = {};
  if (e.extends) sdef.extends = e.extends;
  if (e.label) sdef.label = e.label;
  if (e.size) sdef.size = +e.size;
  if (e.strokeWidth) sdef.stroke = { width: +e.strokeWidth, linecap: 'round', linejoin: 'round' };
  sdef.min_gap = +e.minGap || 1.5;
  sdef.max_nodes = +e.maxNodes || 40;
  if (e.paletteList && e.paletteList.length) sdef.palette = e.paletteList;
  if (e.words.trim()) sdef.style_words = e.words.split(',').map(s => s.trim()).filter(Boolean);
  if (e.avoid.trim()) sdef.avoid = e.avoid.split(',').map(s => s.trim()).filter(Boolean);
  if (e.guidance.trim()) sdef.guidance = e.guidance;
  const off = Object.fromEntries((e.gateOff || []).map(k => [k, false]));
  if (Object.keys(off).length) sdef.gate = off;
  try {
    await api('/api/pack-style', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: e.id, def: sdef }) });
    flash('style rules saved: ' + e.id, true);
    S.styleEdit = null; await load();
  } catch (err) { flash('save style: ' + (err.d?.error || err.message), false); }
}
async function removeStyle(sid) {
  if (S.removeArm !== sid) { S.removeArm = sid; flash('click remove again to delete "' + sid + '" from every glyph', false); return; }
  S.removeArm = null;
  try {
    await api('/api/pack-style-remove', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: sid }) });
    flash('style removed: ' + sid, true);
    await load();
  } catch (err) { flash('remove style: ' + (err.d?.error || err.message), false); }
}
async function addStyleToPack(sid) {
  if (!confirm('Add style "' + sid + '" as a variant to every glyph?')) return;
  await addVariantBulkFor(sid);
  await load();
}
async function addVariantBulkFor(sid) {
  try {
    const r = await api('/api/pack-variant-bulk', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: sid }) });
    flash('variant ' + sid + ' added to ' + r.added + ' glyph(s)', true);
  } catch (err) { flash('add: ' + (err.d?.error || err.message), false); }
}
function pickRefFile(sid) {
  const inp = document.createElement('input');
  inp.type = 'file'; inp.accept = '.svg,image/svg+xml';
  inp.onchange = async () => {
    const f = inp.files[0]; if (!f) return;
    const svg = await f.text();
    try {
      await api('/api/style-ref-upload', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style: sid, name: f.name, svg }) });
      flash('reference uploaded: ' + f.name, true);
      await load();
    } catch (err) { flash('upload: ' + (err.d?.error || err.message), false); }
  };
  inp.click();
}
async function removeRef(sid, name) {
  try {
    await api('/api/style-ref-remove', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: sid, name }) });
    flash('reference removed: ' + name, true);
    await load();
  } catch (err) { flash('remove ref: ' + (err.d?.error || err.message), false); }
}
function usedStyles() {
  const used = new Set();
  for (const icon of Object.values(S.pack.icons || {}))
    for (const v of Object.values(icon.variants || {}))
      if (v.style && !v.link) used.add(v.style);
  return [...used].sort();
}
function isPostponed(icon, variant) { return !!S.pack.icons?.[icon]?.variants?.[variant]?.postponed; }
async function togglePostpone(icon, variant) {
  try {
    await api('/api/variant', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon, variant, postponed: !isPostponed(icon, variant) }) });
    flash(icon + '#' + variant + (isPostponed(icon, variant) ? ' resumed' : ' postponed'), true);
    await load();
  } catch (e) { flash('postpone: ' + e.message, false); }
}
function isLocked(icon, variant) { return !!S.locked[icon + '/' + variant]; }
async function loadIconHist(g) {
  if (S.iconHist[g.icon]) return;
  try {
    const r = await api('/api/icon-runs?icon=' + encodeURIComponent(g.icon));
    S.iconHist = { ...S.iconHist, [g.icon]: r.candidates };
  } catch (e) { flash('history: ' + e.message, false); }
}
async function reopen(icon, variant) {
  if (!confirm('Reopen ' + icon + '#' + variant + ' for drafting? The approved file stays in history.')) return;
  try {
    await api('/api/variant', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon, variant, reopen: true }) });
    flash(icon + '#' + variant + ' reopened', true);
    await load();
  } catch (e) { flash('reopen: ' + e.message, false); }
}
async function switchRound(r) {
  S.viewRound = r === S.latest ? null : r;
  S.decisions = {}; editDirty = false; S.decisionEdit = ''; S.instructions = ''; S.compare = null; S.appliedRound = null;
  await load();
}
function totalCost() { return S.history.reduce((a, h) => a + (h.cost_usd || 0), 0); }

async function showDebug(icon, variant, model, n, grid) {
  try {
    if (S.debugDlg) S.debugDlg.error = '';
    const q = new URLSearchParams({ icon, variant });
    if (model) q.set('model', model);
    if (n) q.set('n', n);
    if (grid) q.set('grid', grid);
    const r = await api('/api/recraft-request?' + q);
    S.debugDlg = null;  // reset before rebuild
    const fullPrompt = r.request.prompt || '';
    r.request.prompt = fullPrompt.length > 300 ? fullPrompt.slice(0, 300) + '… (full hint below)' : fullPrompt;
    S.debugDlg = {
      icon, variant,
      variants: openVariantIds(icon),
      style: (S.pack.icons?.[icon]?.variants?.[variant]?.style) || '',
      endpoint: r.endpoint, refs: r.style_refs_attached,
      request: JSON.stringify(r.request, null, 2),
      full: r.full_prompt || '',
      fullPrompt,
      promptChars: fullPrompt.length,
      promptLimit: fullPrompt.length > 1000 ? 10000 : 1000,
      cost: r.est_cost_usd, models: r.models || [], model: r.request.model,
      n: r.versions || r.request.n || 4, grid: r.grid || 1,
      copied: '',
    };
    focusDialog();
  } catch (e) { flash('preview: ' + e.message, false); }
}
async function debugCopy(what) {
  const d = S.debugDlg;
  if (!d) return;
  let text = '', label = '';
  if (what === 'request') { text = d.request; label = 'request JSON'; }
  else if (what === 'full') { text = d.full; label = 'full hint (' + d.full.length + ' chars)'; }
  else if (what === 'prompt') { text = d.fullPrompt; label = 'prompt'; }
  try {
    await copyText(text, '');
    d.copied = label + ' copied';
    setTimeout(() => { if (S.debugDlg) S.debugDlg.copied = ''; }, 2000);
  } catch (e) { d.copied = 'copy blocked'; }
}
function openVariantIds(icon) {
  const icon0 = S.pack.icons?.[icon];
  if (!icon0) return [];
  return Object.entries(icon0.variants || {})
    .filter(([vid, v]) => !v.link && !S.locked[icon + '/' + vid] && !v.postponed).map(([vid]) => vid);
}
async function saveRecraftDefaults(model, n) {
  try {
    await api('/api/pack', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recraft: { model, n } }) });
    flash('Recraft defaults saved: ' + model + ' · ' + n + '/request', true);
    await load();
  } catch (e) { flash('defaults: ' + (e.d?.error || e.message), false); }
}
async function openStyleRc(sid) {
  try {
    const r = await api('/api/recraft-style-request?style=' + encodeURIComponent(sid));
    S.styleRc = {
      id: sid, cached: r.cached_id, fresh: r.fresh, refs: r.refs_count,
      cost: r.cost_usd, endpoint: r.endpoint,
      reqs: JSON.stringify(r.request, null, 2),
      uuid: '', busy: false, err: '',
    };
    focusDialog();
  } catch (e) { flash('style: ' + (e.d?.error || e.message), false); }
}
async function styleRcCreate() {
  const d = S.styleRc;
  if (!d || d.busy) return;
  d.busy = true; d.err = '';
  try {
    const r = await api('/api/recraft-style-create', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: d.id }) });
    flash('style created · ' + r.style_id + ' ($' + r.cost_usd + ')', true);
    S.styleRc = null;
    await load();
  } catch (e) {
    d.busy = false;
    d.err = e.d?.error || e.message || 'create failed';
  }
}
async function styleRcSave() {
  const d = S.styleRc;
  if (!d || !d.uuid.trim()) { d.err = 'paste a UUID first'; return; }
  try {
    await api('/api/recraft-style-save', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: d.id, style_id: d.uuid.trim() }) });
    flash('style uuid saved — drafts will use it', true);
    S.styleRc = null;
    await load();
  } catch (e) { d.err = e.d?.error || e.message || 'save failed'; }
}
async function adoptPreview() {
  const d = S.dlg;
  if (!d) return;
  try {
    const r = await api('/api/adopt', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: d.icon, variant: d.variant, cand: d.cand || '' }) });
    S.adoptDlg = { icon: r.icon, variant: r.variant, cand: r.cand,
      svg_data: r.svg_data, fixes: r.fixes, gate_errors: r.gate_errors, busy: false, err: '' };
    S.dlg = null;
    focusDialog();
  } catch (e) { flash('adopt: ' + (e.d?.error || e.message), false); }
}
async function adoptCommit() {
  const d = S.adoptDlg;
  if (!d || d.busy) return;
  d.busy = true; d.err = '';
  try {
    const svg = atob(d.svg_data.split(',')[1]);
    const r = await api('/api/adopt-commit', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: d.icon, variant: d.variant, cand: d.cand, svg, gate_errors: d.gate_errors }) });
    flash('adopted ' + d.icon + '#' + d.variant + (r.gate_issues ? ' — ' + r.gate_issues + ' gate issue(s) recorded' : ' — gate clean'), true);
    S.adoptDlg = null;
    await load();
  } catch (e) {
    d.busy = false;
    d.err = e.d?.error || e.message || 'commit failed';
  }
}
function openRefineDlg(iconId) {
  const targets = [];
  const collect = (iid, icon) => {
    for (const [vid, v] of Object.entries(icon.variants || {})) {
      if (v.link || v.postponed || (S.locked || {})[iid + '/' + vid]) continue;
      targets.push({ icon: iid, variant: vid });
    }
  };
  if (iconId) collect(iconId, S.pack.icons[iconId] || { variants: {} });
  else for (const [iid, icon] of Object.entries(S.pack.icons || {})) collect(iid, icon);
  if (!targets.length) { flash('no open variants to refine', false); return; }
  const items = targets.map(tg => {
    const fb = (S.pack.feedback || []).filter(i =>
      i.scope === 'variant' && i.icon === tg.icon && i.variant === tg.variant && i.round === S.round)
      .map(i => i.text).join('; ');
    return { ...tg, feedback: fb, skip: !fb };
  });
  const withFb = items.filter(i => !i.skip).length;
  if (!withFb) {
    flash('no feedback this round — write feedback first (💬), refine needs it', false);
  }
  S.refineDlg = { items, strength: 0.3, takes: 2, model: 'recraftv4_1_vector', busy: false, err: '' };
  focusDialog();
}
function refineMatrix() {
  const styles = [], icons = [], cells = {};
  for (const it of S.refineDlg?.items || []) {
    const st = S.pack.icons?.[it.icon]?.variants?.[it.variant]?.style || '?';
    if (!cells[st]) { cells[st] = {}; styles.push(st); }
    (cells[st][it.icon] = cells[st][it.icon] || []).push(it);
    if (!icons.includes(it.icon)) icons.push(it.icon);
  }
  styles.sort(); icons.sort();
  return { styles: styles.map(s => ({ style: s, cells: cells[s] })), icons };
}
function refineRowItems(row) {
  const out = [];
  for (const list of Object.values(row.cells || {})) out.push(...list);
  return out;
}
function refineRowAll(row) { return refineRowItems(row).every(it => !it.skip && (it.feedback || '').trim()); }
function refineToggleRow(row) {
  const on = !refineRowAll(row);
  refineRowItems(row).forEach(it => { it.skip = !on; });
}
function refineColItems(ic) {
  const out = [];
  for (const row of refineMatrix().styles) out.push(...((row.cells[ic] || [])));
  return out;
}
function refineColAll(ic) { const t = refineColItems(ic); return t.length > 0 && t.every(it => !it.skip && (it.feedback || '').trim()); }
function refineToggleCol(ic) {
  const on = !refineColAll(ic);
  refineColItems(ic).forEach(it => { it.skip = !on; });
}
function refineSetAll(on) {
  (S.refineDlg?.items || []).forEach(it => { it.skip = !on; });
}
function refineActive() { return (S.refineDlg?.items || []).filter(i => !i.skip && (i.feedback || '').trim()); }
function refineReady() { return refineActive().length > 0 && !S.refineDlg.busy; }
function refineEst() {
  const d = S.refineDlg; if (!d) return '0.00';
  const price = (S.recraftModels.prices || {})[d.model] || 0.08;
  return (refineActive().length * d.takes * price).toFixed(2);
}
async function refineGenerate() {
  const d = S.refineDlg;
  if (!d || d.busy || !refineReady()) return;
  d.busy = true; d.err = '';
  try {
    const active = refineActive();
    const feedback = {};
    active.forEach(i => { feedback[i.icon + '#' + i.variant] = i.feedback.trim(); });
    const r = await api('/api/recraft-refine', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        targets: active.map(i => i.icon + '#' + i.variant),
        feedback, strength: d.strength, takes: d.takes, model: d.model,
      }) });
    S.refineDlg = null;
    if ((r.skipped || []).length) {
      flash('skipped: ' + r.skipped.map(s => s.target + ' (' + s.reason + ')').join(', '), false);
    }
    let seq = 0;
    S.resultDlg = {
      batch: true,
      drag: null,
      items: (r.items || []).map(it => ({ ...it, results: (it.results || []).map(x => ({ ...x, keep: true, uid: ++seq })) })),
      takes: r.takes, model: r.model, cost: r.cost_usd,
    };
  } catch (e) {
    d.busy = false;
    d.err = e.d?.error || e.message || 'refine failed';
  }
}
function openBatchDlg() {
  const sel = {};
  let any = false;
  for (const [iid, icon] of Object.entries(S.pack.icons || {})) {
    for (const [vid, v] of Object.entries(icon.variants || {})) {
      if (v.link || v.postponed || isLocked(iid, vid)) continue;
      sel[iid + '#' + vid] = true; any = true;
    }
  }
  if (!any) { flash('no open icons to draft — everything approved or postponed', false); return; }
  S.batchDlg = { sel, takes: 4, model: '', maxGrid: 0, busy: false, err: '', warn: '' };
  focusDialog();
  planCheck();
}
async function planCheck() {
  const d = S.batchDlg;
  if (!d) return;
  const targets = Object.entries(d.sel || {}).filter(([, on]) => on).map(([tg]) => tg);
  if (!targets.length) return;
  try {
    const r = await api('/api/recraft-batch', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targets, takes: d.takes, model: d.model || undefined, max_grid: d.maxGrid || undefined, debug: true }) });
    const bad = (r.calls || []).filter(c => !c.prompt_fits);
    if (bad.length) {
      const c = bad[0];
      d.warn = `⚠ prompt ${c.prompt_chars}/${c.prompt_limit} chars on ${c.model.split('_')[0]} — pick a v4 model`;
    } else {
      d.warn = '';
    }
  } catch { d.warn = ''; }
}
function batchMatrix() {
  const styles = [], icons = [], cells = {};
  for (const tg of Object.keys(S.batchDlg?.sel || {})) {
    const [iid, vid] = tg.split('#');
    const st = S.pack.icons?.[iid]?.variants?.[vid]?.style || '?';
    if (!cells[st]) { cells[st] = {}; styles.push(st); }
    (cells[st][iid] = cells[st][iid] || []).push(tg);
    if (!icons.includes(iid)) icons.push(iid);
  }
  styles.sort(); icons.sort();
  return { styles: styles.map(s => ({ style: s, cells: cells[s] })), icons };
}
function batchRowTargets(row) {
  const out = [];
  for (const list of Object.values(row.cells || {})) out.push(...list);
  return out;
}
function batchRowAll(row) { return batchRowTargets(row).every(tg => S.batchDlg.sel[tg]); }
function batchToggleRow(row) {
  const on = !batchRowAll(row);
  batchRowTargets(row).forEach(tg => { S.batchDlg.sel[tg] = on; });
}
function batchColTargets(ic) {
  const out = [];
  for (const row of batchMatrix().styles) out.push(...((row.cells[ic] || [])));
  return out;
}
function batchColAll(ic) { const t = batchColTargets(ic); return t.length > 0 && t.every(tg => S.batchDlg.sel[tg]); }
function batchToggleCol(ic) {
  const on = !batchColAll(ic);
  batchColTargets(ic).forEach(tg => { S.batchDlg.sel[tg] = on; });
}
function batchSelAll(on) {
  for (const tg of Object.keys(S.batchDlg.sel || {})) S.batchDlg.sel[tg] = on;
}
function batchSelCount() { return Object.values(S.batchDlg?.sel || {}).filter(Boolean).length; }
function batchTotal() { return Object.keys(S.batchDlg?.sel || {}).length; }
function batchSheets() {
  const cap = (S.batchDlg?.maxGrid || 0) >= 2 ? S.batchDlg.maxGrid * S.batchDlg.maxGrid : 25;
  const byStyle = {};
  for (const [tg, on] of Object.entries(S.batchDlg?.sel || {})) {
    if (!on) continue;
    const [iid, vid] = tg.split('#');
    const st = S.pack.icons?.[iid]?.variants?.[vid]?.style || '?';
    byStyle[st] = (byStyle[st] || 0) + 1;
  }
  return Object.values(byStyle).reduce((a, n) => a + Math.ceil(n / cap), 0);
}
async function batchDebug() {
  const d = S.batchDlg;
  if (!d) return;
  try {
    const targets = Object.entries(d.sel).filter(([, on]) => on).map(([tg]) => tg);
    const r = await api('/api/recraft-batch', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targets, takes: d.takes, model: d.model || undefined, debug: true }) });
    d.reqs = r.calls.map(c => 'POST ' + c.endpoint + String.fromCharCode(10) + JSON.stringify(c.request, null, 2)).join(String.fromCharCode(10) + String.fromCharCode(10));
  } catch (e) { d.reqs = 'error: ' + (e.d?.error || e.message); }
}
function batchEst() {
  const d = S.batchDlg; if (!d) return '0.00';
  const byStyle = {};
  for (const [tg, on] of Object.entries(d.sel)) {
    if (!on) continue;
    const [iid, vid] = tg.split('#');
    const st = S.pack.icons?.[iid]?.variants?.[vid]?.style || '?';
    byStyle[st] = (byStyle[st] || 0) + 1;
  }
  let sheets = 0;
  for (const n of Object.values(byStyle)) sheets += Math.ceil(n / 9);
  const price = (S.recraftModels.prices || {})[d.model] || 0.05;
  return (sheets * d.takes * price).toFixed(2);
}
let batchTimer = null;
function batchElapsed() { return S.batchDlg?.t0 ? Math.round((Date.now() - S.batchDlg.t0) / 1000) : 0; }
function batchProgress() {
  const d = S.batchDlg;
  if (!d || !d.est) return 0;
  return Math.min(95, Math.round((batchElapsed() / d.est) * 100));
}
async function batchGenerate() {
  const d = S.batchDlg;
  if (!d || d.busy) return;
  d.busy = true; d.err = '';
  d.t0 = Date.now();
  const sheets = batchSheets();
  d.est = Math.max(10, sheets * 12);  // ~12s per paid image, rough
  d.phase = 'sending ' + sheets + ' sheet request' + (sheets > 1 ? 's' : '') + ' to Recraft';
  batchTimer = setInterval(() => {
    const s = batchElapsed();
    d.phase = s < 3 ? d.phase : s > d.est * 0.6 ? 'splitting sheets into cells' : 'generating sheets at Recraft…';
  }, 1000);
  try {
    const targets = Object.entries(d.sel).filter(([, on]) => on).map(([tg]) => tg);
    const r = await api('/api/recraft-batch', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targets, takes: d.takes, model: d.model || undefined, max_grid: d.maxGrid || undefined }) });
    if (batchTimer) { clearInterval(batchTimer); batchTimer = null; }
    S.batchDlg = null;
    let seq = 0;
    S.resultDlg = {
      batch: true,
      drag: null,
      items: (r.items || []).map(it => ({ ...it, results: (it.results || []).map(x => ({ ...x, keep: true, uid: ++seq })) })),
      takes: r.takes, model: (r.calls || []).map(c => c.model).filter((m, i, a) => a.indexOf(m) === i).join(', '),
      cost: r.cost_usd,
    };
  } catch (e) {
    if (batchTimer) { clearInterval(batchTimer); batchTimer = null; }
    d.busy = false;
    d.err = e.message || e.d?.error || 'Recraft request failed';
  }
}
function dropResult(target) {
  const d = S.resultDlg;
  const drag = d?.drag;
  d.drag = null;
  if (!drag || !target) return;
  if (drag.icon === target.icon && drag.variant === target.variant) return;
  if (drag.variant !== target.variant) {
    flash('cannot move across variants — different style rules apply', false);
    return;
  }
  const src = d.items.find(it => it.icon === drag.icon && it.variant === drag.variant);
  if (!src) return;
  const idx = src.results.findIndex(r => r.uid === drag.uid);
  if (idx < 0) return;
  const [moved] = src.results.splice(idx, 1);
  target.results.push(moved);
  flash('moved take → ' + target.icon + '#' + target.variant, true);
}
function keptCount() {
  const d = S.resultDlg; if (!d) return 0;
  if (d.batch) return d.items.reduce((a, it) => a + it.results.filter(r => r.keep).length, 0);
  return d.results.filter(r => r.keep).length;
}
function totalCount() {
  const d = S.resultDlg; if (!d) return 0;
  if (d.batch) return d.items.reduce((a, it) => a + it.results.length, 0);
  return d.results.length;
}
function keepAll(on) {
  const d = S.resultDlg; if (!d) return;
  if (d.batch) d.items.forEach(it => it.results.forEach(r => { r.keep = on; }));
  else d.results.forEach(r => { r.keep = on; });
}
async function recraftGenerate() {
  const d = S.debugDlg;
  if (!d || d.generating) return;
  d.generating = true;
  try {
    const body = { icon: d.icon, variant: d.variant, n: d.n, model: d.model };
    if (d.grid >= 2) body.grid = d.grid;
    const r = await api('/api/recraft-preview', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body) });
    // show results for review before committing
    S.debugDlg = null;
    S.resultDlg = {
      icon: d.icon, variant: d.variant, model: r.model, grid: r.grid, cost: r.cost_usd,
      results: r.results.map(x => ({ ...x, keep: true })),
    };
  } catch (e) {
    d.generating = false;
    d.error = e.message || 'Recraft request failed';
  }
}
async function commitResults() {
  const d = S.resultDlg;
  if (!d) return;
  if (d.batch) {
    const items = d.items
      .map(it => ({ icon: it.icon, variant: it.variant, svgs: it.results.filter(r => r.keep).map(x => atob(x.svg_data.split(',')[1])) }))
      .filter(it => it.svgs.length);
    if (!items.length) { flash('nothing selected', false); return; }
    try {
      const r = await api('/api/recraft-commit', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items, cost_usd: d.cost }) });
      flash(`⚡ pack: ${r.wrote.length} candidates added across ${items.length} icons (gate ${r.gate_passed}/${r.wrote.length}) ~$${d.cost}`, true);
      S.resultDlg = null;
      await load();
    } catch (e) { flash('commit: ' + (e.d?.error || e.message), false); }
    return;
  }
  const keep = d.results.filter(r => r.keep);
  if (!keep.length) { flash('nothing selected', false); return; }
  try {
    const r = await api('/api/recraft-commit', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        icon: d.icon, variant: d.variant,
        svgs: keep.map(x => atob(x.svg_data.split(',')[1])),
      }) });
    flash(`⚡ ${d.icon}#${d.variant}: ${r.wrote.length} added (gate ${r.gate_passed}/${r.wrote.length}) ~$${d.cost}`, true);
    S.resultDlg = null;
    await load();
  } catch (e) { flash('commit: ' + e.message, false); }
}
async function recraftDraft(icon, variant, n = 4) {
  const key = icon + '/' + variant;
  S.drafting = key;
  try {
    const r = await api('/api/recraft', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon, variant, n }) });
    flash(`⚡ ${key}: ${r.wrote.length} seeds (gate ${r.gate_passed}/${r.wrote.length}) ~$${r.cost_usd}`, true);
    await load();
  } catch (e) { flash('recraft: ' + e.message, false); }
  S.drafting = '';
}

async function recraftIcon(g) {
  const open = variantGroups(g).filter(vg => !isLocked(g.icon, vg.variant));
  if (!open.length) { flash('all variants locked — nothing to draft', false); return; }
  showDebug(g.icon, open[0].variant); return;
  const cost = (open.length * 0.2).toFixed(2);
  if (!confirm(`Draft ${open.length} variant(s) of "${g.icon}" via Recraft? (~$${cost})`)) return;
  for (const vg of open) await recraftDraft(g.icon, vg.variant);
}

function iconSuggest() {
  const q = (S.nextDlg?.newIcon || '').toLowerCase().trim();
  if (!q || q.length < 2) { if (S.nextDlg) S.nextDlg.suggestions = []; return; }
  const existing = Object.keys(S.pack.icons || {}).map(iid => {
    const icon = S.pack.icons[iid];
    const brief = (icon.brief || '').toLowerCase();
    return { key: iid, label: iid + ' — ' + (icon.brief || '').slice(0, 60), brief, isExisting: true };
  });
  const matches = existing.filter(s => s.key.includes(q) || s.brief.includes(q)).slice(0, 5);
  if (S.nextDlg) S.nextDlg.suggestions = matches;
}
function pickSuggestion(s) {
  const d = S.nextDlg;
  if (!d) return;
  if (s.isExisting) {
    const icon = S.pack.icons[s.key];
    for (const [vid, v] of Object.entries(icon.variants || {})) {
      if (v.link || v.postponed) continue;
      const key = s.key + '#' + vid;
      if (!d.cells.includes(key)) {
        d.cells.push(key);
        d.sel[key] = true;
        if (!d.rows.includes(s.key)) d.rows.push(s.key);
        if (!d.cols.includes(vid)) d.cols.push(vid);
      }
    }
    d.newIcon = ''; d.suggestions = [];
    flash(s.key + ' added to focus', true);
  } else {
    d.pending = d.pending || [];
    d.pending.push(s.label);
    d.newIcon = ''; d.suggestions = [];
  }
}
function addNewIcon() {
  const d = S.nextDlg;
  if (!d || !d.newIcon?.trim()) return;
  const raw = d.newIcon.trim();
  const dashIdx = raw.indexOf('—') >= 0 ? raw.indexOf('—') : raw.indexOf('-') >= 2 ? raw.indexOf('-') : -1;
  const name = (dashIdx > 0 ? raw.slice(0, dashIdx) : raw).trim().toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/^-+|-+$/g, '');
  const brief = dashIdx > 0 ? raw.slice(dashIdx + 1).trim() : raw.trim();
  if (!name) return;
  d.pending = d.pending || [];
  d.pending.push(name + (brief && brief !== name ? ' — ' + brief : ''));
  d.newIcon = ''; d.suggestions = [];
}
async function startRoundWithNew() {
  const d = S.nextDlg;
  if (!d) return;
  const created = [];
  for (const entry of d.pending || []) {
    const dashIdx = entry.indexOf(' — ');
    const name = dashIdx > 0 ? entry.slice(0, dashIdx) : entry;
    const brief = dashIdx > 0 ? entry.slice(dashIdx + 3) : name;
    try {
      await api('/api/icon', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ icon: name, brief }) });
      created.push(name);
    } catch (e) { /* may already exist */ }
    for (const sid of usedStyles()) {
      try {
        await api('/api/pack-variant-bulk', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ style: sid }) });
      } catch (e2) {}
    }
  }
  if (created.length) flash(created.length + ' icon(s) created', true);
  await load();
  const sel = Object.entries(S.nextDlg?.sel || {}).filter(([, on]) => on).map(([k]) => k);
  for (const name of created) {
    const icon = S.pack.icons[name];
    if (!icon) continue;
    for (const vid of Object.keys(icon.variants || {})) {
      if (!icon.variants[vid].link) sel.push(name + '#' + vid);
    }
  }
  await startRound(sel);
}
function openVariantsLive() {
  const out = [];
  for (const [iid, icon] of Object.entries(S.pack.icons || {}))
    for (const [vid, v] of Object.entries(icon.variants || {}))
      if (!v.link && !S.locked[iid + '/' + vid] && !v.postponed) out.push({ key: iid + '#' + vid, label: iid + '#' + vid + ' (' + v.style + ')' + (v.postponed ? ' [postponed]' : '') });
  return out;
}
function openNextDlg() {
  const pending = Object.values(S.decisions).some(e => e.items?.length);
  if (pending && !confirm('There are unapplied ratings. Start a new pass anyway? ' + String.fromCharCode(10) + '(The LLM will not see them — apply first if you want them recorded.)')) return;
  const all = openVariantsLive();
  const cells = all.map(v => v.key);
  const prev = new Set(S.lastFocus || []);
  const sel = Object.fromEntries(all.map(v => [v.key, prev.size ? prev.has(v.key) : true]));
  const rows = [...new Set(all.map(v => v.key.split('#')[0]))];
  const cols = [...new Set(all.map(v => v.key.split('#')[1]))];
  S.nextDlg = { sel, cells, rows, cols, newIcon: '', suggestions: [], pending: [] };
  focusDialog();
}
function colState(col) {
  const keys = S.nextDlg.cells.filter(k => k.endsWith('#' + col));
  const on = keys.filter(k => S.nextDlg.sel[k]).length;
  return on === keys.length ? 'all' : on === 0 ? 'none' : 'some';
}
function toggleCol(col) {
  const turnOn = colState(col) !== 'all';
  for (const k of S.nextDlg.cells.filter(k => k.endsWith('#' + col))) S.nextDlg.sel[k] = turnOn;
}
function toggleAll(on) {
  for (const k of S.nextDlg.cells) S.nextDlg.sel[k] = on;
}
async function startRound(only) {
  try {
    const r = await api('/api/round/new', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(only ? { only } : {}) });
    S.decisions = {}; editDirty = false; S.decisionEdit = ''; S.instructions = ''; S.nextDlg = null;
    await load();
    flash(`pass ${r.round} started — ${r.open.length} open${only ? ' (focused)' : ''} (history kept)`, true);
  } catch (e) { flash('round: ' + e.message, false); }
}

function rejectAllIcon(g) {
  if (isViewing()) { flash('viewing history — switch back to the live pass to decide', false); return; }
  if (S.rejectArm !== g.icon) { S.rejectArm = g.icon; flash('click again to reject ALL of ' + g.icon, false); return; }
  S.rejectArm = null;
  for (const vg of variantGroups(g)) {
    S.decisions[g.icon + '/' + vg.variant] = { items: [{ cand: '*', t: '* no' }] };
  }
  syncEdit(); saveDraft();
}
S.lines = computed(() => {
  const out = [];
  for (const [key, entry] of Object.entries(S.decisions)) {
    if (entry.items.length) out.push(key + ': ' + entry.items.map(i => i.t).join(' · '));
  }
  return out;
});
S.decisionText = computed(() => S.lines.join('\\n'));  // S.lines auto-unwraps
S.actionBar = computed(() => {
  if (S.ai.active) return { working: true, ready: false, text: S.ai.text || 'agent working…' };
  if (S.candidates.length) {
    const n = S.lines.length;
    return { working: false, ready: true,
             text: n ? `${n} decision${n > 1 ? 's' : ''} ready — yours to apply`
                     : `your move — rate ${S.candidates.length} candidates` };
  }
  return { working: false, ready: false, text: 'all decided — agent may continue' };
});

function render(p, size, bg, color) {
  const q = new URLSearchParams({ p, size, bg: bg || '#ffffff' });
  if (color && color !== '#000000') q.set('color', color);
  return '/api/render?' + q;
}
function item(c) {
  return (S.decisions[c.icon + '/' + c.variant]?.items || []).find(i => i.cand === c.cand);
}
function hasRating(c) {
  const it = item(c);
  return !!it && (/(^| )rate [0-9]+$/.test(it.t) || it.t.endsWith(' ok'));
}
function rating(c) {
  const it = item(c);
  if (!it) return 0;
  const m = it.t.match(/rate ([0-9]+)/); if (m) return +m[1];
  if (it.t.endsWith(' ok')) return 10;
  return 0;
}
const draftKey = () => `iconpilot.draft.${S.pack.name}.${S.round}`;
function saveDraft() {
  try { localStorage.setItem(draftKey(), JSON.stringify(S.decisions)); } catch {}
}
function restoreDraft() {
  try {
    const raw = localStorage.getItem(draftKey());
    if (raw) S.decisions = JSON.parse(raw) || {};
  } catch {}
}
function healDraft() {
  // self-heal: drop decision entries whose variant is not authored in the
  // pack (orphan run data, removed variants) so stale ratings never block
  const ok = {};
  let dropped = 0;
  for (const [k, v] of Object.entries(S.decisions || {})) {
    const [iid, vid] = k.split('/');
    if (S.pack.icons?.[iid]?.variants?.[vid]?.style) ok[k] = v;
    else dropped++;
  }
  if (dropped) {
    S.decisions = ok;
    if (!editDirty) { S.decisionEdit = S.decisionText; }
    saveDraft();
  }
}
function clearDraft() {
  try { localStorage.removeItem(draftKey()); } catch {}
}
let editDirty = false;
function syncEdit() { if (!editDirty) S.decisionEdit = S.decisionText; }
function setItem(c, t) {
  if (isViewing()) { flash('viewing history — switch back to the live pass to decide', false); return; }
  if (S.appliedRound === S.round) { flash('this pass is applied — start the next one to keep deciding', false); return; }
  const key = c.icon + '/' + c.variant;
  const entry = S.decisions[key] || (S.decisions[key] = { items: [] });
  entry.items = entry.items.filter(i => i.cand !== '*');
  const i = entry.items.findIndex(x => x.cand === c.cand);
  if (i >= 0) entry.items[i] = { cand: c.cand, t };
  else entry.items.push({ cand: c.cand, t });
  syncEdit(); saveDraft();
}
function drop(c)   { setItem(c, c.cand + ' no'); }
function approve(c){ setItem(c, c.cand + ' ok'); }
function keep(c)   { setItem(c, c.cand + ' keep'); }
function rate(c, n){ setItem(c, +n === 0 ? c.cand + ' no' : `${c.cand} rate ${n}`); }
function mainColor(g) { return S.pack.icons?.[g.icon]?.main_color; }
function packBrief(g) {
  const v = S.pack.icons?.[g.icon];
  return v?.variants?.[g.variant]?.brief || v?.brief || '';
}
async function saveBrief(g, brief) {
  S.editingBrief = null;
  if (!brief || brief === packBrief(g)) return;
  try {
    const r = await api('/api/icon', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: g.icon, brief }) });
    S.msg = `brief saved (rev ${r.rev})`; S.msgClass = 'ok'; await load();
  } catch (e) { S.msg = e.d?.errors ? e.d.errors.join('\\n') : e.message; S.msgClass = 'err'; }
}
async function saveMainColor(g, color) {
  try {
    const r = await api('/api/icon', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: g.icon, main_color: color }) });
    S.msg = `main color saved (rev ${r.rev})`; S.msgClass = 'ok'; await load();
  } catch (e) { S.msg = e.message; S.msgClass = 'err'; }
}
function hasNote(g) {
  return fbFor('icon', g.icon).length > 0 || (S.pack.feedback || []).some(i => i.scope === 'variant' && i.icon === g.icon);
}
async function switchStyle(icon, variant, sid) {
  try {
    const r = await api('/api/variant', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon, variant, style: sid }) });
    S.msg = `style → ${sid} (rev ${r.rev})`; S.msgClass = 'ok'; await load();
  } catch (e) { S.msg = e.d?.errors ? e.d.errors.join('\\n') : e.message; S.msgClass = 'err'; }
}
function variantStatus(g) {
  return S.pack.icons?.[g.icon]?.variants?.[g.variant]?.status || '';
}
function chosenCand(g) {
  const v = S.pack.icons?.[g.icon]?.variants?.[g.variant];
  return v?.chosen?.run === S.round ? v.chosen.variant : null;  // the approved pick this round
}
function styleLabel(sid) {
  const s = S.styles[sid];
  return sid + (s ? ` — ${s.label}` : '');
}
function openSheet(c) {
  focusDialog(); S.sheet = { c }; }
function cmpLabel(c) { return (c.round ? c.round + ' ' : '') + c.variant + '/' + c.cand; }
let _lastFocus = null;
function focusDialog() {
  _lastFocus = document.activeElement;
  requestAnimationFrame(() => {
    const dlg = document.querySelector('.overlay:not([style*="none"]) .dialog, .overlay .sheetbox');
    (dlg?.querySelector('textarea, select, input, button') || dlg)?.focus();
  });
}
function restoreFocus() {
  _lastFocus?.focus?.();
  _lastFocus = null;
}
function kbUsedNow() { S.kbUsed = true; }
function kbScroll() {
  requestAnimationFrame(() => {
    document.querySelector('.card.kbactive')?.scrollIntoView({ block: 'nearest' });
  });
}
function toggleCompare(c) {
  if (S.compare && S.compare.length === 1
      && S.compare[0].variant === c.variant && S.compare[0].cand === c.cand) {
    S.compare = null; flash('compare reset', true); return;
  }
  if (!S.compare || S.compare.length >= 2) {
    S.compare = [c];
    flash('compare: picked ' + cmpLabel(c) + ' — pick a second one', true);
  } else {
    S.compare.push(c); focusDialog();
    flash('comparing ' + S.compare.map(cmpLabel).join(' vs '), true);
  }
}
async function loadSettings() {
  focusDialog();
  const sp = S.pack.spec || {};
  S.set = {
    version: S.pack.version || '',
    description: S.pack.description || '',
    note: S.pack.note || '',
    rules: (S.pack.rules || []).join('\\n'),
    strokeWidth: sp.stroke?.width ?? 2,
    linecap: sp.stroke?.linecap || 'round',
    linejoin: sp.stroke?.linejoin || 'round',
    padding: sp.live_area?.padding ?? 2,
    precision: sp.precision ?? 0.5,
    palette: (S.pack.styles?.['lineal-color']?.palette) || null,
    addStyle: 'lineal-color', csId: '', csBase: 'filled', csSize: '', csPalette: '',
    rcModel: '', rcN: 4,
    errors: '',
  };
  S.set.rcModel = S.pack.recraft?.model || 'recraftv2_vector';
  S.set.rcN = S.pack.recraft?.n || 4;
  if (!Object.keys(S.recraftModels).length) {
    try { S.recraftModels = await (await fetch('/api/recraft-models')).json(); } catch {}
  }
}
async function addVariantBulk() {
  try {
    const r = await api('/api/pack-variant-bulk', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: S.set.addStyle }) });
    S.msg = `variant '${S.set.addStyle}' added to ${r.added} glyph(s) (rev ${r.rev})`; S.msgClass = 'ok';
    await load();
  } catch (e) { flash('add variant: ' + (e.d?.error || e.message), false); }
}
async function addCustomStyle() {
  const sdef = { extends: S.set.csBase };
  if (S.set.csSize) sdef.size = +S.set.csSize;
  if (S.set.csPalette) sdef.palette = S.set.csPalette.split(',').map(s => s.trim()).filter(Boolean);
  try {
    await api('/api/pack-style', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: S.set.csId, def: sdef }) });
    await api('/api/pack-variant-bulk', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: S.set.csId }) });
    flash('custom style defined + added to every glyph', true);
    await load();
  } catch (e) { flash('custom style: ' + (e.d?.error || e.message), false); }
}
async function saveSettings() {
  S.set.errors = '';
  if (S.set.rcModel && S.set.rcModel !== (S.pack.recraft?.model || '')) await saveRecraftDefaults(S.set.rcModel, +S.set.rcN || 4);
  try {
    const r = await api('/api/pack', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        version: S.set.version,
        description: S.set.description.trim(),
        note: S.set.note.trim(),
        rules: S.set.rules.split('\\n').map(s => s.trim()).filter(Boolean),
        spec: { stroke: { width: +S.set.strokeWidth, linecap: S.set.linecap, linejoin: S.set.linejoin },
                live_area: { padding: +S.set.padding }, precision: +S.set.precision },
      }) });
    S.msg = `settings saved (rev ${r.rev})`; S.msgClass = 'ok';
    S.settingsDlg = false; await load();
  } catch (e) { S.set.errors = e.d?.errors ? e.d.errors.join('\\n') : e.message; }
}
function markDirty() { editDirty = true; }
function open(c) {
  const main = S.pack.icons?.[c.icon]?.main_color;
  S.dlg = { icon: c.icon, variant: c.variant, cand: c.cand, path: c.path, styleId: c.style,
            bgs2: [
              {name: 'LIGHT BG', hex: '#f6f9f7', iconColor: main || '#1c1c1c'},
              {name: 'DARK BG',  hex: '#22292e', iconColor: '#f2f7f4'},
            ] };
}
function openIcon(id, vid, v) {
  if (v.link) return;
  const icon = S.pack.icons[id];
  S.dlg = { icon: id, variant: vid, cand: null,
            path: 'icons/' + id + '/' + vid + '.svg', styleId: v.style,
            bgs2: [
              {name: 'LIGHT BG', hex: '#f6f9f7', iconColor: icon.main_color || '#1c1c1c'},
              {name: 'DARK BG',  hex: '#22292e', iconColor: '#f2f7f4'},
            ] };
}
function startManual() { S.manual = true; S.manualText = S.decisionText; }
let flashTimer = null;
function flash(text, ok) {
  S.flash = text; S.flashOk = ok;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => { S.flash = ''; }, 5000);
}
async function undo() {
  try {
    const r = await api('/api/undo', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: '{}' });
    flash('undone (rev ' + r.rev + ')', true);
    S.decisions = {}; editDirty = false; S.decisionEdit = ''; S.instructions = '';
    clearDraft(); await load();
  } catch (e) { flash('✗ ' + e.message, false); }
}
async function apply() {
  if (isViewing()) { flash('viewing history — switch back to the live pass', false); return false; }
  const text = S.decisionEdit.trim();
  if (!text || S.applying) return false;
  S.applying = true;
  flash('applying…', true);
  let ok = false;
  try {
    const r = await api('/api/decision', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, round: S.round, instructions: S.instructions.trim() }) });
    S.decisions = {}; editDirty = false; S.decisionEdit = ''; S.instructions = '';
    clearDraft();
    await load();
    S.appliedRound = S.round;
    const approves = (r.log || []).filter(l => l.includes('→ approved')).length;
    flash('✓ applied — ' + (r.log || []).length + ' change(s), ' + approves + ' approved', true);
    ok = true;
  } catch (e) {
    const detail = e.d?.errors ? e.d.errors.join(' · ') : e.message;
    flash('✗ ' + detail.slice(0, 220), false);
    S.msg = detail; S.msgClass = 'err';
  }
  S.applying = false;
  return ok;
}
async function applyAndNext() {
  const ok = await apply();
  if (!ok) return;
  const focus = S.lastFocus && S.lastFocus.length ? S.lastFocus : null;
  await startRound(focus || undefined);
}
function decisionsJson() {
  const icons = {};
  for (const [key, entry] of Object.entries(S.decisions)) {
    if (entry.items.length) {
      icons[key] = { items: entry.items.map(i => {
        const m = i.t.match(/^([^ ]+) (ok|keep|no|rate [0-9]+|more [0-9]+|like [^ ]+ [0-9]+|restart|note)/);
        const o = { t: i.t };
        if (m) { o.cand = m[1]; const rest = m[2];
          if (rest.startsWith('rate')) { o.rate_cand = m[1]; o.rate_n = rest.split(' ')[1]; }
          else if (['ok', 'keep', 'no'].includes(rest)) { o.cand = m[1]; o.action = rest; }
          else if (rest.startsWith('more')) o.more = rest.split(' ')[1];
          else if (rest.startsWith('like')) { o.like_cand = rest.split(' ')[1]; o.like_n = rest.split(' ')[2]; }
          else if (rest === 'restart') o.restart = 'restart';
          else if (rest === 'note') o.note = 'note';
        }
        if (i.cand === '__note') { o.note = 'note'; delete o.cand; }
        return o;
      }) };
    }
  }
  return { pack: S.pack.name, round: S.round, source: 'page', icons,
           decision_text: S.decisionEdit.trim() };
}
async function copy() {
  const payload = JSON.stringify(decisionsJson(), null, 2);
  let ok = false;
  try { await navigator.clipboard.writeText(payload); ok = true; } catch {}
  if (!ok) {  // http:// (non-secure context) fallback
    const ta = document.createElement('textarea');
    ta.value = payload; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { ok = document.execCommand('copy'); } catch {}
    ta.remove();
  }
  S.msg = ok ? 'decisions JSON copied' : 'copy blocked — select the textarea manually';
  S.msgClass = ok ? 'ok' : 'err';
}
async function saveIcon(id, brief) {
  S.editing = null;
  if (!brief || brief === S.pack.icons[id].brief) return;
  try {
    const r = await api('/api/icon', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: id, brief }) });
    S.msg = `saved ${id} (rev ${r.rev})`; S.msgClass = 'ok'; await load();
  } catch (e) { S.msg = e.d?.errors ? e.d.errors.join('\\n') : e.message; S.msgClass = 'err'; }
}
function edited(id, vid) { return false; } // server marks ✎edited via status; page keeps simple

async function load(manual) {
  const runUrl = S.viewRound ? '/api/run?round=' + encodeURIComponent(S.viewRound) : '/api/run';
  const [p, run, styles, ai, hist] = await Promise.all([
    api('/api/pack'), api(runUrl), api('/api/styles'), api('/api/ai-status'), api('/api/history'),
  ]);
  S.pack = p.pack; S.rev = p.rev; S.svgFiles = p.svg_files || {};
  if (Object.keys(S.decisions || {}).length) healDraft();
  S.recraftReady = !!p.recraft_ready;
  if (!S.recraftModels || !S.recraftModels.prices) {
    try { S.recraftModels = await (await fetch('/api/recraft-models')).json(); } catch {}
  }
  S.round = run.round; S.latest = run.latest;
  S.locked = run.locked || {};
  S.candidates = run.candidates.map(c => ({
    ...c,
    path: `.runs/${run.round}/${c.variant}/${c.icon}/${c.cand}.svg`,
    style: p.pack.icons?.[c.icon]?.variants?.[c.variant]?.style,
  }));
  S.styles = styles;
  try { S.styleRefs = await api('/api/style-refs'); } catch { S.styleRefs = {}; }
  S.ai = { text: ai.status || '', active: !!ai.active };
  setFavicon(ai.phase || 'idle');
  S.version = p.version || '';
  S.history = hist.rounds || [];
  S.rounds = (S.history || []).map(h => h.round).reverse();  // newest first — after history lands
  restoreDraft();  // bring back in-progress ratings after a reload
}

const App = {
  setup() {
    onMounted(() => {
      document.getElementById('app').style.visibility = 'visible';
      document.getElementById('loader')?.remove();
      initTheme();
      if (S.tab === 'settings') loadSettings();
      load().catch(e => { S.msg = e.message; S.msgClass = 'err'; });
      setInterval(async () => {
        try {
          const [p, ai] = await Promise.all([api('/api/pack'), api('/api/ai-status')]);
          if (p.rev !== S.rev || (ai.status || '') !== S.ai.text) await load();
        } catch {}
      }, 2000);
    });

    // keyboard shortcuts
    const onKey = (e) => {
      if (S.dlg || S.sheet || S.fbDlg || S.compare) {
        if (e.key === 'Escape') { S.dlg = null; S.sheet = null; S.fbDlg = null; S.compare = null; restoreFocus(); }
        return;
      }
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
      const groups = S.grouped;
      if (!groups.length) return;
      const gi = S.kbFocus ?? 0;
      const g = groups[gi];
      if (!g) return;
      const vgs = variantGroups(g);
      if (!vgs.length) return;
      const vi = S.kbVariant ?? 0;
      const vg = vgs[vi];
      if (!vg || !vg.cands.length) return;
      const ci = S.kbCand ?? 0;
      const c = vg.cands[Math.min(ci, vg.cands.length - 1)];
      if (e.key === '1') { approve(c); e.preventDefault(); }
      else if (e.key === '2') { drop(c); e.preventDefault(); }
      else if (e.key === '0') { openSheet(c); e.preventDefault(); }
      else if (e.key === '3') { drop(c); e.preventDefault(); }
      else if (e.key === '[') { kbUsedNow(); S.kbFocus = Math.max(0, gi - 1); S.kbVariant = 0; S.kbCand = 0; e.preventDefault(); kbScroll(); }
      else if (e.key === ']') { kbUsedNow(); S.kbFocus = Math.min(groups.length - 1, gi + 1); S.kbVariant = 0; S.kbCand = 0; e.preventDefault(); kbScroll(); }
      else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        const next = ci + 1;
        if (next < vg.cands.length) S.kbCand = next;
        else if (vi + 1 < vgs.length) { S.kbVariant = vi + 1; S.kbCand = 0; }
        else if (gi + 1 < groups.length) { S.kbFocus = gi + 1; S.kbVariant = 0; S.kbCand = 0; }
        kbScroll();
        e.preventDefault();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        const prev = ci - 1;
        if (prev >= 0) S.kbCand = prev;
        else if (vi - 1 >= 0) { S.kbVariant = vi - 1; S.kbCand = (vgs[vi-1]?.cands.length || 1) - 1; }
        else if (gi - 1 >= 0) { S.kbFocus = gi - 1; S.kbVariant = vgs.length - 1; S.kbCand = 0; }
        kbScroll();
        e.preventDefault();
      } else if (e.key === 'Enter') {
        if (S.decisionEdit.trim()) apply();
        e.preventDefault();
      }
    };
    window.addEventListener('keydown', onKey);
  window.addEventListener('click', () => { if (S.aistatOpen) S.aistatOpen = false; });

    return {
      S, render, item, rating, drop, approve, keep, rate,
      styleLabel, open, openIcon, openSheet, switchStyle, startManual,
      apply, copy, saveIcon, edited, load, chosenCand, variantStatus,
      mainColor, packBrief, saveBrief, saveMainColor, hasNote,
      saveSettings, loadSettings, markDirty,
      variantGroups, packBriefIcon, mainColorIcon, saveMainColorIcon, rejectAllIcon,
       copyPath, togglePin, isPinned, undo,
      batchApprove, batchReject, toggleCompare,
      isLocked, recraftDraft, recraftIcon, startRound, totalCost,
      fbFor, fbNew, fbTitle, fbItems, fbChat, openFb, addFeedback, resolveFeedback, switchRound, isViewing,
      IC, relTime, isNew, copyPrompt, reopen, toggleTheme, cmpLabel, initTheme, loadIconHist, hasRating,
      showDebug, debugCopy, openNextDlg, addVariantBulk, addCustomStyle, saveRecraftDefaults,
      GATE_HELP, styleRules, stylePalette, ruleTitle, styleUsageCount, isPostponed, togglePostpone, applyAndNext, colState, toggleCol, toggleAll, usedStyles, setTab, iconSuggest, pickSuggestion, addNewIcon, startRoundWithNew,
      styleSummary, isOwnRef, editStyle, toggleGate, saveStyleRules, removeStyle, addStyleToPack, pickRefFile, removeRef,
      vectorModels, curatedNames, styleDetail, editCustomStyle, recraftGenerate, commitResults, iconStylePalette, toggleIconColor, waitingForAgent, waitTargets, adoptPreview, adoptCommit, openRefineDlg, refineMatrix, refineRowAll, refineToggleRow, refineColAll, refineToggleCol, refineSetAll, refineActive, refineReady, refineEst, refineGenerate, openStyleRc, styleRcCreate, styleRcSave, openBatchDlg, batchMatrix, batchRowTargets, batchRowAll, batchToggleRow, batchColAll, batchToggleCol, batchSelAll, batchSelCount, batchTotal, batchSheets, batchDebug, batchEst, batchGenerate, batchElapsed, batchProgress, planCheck, dropResult, keptCount, totalCount, keepAll,

    };
  },
};
window.__ip = S;  // console/debug access to the page state
createApp(App).mount('#app');
</script>
</body></html>
"""
