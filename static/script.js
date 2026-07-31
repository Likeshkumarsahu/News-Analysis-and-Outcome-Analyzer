window.showSection = function(name, btn) {
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const sec = document.getElementById("section-" + name);
  if (sec) sec.classList.add("active");
  if (btn) btn.classList.add("active");
}


const API = "";

let currentProvider = localStorage.getItem("newsana_provider") || "local";
let groqApiKey       = localStorage.getItem("newsana_groq_key") || "";
let groqModel        = localStorage.getItem("newsana_groq_model") || "";

window.setProvider = function(provider) {
  currentProvider = provider;
  localStorage.setItem("newsana_provider", provider);

  document.getElementById("provider-local-btn").classList.toggle("active", provider === "local");
  document.getElementById("provider-groq-btn").classList.toggle("active", provider === "groq");
  document.getElementById("groq-config").classList.toggle("hidden", provider !== "groq");

  if (provider === "local") checkOllamaStatus();
  else updateProviderStatus("");
}

window.saveGroqConfig = function() {
  const model = document.getElementById("groq-model-select").value;
  const key   = document.getElementById("groq-api-key").value.trim();

  if (!model) { alert("Select a Groq model first."); return; }
  if (!key)   { alert("Enter your Groq API key."); return; }

  groqModel  = model;
  groqApiKey = key;
  localStorage.setItem("newsana_groq_model", model);
  localStorage.setItem("newsana_groq_key", key);
  updateProviderStatus("✅ Groq configured: " + model);
}

async function checkOllamaStatus() {
  updateProviderStatus("Checking Ollama...");
  try {
    const res  = await fetch(`${API}/api/llm/status`);
    const data = await res.json();

    populateGroqModels(data.groq_models || []);

    if (data.connected && data.model_available) {
      updateProviderStatus("✅ Ollama connected and ready");
    } else {
      updateProviderStatus("⚠️ " + data.message);
    }
  } catch {
    updateProviderStatus("⚠️ Could not reach backend");
  }
}

function populateGroqModels(models) {
  const sel = document.getElementById("groq-model-select");
  if (sel.options.length > 1) return; // already populated
  models.forEach(m => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    if (m === groqModel) opt.selected = true;
    sel.appendChild(opt);
  });
}

function updateProviderStatus(msg) {
  document.getElementById("provider-status").textContent = msg;
}

// ── Navigation ────────────────────────────────────────────
function showSection(name, btn) {
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const sec = document.getElementById("section-" + name);
  if (sec) sec.classList.add("active");
  if (btn) btn.classList.add("active");
}

// ── Status ────────────────────────────────────────────────
async function checkStatus() {
  try {
    const res  = await fetch(`${API}/api/status`);
    const data = await res.json();
    const el   = document.getElementById("status-pill");
    if (data.status === "ok") {
      el.textContent = `✅ ${data.articles_in_db} articles`;
      el.style.color = "var(--green)";
    } else {
      el.textContent = "⚠️ DB error";
    }
  } catch {
    document.getElementById("status-pill").textContent = "⚠️ Offline";
  }
}

// ── Analyze ───────────────────────────────────────────────
async function analyzeQuery() {
  const query = document.getElementById("query-input").value.trim();
  if (!query) return;

  if (currentProvider === "groq" && (!groqApiKey || !groqModel)) {
    showError("Select a Groq model and enter your API key first.");
    return;
  }

  showLoader(true);
  hideError();
  document.getElementById("results").classList.add("hidden");

  try {
    const res  = await fetch(`${API}/api/analyze`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        query,
        provider: currentProvider,
        groq_model: currentProvider === "groq" ? groqModel : undefined,
        groq_api_key: currentProvider === "groq" ? groqApiKey : undefined,
      }),
    });
    const data = await res.json();

    if (!res.ok || data.error) { showError(data.error || "Something went wrong."); return; }
    renderResults(data);

  } catch {
    showError("Could not reach the server. Is Flask running?");
  } finally {
    showLoader(false);
  }
}

// ── Ingest ────────────────────────────────────────────────
async function triggerIngest() {
  const btn = document.querySelector(".btn-refresh");
  btn.textContent = "⏳ Refreshing...";
  btn.disabled = true;
  try {
    const res  = await fetch(`${API}/api/ingest`, { method: "POST" });
    const data = await res.json();
    alert(data.message || data.error);
    checkStatus();
  } catch { alert("Ingestion failed."); }
  finally {
    btn.textContent = "🔄 Refresh News";
    btn.disabled = false;
  }
}

// ── Render ────────────────────────────────────────────────
function renderResults(data) {
  // Sentiment
  const sLabel = (data.sentiment.label || "").toUpperCase();
  const sConf  = data.sentiment.confidence;
  const sEl    = document.getElementById("sentiment-label");
  sEl.textContent = sLabel;
  sEl.className   = `card-value ${sLabel}`;
  document.getElementById("sentiment-conf").textContent = `Confidence: ${(sConf * 100).toFixed(1)}%`;
  document.getElementById("sentiment-bar").style.width = `${sConf * 100}%`;

  // Impact
  const iLabel = (data.outcome.impact || "").toUpperCase();
  const iConf  = data.outcome.confidence;
  const iEl    = document.getElementById("impact-label");
  iEl.textContent = iLabel;
  iEl.className   = `card-value ${iLabel}`;
  document.getElementById("impact-conf").textContent = `Confidence: ${(iConf * 100).toFixed(0)}%`;
  document.getElementById("impact-bar").style.width = `${iConf * 100}%`;

  // Sources count
  document.getElementById("sources-count").textContent = data.articles.length;
  const sources = [...new Set(data.articles.map(a => a.source))].join(", ");
  document.getElementById("sources-names").textContent = sources;

  // Signals
  const sigList = document.getElementById("signals-list");
  sigList.innerHTML = "";
  if (data.outcome.matched?.length) {
    data.outcome.matched.forEach(kw => {
      const t = document.createElement("span");
      t.className   = "tag";
      t.textContent = kw;
      sigList.appendChild(t);
    });
  } else {
    sigList.innerHTML = "<span style='color:var(--text3);font-size:0.82rem'>No strong signals</span>";
  }

  // Explanation
  document.getElementById("explanation-text").textContent = data.explanation;

  // XAI
  if (data.xai) renderXAI(data.xai);

  // Articles
  const artList = document.getElementById("articles-list");
  artList.innerHTML = "";
  data.articles.forEach(art => {
    artList.innerHTML += `
      <div class="article-card">
        <div class="article-top">
          <div class="article-title">${escHtml(art.title)}</div>
          <span class="score-badge">score: ${art.score}</span>
        </div>
        <div class="article-meta">${escHtml(art.source)} · ${escHtml(art.published || "")}</div>
        <div class="article-snippet">${escHtml(art.text)}</div>
        <a class="article-link" href="${escHtml(art.link)}" target="_blank" rel="noopener">Read full article →</a>
      </div>`;
  });

  document.getElementById("results").classList.remove("hidden");
}

function renderXAI(xai) {
  const block = document.getElementById("xai-block");
  if (!block) return;

  const s = xai.sentiment;
  const o = xai.outcome;

  if (!s && !o) { block.innerHTML = "<span style='color:var(--text3)'>XAI not available</span>"; return; }

  block.innerHTML = `
    <div class="xai-row">
      <div>
        <div class="xai-section-title">Sentiment — <span class="${s?.label}">${s?.label || "—"}</span></div>
        <p class="xai-desc">${escHtml(s?.explanation || "")}</p>
        <div class="xai-words">
          ${(s?.top_words || []).slice(0,6).map(w => `
            <span class="xai-word ${w.direction}" title="weight: ${w.weight}">
              ${escHtml(w.word)}
              <span class="xai-bar" style="width:${Math.min(Math.abs(w.weight)*250,50)}px"></span>
            </span>`).join("")}
        </div>
      </div>
      <div>
        <div class="xai-section-title">Impact — <span class="${o?.impact}">${o?.impact || "—"}</span></div>
        <p class="xai-desc">${escHtml(o?.explanation || "")}</p>
        <div class="xai-words">
          ${(o?.top_words || []).slice(0,6).map(w => `
            <span class="xai-word ${w.direction}" title="weight: ${w.weight}">
              ${escHtml(w.word)}
              <span class="xai-bar" style="width:${Math.min(Math.abs(w.weight)*250,50)}px"></span>
            </span>`).join("")}
        </div>
      </div>
    </div>`;
}

// ── Helpers ───────────────────────────────────────────────
function showLoader(on) {
  document.getElementById("loader").classList.toggle("hidden", !on);
  document.getElementById("analyze-btn").disabled = on;
}

function hideError() {
  const el = document.getElementById("error-box");
  el.classList.add("hidden");
  el.textContent = "";
}

function showError(msg) {
  const el = document.getElementById("error-box");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function escHtml(str) {
  return String(str || "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

window.addEventListener("load", () => {
  const qi = document.getElementById("query-input");
  if (qi) qi.addEventListener("keydown", e => { if (e.key === "Enter") analyzeQuery(); });
});

checkStatus();

// ── Knowledge Graph ───────────────────────────────────────
const KG_COLORS = {
  PERSON: '#5B8AF5',
  ORG:    '#4BBFA5',
  GPE:    '#F5A623',
  EVENT:  '#E24B4A',
  NORP:   '#A78BFA',
  OTHER:  '#888',
};

let kgData = null;
let kgSim  = null;
let kgType = 'ALL';

async function loadGraph() {
  const btn = document.getElementById('graph-load-btn');
  const status = document.getElementById('graph-status');
  btn.disabled = true;
  btn.textContent = '⏳ Loading...';
  status.textContent = '';

  try {
    const res  = await fetch('/api/graph');
    const data = await res.json();
    if (data.error) { status.textContent = data.error; return; }
    kgData = data;
    renderGraph(data);
    renderGraphMeta(data);
  } catch(e) {
    status.textContent = 'Failed to load graph: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Load Graph';
  }
}

async function rebuildGraph() {
  const btn = document.getElementById('graph-rebuild-btn');
  const status = document.getElementById('graph-status');
  btn.disabled = true;
  btn.textContent = '⏳ Rebuilding...';
  try {
    const res  = await fetch('/api/graph/rebuild', { method: 'POST' });
    const data = await res.json();
    status.textContent = data.message || data.error;
    if (!data.error) await loadGraph();
  } catch(e) {
    status.textContent = 'Rebuild failed: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '🔄 Rebuild from DB';
  }
}

function renderGraphMeta(data) {
  const types = [...new Set(data.nodes.map(n => n.type))];

  // Stats
  document.getElementById('graph-stats-row').innerHTML = `
    ${[
      ['Entities', data.nodes.length],
      ['Relations', data.links.length],
      ['Types', types.length],
    ].map(([l,v]) => `
      <div style="background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:10px 18px;text-align:center;flex:1;min-width:80px">
        <div style="font-size:1.4rem;font-weight:700;color:var(--accent)">${v}</div>
        <div style="font-size:11px;color:var(--text2);margin-top:2px">${l}</div>
      </div>`).join('')}
  `;

  // Filter buttons
  document.getElementById('graph-controls').innerHTML = `
    <span style="font-size:12px;color:var(--text2);align-self:center">Filter:</span>
    ${['ALL', ...types].map(t => `
      <button class="filter-btn${t==='ALL'?' kg-active':''}"
        onclick="kgFilter('${t}',this)"
        style="padding:4px 12px;border-radius:20px;border:1px solid var(--border2);
               background:${t==='ALL'?'var(--accent)':'transparent'};
               color:${t==='ALL'?'#0a0c10':'var(--text2)'};
               font-size:12px;cursor:pointer">
        ${t}
      </button>`).join('')}
  `;

  // Legend
  document.getElementById('graph-legend').innerHTML = `
    <span style="font-size:11px;color:var(--text2)">Entity types:</span>
    ${Object.entries(KG_COLORS).map(([t,c]) => `
      <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text2)">
        <div style="width:10px;height:10px;border-radius:50%;background:${c};flex-shrink:0"></div>${t}
      </div>`).join('')}
    <span style="font-size:11px;color:var(--text2);margin-left:8px">Node size = mentions · Drag to explore</span>
  `;
}

function kgFilter(type, btn) {
  kgType = type;
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.style.background = 'transparent';
    b.style.color = 'var(--text2)';
  });
  btn.style.background = 'var(--accent)';
  btn.style.color = '#0a0c10';
  if (kgData) renderGraph(kgData);
}

function renderGraph(data) {
  document.getElementById('graph-placeholder').style.display = 'none';
  const svgEl = document.getElementById('kg-svg');
  svgEl.style.display = 'block';

  // Filter
  const nodes = kgType === 'ALL'
    ? data.nodes.map(n => ({...n}))
    : data.nodes.filter(n => n.type === kgType).map(n => ({...n}));
  const ids = new Set(nodes.map(n => n.id));
  const links = data.links
    .filter(l => ids.has(l.source.id||l.source) && ids.has(l.target.id||l.target))
    .map(l => ({...l}));

  const W = svgEl.clientWidth  || 680;
  const H = svgEl.clientHeight || 560;

  const svg = d3.select('#kg-svg');
  svg.selectAll('*').remove();

  // Defs
  svg.append('defs').append('marker')
    .attr('id','kgarrow').attr('viewBox','0 0 10 6')
    .attr('refX',10).attr('refY',3)
    .attr('markerWidth',6).attr('markerHeight',6)
    .attr('orient','auto')
    .append('path').attr('d','M0,0L10,3L0,6').attr('fill','#555').attr('opacity',0.6);

  const g = svg.append('g');
  svg.call(d3.zoom().scaleExtent([0.2,4]).on('zoom', e => g.attr('transform', e.transform)));

  const r = d => Math.max(9, Math.min(26, 7 + (d.mentions||1)*1.5));

  const sim = d3.forceSimulation(nodes)
    .force('link',      d3.forceLink(links).id(d => d.id).distance(d => 70 + (d.weight||1)*12))
    .force('charge',    d3.forceManyBody().strength(-200))
    .force('center',    d3.forceCenter(W/2, H/2))
    .force('collision', d3.forceCollide().radius(d => r(d)+6));

  kgSim = sim;

  const link = g.append('g').selectAll('line').data(links).join('line')
    .attr('stroke', d => KG_COLORS[(d.source.type||d.source)] || '#555')
    .attr('stroke-opacity', 0.4)
    .attr('stroke-width', d => Math.max(0.8, (d.weight||1)*0.6))
    .attr('marker-end','url(#kgarrow)');

  const node = g.append('g').selectAll('g').data(nodes).join('g')
    .style('cursor','pointer')
    .call(d3.drag()
      .on('start', (e,d) => { if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
      .on('drag',  (e,d) => { d.fx=e.x; d.fy=e.y; })
      .on('end',   (e,d) => { if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }))
    .on('mouseover', (e,d) => kgTooltip(e,d,true))
    .on('mouseout',  ()    => kgTooltip(null,null,false))
    .on('click',     (e,d) => kgHighlight(d, node, link));

  node.append('circle')
    .attr('r',    d => r(d))
    .attr('fill', d => KG_COLORS[d.type]||KG_COLORS.OTHER)
    .attr('fill-opacity', 0.82)
    .attr('stroke', d => KG_COLORS[d.type]||KG_COLORS.OTHER)
    .attr('stroke-opacity', 0.4)
    .attr('stroke-width', 1.5);

  node.append('text')
    .attr('dy', d => r(d)+12)
    .attr('text-anchor','middle')
    .attr('font-size','10px')
    .attr('fill','var(--text2)')
    .text(d => d.id.length > 12 ? d.id.slice(0,11)+'…' : d.id);

  sim.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => {
        const dx=d.target.x-d.source.x, dy=d.target.y-d.source.y;
        const l=Math.sqrt(dx*dx+dy*dy)||1;
        return d.target.x - dx/l*(r(d.target)+3);
      })
      .attr('y2', d => {
        const dx=d.target.x-d.source.x, dy=d.target.y-d.source.y;
        const l=Math.sqrt(dx*dx+dy*dy)||1;
        return d.target.y - dy/l*(r(d.target)+3);
      });
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
}

function kgHighlight(d, node, link) {
  const connected = new Set([d.id]);
  link.each(l => {
    const s=l.source.id||l.source, t=l.target.id||l.target;
    if(s===d.id) connected.add(t);
    if(t===d.id) connected.add(s);
  });
  node.selectAll('circle').attr('opacity', n => connected.has(n.id)?1:0.12);
  node.selectAll('text').attr('opacity',   n => connected.has(n.id)?1:0.12);
  link.attr('opacity', l => {
    const s=l.source.id||l.source, t=l.target.id||l.target;
    return (s===d.id||t===d.id) ? 1 : 0.03;
  });
}

function kgTooltip(e, d, show) {
  const tt = document.getElementById('kg-tooltip');
  if (!show || !d) { tt.style.opacity=0; kgResetHighlight(); return; }
  const wrap = document.getElementById('graph-container');
  const rect = wrap.getBoundingClientRect();
  tt.innerHTML = `
    <div style="font-weight:500;font-size:13px;margin-bottom:3px">${d.id}</div>
    <div style="font-size:11px;color:var(--text2);margin-bottom:3px">${d.type}</div>
    <div style="font-size:11px;color:var(--accent)">${d.mentions} mentions</div>
  `;
  tt.style.opacity = 1;
  const x = e.clientX - rect.left + 12;
  const y = e.clientY - rect.top  - 10;
  tt.style.left = Math.min(x, wrap.clientWidth-210)+'px';
  tt.style.top  = Math.max(y-80, 8)+'px';
}

function kgResetHighlight() {
  d3.selectAll('#kg-svg circle').attr('opacity',1);
  d3.selectAll('#kg-svg text').attr('opacity',1);
  d3.selectAll('#kg-svg line').attr('opacity',0.4);
}

window.analyzeQuery   = analyzeQuery;
window.triggerIngest  = triggerIngest;
window.loadGraph      = loadGraph;
window.rebuildGraph   = rebuildGraph;
window.kgFilter       = kgFilter;



// ── CrewAI ───────────────────────────────────────────────
window.runCrew = async function() {
  const query = document.getElementById("query-input").value.trim();
  if (!query) { alert("Enter a query first"); return; }

  const btn = document.getElementById("crew-btn");
  btn.disabled = true;
  btn.textContent = "⏳ Running agents...";

  document.getElementById("crew-results").classList.remove("hidden");
  document.getElementById("crew-loading").classList.remove("hidden");
  document.getElementById("crew-content").innerHTML = "";

  try {
    const res  = await fetch(`${API}/api/crew`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ query }),
    });
    const data = await res.json();

    if (data.error) {
      document.getElementById("crew-content").innerHTML =
        `<p style="color:var(--red)">${escHtml(data.error)}</p>`;
      return;
    }

    document.getElementById("crew-content").innerHTML = `
      <div style="display:grid;gap:14px;margin-top:4px">
        <div>
          <div style="font-size:11px;color:var(--text3);text-transform:uppercase;
                      letter-spacing:1px;margin-bottom:6px">
            🔍 Analyst Agent
          </div>
          <p style="font-size:0.88rem;color:var(--text2);line-height:1.7;
                    white-space:pre-wrap">${escHtml(data.analysis)}</p>
        </div>
        <div>
          <div style="font-size:11px;color:var(--text3);text-transform:uppercase;
                      letter-spacing:1px;margin-bottom:6px">
            ⚡ Predictor Agent
          </div>
          <p style="font-size:0.88rem;color:var(--text2);line-height:1.7;
                    white-space:pre-wrap">${escHtml(data.predictions)}</p>
        </div>
        <div>
          <div style="font-size:11px;color:var(--text3);text-transform:uppercase;
                      letter-spacing:1px;margin-bottom:6px">
            ✅ Critic Agent
          </div>
          <p style="font-size:0.88rem;color:var(--text2);line-height:1.7;
                    white-space:pre-wrap">${escHtml(data.critique)}</p>
        </div>
        <div style="background:var(--bg3);border-radius:8px;padding:14px">
          <div style="font-size:11px;color:var(--accent);text-transform:uppercase;
                      letter-spacing:1px;margin-bottom:6px">
            📋 Executive Summary
          </div>
          <p style="font-size:0.92rem;color:var(--text);line-height:1.7;
                    white-space:pre-wrap">${escHtml(data.final_summary)}</p>
        </div>
      </div>`;

  } catch(e) {
    document.getElementById("crew-content").innerHTML =
      `<p style="color:var(--red)">Request failed: ${e.message}</p>`;
  } finally {
    document.getElementById("crew-loading").classList.add("hidden");
    btn.disabled = false;
    btn.textContent = "🤖 Deep Analysis (CrewAI)";
  }
}

window.addEventListener("load", () => {
  setProvider(currentProvider);
});