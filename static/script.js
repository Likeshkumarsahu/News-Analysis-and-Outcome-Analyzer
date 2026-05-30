const API = "";   // same origin

// ── Status bar ────────────────────────────────────────────────────────────────
async function checkStatus() {
  try {
    const res  = await fetch(`${API}/api/status`);
    const data = await res.json();
    const bar  = document.getElementById("status-bar");
    if (data.status === "ok") {
      bar.textContent = `✅ DB ready — ${data.articles_in_db} articles indexed`;
      bar.style.color = "#68d391";
    } else {
      bar.textContent = "⚠️ DB error";
      bar.style.color = "#fc8181";
    }
  } catch {
    document.getElementById("status-bar").textContent = "⚠️ Server offline";
  }
}

// ── Analyze ───────────────────────────────────────────────────────────────────
async function analyzeQuery() {
  const query = document.getElementById("query-input").value.trim();
  if (!query) return;

  showLoader(true);
  hideError();
  hideResults();

  try {
    const res  = await fetch(`${API}/api/analyze`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ query }),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || "Something went wrong.");
      return;
    }

    renderResults(data);

  } catch (err) {
    showError("Could not reach the server. Is Flask running?");
  } finally {
    showLoader(false);
  }
}

// ── Ingest ────────────────────────────────────────────────────────────────────
async function triggerIngest() {
  const btn = document.getElementById("ingest-btn");
  btn.textContent = "⏳ Refreshing...";
  btn.disabled = true;

  try {
    const res  = await fetch(`${API}/api/ingest`, { method: "POST" });
    const data = await res.json();
    alert(data.message || data.error);
    checkStatus();
  } catch {
    alert("Ingestion failed. Check server logs.");
  } finally {
    btn.textContent = "🔄 Refresh News";
    btn.disabled = false;
  }
}

// ── Render ────────────────────────────────────────────────────────────────────
function renderResults(data) {
  if (data.xai) renderXAI(data.xai);
  // Sentiment card
  const sLabel = data.sentiment.label;
  const sEl    = document.getElementById("sentiment-label");
  sEl.textContent  = sLabel;
  sEl.className    = `card-value ${sLabel}`;
  document.getElementById("sentiment-conf").textContent =
    `Confidence: ${(data.sentiment.confidence * 100).toFixed(1)}%`;

  // Impact card
  const iLabel = data.outcome.impact;
  const iEl    = document.getElementById("impact-label");
  iEl.textContent = iLabel;
  iEl.className   = `card-value ${iLabel}`;
  document.getElementById("impact-conf").textContent =
    `Confidence: ${(data.outcome.confidence * 100).toFixed(0)}%`;

  // Impact signals
  const signalsList = document.getElementById("signals-list");
  signalsList.innerHTML = "";
  if (data.outcome.matched && data.outcome.matched.length > 0) {
    data.outcome.matched.forEach(kw => {
      const tag = document.createElement("span");
      tag.className   = "signal-tag";
      tag.textContent = kw;
      signalsList.appendChild(tag);
    });
  } else {
    signalsList.innerHTML = "<span style='color:#4a5568;font-size:0.85rem'>No strong signals detected</span>";
  }

  // Explanation
  document.getElementById("explanation-text").textContent = data.explanation;

  // Articles
  const articlesList = document.getElementById("articles-list");
  articlesList.innerHTML = "";
  data.articles.forEach(art => {
    articlesList.innerHTML += `
      <div class="article-card">
        <div class="article-title">
          ${escHtml(art.title)}
          <span class="score-badge">score: ${art.score}</span>
        </div>
        <div class="article-meta">${escHtml(art.source)} · ${escHtml(art.published || "")}</div>
        <div class="article-snippet">${escHtml(art.text)}</div>
        <a class="article-link" href="${escHtml(art.link)}" target="_blank" rel="noopener">
          Read full article →
        </a>
      </div>`;
  });

  document.getElementById("results").classList.remove("hidden");
}

function renderXAI(xai) {
  // Find or create XAI section
  let xaiBlock = document.getElementById("xai-block");
  if (!xaiBlock) return;

  const s = xai.sentiment;
  const o = xai.outcome;

  let html = `
    <div class="xai-section">
      <div class="xai-title">Sentiment XAI — <span class="${s.label}">${s.label}</span></div>
      <p class="xai-desc">${s.explanation}</p>
      <div class="xai-words">
        ${s.top_words.slice(0,6).map(w => `
          <span class="xai-word ${w.direction}" title="weight: ${w.weight}">
            ${escHtml(w.word)}
            <span class="xai-bar" style="width:${Math.min(Math.abs(w.weight)*200,60)}px"></span>
          </span>`).join("")}
      </div>
    </div>
    <div class="xai-section" style="margin-top:14px">
      <div class="xai-title">Impact XAI — <span class="${o.impact}">${o.impact}</span></div>
      <p class="xai-desc">${o.explanation}</p>
      <div class="xai-words">
        ${o.top_words.slice(0,6).map(w => `
          <span class="xai-word ${w.direction}" title="weight: ${w.weight}">
            ${escHtml(w.word)}
            <span class="xai-bar" style="width:${Math.min(Math.abs(w.weight)*200,60)}px"></span>
          </span>`).join("")}
      </div>
    </div>`;

  xaiBlock.innerHTML = html;
}

async function runEvaluation() {
  const btn = document.getElementById("eval-btn");
  btn.textContent = "⏳ Evaluating... (1-2 min)";
  btn.disabled = true;

  try {
    const res  = await fetch(`${API}/api/evaluate`, { method: "POST" });
    const data = await res.json();

    if (data.error) {
      alert("Evaluation failed: " + data.error);
      return;
    }

    const s = data.scores;
    alert(
      `RAGAS Evaluation Results\n\n` +
      `Faithfulness:      ${s.faithfulness}\n` +
      `Answer Relevancy:  ${s.answer_relevancy}\n` +
      `Context Recall:    ${s.context_recall}\n` +
      `Context Precision: ${s.context_precision}\n` +
      `─────────────────────────\n` +
      `Overall Score:     ${s.overall}`
    );
  } catch {
    alert("Evaluation request failed.");
  } finally {
    btn.textContent = "📊 Run Evaluation";
    btn.disabled = false;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
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

function hideResults() {
  document.getElementById("results").classList.add("hidden");
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Enter key triggers analyze
document.getElementById("query-input")
  .addEventListener("keydown", e => { if (e.key === "Enter") analyzeQuery(); });

// Check status on load
checkStatus();