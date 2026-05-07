/**
 * NCPS Dashboard — Main Application Logic
 * State management, D3 network graph, charts, and API integration.
 */

const API = window.location.origin;
let currentState = null;

// ═══════════════════════════════════════════════════════════
// API Layer
// ═══════════════════════════════════════════════════════════

async function runSimulation() {
  const btn = document.getElementById('run-btn');
  const runText = document.getElementById('run-text');
  btn.disabled = true;
  runText.innerHTML = '&#9203; Running...';

  const scenario = document.getElementById('scenario-select').value;
  const phase = parseInt(document.getElementById('phase-select').value);

  try {
    const res = await fetch(API + '/api/simulation/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario, phase }),
    });
    if (!res.ok) throw new Error('Server returned ' + res.status);
    const data = await res.json();
    currentState = data;
    renderDashboard(data);
  } catch (e) {
    console.error('Simulation failed:', e);
    showError('Simulation failed: ' + e.message);
  }

  btn.disabled = false;
  runText.innerHTML = '&#9654; Run';
}

function showError(msg) {
  document.getElementById('user-list').innerHTML =
    '<div class="loading"><span class="text-red">' + msg + '</span></div>';
}

// ═══════════════════════════════════════════════════════════
// Render Dashboard
// ═══════════════════════════════════════════════════════════

function renderDashboard(data) {
  renderMetrics(data.metrics, data.config);
  renderUsers(data.users);
  renderPosts(data.posts);
  renderGraph(data.users, data.edges);
  renderBottomPanel(data);
}

// ── Metrics ──
function renderMetrics(metrics, config) {
  animateValue('val-accuracy', metrics.accuracy, 3);
  animateValue('val-attack', metrics.attack_success, 3);
  animateValue('val-brier', metrics.brier_score, 3);
  animateValue('val-wcorr', metrics.weight_correlation, 3);
  document.getElementById('val-users').textContent = config.num_users;
  document.getElementById('val-posts').textContent = config.num_posts;

  // Animate metric cards in
  document.querySelectorAll('.metric-card').forEach((card, i) => {
    card.style.animation = 'none';
    card.offsetHeight; // trigger reflow
    card.style.animation = `fadeInUp 0.4s ease-out ${i * 0.05}s both`;
  });
}

function animateValue(id, target, decimals) {
  const el = document.getElementById(id);
  if (!el || target === undefined || target === null) return;
  const start = parseFloat(el.textContent) || 0;
  const duration = 600;
  const startTime = performance.now();

  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = start + (target - start) * eased;
    el.textContent = current.toFixed(decimals);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// ── Users Table ──
function renderUsers(users) {
  const sorted = [...users].sort((a, b) => b.weight - a.weight);
  document.getElementById('user-count').textContent = sorted.length + ' users';

  let html = '<table class="user-table"><thead><tr>';
  html += '<th></th><th>ID</th><th>R*</th><th>Anom</th><th>T</th><th>w</th>';
  html += '</tr></thead><tbody>';

  sorted.forEach(u => {
    const cls = u.type;
    const dotColor = u.type === 'bot' ? '#ef4444' : u.type === 'adversarial' ? '#f59e0b' :
                     u.type === 'honest' ? '#10b981' : '#64748b';
    html += '<tr class="' + cls + '" onclick="openUser(\'' + encodeURIComponent(JSON.stringify(u)) + '\')">';
    html += '<td><span class="type-badge" style="background:' + dotColor + '"></span></td>';
    html += '<td>' + u.id + '</td>';
    html += '<td>' + u.reliability.toFixed(2) + '</td>';
    html += '<td>' + u.anomaly.toFixed(2) + '</td>';
    html += '<td>' + u.trust.toFixed(2) + '</td>';
    html += '<td>' + u.weight.toFixed(2) + '</td>';
    html += '</tr>';
  });

  html += '</tbody></table>';
  document.getElementById('user-list').innerHTML = html;
}

function openUser(encodedData) {
  window.open('/user.html?data=' + encodedData, '_blank');
}

// ── Posts List ──
function renderPosts(posts) {
  const sorted = [...posts].sort((a, b) => b.credibility - a.credibility);
  document.getElementById('post-count').textContent = sorted.length + ' posts';

  let html = '';
  sorted.forEach(p => {
    const credColor = scoreColor(p.credibility);
    const labelBadge = p.label === 'TRUE' ? 'badge-green' : p.label === 'FALSE' ? 'badge-red' : 'badge-yellow';

    html += '<div class="post-card" onclick="openPost(\'' + encodeURIComponent(JSON.stringify(p)) + '\')">';
    html += '<div class="post-content">' + escapeHtml(p.content) + '</div>';
    html += '<div class="post-meta">';
    html += '<span class="badge ' + labelBadge + '">' + p.label + '</span>';
    html += '<span style="color:' + credColor + '">' + p.credibility.toFixed(3) + '</span>';
    if (p.c_ml !== null && p.c_ml !== undefined) {
      html += '<span class="text-muted">ML:' + p.c_ml.toFixed(2) + '</span>';
    }
    html += '</div>';
    html += '<div class="cred-bar" style="margin-top:5px;">';
    html += '<div class="cred-bar-fill" style="width:' + (p.credibility * 100) + '%;background:' + credColor + ';"></div>';
    html += '</div>';
    html += '</div>';
  });

  document.getElementById('post-list').innerHTML = html;
}

function openPost(encodedData) {
  window.open('/post.html?data=' + encodedData, '_blank');
}

// ═══════════════════════════════════════════════════════════
// D3.js Network Graph
// ═══════════════════════════════════════════════════════════

function renderGraph(users, edges) {
  const container = document.getElementById('graph-container');
  container.innerHTML = '';

  const uniqueEdges = [];
  const seen = new Set();
  edges.forEach(e => {
    const key = [e.source, e.target].sort().join('-');
    if (!seen.has(key)) { seen.add(key); uniqueEdges.push(e); }
  });

  document.getElementById('edge-count').textContent = uniqueEdges.length + ' edges';

  const width = container.clientWidth || 600;
  const height = container.clientHeight || 400;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  // Background
  svg.append('rect').attr('width', width).attr('height', height)
    .attr('fill', 'transparent');

  const g = svg.append('g');

  // Zoom
  const zoom = d3.zoom()
    .scaleExtent([0.3, 4])
    .on('zoom', (event) => g.attr('transform', event.transform));
  svg.call(zoom);

  // Build data
  const nodeMap = {};
  users.forEach(u => { nodeMap[u.full_id] = u; });

  const nodes = users.map(u => ({
    id: u.full_id, label: u.id, type: u.type,
    weight: u.weight, anomaly: u.anomaly, trust: u.trust,
    coordination: u.coordination || 0,
  }));

  const nodeIndex = {};
  nodes.forEach((n, i) => { nodeIndex[n.id] = i; });

  const links = uniqueEdges
    .filter(e => nodeIndex[e.source] !== undefined && nodeIndex[e.target] !== undefined)
    .map(e => ({
      source: nodeIndex[e.source], target: nodeIndex[e.target], weight: e.weight,
    }));

  // Force simulation
  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).distance(50).strength(0.4))
    .force('charge', d3.forceManyBody().strength(-30))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => 4 + d.weight * 8));

  // Edges
  const linkSel = g.append('g')
    .selectAll('line').data(links).enter().append('line')
    .attr('stroke', d => d.weight > 0.5 ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.06)')
    .attr('stroke-width', d => Math.max(0.5, d.weight * 2.5));

  // Nodes
  const nodeSel = g.append('g')
    .selectAll('circle').data(nodes).enter().append('circle')
    .attr('r', d => 3 + d.weight * 7)
    .attr('fill', d => nodeColor(d))
    .attr('stroke', d => d.trust > 0.5 ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.06)')
    .attr('stroke-width', 1.5)
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      const u = nodeMap[d.id];
      if (u) openUser(encodeURIComponent(JSON.stringify(u)));
    });

  // Labels
  const labelSel = g.append('g')
    .selectAll('text')
    .data(nodes.filter(n => n.weight > 0.3 || n.type === 'bot'))
    .enter().append('text')
    .text(d => d.label)
    .attr('fill', 'rgba(255,255,255,0.35)')
    .attr('font-size', '7px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('text-anchor', 'middle')
    .attr('dy', -9);

  // Tooltip
  nodeSel.append('title')
    .text(d => d.label + ' (' + d.type + ')\nw=' + d.weight.toFixed(3) +
          ' T=' + d.trust.toFixed(3) + ' Anom=' + d.anomaly.toFixed(3));

  // Tick
  sim.on('tick', () => {
    linkSel
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    nodeSel
      .attr('cx', d => d.x = Math.max(8, Math.min(width - 8, d.x)))
      .attr('cy', d => d.y = Math.max(8, Math.min(height - 8, d.y)));
    labelSel.attr('x', d => d.x).attr('y', d => d.y);
  });

  // Drag
  nodeSel.call(d3.drag()
    .on('start', (event, d) => {
      if (!event.active) sim.alphaTarget(0.3).restart();
      d.fx = d.x; d.fy = d.y;
    })
    .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
    .on('end', (event, d) => {
      if (!event.active) sim.alphaTarget(0);
      d.fx = null; d.fy = null;
    })
  );
}

// ═══════════════════════════════════════════════════════════
// Bottom Panel — Metrics Charts
// ═══════════════════════════════════════════════════════════

function renderBottomPanel(data) {
  document.getElementById('bottom-panel').style.display = '';

  // Tab 1: Overview — key metrics as mini cards
  const overview = document.getElementById('overview-charts');
  const m = data.metrics;
  overview.innerHTML = `
    <div class="panel" style="text-align:center;padding:16px">
      <div class="metric-value text-green" style="font-size:32px">${(m.accuracy * 100).toFixed(1)}%</div>
      <div class="metric-label">Overall Accuracy</div>
      <div class="cred-bar mt-8"><div class="cred-bar-fill" style="width:${m.accuracy*100}%;background:var(--accent-green)"></div></div>
    </div>
    <div class="panel" style="text-align:center;padding:16px">
      <div class="metric-value text-red" style="font-size:32px">${(m.attack_success * 100).toFixed(1)}%</div>
      <div class="metric-label">Attack Success Rate</div>
      <div class="cred-bar mt-8"><div class="cred-bar-fill" style="width:${m.attack_success*100}%;background:var(--accent-red)"></div></div>
    </div>
    <div class="panel" style="text-align:center;padding:16px">
      <div class="metric-value text-blue" style="font-size:32px">${m.brier_score.toFixed(3)}</div>
      <div class="metric-label">Brier Score (lower = better)</div>
      <div class="cred-bar mt-8"><div class="cred-bar-fill" style="width:${(1-m.brier_score)*100}%;background:var(--accent-blue)"></div></div>
    </div>
    <div class="panel" style="text-align:center;padding:16px">
      <div class="metric-value text-yellow" style="font-size:32px">${m.weight_correlation.toFixed(3)}</div>
      <div class="metric-label">Weight ↔ Truth Correlation</div>
      <div class="cred-bar mt-8"><div class="cred-bar-fill" style="width:${Math.max(0,m.weight_correlation)*100}%;background:var(--accent-yellow)"></div></div>
    </div>
  `;

  // Tab 2: Attack Analysis — user type breakdown
  const attackDiv = document.getElementById('attack-charts');
  const types = { honest: [], bot: [], adversarial: [], noisy: [] };
  data.users.forEach(u => {
    if (types[u.type]) types[u.type].push(u);
  });
  let attackHtml = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">';
  Object.entries(types).forEach(([type, users]) => {
    if (users.length === 0) return;
    const avgW = users.reduce((s, u) => s + u.weight, 0) / users.length;
    const avgA = users.reduce((s, u) => s + u.anomaly, 0) / users.length;
    const color = type === 'bot' ? '#ef4444' : type === 'adversarial' ? '#f59e0b' :
                  type === 'honest' ? '#10b981' : '#64748b';
    attackHtml += `<div class="panel" style="padding:14px;text-align:center">
      <div style="font-size:10px;text-transform:uppercase;color:${color};letter-spacing:0.5px;margin-bottom:6px">${type}</div>
      <div class="metric-value" style="font-size:20px;color:${color}">${users.length}</div>
      <div class="metric-label">Count</div>
      <div style="margin-top:10px">
        <div style="font-size:10px;color:var(--text-muted)">Avg Weight</div>
        <div class="mono" style="font-size:13px">${avgW.toFixed(3)}</div>
      </div>
      <div style="margin-top:6px">
        <div style="font-size:10px;color:var(--text-muted)">Avg Anomaly</div>
        <div class="mono" style="font-size:13px">${avgA.toFixed(3)}</div>
      </div>
    </div>`;
  });
  attackHtml += '</div>';
  attackDiv.innerHTML = attackHtml;

  // Tab 3: Anomaly — distribution histogram
  const anomDiv = document.getElementById('anomaly-charts');
  const buckets = new Array(10).fill(0);
  data.users.forEach(u => {
    const idx = Math.min(9, Math.floor(u.anomaly * 10));
    buckets[idx]++;
  });
  const maxBucket = Math.max(...buckets, 1);
  let anomHtml = '<div style="width:100%"><h4 style="font-size:12px;color:var(--text-secondary);margin-bottom:10px">Anomaly Score Distribution</h4>';
  anomHtml += '<div class="chart-bar" style="height:140px">';
  buckets.forEach((count, i) => {
    const h = (count / maxBucket) * 90;
    const color = i < 3 ? '#10b981' : i < 6 ? '#f59e0b' : '#ef4444';
    anomHtml += `<div class="chart-bar-item" style="height:${h}%;background:${color}">
      <div class="chart-bar-value" style="color:${color}">${count}</div>
      <div class="chart-bar-label">${(i/10).toFixed(1)}</div>
    </div>`;
  });
  anomHtml += '</div></div>';
  anomDiv.innerHTML = anomHtml;

  // Tab 4: Weight distribution
  const wDiv = document.getElementById('weight-charts');
  const wBuckets = new Array(10).fill(0);
  data.users.forEach(u => {
    const idx = Math.min(9, Math.floor(u.weight * 10));
    wBuckets[idx]++;
  });
  const maxW = Math.max(...wBuckets, 1);
  let wHtml = '<div style="width:100%"><h4 style="font-size:12px;color:var(--text-secondary);margin-bottom:10px">User Weight Distribution</h4>';
  wHtml += '<div class="chart-bar" style="height:140px">';
  wBuckets.forEach((count, i) => {
    const h = (count / maxW) * 90;
    const hue = (i / 10) * 120;
    const color = `hsl(${hue}, 70%, 55%)`;
    wHtml += `<div class="chart-bar-item" style="height:${h}%;background:${color}">
      <div class="chart-bar-value" style="color:${color}">${count}</div>
      <div class="chart-bar-label">${(i/10).toFixed(1)}</div>
    </div>`;
  });
  wHtml += '</div></div>';
  wDiv.innerHTML = wHtml;
}

// ═══════════════════════════════════════════════════════════
// Tab Switching
// ═══════════════════════════════════════════════════════════

function switchTab(event, tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

// ═══════════════════════════════════════════════════════════
// Utilities
// ═══════════════════════════════════════════════════════════

function nodeColor(d) {
  if (d.type === 'bot') return '#ef4444';
  if (d.type === 'adversarial') return '#f59e0b';
  if (d.type === 'noisy') return '#64748b';
  return d.anomaly > 0.3 ? '#f59e0b' : '#10b981';
}

function scoreColor(v) {
  if (v >= 0.7) return '#10b981';
  if (v >= 0.4) return '#f59e0b';
  return '#ef4444';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
