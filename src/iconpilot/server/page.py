"""Mobile-first review page — vanilla, no build step, served inline."""

PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iconpilot review</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, sans-serif; margin: 0; padding: 12px; max-width: 760px; margin-inline: auto; }
  h1 { font-size: 1.1rem; } h2 { font-size: .95rem; margin: 18px 0 6px; }
  .card { border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
          border-radius: 10px; padding: 10px; margin: 10px 0; }
  .row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .variants { display: flex; gap: 6px; flex-wrap: wrap; margin: 6px 0; }
  .chip { padding: 2px 8px; border-radius: 99px; font-size: .75rem; border: 1px solid currentColor; }
  .chip.approved { background: #2e7d32; color: #fff; border: 0; }
  .chip.in_review, .chip.stale { background: #b07d2e; color: #fff; border: 0; }
  .chip.todo, .chip.drafting { opacity: .6; }
  img.i { width: 48px; height: 48px; background: #fff; border-radius: 6px; }
  img.i.dark { background: #112119; }
  button { font: inherit; padding: 5px 10px; border-radius: 8px; border: 1px solid currentColor; background: transparent; cursor: pointer; }
  button.primary { background: #2e7d32; color: #fff; border: 0; }
  button.warn { background: #b07d2e; color: #fff; border: 0; }
  input, textarea { font: inherit; width: 100%; box-sizing: border-box; padding: 6px; border-radius: 8px;
        border: 1px solid color-mix(in srgb, currentColor 30%, transparent); background: transparent; }
  textarea { min-height: 60px; }
  .muted { opacity: .65; font-size: .8rem; }
  .err { color: #d32f2f; white-space: pre-wrap; }
  .ok { color: #2e7d32; }
  .cands { display: flex; gap: 10px; flex-wrap: wrap; }
  .cand { text-align: center; font-size: .8rem; }
  details summary { cursor: pointer; }
</style></head><body>
<h1>iconpilot review — <span id="packname"></span> <span class="muted" id="rev"></span></h1>
<div id="msg" class="muted"></div>

<h2>Decision text <span class="muted">(same grammar as the CLI)</span></h2>
<textarea id="decision" placeholder='hut/mono: a2 keep "thinner roof" · b1 no · more 2'></textarea>
<div class="row" style="margin-top:6px">
  <button class="primary" onclick="applyDecisions()">Apply decisions</button>
  <button onclick="copyDecisions()">Copy decisions</button>
</div>

<h2>Current round candidates <span class="muted" id="round"></span></h2>
<div id="cands"></div>

<h2>Icons</h2>
<div id="icons"></div>

<script>
let PACK = null, REV = 0, ROUND = null;

async function j(url, opts) {
  const r = await fetch(url, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(data.error || JSON.stringify(data.errors) || r.status), {data});
  return data;
}
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function msg(t, cls='') { const m = document.getElementById('msg'); m.className = cls; m.textContent = t; }

async function load() {
  const [p, run] = await Promise.all([j('/api/pack'), j('/api/run')]);
  PACK = p.pack; REV = p.rev; ROUND = run.round;
  document.getElementById('packname').textContent = PACK.name;
  document.getElementById('rev').textContent = 'rev ' + REV;
  document.getElementById('round').textContent = ROUND ? '(' + ROUND + ')' : '(none)';
  renderIcons(); renderCands(run.candidates);
}

function renderIcons() {
  const el = document.getElementById('icons'); el.innerHTML = '';
  for (const [id, icon] of Object.entries(PACK.icons)) {
    const card = document.createElement('div'); card.className = 'card';
    const variants = Object.entries(icon.variants).map(([v, d]) => {
      const st = d.link ? 'link→' + d.link : (d.status || 'todo');
      const file = d.link ? null : `icons/${id}/${v}.svg`;
      const img = file ? `<img class="i" loading="lazy" src="/api/render?p=${encodeURIComponent(file)}&size=48">` : '';
      return `<div class="cand">${img}<div>${esc(v)} <span class="chip ${esc(d.status||'')}">${esc(st)}</span></div></div>`;
    }).join('');
    card.innerHTML = `
      <details open>
        <summary><b>${esc(id)}</b>${icon.main_color ? ` <span class="chip" style="background:${esc(icon.main_color)};color:#fff;border:0">${esc(icon.main_color)}</span>` : ''}</summary>
        <div class="variants">${variants}</div>
        <div class="row" style="gap:4px">
          <input style="flex:1" id="brief-${esc(id)}" placeholder="brief" value="${esc(icon.brief)}">
          <input style="flex:1" id="prompt-${esc(id)}" placeholder="prompt (optional)" value="${esc(icon.prompt||'')}">
          <input style="width:90px" id="main_color-${esc(id)}" placeholder="#hex" value="${esc(icon.main_color||'')}">
          <button onclick="saveIcon('${esc(id)}')">Save</button>
        </div>
      </details>`;
    el.appendChild(card);
  }
}

function renderCands(cands) {
  const el = document.getElementById('cands'); el.innerHTML = '';
  if (!cands.length) { el.innerHTML = '<div class="muted">no candidates in the latest run</div>'; return; }
  const byIcon = {};
  for (const c of cands) (byIcon[c.icon + '/' + c.variant] ??= []).push(c);
  for (const [key, list] of Object.entries(byIcon)) {
    const d = document.createElement('div'); d.className = 'card';
    d.innerHTML = `<b>${esc(key)}</b><div class="cands">` + list.map(c => `
      <div class="cand">
        <img class="i" loading="lazy" src="/api/render?p=${encodeURIComponent('.runs/'+ROUND+'/'+c.variant+'/'+c.icon+'/'+c.cand+'.svg')}&size=48">
        <div class="row" style="justify-content:center;gap:2px">
          <span>${esc(c.cand)}</span>
          <button title="approve" onclick="cand('${esc(key)}','${esc(c.cand)}','ok')">ok</button>
          <button title="keep" onclick="cand('${esc(key)}','${esc(c.cand)}','keep')">keep</button>
          <button title="reject" onclick="cand('${esc(key)}','${esc(c.cand)}','no')">no</button>
        </div>
      </div>`).join('') + '</div>';
    el.appendChild(d);
  }
}

function cand(key, c, action) {
  const t = document.getElementById('decision');
  const item = `${c} ${action}`;
  t.value = t.value ? t.value.split('\\n').filter(Boolean).map(l => l.startsWith(key+':') ? mergeItem(l, item) : l).concat(key.startsWith('$') ? [] : (t.value.includes(key+':') ? [] : [key + ': ' + item])).join('\\n') : key + ': ' + item;
}
function mergeItem(line, item) {
  const [k, rest] = [line.slice(0, line.indexOf(':')), line.slice(line.indexOf(':')+1).trim()];
  return k + ': ' + (rest ? rest + ' · ' + item : item);
}

async function applyDecisions() {
  const text = document.getElementById('decision').value.trim();
  if (!text) return msg('nothing to apply');
  try {
    const r = await j('/api/decision', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text, round: ROUND})});
    msg('applied: ' + (r.log || []).join(' | '), 'ok');
    document.getElementById('decision').value = '';
    load();
  } catch (e) { msg(e.message, 'err'); }
}

function copyDecisions() {
  const t = document.getElementById('decision').value.trim();
  navigator.clipboard.writeText(t).then(() => msg('copied — paste to your agent', 'ok'));
}

async function saveIcon(id) {
  const patch = {icon: id};
  for (const f of ['brief','prompt','main_color']) {
    const v = document.getElementById(`${f}-${id}`).value;
    if (v) patch[f] = v;
  }
  try {
    const r = await j('/api/icon', {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch)});
    msg('saved ' + id + ' (rev ' + r.rev + ')', 'ok');
  } catch (e) { msg(e.data?.errors ? e.data.errors.join('\\n') : e.message, 'err'); }
}

setInterval(async () => {
  try { const r = await j('/api/pack'); if (r.rev !== REV) { msg('pack changed — reloading'); load(); } } catch {}
}, 2500);

load();
</script></body></html>
"""
