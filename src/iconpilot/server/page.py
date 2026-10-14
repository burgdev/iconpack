"""Review page — Vue 3 (vendored ESM, no build step), responsive, interactive."""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iconpilot review</title>
<style>
:root {
  --bg: #f6f7f9; --card: #ffffff; --ink: #17202a; --muted: #66707a;
  --line: #dfe3e8; --accent: #2e7d32; --accent-ink: #ffffff;
  --warn: #b07d2e; --danger: #c62828; --chip: #eceff3; --shadow: 0 1px 3px rgba(20,30,40,.08);
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#12161b; --card:#1a2027; --ink:#e8ecf0; --muted:#8b95a0; --line:#2a323c;
          --chip:#242c35; --shadow:0 1px 3px rgba(0,0,0,.4); }
}
* { box-sizing: border-box; }
body { margin:0; font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
       background:var(--bg); color:var(--ink); }
header { position:sticky; top:0; z-index:10; background:var(--card); border-bottom:1px solid var(--line);
         padding:10px 16px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; box-shadow:var(--shadow); }
header h1 { font-size:1rem; margin:0; font-weight:650; }
header .meta { color:var(--muted); font-size:.8rem; }
.spacer { flex:1; }
.banner { width:100%; padding:6px 12px; border-radius:8px; font-size:.85rem; display:flex; gap:8px; align-items:center; }
.banner.working { background:color-mix(in srgb, var(--warn) 15%, transparent); color:var(--warn); }
.banner.ready  { background:color-mix(in srgb, var(--accent) 14%, transparent); color:var(--accent); }
.dot { width:8px; height:8px; border-radius:50%; background:currentColor; animation:pulse 1.6s infinite; }
.banner.ready .dot { animation:none; }
@keyframes pulse { 50% { opacity:.3; } }
main { max-width:1200px; margin:0 auto; padding:16px; }
section h2 { font-size:.85rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:22px 0 10px; }
.group { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; margin:10px 0; box-shadow:var(--shadow); }
.group > .ghead { display:flex; align-items:center; gap:10px; margin-bottom:8px; flex-wrap:wrap; }
.group b { font-size:.95rem; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:12px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px; text-align:center;
        box-shadow:var(--shadow); display:flex; flex-direction:column; gap:8px; }
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
button.armed-x { border-color:var(--danger); color:var(--danger); font-weight:600; }
.chip { display:inline-block; padding:1px 8px; border-radius:99px; font-size:.72rem; background:var(--chip); color:var(--muted); }
.chip.approved { background:var(--accent); color:var(--accent-ink); }
.chip.in_review, .chip.stale { background:var(--warn); color:#fff; }
textarea { font:13px/1.5 ui-monospace,Menlo,Consolas,monospace; width:100%; min-height:64px; padding:8px;
           border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--ink); resize:vertical; }
textarea[readonly] { color:var(--muted); }
.composer { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; margin:14px 0; }
.composer .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-top:8px; }
.err { color:var(--danger); font-size:.85rem; white-space:pre-wrap; margin:4px 0; }
.ok { color:var(--accent); font-size:.85rem; }
/* dialog */
.overlay { position:fixed; inset:0; background:rgba(8,12,16,.55); display:flex; align-items:center;
           justify-content:center; z-index:50; padding:16px; }
.dialog { background:var(--card); border:1px solid var(--line); border-radius:14px; max-width:560px; width:100%;
          max-height:92vh; overflow:auto; padding:16px; box-shadow:0 12px 40px rgba(0,0,0,.25); }
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
                   box-shadow:0 -8px 32px rgba(0,0,0,.25); }
.sheet .sheetbox h3 { display:flex; justify-content:space-between; align-items:center; margin:0 0 10px; font-size:.95rem; }
.sheetstage { display:flex; align-items:flex-end; justify-content:center; gap:20px; padding:12px 0 16px; }
.stars { display:flex; gap:2px; }
.stars button { flex:1; font-size:30px; line-height:1.3; padding:10px 0; color:var(--line); border:none; background:none; }
.stars button.on { color:#e8a825; }
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
             background:var(--card); border-top:1px solid var(--line); box-shadow:0 -4px 16px rgba(10,16,22,.12); }
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
.colorchip { width:30px; height:30px; flex:none; }
.gmeta select { font:inherit; font-size:.8rem; padding:4px 6px; border-radius:8px;
                border:1px solid var(--line); background:var(--card); color:var(--ink); max-width:140px; }
.vargrid { display:flex; flex-direction:column; gap:10px; }
.vargroup { border-left:3px solid var(--line); padding-left:10px; }
.varhead { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.varstyle { font:inherit; font-size:.75rem; padding:2px 4px; border-radius:6px;
            border:1px solid var(--line); background:var(--card); color:var(--ink); }
@media (max-width: 640px) {
  main { padding:12px; }
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
    <span class="spacer"></span>
    <span class="meta">{{ S.candidates.length }} candidates</span>
    <button class="subtle" @click="openSettings" title="settings">⚙</button>
    <button class="subtle" @click="load(true)">refresh</button>
    <div v-if="S.ai.text" class="banner" :class="S.ai.active ? 'working' : 'ready'">
      <span class="dot"></span>{{ S.ai.text }}
    </div>
  </header>

  <main>
    <div v-if="S.msg" :class="S.msgClass">{{ S.msg }}</div>

    <section v-if="S.grouped.length">
      <h2>Current round — rate, then decide</h2>
      <div class="group" v-for="g in S.grouped" :key="g.key">
        <div class="ghead">
          <b>{{ g.icon }}</b>
          <span class="muted">{{ g.cands.length }} candidates across variants</span>
          <span class="spacer"></span>
          <button class="subtle armed-x" @click="rejectAllIcon(g)" title="reject every candidate for this icon">reject all</button>
        </div>
        <div class="gmeta">
          <span class="muted brief">{{ packBriefIcon(g) }}</span>
          <input type="color" class="colorchip" :value="mainColorIcon(g) || '#89919a'"
                 title="main color"
                 @input="saveMainColorIcon(g, $event.target.value)">
        </div>
        <div class="vargrid">
          <div class="vargroup" v-for="vg in variantGroups(g)" :key="vg.variant">
            <div class="varhead">
              <span class="chip">{{ vg.variant }}</span>
              <select :value="vg.style" @change="switchStyle(g.icon, vg.variant, $event.target.value)" class="varstyle" title="style">
                <option v-for="(st, sid) in S.styles" :key="sid" :value="sid">{{ sid }}</option>
              </select>
            </div>
            <div class="grid">
              <div class="card" v-for="c in vg.cands" :key="c.cand">
                <img class="thumb" loading="lazy" width="64" height="64"
                     :src="render(c.path, 64, '#f6f9f7', mainColorIcon(g))" @click="open(c)">
            <div class="name">{{ c.cand }}
            </div>
            <div class="rating">
              <button :class="{ 'armed-x': item(c)?.t?.startsWith(c.cand + ' no') }"
                      title="drop (rate 0)" @click="drop(c)">✕</button>
              <button class="ratebtn" :class="{ armed: rating(c) > 0 }"
                      @click="openSheet(c)" :title="'rate ' + c.cand">
                <template v-if="rating(c) > 0">★ {{ rating(c) }}</template>
                <template v-else>rate</template>
              </button>
              <button :class="{ armed: item(c)?.t === c.cand + ' ok' }"
                      title="approve — final" @click="approve(c)">✓</button>
            </div>
            <button class="subtle" :class="{ armed: item(c)?.t === c.cand + ' keep' }"
                    @click="keep(c)">keep (refine)</button>
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
          ok = <b>approve final</b> · keep = <b>refine</b> · rate 0 = drop.
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
        <textarea v-if="S.showGen" readonly :value="S.decisionText"></textarea>
      </details>
    </div>

    <section>
      <h2>Icons</h2>
      <div class="group" v-for="(icon, id) in S.pack.icons" :key="id">
        <div class="ghead">
          <b>{{ id }}</b>
          <span v-if="icon.main_color" class="chip" :style="{background: icon.main_color, color:'#fff'}">{{ icon.main_color }}</span>
          <input v-if="S.editing === id" style="flex:1; min-width:120px" :value="icon.brief"
                 @keydown.enter="saveIcon(id, $event.target.value)" @blur="saveIcon(id, $event.target.value)">
          <span v-else class="muted" style="flex:1; cursor:text" @click="S.editing = id">{{ icon.brief }}</span>
          <button class="subtle" @click="S.editing = S.editing === id ? null : id">edit</button>
        </div>
        <div class="grid">
          <div class="card" v-for="(v, vid) in icon.variants" :key="vid">
            <img v-if="!v.link" class="thumb" loading="lazy" width="64" height="64"
                 :src="render('icons/' + id + '/' + vid + '.svg', 64, '#ffffff')"
                 @click="openIcon(id, vid, v)">
            <div class="name">{{ vid }}</div>
            <span class="chip" :class="v.status">{{ v.link ? '→ ' + v.link : v.status }}</span>
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
    <button class="primary ab-apply" @click="apply"
            :disabled="!S.decisionEdit.trim() || S.applying">
      {{ S.applying ? '…' : 'Apply' + (S.lines.length ? ' · ' + S.lines.length : '') }}</button>
  </div>

  <div v-if="S.settingsDlg" class="overlay" @click.self="S.settingsDlg = false">
    <div class="dialog">
      <h3><span>⚙ {{ S.pack.name }} settings</span>
          <button class="subtle" @click="S.settingsDlg = false">✕</button></h3>
      <div class="controls"><label>version</label>
        <input v-model="S.set.version" style="width:110px"></div>
      <div class="controls" style="align-items:flex-start"><label>global note</label>
        <textarea v-model="S.set.note" placeholder="standing instructions for every draft — e.g. 'no chimneys anywhere'"></textarea></div>
      <div class="controls" style="align-items:flex-start"><label>rules</label>
        <textarea v-model="S.set.rules" placeholder="one rule per line — injected into every drafting context"></textarea></div>
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

  <div v-if="S.noteDlg" class="overlay" @click.self="S.noteDlg = null">
    <div class="dialog">
      <h3><span>💬 {{ S.noteDlg.g.icon }} / {{ S.noteDlg.g.variant }}</span>
          <button class="subtle" @click="S.noteDlg = null">✕</button></h3>
      <p class="muted" style="margin:0 0 8px">Persistent note for this icon — saved immediately, shown to the agent in every future round (on top of the pack note).</p>
      <textarea v-model="S.noteDlg.text" placeholder="thinner roof, door on the right, less mass at the base…"></textarea>
      <div class="row" style="margin-top:8px">
        <button class="primary" @click="saveNote">Save note</button>
        <button class="subtle" v-if="S.noteDlg.text" @click="S.noteDlg.text = ''; saveNote()">Clear</button>
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
  pack: { icons: {} }, rev: 0, round: null, candidates: [],
  styles: {}, ai: { text: '', active: false }, version: '',
  decisions: {}, manual: false, manualText: '',
  msg: '', msgClass: 'muted', editing: null,
  dlg: null, sheet: null, noteDlg: null, settingsDlg: false,
  decisionEdit: '', showGen: false, editingBrief: null,
  flash: '', flashOk: true, applying: false, instructions: '',
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

S.grouped = computed(() => {
  const m = new Map();
  for (const c of S.candidates) {
    if (!m.has(c.icon)) m.set(c.icon, { key: c.icon, icon: c.icon, cands: [] });
    m.get(c.icon).cands.push(c);
  }
  return [...m.values()];
});
function variantGroups(g) {
  const m = new Map();
  for (const c of g.cands) {
    if (!m.has(c.variant)) m.set(c.variant, { variant: c.variant, cands: [], style: c.style });
    m.get(c.variant).cands.push(c);
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
function rejectAllIcon(g) {
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
function rating(c) {
  const it = item(c);
  if (!it) return 5;
  const m = it.t.match(/rate ([0-9]+)/); if (m) return +m[1];
  if (it.t.endsWith(' ok')) return 10;
  if (it.t.includes(' no') || it.t.endsWith(' keep')) return 0;
  return 5;
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
  return !!S.pack.icons?.[g.icon]?.note;
}
function openNote(g) { S.noteDlg = { g, text: S.pack.icons?.[g.icon]?.note || '' }; }
async function saveNote() {
  const g = S.noteDlg.g;
  try {
    const r = await api('/api/icon', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ icon: g.icon, note: S.noteDlg.text.trim() }) });
    S.msg = `note saved (rev ${r.rev})`; S.msgClass = 'ok';
    S.noteDlg = null; await load();
  } catch (e) { S.msg = e.d?.errors ? e.d.errors.join(' ') : e.message; S.msgClass = 'err'; }
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
function openSheet(c) { S.sheet = { c }; }
function openSettings() {
  const sp = S.pack.spec || {};
  S.set = {
    version: S.pack.version || '',
    note: S.pack.note || '',
    rules: (S.pack.rules || []).join('\\n'),
    strokeWidth: sp.stroke?.width ?? 2,
    linecap: sp.stroke?.linecap || 'round',
    linejoin: sp.stroke?.linejoin || 'round',
    padding: sp.live_area?.padding ?? 2,
    precision: sp.precision ?? 0.5,
    palette: (S.pack.styles?.['lineal-color']?.palette) || null,
    errors: '',
  };
  S.settingsDlg = true;
}
async function saveSettings() {
  S.set.errors = '';
  try {
    const r = await api('/api/pack', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        version: S.set.version,
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
async function apply() {
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
  const [p, run, styles, ai] = await Promise.all([
    api('/api/pack'), api('/api/run'), api('/api/styles'), api('/api/ai-status'),
  ]);
  S.pack = p.pack; S.rev = p.rev; S.round = run.round;
  S.candidates = run.candidates.map(c => ({
    ...c,
    path: `.runs/${run.round}/${c.variant}/${c.icon}/${c.cand}.svg`,
    style: p.pack.icons?.[c.icon]?.variants?.[c.variant]?.style,
  }));
  S.styles = styles;
  S.ai = { text: ai.status || '', active: !!ai.active };
  S.version = p.version || '';
  restoreDraft();  // bring back in-progress ratings after a reload
}

const App = {
  setup() {
    onMounted(() => {
      load().catch(e => { S.msg = e.message; S.msgClass = 'err'; });
      setInterval(async () => {
        try {
          const [p, ai] = await Promise.all([api('/api/pack'), api('/api/ai-status')]);
          if (p.rev !== S.rev || (ai.status || '') !== S.ai.text) await load();
        } catch {}
      }, 2000);
    });
    return {
      S, render, item, rating, drop, approve, keep, rate, rejectAll,
      styleLabel, open, openIcon, openSheet, switchStyle, startManual,
      apply, copy, saveIcon, edited, load, chosenCand, variantStatus,
      mainColor, packBrief, saveBrief, saveMainColor, hasNote, openNote, saveNote,
      openSettings, saveSettings, markDirty,
      variantGroups, packBriefIcon, mainColorIcon, saveMainColorIcon, rejectAllIcon,
    };
  },
};
createApp(App).mount('#app');
</script>
</body></html>
"""
