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
function apiPost(url, data, cb) {
  fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data||{}) })
    .then(r=>r.json()).then(cb||function(){}).catch(console.error);
}

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
  setText('m-acc', acc+'%'); setText('m-acc2', acc+'%');
  setWidth('acc-bar', acc);
}

function updateStatusBar(d) {
  const bar  = document.getElementById('status-bar');
  const dot  = document.getElementById('sbar-dot');
  const txt  = document.getElementById('sbar-txt');
  const sub  = document.getElementById('sbar-sub');
  if (!bar) return;
  const atk = d.attack !== 'Normal';
  bar.className = 'sbar ' + (atk ? 'atk' : 'ok');
  if (dot) dot.className = 'sbar-dot ' + (atk ? 'atk' : 'ok');
  if (txt) txt.textContent = atk ? d.attack : 'All Systems Normal';
  if (sub) sub.textContent = 'IPS: ' + d.ips_status;
}

function updateMonitor(d) {
  const s = document.getElementById('mon-screen');
  const t = document.getElementById('mon-status');
  if (!s) return;
  const atk = d.attack !== 'Normal';
  s.className = 'mon-screen ' + (atk ? 'atk' : 'ok');
  if (t) { t.textContent = atk ? d.attack : 'NORMAL'; t.style.color = atk ? '#f43f5e' : '#22c55e'; }
}

function updateSidebarDot(running) {
  const d = document.getElementById('sb-run-dot');
  const t = document.getElementById('sb-run-txt');
  if (d) d.className = 'sb-dot ' + (running ? 'on' : 'off');
  if (t) t.textContent = running ? 'System Running' : 'System Stopped';
}

// ── Log Detail Panel ──────────────────────────────────────
let _logData = [];

function setLogData(arr) { _logData = arr; }

function openDetail(idx) {
  const log = _logData[idx];
  if (!log) return;
  const panel = document.getElementById('detail-panel');
  if (!panel) return;

  // Populate
  document.getElementById('dp-type').textContent    = log.type || '-';
  document.getElementById('dp-canid').textContent   = log.can_id || '-';
  document.getElementById('dp-time').textContent    = log.time || '-';
  document.getElementById('dp-det').textContent     = (log.detection_time || 0) + 'ms';
  document.getElementById('dp-real').textContent    = log.real || '-';
  document.getElementById('dp-sev').textContent     = log.severity || '-';
  document.getElementById('dp-action').textContent  = log.action || 'BLOCKED';

  // Severity badge
  const sevEl = document.getElementById('dp-sev-badge');
  if (sevEl) {
    sevEl.textContent = log.severity || '-';
    sevEl.className = 'bdg ' + (log.severity==='Critical'?'bdg-purple':log.severity==='High'?'bdg-red':'bdg-amber');
  }

  // Analysis
  const analysis = analyzeLog(log);
  document.getElementById('dp-analysis').innerHTML = analysis;

  panel.classList.add('open');
}

function closeDetail() {
  const panel = document.getElementById('detail-panel');
  if (panel) panel.classList.remove('open');
}

function analyzeLog(log) {
  if (log.type === 'DoS') {
    return `
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt">DoS packet flood detected on CAN ID ${log.can_id}</div></div>
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt">Random Forest classifier confidence: HIGH — pattern matched DoS signature</div></div>
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt">IPS triggered: CAN Bus traffic filtered at gateway</div></div>
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt">Detection latency: ${log.detection_time}ms — within acceptable threshold</div></div>
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt" style="color:var(--green)">✓ Attack neutralized — Normal traffic restored</div></div>
    `;
  } else if (log.type === 'Fuzzy') {
    return `
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt">Anomalous CAN message detected — CAN ID: ${log.can_id}</div></div>
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt">Random Forest: data bytes show random distribution — Fuzzy attack signature</div></div>
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt">IPS triggered: invalid CAN IDs filtered — ECUs protected</div></div>
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt">Detection latency: ${log.detection_time}ms</div></div>
      <div class="dp-event"><div class="dp-event-time">${log.time}</div><div class="dp-event-txt" style="color:var(--green)">✓ Fuzzy traffic neutralized — CAN Bus validated</div></div>
    `;
  }
  return '<div class="dp-event-txt" style="color:var(--txt2)">No additional analysis available.</div>';
}

// ── Logs filter ──────────────────────────────────────
function filterLogs(val) {
  document.querySelectorAll('.log-row').forEach(r => {
    r.style.display = r.textContent.toLowerCase().includes(val.toLowerCase()) ? '' : 'none';
  });
  updateCount();
}

function filterByType(val) {
  document.querySelectorAll('.log-row').forEach(r => {
    r.style.display = (val==='all' || r.dataset.type===val) ? '' : 'none';
  });
  updateCount();
}

function filterBySev(val) {
  document.querySelectorAll('.log-row').forEach(r => {
    r.style.display = (val==='all' || r.dataset.sev===val) ? '' : 'none';
  });
  updateCount();
}

function updateCount() {
  const visible = [...document.querySelectorAll('.log-row')].filter(r => r.style.display !== 'none').length;
  setText('log-count', visible + ' events');
}

function exportCSV() {
  const rows = document.querySelectorAll('.log-row');
  let csv = '#,Time,Type,CAN ID,Severity,Detection Time,Real Label,Action\n';
  rows.forEach(r => {
    const cells = r.querySelectorAll('td');
    const line = [];
    cells.forEach(c => line.push('"' + c.textContent.trim() + '"'));
    csv += line.join(',') + '\n';
  });
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
  a.download = 'sentrix_logs_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}

// ── Login particles ──────────────────────────────────────
function initParticles() {
  const c = document.getElementById('lp-canvas');
  if (!c) return;
  const ctx = c.getContext('2d');
  const resize = () => { c.width=innerWidth; c.height=innerHeight; };
  resize(); window.addEventListener('resize', resize);

  const pts = Array.from({length:55}, () => ({
    x: Math.random()*innerWidth, y: Math.random()*innerHeight,
    vx:(Math.random()-.5)*.25, vy:(Math.random()-.5)*.25,
    r: Math.random()*1.2+.4, a: Math.random()*.35+.08
  }));

  (function draw() {
    ctx.clearRect(0,0,c.width,c.height);
    pts.forEach(p => {
      p.x+=p.vx; p.y+=p.vy;
      if(p.x<0)p.x=c.width; if(p.x>c.width)p.x=0;
      if(p.y<0)p.y=c.height; if(p.y>c.height)p.y=0;
      ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle=`rgba(59,130,246,${p.a})`; ctx.fill();
    });
    for(let i=0;i<pts.length;i++) for(let j=i+1;j<pts.length;j++) {
      const dx=pts[i].x-pts[j].x, dy=pts[i].y-pts[j].y, d=Math.hypot(dx,dy);
      if(d<110) { ctx.beginPath(); ctx.moveTo(pts[i].x,pts[i].y); ctx.lineTo(pts[j].x,pts[j].y);
        ctx.strokeStyle=`rgba(59,130,246,${.05*(1-d/110)})`; ctx.lineWidth=.7; ctx.stroke(); }
    }
    requestAnimationFrame(draw);
  })();
}

// ── Init ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  startClock();
  initParticles();
  startLive();

  // Close detail panel on overlay click
  document.addEventListener('keydown', e => { if(e.key==='Escape') closeDetail(); });
});
