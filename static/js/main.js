/* SENTRIX AI — main.js */

// ── Clock ──────────────────────────────────────
function startClock() {
  const tick = () => {
    const n = new Date();
    const s = [n.getHours(), n.getMinutes(), n.getSeconds()]
      .map(v => String(v).padStart(2,'0')).join(':');
    setText('sys-clock', s);
    setText('sb-clock-val', s);
  };
  tick(); setInterval(tick, 1000);
}

// ── Toast ──────────────────────────────────────
let _toastTimer = null;
function showToast(title, sub, type='ok') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.className = 'toast' + (type==='atk' ? ' atk' : '');
  el.querySelector('.t-icon').textContent  = type==='atk' ? '🚨' : '✅';
  el.querySelector('.t-title').textContent = title;
  el.querySelector('.t-sub').textContent   = sub || '';
  el.style.display = 'block';
  if (_toastTimer) clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.style.display='none', 5000);
}

// ── Audio ──────────────────────────────────────
let _actx = null;
function playAlert() {
  try {
    if (!_actx) _actx = new (window.AudioContext||window.webkitAudioContext)();
    [880,440,660].forEach((f,i) => {
      const o = _actx.createOscillator(), g = _actx.createGain();
      o.connect(g); g.connect(_actx.destination);
      o.frequency.value = f;
      g.gain.setValueAtTime(.25, _actx.currentTime + i*.2);
      g.gain.exponentialRampToValueAtTime(.001, _actx.currentTime + i*.2 + .3);
      o.start(_actx.currentTime + i*.2);
      o.stop(_actx.currentTime + i*.2 + .3);
    });
  } catch(e){}
}

// ── Helpers ──────────────────────────────────────
function setText(id, v) { const e=document.getElementById(id); if(e) e.textContent=v; }
function setWidth(id, v) { const e=document.getElementById(id); if(e) e.style.width=Math.min(100,Math.max(0,v))+'%'; }

// ── Live Updates ──────────────────────────────────────
let _prevStatus = 'Normal';

function startLive() {
  setInterval(() => {
    fetch('/api/status').then(r=>r.json()).then(d => {
      updateMetrics(d);
      updateStatusBar(d);
      updateMonitor(d);
      updateSidebarDot(d.running);

      if (d.attack !== 'Normal' && _prevStatus === 'Normal') {
        showToast('Attack Detected!', d.attack + ' — ' + d.can_id, 'atk');
        playAlert();
      }

      _prevStatus = d.attack;
    }).catch(()=>{});
  }, 2000);
}

// ── 🔥 NEW: Traffic Live ─────────────────────────────
function startTraffic() {
  setInterval(() => {
    fetch('/api/traffic')
      .then(r => r.json())
      .then(data => renderTraffic(data))
      .catch(()=>{});
  }, 2000);
}

function renderTraffic(data) {
  const table = document.getElementById('traffic-table');
  if (!table) return;

  table.innerHTML = '';

  data.forEach(row => {
    const tr = document.createElement('tr');

    tr.innerHTML = `
      <td>${row.time}</td>
      <td>${row.can_id}</td>
      <td class="${row.type === 'Normal' ? 'green' : 'red'}">${row.type}</td>
      <td>${row.detection_time} ms</td>
      <td>${row.action}</td>
      <td>${row.severity}</td>
    `;

    table.appendChild(tr);
  });
}

// ── Metrics ──────────────────────────────────────
function updateMetrics(d) {
  setText('m-total',   d.total);
  setText('m-normal',  d.normal);
  setText('m-dos',     d.dos);
  setText('m-fuzzy',   d.fuzzy);
  setText('m-blocked', d.blocked);
  setText('m-correct', d.correct);
  setText('m-det',     (d.detection_time||0)+'ms');
  setText('m-canid',   d.can_id);
  setText('m-real',    d.real_label);
  setText('m-ml',      d.ml_label);
  setText('m-time',    d.time);
  setText('m-ips',     d.ips_status);

  const acc = d.total > 0 ? Math.round(d.correct/d.total*100) : 0;
  setText('m-acc', acc+'%');
  setWidth('acc-bar', acc);
}

// ── Status Bar ──────────────────────────────────────
function updateStatusBar(d) {
  const bar  = document.getElementById('status-bar');
  if (!bar) return;

  const atk = d.attack !== 'Normal';
  bar.className = 'sbar ' + (atk ? 'atk' : 'ok');
}

// ── Monitor ──────────────────────────────────────
function updateMonitor(d) {
  const s = document.getElementById('mon-screen');
  if (!s) return;

  const atk = d.attack !== 'Normal';
  s.className = 'mon-screen ' + (atk ? 'atk' : 'ok');
}

// ── Sidebar ──────────────────────────────────────
function updateSidebarDot(running) {
  const d = document.getElementById('sb-run-dot');
  const t = document.getElementById('sb-run-txt');

  if (d) d.className = 'sb-dot ' + (running ? 'on' : 'off');
  if (t) t.textContent = running ? 'System Running' : 'System Stopped';
}

// ── Particles ──────────────────────────────────────
function initParticles() {
  const c = document.getElementById('lp-canvas');
  if (!c) return;

  const ctx = c.getContext('2d');

  const resize = () => {
    c.width = innerWidth;
    c.height = innerHeight;
  };

  resize();
  window.addEventListener('resize', resize);

  const pts = Array.from({length:40}, () => ({
    x: Math.random()*innerWidth,
    y: Math.random()*innerHeight,
    vx:(Math.random()-.5)*.2,
    vy:(Math.random()-.5)*.2
  }));

  (function draw() {
    ctx.clearRect(0,0,c.width,c.height);
    pts.forEach(p => {
      p.x+=p.vx; p.y+=p.vy;
      ctx.fillRect(p.x,p.y,1,1);
    });
    requestAnimationFrame(draw);
  })();
}

// ── Init ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  startClock();
  initParticles();
  startLive();
  startTraffic(); // 🔥 المهم
});