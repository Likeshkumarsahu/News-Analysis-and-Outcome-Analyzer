const API = "";

// ── Navigation ────────────────────────────────────────────
function showSection(name) {
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  document.getElementById("section-" + name).classList.add("active");
  event.currentTarget.classList.add("active");
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

  showLoader(true);
  hideError();
  document.getElementById("results").classList.add("hidden");

  try {
    const res  = await fetch(`${API}/api/analyze`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ query }),
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

document.getElementById("query-input")
  .addEventListener("keydown", e => { if (e.key === "Enter") analyzeQuery(); });

checkStatus();