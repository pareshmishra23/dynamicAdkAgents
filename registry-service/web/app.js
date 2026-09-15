/* ==========================================================================
   ADK Agent Platform Control & Observability Studio — Client Application
   ========================================================================== */

const API_BASE = '/api/v1';

// Global State
const state = {
  agents: [],
  mcpServers: [],
  tools: [],
  benchmarkProblems: [],
  overview: null,
  activeProblemId: null,
};

// DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
  initTabs();
  initModal();
  initEventHandlers();
  await loadAllData();
});

// --------------------------------------------------------------------------
// Navigation Tabs
// --------------------------------------------------------------------------
function initTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      tabButtons.forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach((p) => p.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });
}

// --------------------------------------------------------------------------
// Data Loading
// --------------------------------------------------------------------------
async function loadAllData() {
  await Promise.all([
    loadAgents(),
    loadMcpServers(),
    loadTools(),
    loadBenchmarkProblems(),
    loadOverview(),
  ]);
}

async function loadAgents() {
  try {
    const res = await fetch(`${API_BASE}/agents`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.agents = await res.json();
    renderAgentsTable();
    updateHeaderCounters();
  } catch (err) {
    console.error('Failed to load agents:', err);
    document.getElementById('agentsTableBody').innerHTML = `<tr><td colspan="7" class="loading-td">Error loading agents: ${err.message}</td></tr>`;
  }
}

async function loadMcpServers() {
  try {
    const res = await fetch(`${API_BASE}/mcp-servers`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.mcpServers = await res.json();
    renderMcpTable();
  } catch (err) {
    console.error('Failed to load MCP servers:', err);
  }
}

async function loadTools() {
  try {
    const res = await fetch(`${API_BASE}/tools`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.tools = await res.json();
    renderToolsTable();
    updateHeaderCounters();
  } catch (err) {
    console.error('Failed to load tools:', err);
  }
}

async function loadBenchmarkProblems() {
  try {
    const res = await fetch(`${API_BASE}/benchmark-problems`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.benchmarkProblems = await res.json();
    populateProblemSelector();
    renderBenchmarkTable();
  } catch (err) {
    console.error('Failed to load benchmark problems:', err);
  }
}

async function loadOverview() {
  try {
    const res = await fetch(`${API_BASE}/overview`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.overview = await res.json();
    renderRelationshipGraph();
  } catch (err) {
    console.error('Failed to load overview:', err);
  }
}

function updateHeaderCounters() {
  const activeCount = state.agents.filter((a) => a.enabled).length;
  document.getElementById('headerActiveAgentsCount').textContent = `${activeCount} / ${state.agents.length}`;
  document.getElementById('headerToolsCount').textContent = `${state.tools.length}`;
  const badgeMcp = document.getElementById('badgeMcpCount');
  if (badgeMcp) badgeMcp.textContent = `${state.mcpServers.length} Servers`;
  const badgeTools = document.getElementById('badgeToolsCount');
  if (badgeTools) badgeTools.textContent = `${state.tools.length} Tools`;
}

// --------------------------------------------------------------------------
// Rendering Tables
// --------------------------------------------------------------------------
function renderAgentsTable() {
  const tbody = document.getElementById('agentsTableBody');
  if (!state.agents || state.agents.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading-td">No agents registered in control plane.</td></tr>';
    return;
  }

function extractCapabilities(item) {
  if (!item) return [];
  if (Array.isArray(item.capabilities)) {
    return item.capabilities.map((c) => String(c).trim()).filter(Boolean);
  }
  const raw = item.capabilities || item.capability || '';
  if (Array.isArray(raw)) {
    return raw.map((c) => String(c).trim()).filter(Boolean);
  }
  return String(raw).split(',').map((c) => c.trim()).filter(Boolean);
}

  tbody.innerHTML = state.agents.map((agent) => {
    const statusBadge = agent.enabled
      ? '<span class="badge badge-enabled">🟢 ENABLED</span>'
      : '<span class="badge badge-disabled">🔴 DISABLED</span>';

    const toggleBtn = agent.enabled
      ? `<button class="btn btn-sm btn-toggle-disable" onclick="toggleAgent('${agent.id}', false)">Disable</button>`
      : `<button class="btn btn-sm btn-toggle-enable" onclick="toggleAgent('${agent.id}', true)">Enable</button>`;

    const capsList = extractCapabilities(agent);
    const caps = capsList.length > 0
      ? capsList.map((c) => `<span class="trace-chip">${escapeHtml(c)}</span>`).join(' ')
      : '<span class="trace-chip">none</span>';

    const limits = agent.policy
      ? `${agent.policy.timeout_seconds || 30}s / max ${agent.policy.max_tool_calls || 5} tools`
      : 'Standard';

    return `
      <tr>
        <td>${statusBadge}</td>
        <td><code>${escapeHtml(agent.id)}</code></td>
        <td><strong>${escapeHtml(agent.name)}</strong></td>
        <td>${caps}</td>
        <td><small>${escapeHtml(agent.model || 'default')}</small></td>
        <td><small>${limits}</small></td>
        <td>${toggleBtn}</td>
      </tr>
    `;
  }).join('');
}

function renderMcpTable() {
  const tbody = document.getElementById('mcpTableBody');
  if (!state.mcpServers || state.mcpServers.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="loading-td">No MCP servers registered.</td></tr>';
    return;
  }

  tbody.innerHTML = state.mcpServers.map((s) => {
    const statusBadge = s.enabled
      ? '<span class="badge badge-enabled">ONLINE</span>'
      : '<span class="badge badge-disabled">OFFLINE</span>';

    const toggleBtn = s.enabled
      ? `<button class="btn btn-sm btn-toggle-disable" onclick="toggleMcp('${s.id}', false)">Disable</button>`
      : `<button class="btn btn-sm btn-toggle-enable" onclick="toggleMcp('${s.id}', true)">Enable</button>`;

    return `
      <tr>
        <td>${statusBadge}</td>
        <td><code>${escapeHtml(s.id)}</code></td>
        <td><strong>${escapeHtml(s.name)}</strong></td>
        <td><code>${escapeHtml(s.endpoint)}</code></td>
        <td><small>${escapeHtml(s.transport)}</small></td>
        <td>${toggleBtn}</td>
      </tr>
    `;
  }).join('');
}

function renderToolsTable() {
  const tbody = document.getElementById('toolsTableBody');
  if (!state.tools || state.tools.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="loading-td">No tools registered.</td></tr>';
    return;
  }

  tbody.innerHTML = state.tools.map((t) => {
    const statusBadge = t.enabled
      ? '<span class="badge badge-enabled">ACTIVE</span>'
      : '<span class="badge badge-disabled">INACTIVE</span>';

    const toggleBtn = t.enabled
      ? `<button class="btn btn-sm btn-toggle-disable" onclick="toggleTool('${t.tool_id}', false)">Disable</button>`
      : `<button class="btn btn-sm btn-toggle-enable" onclick="toggleTool('${t.tool_id}', true)">Enable</button>`;

    return `
      <tr>
        <td>${statusBadge}</td>
        <td><code>${escapeHtml(t.tool_id)}</code></td>
        <td><strong>${escapeHtml(t.name)}</strong></td>
        <td><span class="badge badge-info">${escapeHtml(t.capability)}</span></td>
        <td><code>${escapeHtml(t.provider || 'builtin')}</code></td>
        <td>${toggleBtn}</td>
      </tr>
    `;
  }).join('');
}

function populateProblemSelector() {
  const select = document.getElementById('problemSelect');
  select.innerHTML = '<option value="">-- Select Benchmark Problem (1–10) --</option>' +
    state.benchmarkProblems.map((p) => `
      <option value="${p.id}">Problem ${p.id}: ${p.title} (${p.cities_count} cities${p.impossible ? ' - IMPOSSIBLE' : ''})</option>
    `).join('');
}

function renderBenchmarkTable() {
  const tbody = document.getElementById('benchmarkTableBody');
  if (!state.benchmarkProblems || state.benchmarkProblems.length === 0) return;

  tbody.innerHTML = state.benchmarkProblems.map((p) => {
    const expState = p.impossible
      ? '<span class="badge badge-disabled">IMPOSSIBLE</span>'
      : p.cities_count > 9
      ? '<span class="badge badge-neutral">UNPROVEN</span>'
      : '<span class="badge badge-enabled">OPTIMAL</span>';

    return `
      <tr id="benchRow_${p.id}">
        <td><strong>#${p.id}</strong></td>
        <td>${escapeHtml(p.title)}</td>
        <td>${p.cities_count}</td>
        <td><small>${escapeHtml(p.kind)}</small></td>
        <td>${expState}</td>
        <td id="benchResult_${p.id}"><span class="badge badge-neutral">UNTESTED</span></td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="runSingleBenchmark('${p.id}')">Run</button>
        </td>
      </tr>
    `;
  }).join('');
}

// --------------------------------------------------------------------------
// Relationship Graph (Provider Independence View)
// --------------------------------------------------------------------------
function renderRelationshipGraph() {
  const colAgents = document.getElementById('colAgents');
  const colCaps = document.getElementById('colCapabilities');
  const colTools = document.getElementById('colTools');
  const colProviders = document.getElementById('colProviders');

  colAgents.innerHTML = state.agents.map((a) => `
    <div class="rel-node-card">
      <div class="rel-node-title">${a.enabled ? '🟢' : '🔴'} ${escapeHtml(a.name)}</div>
      <div class="rel-node-sub">ID: ${a.id}</div>
    </div>
  `).join('');

  const distinctCaps = [...new Set(
    state.tools.map((t) => t.capability).filter(Boolean).concat(
      state.agents.flatMap((a) => extractCapabilities(a))
    )
  )];

  colCaps.innerHTML = distinctCaps.map((c) => `
    <div class="rel-node-card">
      <div class="rel-node-title">⚡ ${escapeHtml(c)}</div>
      <div class="rel-node-sub">Semantic Tag</div>
    </div>
  `).join('');

  colTools.innerHTML = state.tools.map((t) => `
    <div class="rel-node-card">
      <div class="rel-node-title">🔧 ${escapeHtml(t.name)}</div>
      <div class="rel-node-sub">Tool: ${t.tool_id} (${t.capability})</div>
    </div>
  `).join('');

  colProviders.innerHTML = state.mcpServers.map((s) => `
    <div class="rel-node-card">
      <div class="rel-node-title">🌐 ${escapeHtml(s.name)}</div>
      <div class="rel-node-sub">${s.endpoint} (${s.transport})</div>
    </div>
  `).join('');
}

// --------------------------------------------------------------------------
// Interactive Toggles (Live Control Plane)
// --------------------------------------------------------------------------
window.toggleAgent = async (agentId, enable) => {
  try {
    const action = enable ? 'enable' : 'disable';
    const res = await fetch(`${API_BASE}/agents/${agentId}/${action}`, { method: 'PATCH' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await loadAgents();
    await loadOverview();
  } catch (err) {
    alert(`Failed to toggle agent: ${err.message}`);
  }
};

window.toggleMcp = async (serverId, enable) => {
  try {
    const action = enable ? 'enable' : 'disable';
    const res = await fetch(`${API_BASE}/mcp-servers/${serverId}/${action}`, { method: 'PATCH' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await loadMcpServers();
    await loadOverview();
  } catch (err) {
    alert(`Failed to toggle MCP server: ${err.message}`);
  }
};

window.toggleTool = async (toolId, enable) => {
  try {
    const action = enable ? 'enable' : 'disable';
    const res = await fetch(`${API_BASE}/tools/${toolId}/${action}`, { method: 'PATCH' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await loadTools();
    await loadOverview();
  } catch (err) {
    alert(`Failed to toggle tool: ${err.message}`);
  }
};

// --------------------------------------------------------------------------
// Execution Studio Handler
// --------------------------------------------------------------------------
function initEventHandlers() {
  document.getElementById('problemSelect').addEventListener('change', (e) => {
    const pid = e.target.value;
    state.activeProblemId = pid || null;
    const prob = state.benchmarkProblems.find((p) => p.id === pid);
    if (prob) {
      document.getElementById('queryInput').value = `Solve ${prob.title} (${prob.cities_count} cities): ${prob.notes || ''}`;
    }
  });

  document.getElementById('btnQuickP1').addEventListener('click', () => selectQuickProblem('1'));
  document.getElementById('btnQuickP7').addEventListener('click', () => selectQuickProblem('7'));
  document.getElementById('btnQuickP9').addEventListener('click', () => selectQuickProblem('9'));
  document.getElementById('btnQuickP10').addEventListener('click', () => selectQuickProblem('10'));

  document.getElementById('btnExecute').addEventListener('click', () => executeTask());
  document.getElementById('btnRefreshGraph').addEventListener('click', () => loadOverview());
  document.getElementById('btnRunAllBenchmarks').addEventListener('click', () => runAllBenchmarks());
}

function selectQuickProblem(id) {
  const select = document.getElementById('problemSelect');
  select.value = id;
  select.dispatchEvent(new Event('change'));
  // Switch to Execution Tab
  document.getElementById('tabBtnExecution').click();
}

async function executeTask() {
  const query = document.getElementById('queryInput').value.trim();
  const problemId = state.activeProblemId;

  if (!query && !problemId) {
    alert('Please enter a query or select a problem.');
    return;
  }

  const spinner = document.getElementById('executionSpinner');
  const btn = document.getElementById('btnExecute');
  spinner.classList.remove('hidden');
  btn.disabled = true;

  resetPipelineVisualizer();

  try {
    const res = await fetch(`${API_BASE}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ problem_id: problemId, query: query }),
    });

    if (!res.ok) {
      const errPayload = await res.json();
      throw new Error(errPayload.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    renderExecutionResponse(data);
  } catch (err) {
    alert(`Execution failed: ${err.message}`);
    document.getElementById('pipelineStatusBadge').className = 'badge badge-disabled';
    document.getElementById('pipelineStatusBadge').textContent = 'ERROR';
  } finally {
    spinner.classList.add('hidden');
    btn.disabled = false;
  }
}

function resetPipelineVisualizer() {
  document.querySelectorAll('.step-node').forEach((node) => {
    node.className = 'step-node';
  });
  document.getElementById('pipelineStatusBadge').className = 'badge badge-info';
  document.getElementById('pipelineStatusBadge').textContent = 'RUNNING';
  document.getElementById('guardrailStateBadge').className = 'guardrail-state-badge';
  document.getElementById('guardrailStateBadge').textContent = 'CHECKING...';
  document.getElementById('finalDecisionText').textContent = 'Orchestrator evaluating...';
}

function renderExecutionResponse(data) {
  // 1. Status & Timing
  const statusBadge = document.getElementById('pipelineStatusBadge');
  if (data.status === 'completed') {
    statusBadge.className = 'badge badge-enabled';
    statusBadge.textContent = 'COMPLETED';
  } else if (data.status === 'completed_abstained') {
    statusBadge.className = 'badge badge-disabled';
    statusBadge.textContent = 'ABSTAINED (IMPOSSIBLE)';
  } else if (data.status === 'rejected') {
    statusBadge.className = 'badge badge-disabled';
    statusBadge.textContent = 'REJECTED';
  } else {
    statusBadge.className = 'badge badge-disabled';
    statusBadge.textContent = data.status.toUpperCase();
  }

  document.getElementById('pipelineDurationBadge').textContent = `${data.duration_ms} ms`;

  // 2. Animate Stepper Nodes
  const nodes = [
    { id: 'nodeTaskAnalyzer', sub: data.capabilities.join(', ') },
    { id: 'nodeCapabilityResolver', sub: 'Bound to MCP tools' },
    { id: 'nodeScopedPool', sub: `${data.scoped_agents.length} agents active` },
    { id: 'nodeSpecialists', sub: `${data.specialist_recommendations.length} recommendations` },
    { id: 'nodeCriticRefiner', sub: data.critic_evaluation.valid ? 'Passed review' : 'Challenged' },
    { id: 'nodeGuardrail', sub: data.guardrail_state },
    { id: 'nodeFinalDecision', sub: 'Decision rendered' },
  ];

  nodes.forEach((item, index) => {
    const el = document.getElementById(item.id);
    if (el) {
      setTimeout(() => {
        el.className = 'step-node node-passed';
        const subEl = el.querySelector('.node-sub');
        if (subEl) subEl.textContent = item.sub;
      }, index * 60);
    }
  });

  // 3. Guardrail Badge & Explanation
  const guardBadge = document.getElementById('guardrailStateBadge');
  const guardExp = document.getElementById('guardrailExplanation');
  const gState = (data.guardrail_state || 'UNKNOWN').toUpperCase();

  guardBadge.className = 'guardrail-state-badge';
  if (gState === 'OPTIMAL') {
    guardBadge.classList.add('state-optimal');
  } else if (gState === 'FEASIBLE') {
    guardBadge.classList.add('state-feasible');
  } else if (gState === 'UNPROVEN') {
    guardBadge.classList.add('state-unproven');
  } else if (gState === 'IMPOSSIBLE') {
    guardBadge.classList.add('state-impossible');
  }
  guardBadge.textContent = gState;
  guardExp.textContent = data.guardrail_reason || 'Deterministic truth verified.';

  // 4. Final Decision
  document.getElementById('finalDecisionText').textContent = data.final_decision;

  // 5. Specialist Recommendations
  const specContainer = document.getElementById('specialistResultsContainer');
  if (data.specialist_recommendations && data.specialist_recommendations.length > 0) {
    specContainer.innerHTML = data.specialist_recommendations.map((r) => `
      <div class="specialist-item">
        <div class="specialist-item-head">
          <span>⚙️ Specialist: ${escapeHtml(r.agent_id)}</span>
          <span class="badge badge-info">Tool Recommendation</span>
        </div>
        <div class="specialist-item-rec">${escapeHtml(r.recommendation)}</div>
      </div>
    `).join('');
  } else {
    specContainer.innerHTML = '<div class="empty-state">No specialist recommendations (Execution rejected before invocation).</div>';
  }

  // 6. Trace Hops
  const traceContainer = document.getElementById('traceHopsContainer');
  traceContainer.innerHTML = data.trace.map((hop) => `
    <span class="trace-chip hop-active">${escapeHtml(hop)}</span>
  `).join(' → ');
}

// --------------------------------------------------------------------------
// Benchmark Runner
// --------------------------------------------------------------------------
window.runSingleBenchmark = async (problemId) => {
  const resultCell = document.getElementById(`benchResult_${problemId}`);
  if (resultCell) resultCell.innerHTML = '<span class="spinner"></span>';

  try {
    const res = await fetch(`${API_BASE}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ problem_id: problemId }),
    });
    const data = await res.json();
    if (resultCell) {
      const gState = data.guardrail_state;
      const isPassed = data.status.startsWith('completed');
      resultCell.innerHTML = `
        <span class="badge ${isPassed ? 'badge-enabled' : 'badge-disabled'}">
          ${isPassed ? 'PASS' : 'FAIL'} (${gState})
        </span>
      `;
    }
  } catch (err) {
    if (resultCell) resultCell.innerHTML = `<span class="badge badge-disabled">ERR</span>`;
  }
};

async function runAllBenchmarks() {
  const btn = document.getElementById('btnRunAllBenchmarks');
  btn.disabled = true;
  for (const prob of state.benchmarkProblems) {
    await window.runSingleBenchmark(prob.id);
  }
  btn.disabled = false;
}

// --------------------------------------------------------------------------
// Modal (Register New Agent at Runtime)
// --------------------------------------------------------------------------
function initModal() {
  const modal = document.getElementById('addAgentModal');
  const btnOpen = document.getElementById('btnOpenAddAgentModal');
  const btnClose = document.getElementById('btnCloseAddAgentModal');
  const btnCancel = document.getElementById('btnCancelAddAgent');
  const form = document.getElementById('formAddAgent');

  btnOpen.addEventListener('click', () => modal.classList.remove('hidden'));
  btnClose.addEventListener('click', () => modal.classList.add('hidden'));
  btnCancel.addEventListener('click', () => modal.classList.add('hidden'));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('newAgentId').value.trim();
    const name = document.getElementById('newAgentName').value.trim();
    const caps = document.getElementById('newAgentCapabilities').value.split(',').map((c) => c.trim()).filter(Boolean);
    const model = document.getElementById('newAgentModel').value.trim();
    const description = document.getElementById('newAgentDescription').value.trim();

    try {
      const payload = {
        id: id,
        name: name,
        capabilities: caps,
        model: model,
        description: description,
        enabled: true,
      };

      const res = await fetch(`${API_BASE}/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || `HTTP ${res.status}`);
      }

      modal.classList.add('hidden');
      form.reset();
      await loadAgents();
      await loadOverview();
      alert(`Agent '${id}' registered successfully without restarting!`);
    } catch (err) {
      alert(`Failed to register agent: ${err.message}`);
    }
  });
}

// --------------------------------------------------------------------------
// Utility
// --------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
