// TeachWise AI — Application JS

// ── Toast notifications ──────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  const icons = { success: '✓', error: '✕', info: '◎' };
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || '•'}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; }, 3500);
  setTimeout(() => toast.remove(), 3900);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ── Tabs ─────────────────────────────────────────────────────────────────────
function initTabs(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const buttons = container.querySelectorAll('.tab-btn');
  const panels = container.querySelectorAll('.tab-panel');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add('active');
    });
  });
  if (buttons.length) buttons[0].click();
}

// ── Upload zone drag-and-drop ─────────────────────────────────────────────────
function initUploadZone(zoneId, inputId) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length) {
      const dt = new DataTransfer();
      dt.items.add(files[0]);
      input.files = dt.files;
      updateZoneLabel(zone, files[0].name);
    }
  });
  input.addEventListener('change', () => {
    if (input.files.length) updateZoneLabel(zone, input.files[0].name);
  });
}

function updateZoneLabel(zone, filename) {
  const p = zone.querySelector('p');
  if (p) p.textContent = `Selected: ${filename}`;
}

// ── Markdown-ish formatter ────────────────────────────────────────────────────
function formatAiOutput(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^#{1,3}\s+(.+)$/gm, '<span class="font-semibold text-accent" style="display:block;margin-top:14px;margin-bottom:4px;">$1</span>')
    .replace(/^[-•]\s+(.+)$/gm, '<span style="display:block;padding-left:16px;">• $1</span>')
    .replace(/`([^`]+)`/g, '<code style="background:var(--surface-3);padding:1px 5px;border-radius:3px;font-family:var(--mono);font-size:12.5px;">$1</code>')
    .replace(/\n{2,}/g, '<br><br>')
    .replace(/\n/g, '<br>');
}

// ── Loading state helpers ────────────────────────────────────────────────────
function setLoading(buttonEl, isLoading, loadingText = 'Generating...') {
  if (isLoading) {
    buttonEl.dataset.originalText = buttonEl.innerHTML;
    buttonEl.innerHTML = `<span class="loading-spinner" style="width:14px;height:14px;border-width:2px;"></span> ${escapeHtml(loadingText)}`;
    buttonEl.disabled = true;
  } else {
    buttonEl.innerHTML = buttonEl.dataset.originalText || buttonEl.innerHTML;
    buttonEl.disabled = false;
  }
}

// ── API helpers ───────────────────────────────────────────────────────────────
async function apiPost(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

async function apiPostForm(url, formData) {
  const res = await fetch(url, { method: 'POST', body: formData });
  return res.json();
}

// ── Progress bar helper ───────────────────────────────────────────────────────
function makeProgressBar(value, max = 100) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  let cls = 'accent';
  if (pct < 40) cls = 'danger';
  else if (pct < 60) cls = 'warning';
  else if (pct >= 80) cls = 'success';
  return `<div class="progress-wrap" style="margin-top:4px;">
    <div class="progress-bar ${cls}" style="width:${pct}%;"></div>
  </div>`;
}

// ── Render pipeline stage log ─────────────────────────────────────────────────
function renderStageLog(stages, containerId) {
  const el = document.getElementById(containerId);
  if (!el || !stages) return;
  const icons = { success: '✓', failed: '✕', running: '◎', pending: '○' };
  el.innerHTML = stages.map(s => `
    <div class="pipeline-stage">
      <div class="stage-icon ${s.status}">${icons[s.status] || '○'}</div>
      <div class="stage-name">${escapeHtml(s.stage)}</div>
      <div class="stage-message">${s.message ? escapeHtml(s.message) : (s.error ? escapeHtml(s.error) : '')}</div>
    </div>
  `).join('');
}

// ── Chart defaults ────────────────────────────────────────────────────────────
const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: '#8b949e', font: { size: 12 } } },
    tooltip: {
      backgroundColor: '#1c2333',
      titleColor: '#e6edf3',
      bodyColor: '#8b949e',
      borderColor: '#30363d',
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      ticks: { color: '#6e7681', font: { size: 11 } },
      grid: { color: 'rgba(48,54,61,0.5)' },
    },
    y: {
      ticks: { color: '#6e7681', font: { size: 11 } },
      grid: { color: 'rgba(48,54,61,0.5)' },
      beginAtZero: true,
      max: 100,
    },
  },
};

Chart.defaults.color = '#8b949e';
Chart.defaults.font.family = '-apple-system, "Segoe UI", system-ui, sans-serif';
