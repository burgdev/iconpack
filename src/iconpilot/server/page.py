"""Review page — Vue 3 (vendored ESM, no build step), responsive, interactive."""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iconpilot review</title>
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
input, select, textarea {
  font: inherit; color: var(--ink); background: var(--card);
  border: 1px solid var(--line); border-radius: 8px;
  padding: 6px 10px; min-height: 32px;
}
select { cursor: pointer; }
input[type="color"] { min-height: 28px; padding: 0 2px; }
input[type="range"] { min-height: 0; padding: 0; }
:is(button, input, select, textarea, summary):focus-visible {
  outline: 2px solid var(--focus); outline-offset: 1px;
}
button { transition: border-color .12s ease-out, background-color .12s ease-out, color .12s ease-out; }
button:disabled { opacity:.45; cursor:not-allowed; }
.ab-apply:disabled { background:var(--card); color:var(--muted); border-color:var(--line); }
body { margin:0; font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
       background:var(--bg); color:var(--ink); }
header { position:sticky; top:0; z-index:10; background:var(--card); border-bottom:1px solid var(--line);
         padding:10px 16px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; box-shadow:var(--shadow); }
header h1 { font-size:1rem; margin:0; font-weight:650; }
header .meta { color:var(--muted); font-size:.8rem; }
.spacer { flex:1; }
.banner { width:100%; padding:6px 12px; border-radius:8px; font-size:.85rem; display:flex; gap:8px; align-items:center; }
.ic { display:inline-flex; vertical-align:-2px; }
.ic svg { width:14px; height:14px; }
.ic-lg svg { width:18px; height:18px; vertical-align:-4px; }
.dotnew { width:7px; height:7px; border-radius:50%; background:var(--warn); display:inline-block; margin-left:2px; }
.chip.new { background:var(--warn); color:var(--bg); font-size:.65rem; padding:1px 6px; font-weight:600; }
.chat { max-height:280px; overflow-y:auto; border:1px solid var(--line); border-radius:8px; padding:8px; margin-bottom:10px; background:color-mix(in srgb, var(--bg) 60%, transparent); }
.chat-head { font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:8px 0 4px; }
.chat-head:first-child { margin-top:0; }
.bubble { display:flex; align-items:baseline; gap:6px; padding:3px 0; }
.msg.agent .bubble-text { color:var(--warn); }
.bubble-text { flex:1; }
.bubble-time { font-size:.7rem; }
.scope { font-size:.75rem; }
.chip.agent { background:color-mix(in srgb, var(--warn) 18%, transparent); }
.chip.user { background:color-mix(in srgb, var(--line) 40%, transparent); }
.chip.done { background:color-mix(in srgb, var(--accent) 18%, transparent); }
.iconbtn.busy, button.busy { opacity:.45; pointer-events:none; }
.banner.working { background:color-mix(in srgb, var(--warn) 15%, transparent); color:var(--warn); }
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
button { font:inherit; padding:6px 12px; border-radius:8px; border:1px solid var(--line);
         background:var(--card); color:var(--ink); cursor:pointer; }
button:hover { border-color:var(--accent); }
button.primary { background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }
button.subtle { font-size:.8rem; padding:4px 8px; color:var(--muted); }
button.armed { border-color:var(--accent); color:var(--accent); font-weight:600; }
button.armed-x { border-color:var(--warn); color:var(--warn); font-weight:600; }
.chip { display:inline-block; padding:1px 8px; border-radius:99px; font-size:.72rem; background:var(--chip); color:var(--muted); }
.chip.approved { background:var(--accent); color:var(--accent-ink); }
.chip.in_review, .chip.stale { background:var(--warn); color:var(--bg); }
textarea { font:13px/1.5 ui-monospace,Menlo,Consolas,monospace; width:100%; min-height:64px; padding:8px;
           border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--ink); resize:vertical; }
textarea[readonly] { color:var(--muted); }
.composer { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; margin:14px 0; }
.composer .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-top:8px; }
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
.matrix .colhead { font-size:.72rem; letter-spacing:.08em; color:var(--muted); margin-bottom:4px; }
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
.colorchip { width:30px; height:30px; flex:none; border-radius:99px; border:2px solid var(--line); cursor:pointer; }
.gmeta select { font:inherit; font-size:.8rem; padding:4px 6px; border-radius:8px;
                border:1px solid var(--line); background:var(--card); color:var(--ink); max-width:140px; }
.vargrid { display:flex; flex-direction:column; gap:10px; }
.vargroup { border:1px solid var(--line); background: color-mix(in oklab, var(--card-2) 55%, var(--card));
            border-radius:10px; padding:8px 10px; }
.varhead { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.compare-grid { display:flex; gap:16px; }
.compare-col { flex:1; text-align:center; }
.compare-label { font-weight:600; margin-bottom:8px; }
.compare-sizes { display:flex; justify-content:center; gap:12px; align-items:flex-end; margin-top:8px; }
.card.kbactive { outline: 3px solid var(--accent); outline-offset: 2px; }
.iconbtn-lg { padding:6px 9px; display:inline-flex; align-items:center; }
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
.histcell figcaption { font-size:.68rem; }
.thumb.missing { width:64px; height:64px; display:flex; align-items:center; justify-content:center;
                 color:var(--muted); border:1px dashed var(--line); border-radius:8px; }
.iconbtn { padding:3px 7px; font-size:.85rem; border:none; background:none; cursor:pointer;
             color:var(--muted); border-radius:6px; }
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
<div id="app">
  <header>
    <h1>{{ S.pack.name || 'iconpilot' }}</h1>
    <span class="meta">rev {{ S.rev }} · S.round {{ S.round || '—' }}</span>
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
    <button class="subtle" @click="openNextDlg()"
            title="apply first, then start the next pass — history is kept">
      <span class="ic" v-html="IC.plus"></span> next round</button>
    <span class="spacer"></span>
    <span class="meta">{{ S.candidates.length }} candidates</span>
    <button class="subtle" @click="openSettings" title="settings" aria-label="settings"><span class="ic" v-html="IC.gear"></span></button>
    <button class="subtle" @click="load(true)">refresh</button>
    <div v-if="S.ai.text" class="banner" :class="S.ai.active ? 'working' : 'ready'">
      <span class="dot"></span>{{ S.ai.text }}
    </div>
  </header>

  <main>
    <div v-if="S.msg" :class="S.msgClass">{{ S.msg }}</div>

    <section v-if="S.viewRound && S.viewRound !== S.latest">
      <div class="banner working" style="margin:8px 0">
        viewing {{ S.viewRound }} (history — read only). <button class="subtle" @click="switchRound(S.latest)">back to {{ S.latest }}</button>
      </div>
    </section>
    <section v-if="S.grouped.length">
      <h2>{{ S.viewRound && S.viewRound !== S.latest ? 'Archived pass ' + S.viewRound : 'Current pass — rate, then decide' }}</h2>
      <div class="group" v-for="(g, gi) in S.grouped" :key="g.key">
        <div class="ghead">
          <b>{{ g.icon }}</b>
          <span class="muted">{{ g.cands.length }} candidates across variants</span>
          <span class="spacer"></span>
          <button v-if="S.recraftReady || S.debug" class="subtle" :class="{ busy: S.drafting.startsWith(g.icon + '/') }"
                  title="Recraft: seed 4 drafts for every open variant of this icon"
                  @click="recraftIcon(g)"><span class="ic" v-html="IC.bolt"></span> draft</button>
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
              <select :value="vg.style" @change="switchStyle(g.icon, vg.variant, $event.target.value)" class="varstyle" title="style">
                <option v-for="(st, sid) in S.styles" :key="sid" :value="sid">{{ sid }}</option>
              </select>
              <button class="iconbtn" :class="{ on: fbFor('variant', g.icon, vg.variant).length }"
                      title="feedback for this variant" aria-label="feedback for this variant" @click="openFb('variant', g.icon, vg.variant)">
                <span class="ic" v-html="IC.comment"></span><span v-if="fbNew('variant', g.icon, vg.variant)" class="dotnew"></span>
              </button>
              <button class="iconbtn" title="copy a complete LLM hint for this variant — paste into any model, bring SVGs back"
                      @click="copyPrompt(g.icon, vg.variant)"><span class="ic" v-html="IC.copy"></span></button>
              <button v-if="S.recraftReady || S.debug" class="iconbtn" :class="{ on: S.drafting === g.icon + '/' + vg.variant }"
                      :title="S.debug && !S.recraftReady ? 'preview the Recraft request (no call)' : 'Recraft: seed 4 drafts for this variant (~$0.18-0.20)'" aria-label="Recraft draft"
                      @click="S.debug && !S.recraftReady ? showDebug(g.icon, vg.variant) : recraftDraft(g.icon, vg.variant)"><span class="ic" v-html="IC.bolt"></span></button>
            </div>
            <div v-if="!vg.cands.length" class="card empty" style="border-style:dashed">
              <span class="muted">open — no drafts yet</span>
              <button v-if="S.recraftReady || S.debug" class="subtle" @click="S.debug && !S.recraftReady ? showDebug(g.icon, vg.variant) : recraftDraft(g.icon, vg.variant)"><span class="ic" v-html="IC.bolt"></span> seed</button>
              <button class="subtle" @click="copyPrompt(g.icon, vg.variant)"><span class="ic" v-html="IC.spark"></span> LLM hint</button>
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
      <p class="muted">no candidates in the latest run — the status above shows agent progress.</p>
    </section>

    <div class="composer">
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
          <span class="muted">keys: ←→ move · [ ] group · 1 ok · 2 drop · 0 rate · esc close</span>
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

    <section>
      <h2>Icons</h2>
      <div class="group" v-for="(icon, id) in S.pack.icons" :key="id">
        <div class="ghead">
          <b>{{ id }}</b>
          <span v-if="icon.main_color" class="chip" :style="{background: icon.main_color}">{{ icon.main_color }}</span>
          <div v-if="S.editing === id" style="display:flex; gap:6px; flex:1">
            <input style="flex:1; min-width:100px" :value="icon.brief"
                   placeholder="brief — what to draw (agent instruction)"
                   @keydown.enter="saveIcon(id, $event.target.value)" @blur="saveIcon(id, $event.target.value)">
            <input style="flex:1; min-width:100px" :value="icon.description"
                   placeholder="description — durable docs for humans"
                   @keydown.enter="saveIconDesc(id, $event.target.value)" @blur="saveIconDesc(id, $event.target.value)">
          </div>
          <span v-else class="muted" style="flex:1; cursor:text" @click="S.editing = id">{{ icon.brief }}</span>
          <button class="subtle" @click="S.editing = S.editing === id ? null : id">edit</button>
        </div>
        <div class="grid">
          <div class="card" v-for="(v, vid) in icon.variants" :key="vid">
            <img v-if="!v.link && S.svgFiles[id + '/' + vid]" class="thumb" loading="lazy" width="64" height="64"
                 :src="render('icons/' + id + '/' + vid + '.svg', 64, '#ffffff')"
                 @click="openIcon(id, vid, v)">
            <div v-else-if="!v.link" class="thumb missing" title="not drafted yet">—</div>
            <div class="name">{{ vid }}</div>
            <span class="chip" :class="v.status">{{ v.link ? '→ ' + v.link : v.status }}</span>
            <button v-if="v.status === 'approved' && !v.link" class="iconbtn"
                    :class="{ on: isPinned(id, vid) }" :title="isPinned(id, vid) ? 'unpin' : 'pin as style reference'"
                    @click="togglePin(id, vid)"><span class="ic" :class="{ filled: isPinned(id, vid) }" v-html="IC.pin"></span></button>
            <span v-if="v.status === 'stale' || edited(id, vid)" class="muted">needs re-review</span>
          </div>
        </div>
      </div>
    </section>
    <footer>iconpilot review v{{ S.version }} · flock-serialized writes · approval is always yours</footer>
  </main>

  <div class="actionbar" :class="{ ready: S.actionBar.ready }">
    <span class="ab-status" :class="{ 'flash-ok': S.flash && S.flashOk, 'flash-err': S.flash && !S.flashOk }">
      <template v-if="S.flash">{{ S.flash }}</template>
      <template v-else>
        <span v-if="S.actionBar.working" class="dot amber"></span>
        <span v-else-if="S.actionBar.ready" class="dot green"></span>
        <span v-else class="dot gray"></span>
        {{ S.actionBar.text }}
      </template>
    </span>
    <button class="subtle" @click="undo" title="undo last apply" aria-label="undo"><span class="ic" v-html="IC.undo"></span></button>
    <button class="primary ab-apply" @click="apply"
            :disabled="!S.decisionEdit.trim() || S.applying">
      {{ S.applying ? '…' : 'Apply' + (S.lines.length ? ' · ' + S.lines.length : '') }}</button>
  </div>

  <div v-if="S.settingsDlg" class="overlay" @click.self="S.settingsDlg = false">
    <div class="dialog">
      <h3><span><span class="ic-lg" v-html="IC.gear"></span> {{ S.pack.name }} settings</span>
          <button class="subtle" @click="S.settingsDlg = false">✕</button></h3>
      <div class="controls"><label>version</label>
        <input v-model="S.set.version" style="width:110px"></div>
      <div class="controls" style="align-items:flex-start"><label>description</label>
        <textarea v-model="S.set.description" placeholder="durable docs: what this collection is for — shown to humans, exports, READMEs"></textarea></div>
      <div class="controls" style="align-items:flex-start"><label>global note</label>
        <textarea v-model="S.set.note" placeholder="FEEDBACK to the agent, every draft — e.g. 'no chimneys anywhere'. Clear when resolved."></textarea></div>
      <div class="controls" style="align-items:flex-start"><label>rules</label>
        <textarea v-model="S.set.rules" placeholder="one rule per line — injected into every drafting context"></textarea></div>
      <div class="controls" style="align-items:flex-start"><label>add variant</label>
        <div class="row">
          <select v-model="S.set.addStyle"><option v-for="(st, sid) in S.styles" :key="sid" :value="sid">{{ sid }}</option></select>
          <button class="subtle" @click="addVariantBulk">add to every glyph</button>
        </div></div>
      <div class="controls" style="align-items:flex-start"><label>custom style</label>
        <div class="row" style="flex-direction:column; align-items:stretch; gap:4px">
          <div class="row"><input v-model="S.set.csId" placeholder="style id (e.g. outline-color)" style="flex:1">
          <select v-model="S.set.csBase"><option v-for="(st, sid) in S.styles" :key="sid" :value="sid">extends {{ sid }}</option></select></div>
          <div class="row"><input v-model="S.set.csSize" type="number" placeholder="grid px (blank = inherit)" style="width:130px">
          <input v-model="S.set.csPalette" placeholder="palette hex csv (optional)" style="flex:1"></div>
          <button class="subtle" @click="addCustomStyle">define + add to every glyph</button>
        </div></div>
      <div class="controls"><label>Recraft</label>
        <div class="row">
          <select v-model="S.set.rcModel"><option v-for="(pr, m) in S.recraftModels" :key="m" :value="m">{{ m }} (${{ pr }}/img)</option></select>
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
  </div>

  <div v-if="S.fbDlg" class="overlay" @click.self="S.fbDlg = null">
    <div class="dialog">
      <h3><span><span class="ic-lg" v-html="IC.comment"></span> {{ fbTitle() }}</span>
          <button class="subtle" @click="S.fbDlg = null">✕</button></h3>
      <p class="muted" style="margin:0 0 8px">Per-round feedback — guides the next draft, then dies with its round (history keeps it). Generally valid? The agent promotes it into the standing note via CLI.</p>
      <div class="chat">
        <template v-for="r in fbChat()" :key="r.round + (r.archived ? '-a' : '-l')">
          <div class="chat-head">{{ r.round }}{{ r.archived ? ' · archived' : ' · live' }}</div>
          <div v-for="i in r.items" :key="r.round + i.id" class="bubble" :class="i.author">
            <span class="chip" :class="i.author">{{ i.author }}</span>
            <span class="bubble-text">{{ i.text }}</span>
            <span class="muted bubble-time">{{ relTime(i.created) }}</span>
            <span v-if="isNew(i)" class="chip new">new</span>
            <button v-if="!r.archived" class="subtle armed-x" title="resolve (done / addressed)" @click="resolveFeedback(i)">✕</button>
          </div>
        </template>
        <p v-if="!fbChat().length" class="muted">no comments yet for this scope</p>
      </div>
      <textarea v-model="S.fbDlg.text" placeholder="what to change in the next draft — e.g. 'thinner roof, door on the right'"></textarea>
      <div class="row" style="margin-top:8px">
        <button class="primary" @click="addFeedback">Add</button>
        <button class="subtle" @click="S.fbDlg = null" aria-label="Close">✕</button>
      </div>
    </div>
  </div>

  <div v-if="S.nextDlg" class="overlay" @click.self="S.nextDlg = null">
    <div class="dialog">
      <h3><span>Focus for the next pass</span><button class="subtle" @click="S.nextDlg = null" aria-label="Close">✕</button></h3>
      <p class="muted" style="margin:0 0 8px">Pick what to draft next — e.g. color first, mono later. Everything stays open; this only sets the focus.</p>
      <div style="max-height:300px; overflow-y:auto">
        <label v-for="v in S.nextDlg.all" :key="v.key" style="display:flex; gap:8px; align-items:center; padding:3px 0">
          <input type="checkbox" v-model="S.nextDlg.sel[v.key]"> {{ v.label }}
        </label>
      </div>
      <div class="row" style="margin-top:10px">
        <button class="primary" @click="startRound(Object.entries(S.nextDlg.sel).filter(([,on]) => on).map(([k]) => k))">start pass</button>
        <button class="subtle" @click="startRound()">all open</button>
        <button class="subtle" @click="S.nextDlg = null" aria-label="Close">✕</button>
      </div>
    </div>
  </div>

  <div v-if="S.debugDlg" class="overlay" @click.self="S.debugDlg = null">
    <div class="dialog">
      <h3><span><span class="ic-lg" v-html="IC.bolt"></span> Recraft request · {{ S.debugDlg.icon }}#{{ S.debugDlg.variant }} (≈ ${{ S.debugDlg.cost }})</span>
          <button class="subtle" @click="S.debugDlg = null" aria-label="Close">✕</button></h3>
      <p class="muted" style="margin:0 0 8px">{{ S.debugDlg.endpoint }}</p>
      <textarea :value="S.debugDlg.request" readonly rows="8"></textarea>
      <div class="row" style="margin-top:8px">
        <button class="primary" @click="copyText(S.debugDlg.request, 'request JSON copied')">copy request JSON</button>
        <button class="subtle" @click="copyText(S.debugDlg.full, 'full hint copied')">copy full hint</button>
        <button class="subtle" @click="S.debugDlg = null" aria-label="Close">✕</button>
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
          <button class="subtle" @click="S.dlg = null">close ✕</button></h3>
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
  kbFocus: 0, kbVariant: 0, kbCand: 0, kbUsed: false, compare: null, histView: null,
  recraftReady: false, debug: new URLSearchParams(location.search).has('debug'), debugDlg: null, nextDlg: null,
  recraftModels: {}, theme: 'light', iconHist: {}, svgFiles: {}, rejectArm: null,
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
  bolt: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>',
  undo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-15-6.7L3 13"/></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1z"/></svg>',
  unlock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"/></svg>',
  history: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>',
  spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6l1.4 1.4m10 10 1.4 1.4m0-12.8-1.4 1.4m-10 10-1.4 1.4"/><path d="M12 8.5 13.5 12 12 15.5 10.5 12z"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
};
function relTime(iso) {
  if (!iso) return '';
  const s = Math.max(0, (Date.now() - new Date(iso + 'Z').getTime()) / 1000);
  if (s < 60) return 'now';
  if (s < 3600) return Math.floor(s / 60) + 'm';
  if (s < 86400) return Math.floor(s / 3600) + 'h';
  return Math.floor(s / 86400) + 'd';
}
function seenKey() { return 'iconpilot.seen.' + (S.pack.name || ''); }
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
    d.text = ''; await load();
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
function isViewing() { return !!(S.viewRound && S.viewRound !== S.latest); }
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
  S.decisions = {}; editDirty = false; S.decisionEdit = ''; S.instructions = ''; S.compare = null;
  await load();
}
function totalCost() { return S.history.reduce((a, h) => a + (h.cost_usd || 0), 0); }

async function showDebug(icon, variant) {
  try {
    const r = await api('/api/recraft-request?icon=' + encodeURIComponent(icon) + '&variant=' + encodeURIComponent(variant));
    r.request.prompt = r.request.prompt.slice(0, 160) + '… (full hint below)';
    S.debugDlg = { icon, variant, endpoint: r.endpoint, request: JSON.stringify(r.request, null, 2), full: r.full_prompt, cost: r.est_cost_usd };
    focusDialog();
  } catch (e) { flash('preview: ' + e.message, false); }
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
  if (S.debug && !S.recraftReady) { showDebug(g.icon, open[0].variant); return; }
  const cost = (open.length * 0.2).toFixed(2);
  if (!confirm(`Draft ${open.length} variant(s) of "${g.icon}" via Recraft? (~$${cost})`)) return;
  for (const vg of open) await recraftDraft(g.icon, vg.variant);
}

function openVariantsLive() {
  const out = [];
  for (const [iid, icon] of Object.entries(S.pack.icons || {}))
    for (const [vid, v] of Object.entries(icon.variants || {}))
      if (!v.link && !S.locked[iid + '/' + vid]) out.push({ key: iid + '#' + vid, label: iid + '#' + vid + ' (' + v.style + ')' });
  return out;
}
function openNextDlg() {
  const pending = Object.values(S.decisions).some(e => e.items?.length);
  if (pending && !confirm('There are unapplied ratings. Start a new pass anyway? ' + String.fromCharCode(10) + '(The LLM will not see them — apply first if you want them recorded.)')) return;
  S.nextDlg = { sel: {}, all: openVariantsLive() };
  S.nextDlg.sel = Object.fromEntries(S.nextDlg.all.map(v => [v.key, true]));
  focusDialog();
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
function clearDraft() {
  try { localStorage.removeItem(draftKey()); } catch {}
}
let editDirty = false;
function syncEdit() { if (!editDirty) S.decisionEdit = S.decisionText; }
function setItem(c, t) {
  if (isViewing()) { flash('viewing history — switch back to the live pass to decide', false); return; }
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
async function saveIconDesc(id, desc) {
  const cur = S.pack.icons?.[id]?.description || '';
  if (desc === cur) return;
  try {
    const r = await api('/api/icon', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: id, description: desc }) });
    S.msg = `description saved (rev ${r.rev})`; S.msgClass = 'ok'; await load();
  } catch (e) { S.msg = e.message; S.msgClass = 'err'; }
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
async function openSettings() {
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
  S.settingsDlg = true;
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
  if (isViewing()) { flash('viewing history — switch back to the live pass', false); return; }
  const text = S.decisionEdit.trim();
  if (!text || S.applying) return;
  S.applying = true;
  flash('applying…', true);
  try {
    const r = await api('/api/decision', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, round: S.round, instructions: S.instructions.trim() }) });
    S.decisions = {}; editDirty = false; S.decisionEdit = ''; S.instructions = '';
    clearDraft();
    await load();
    flash('✓ applied ' + (r.log || []).length + ' change(s)', true);
    S.msg = 'applied: ' + (r.log || []).join(' | '); S.msgClass = 'ok';
  } catch (e) {
    const detail = e.d?.errors ? e.d.errors.join(' · ') : e.message;
    flash('✗ ' + detail.slice(0, 90), false);
    S.msg = detail; S.msgClass = 'err';
  }
  S.applying = false;
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
  S.recraftReady = !!p.recraft_ready;
  S.round = run.round; S.latest = run.latest;
  S.locked = run.locked || {};
  S.rounds = (S.history || []).map(h => h.round).reverse();  // newest first
  S.candidates = run.candidates.map(c => ({
    ...c,
    path: `.runs/${run.round}/${c.variant}/${c.icon}/${c.cand}.svg`,
    style: p.pack.icons?.[c.icon]?.variants?.[c.variant]?.style,
  }));
  S.styles = styles;
  S.ai = { text: ai.status || '', active: !!ai.active };
  S.version = p.version || '';
  S.history = hist.rounds || [];
  restoreDraft();  // bring back in-progress ratings after a reload
}

const App = {
  setup() {
    onMounted(() => {
      initTheme();
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
      if (S.dlg || S.sheet || S.fbDlg || S.settingsDlg || S.compare) {
        if (e.key === 'Escape') { S.dlg = null; S.sheet = null; S.fbDlg = null; S.settingsDlg = false; S.compare = null; restoreFocus(); }
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

    return {
      S, render, item, rating, drop, approve, keep, rate,
      styleLabel, open, openIcon, openSheet, switchStyle, startManual,
      apply, copy, saveIcon, edited, load, chosenCand, variantStatus,
      mainColor, packBrief, saveBrief, saveMainColor, hasNote,
      openSettings, saveSettings, markDirty,
      variantGroups, packBriefIcon, mainColorIcon, saveMainColorIcon, rejectAllIcon,
       copyPath, togglePin, isPinned, undo,
      batchApprove, batchReject, toggleCompare,
      isLocked, recraftDraft, recraftIcon, startRound, saveIconDesc, totalCost,
      fbFor, fbNew, fbTitle, fbItems, fbChat, openFb, addFeedback, resolveFeedback, switchRound, isViewing,
      IC, relTime, isNew, copyPrompt, reopen, toggleTheme, cmpLabel, initTheme, loadIconHist, hasRating,
      showDebug, openNextDlg, addVariantBulk, addCustomStyle, saveRecraftDefaults,

    };
  },
};
createApp(App).mount('#app');
</script>
</body></html>
"""
