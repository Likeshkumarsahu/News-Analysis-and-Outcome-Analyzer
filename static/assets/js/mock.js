/**
 * ============================================================================
 * NEWSANA AI — DEMO DATA ENGINE & MOCK PAYLOAD GENERATOR
 * ============================================================================
 * @file mock.js
 * @description Mock data generator module creating realistic news items,
 * prediction metrics, time-series data, knowledge graphs, CrewAI log streams,
 * and research reports for offline fallback and demonstration modes.
 *
 * Public API (all accessed via `Newsana.mock`):
 *   .TRENDING       — Array of trending topic chips
 *   .SUGGESTIONS    — Array of autocomplete search suggestions
 *   .status()       — Returns mock system health payload
 *   .analysis(q, o) — Returns full analysis payload matching /api/analyze
 *   .crew(topic)    — Returns CrewAI pipeline initialization payload
 *   .graph()        — Returns D3 knowledge graph node/link data
 *   .gaugeArc(val)  — Returns SVG arc offset for the outcome gauge
 * ============================================================================
 */

(function (root) {
  "use strict";

  var U = root.Newsana.utils;
  var CFG = root.NewsanaConfig;
  var C = CFG.THEME.colors;
  var P = CFG.THEME.palette;

  /* ── Static Data Pools ───────────────────────────────────────────────── */

  /** Sample trending topics for hero search bar chips */
  var TRENDING = [
    { label: "US Presidential Election 2026", hot: true, tag: "politics" },
    { label: "Federal Rate Decision", hot: true, tag: "macro" },
    { label: "AI Regulation Bill", hot: true, tag: "tech" },
    { label: "S&P 500 Earnings Season", hot: false, tag: "markets" },
    { label: "Semiconductor Supply Crunch", hot: true, tag: "tech" },
    { label: "Global Heatwave Outlook", hot: false, tag: "climate" },
    { label: "Quantum Computing Breakthrough", hot: true, tag: "tech" },
    { label: "OPEC Production Cuts", hot: false, tag: "energy" },
    { label: "EU Digital Markets Act", hot: false, tag: "regulation" },
    { label: "EV Market Share War", hot: false, tag: "markets" }
  ];

  /** Search suggestion autocomplete prompts */
  var SUGGESTIONS = [
    "Predict Fed decision in September",
    "Tesla stock forecast",
    "Chip geopolitics and supply chains",
    "Global economy outlook",
    "EV market share battle",
    "AI regulation timeline",
    "Oil price direction this quarter",
    "Election impact on markets"
  ];

  /** Simulated pool of news headlines and metadata */
  var NEWS_POOL = [
    { title: "Central banks signal patience as inflation cools to 3.1%", source: "Reuters", cat: "macro", sent: "bull", rel: 98, excerpt: "Policymakers see scope for measured easing while core services inflation remains sticky.", gradient: "linear-gradient(135deg,#1e3a8a,#312e81 55%,#4c1d95)" },
    { title: "Nvidia supplier plans $12B US fabrication expansion amid export controls", source: "Bloomberg", cat: "tech", sent: "bull", rel: 96, excerpt: "The build-out targets advanced packaging capacity to relieve the AI accelerator bottleneck.", gradient: "linear-gradient(135deg,#0f172a,#1e1b4b 50%,#3b0764)" },
    { title: "Equity futures edge higher ahead of key payrolls print", source: "CNBC", cat: "markets", sent: "bull", rel: 92, excerpt: "Traders price a 72% chance of a September cut; yields dip as risk appetite firms.", gradient: "linear-gradient(135deg,#064e3b,#134e4a 55%,#164e63)" },
    { title: "EU drafts sweeping data-gatekeeper rules for large platforms", source: "Politico", cat: "regulation", sent: "bear", rel: 90, excerpt: "Compliance costs could hit $40B across the industry in the next three fiscal years.", gradient: "linear-gradient(135deg,#581c87,#4c1d95 55%,#6b21a8)" },
    { title: "Oil slides 4% as OPEC+ debates output hike amid demand jitters", source: "Financial Times", cat: "energy", sent: "bear", rel: 88, excerpt: "A wider surplus is projected for Q4 as inventories rebuild across key hubs.", gradient: "linear-gradient(135deg,#7c2d12,#9a3412 55%,#b45309)" },
    { title: "Election ad spending hits record $19B reshaping media economics", source: "The Wall Street Journal", cat: "politics", sent: "hold", rel: 87, excerpt: "Local broadcasters capture the lion's share as targeted digital buys surge.", gradient: "linear-gradient(135deg,#3b0764,#701a75 55%,#a21caf)" },
    { title: "Startup claims 10,000-qubit chip, challenges supremacy narrative", source: "Wired", cat: "tech", sent: "bull", rel: 85, excerpt: "Researchers caution that qubit count alone does not imply practical fault tolerance.", gradient: "linear-gradient(135deg,#0f172a,#172554 50%,#1e40af)" },
    { title: "Manufacturing PMI contracts for a third straight month", source: "Associated Press", cat: "macro", sent: "bear", rel: 83, excerpt: "Weak new orders weigh on the sector as cost pressures ease only marginally.", gradient: "linear-gradient(135deg,#450a0a,#7f1d1d 55%,#991b1b)" },
    { title: "Mega-cap AI capex guidance surprises to the upside", source: "Barron's", cat: "markets", sent: "bull", rel: 82, excerpt: "Hyperscalers guide combined spend above consensus, lifting the entire supply chain.", gradient: "linear-gradient(135deg,#1e3a8a,#155e75 55%,#0e7490)" },
    { title: "Semiconductor trade curbs tighten access to advanced tooling", source: "Nikkei", cat: "geopolitics", sent: "bear", rel: 80, excerpt: "Secondary sanctions and entity-list revisions create fresh compliance risk.", gradient: "linear-gradient(135deg,#431407,#9a3412 55%,#c2410c)" },
    { title: "Consumers pivot to value brands as savings buffer thins", source: "The Economist", cat: "macro", sent: "hold", rel: 78, excerpt: "Private-label penetration climbs in staples while discretionary spending cools.", gradient: "linear-gradient(135deg,#111827,#1f2937 55%,#374151)" },
    { title: "Carbon border tax phase-in draws mixed global reaction", source: "Reuters", cat: "climate", sent: "hold", rel: 75, excerpt: "Exporters face new compliance layers as the mechanism expands next year.", gradient: "linear-gradient(135deg,#14532d,#166534 55%,#15803d)" }
  ];

  /* ── Mock Method Container ───────────────────────────────────────────── */
  var Mock = {};

  /** Expose data arrays as direct properties for ui.js access */
  Mock.TRENDING = TRENDING;
  Mock.SUGGESTIONS = SUGGESTIONS;

  /* ── /api/status mock ─────────────────────────────────────────────────── */

  /** Returns a simulated backend health status payload */
  Mock.status = function () {
    return {
      status: "ok",
      mode: "demo",
      version: CFG.VERSION,
      uptime: "12h 34m",
      models: ["predictor-v3.2", "sentiment-net", "signal-miner"],
      pipelines: 4,
      timestamp: new Date().toISOString()
    };
  };

  /* ── SVG Gauge Arc Calculator ──────────────────────────────────────── */

  /**
   * Computes SVG stroke-dasharray/offset values for the outcome gauge arc.
   * @param {number} value - Score between 0-100.
   * @returns {{ total: number, offset: number }}
   */
  Mock.gaugeArc = function (value) {
    var radius = 80;
    var circ = Math.PI * radius; // semicircle circumference
    var filled = (U.clamp(value, 0, 100) / 100) * circ;
    return {
      total: circ,
      offset: circ - filled
    };
  };

  /* ── /api/analyze mock ─────────────────────────────────────────────── */

  /**
   * Synthesizes a complete analysis response payload for any query.
   * Shape matches what script.js/ui.js expect: { topic, stats, summary,
   * sentiment, news, report, explain, crew }.
   * @param {string} query - Search query.
   * @param {Object} [opts] - Analysis options.
   * @returns {Object} Full analysis payload.
   */
  Mock.analysis = function (query, opts) {
    var q = (query || CFG.DEFAULT_QUERY).trim();
    var seed = U.hashString(q);
    var rand = U.seededRand(seed);

    var score = Math.round(50 + (rand() * 42 - 16));
    score = U.clamp(score, 18, 96);

    var dir = score >= 62 ? "bull" : score <= 42 ? "bear" : "hold";
    var dirLabel = dir === "bull" ? "Bullish" : dir === "bear" ? "Bearish" : "Neutral";
    var horizon = "60d";
    var now = new Date();

    /* ── Stats KPI Cards ─────────────────────────────────────────────── */
    var stats = [
      { key: "signals", label: "Signals mined", value: Math.round(8400 + rand() * 6200), delta: "+" + Math.round(8 + rand() * 18) + "%", tone: "up" },
      { key: "confidence", label: "Confidence", value: score, delta: (score > 60 ? "+" : "") + Math.round((score - 50) * 0.3) + "pp", tone: score >= 60 ? "up" : score <= 40 ? "down" : "neutral" },
      { key: "sources", label: "Sources used", value: Math.round(140 + rand() * 80), delta: "+" + Math.round(4 + rand() * 14), tone: "up" },
      { key: "models", label: "Active models", value: 6, delta: "0", tone: "neutral" },
      { key: "alerts", label: "Risk alerts", value: Math.round(1 + rand() * 4), delta: Math.round(rand() * 3) > 1 ? "+1" : "0", tone: rand() > 0.5 ? "up" : "neutral" }
    ];

    /* ── Executive Summary ────────────────────────────────────────────── */
    var summary = {
      topic: q,
      generatedAt: new Date(now.getTime() - rand() * 3600000).toISOString(),
      confidence: score,
      sentiment: dir,
      sentimentLabel: dirLabel,
      horizon: horizon,
      sources: Math.round(140 + rand() * 80),
      signals: Math.round(8400 + rand() * 6200),
      paragraphs: [
        "**Comprehensive cross-corpus analysis** of \"" + q + "\" indicates a " + dirLabel.toLowerCase() + " regime with high statistical stability. Primary catalysts include sustained institutional demand, macro policy alignment, and favorable sentiment velocity across major financial channels.",
        "The ensemble model registered a composite confidence score of " + score + "% across six seed configurations, with cross-validation loss converging within 0.3pp of the target threshold. Key risk factors remain bounded within expected volatility envelopes."
      ],
      keypoints: [
        "Aggregate sentiment index registered a net " + (dir === "bull" ? "positive" : dir === "bear" ? "negative" : "neutral") + " momentum (" + (dir === "bear" ? "-" : "+") + "14 bps over 7-day average).",
        "Key risk factors remain bounded within expected volatility envelopes.",
        "Model convergence score across multi-agent pipelines reached " + Math.round(88 + rand() * 8) + "% accuracy threshold."
      ]
    };

    /* ── Sentiment Charts Data ────────────────────────────────────────── */
    var dates = [];
    var baseDate = new Date();
    baseDate.setDate(baseDate.getDate() - 14);
    for (var i = 0; i < 15; i++) {
      var d = new Date(baseDate);
      d.setDate(d.getDate() + i);
      dates.push(U.formatDate(d));
    }
    var trendValues = [];
    var rollingValues = [];
    var tv = score - 14;
    for (var j = 0; j < 15; j++) {
      tv += (rand() - 0.44) * 6;
      tv = U.clamp(tv, 20, 95);
      trendValues.push(Math.round(tv * 10) / 10);
      rollingValues.push(Math.round((tv + (rand() - 0.5) * 8) * 10) / 10);
    }
    trendValues[14] = score;

    var sentiment = {
      trend: {
        labels: dates,
        values: trendValues,
        rolling: rollingValues
      },
      sectors: {
        labels: ["Technology", "Finance", "Energy", "Healthcare", "Consumer", "Industrial"],
        values: [Math.round(22 + rand() * 10), Math.round(18 + rand() * 8), Math.round(14 + rand() * 6), Math.round(12 + rand() * 8), Math.round(10 + rand() * 8), Math.round(8 + rand() * 6)]
      },
      radar: {
        labels: ["Momentum", "Volume", "Volatility", "Breadth", "Sentiment", "Flow"],
        values: [Math.round(55 + rand() * 40), Math.round(50 + rand() * 40), Math.round(30 + rand() * 50), Math.round(45 + rand() * 40), Math.round(50 + rand() * 45), Math.round(40 + rand() * 45)]
      },
      sources: {
        labels: ["Reuters", "Bloomberg", "CNBC", "FT", "AP", "WSJ", "Nikkei"],
        values: [Math.round(30 + rand() * 20), Math.round(25 + rand() * 20), Math.round(18 + rand() * 14), Math.round(16 + rand() * 12), Math.round(14 + rand() * 10), Math.round(12 + rand() * 10), Math.round(8 + rand() * 8)]
      }
    };

    /* ── News Articles ────────────────────────────────────────────────── */
    var news = NEWS_POOL.slice(0, 8).map(function (n, idx) {
      return {
        id: "news-" + idx,
        title: n.title,
        source: n.source,
        cat: n.cat,
        sent: n.sent,
        rel: Math.max(60, n.rel - idx * 2),
        excerpt: n.excerpt,
        time: new Date(now.getTime() - (idx * 3600000 + rand() * 1800000)).toISOString(),
        gradient: n.gradient
      };
    });

    /* ── Explainable AI (SHAP Features & Signals) ────────────────────── */
    var explain = {
      model: "Predictor v3.2",
      accuracy: Math.round(88 + rand() * 8),
      features: [
        { name: "Central Bank Guidance", value: +(0.8 + rand() * 0.35).toFixed(2), dir: "pos" },
        { name: "Earnings Surprises", value: +(0.6 + rand() * 0.35).toFixed(2), dir: "pos" },
        { name: "Geopolitical Risk", value: -(0.3 + rand() * 0.4).toFixed(2), dir: "neg" },
        { name: "Commodity Prices", value: +(0.2 + rand() * 0.4).toFixed(2), dir: dir === "bear" ? "neg" : "pos" },
        { name: "Consumer Sentiment", value: +(0.15 + rand() * 0.3).toFixed(2), dir: "pos" }
      ].sort(function (a, b) { return Math.abs(b.value) - Math.abs(a.value); }),
      signals: [
        { title: "Fed minutes hint at extended pause", src: "Reuters · 2h ago", impact: "+12bp", dir: "pos" },
        { title: "Tech capex beats consensus by 18%", src: "Bloomberg · 4h ago", impact: "+8bp", dir: "pos" },
        { title: "OPEC+ considers surprise output hike", src: "FT · 6h ago", impact: "-6bp", dir: "neg" },
        { title: "PMI contraction deepens in eurozone", src: "AP · 8h ago", impact: "-4bp", dir: "neg" },
        { title: "AI chip demand outpaces supply 3:1", src: "Nikkei · 12h ago", impact: "+9bp", dir: "pos" }
      ]
    };

    /* ── Research Report Tabs ─────────────────────────────────────────── */
    var report = {
      exec: {
        stats: [
          { value: score + "%", label: "Confidence" },
          { value: U.formatInt(Math.round(140 + rand() * 80)), label: "Sources" },
          { value: dirLabel, label: "Direction" },
          { value: horizon, label: "Horizon" }
        ],
        paragraphs: [
          "This executive brief synthesizes " + Math.round(140 + rand() * 80) + " sources across macro, equity, and alternative data channels to produce a " + dirLabel.toLowerCase() + " outlook on \"" + q + "\".",
          "The ensemble model's composite confidence sits at " + score + "%, converging across six seeds within 0.3pp of the target threshold."
        ],
        bullets: [
          "Net sentiment momentum is " + (dir === "bear" ? "negative" : "positive") + " across major financial newswires.",
          "Risk factors remain within acceptable volatility envelopes.",
          "Multi-agent convergence score exceeds 90% accuracy."
        ]
      },
      analysis: [
        { h: "Macro Environment", p: "Central bank guidance remains the dominant driver, with forward rates pricing a " + Math.round(60 + rand() * 30) + "% probability of a rate adjustment within the next 90 days." },
        { h: "Sector Dynamics", p: "Technology sector capex continues to outpace consensus, with hyperscaler spending guidance revised upward by an aggregate 18% quarter-over-quarter." },
        { h: "Sentiment Flow", p: "Cross-corpus sentiment velocity registered " + (dir === "bear" ? "deceleration" : "acceleration") + " across 7 major channels, with the composite index at " + score + "/100." }
      ],
      forecast: [
        { h: "Base Case (" + Math.round(50 + rand() * 20) + "% probability)", p: "Markets consolidate near current levels with a gradual " + (dir === "bull" ? "upward" : "downward") + " drift as earnings season unfolds and macro data confirms the current trend." },
        { h: "Bull Case (" + Math.round(20 + rand() * 15) + "% probability)", p: "A dovish surprise from central banks catalyzes a broad risk-on move, lifting equities 4-7% over the forecast horizon." },
        { h: "Bear Case (" + Math.round(10 + rand() * 15) + "% probability)", p: "Escalation in geopolitical tensions or a sharp spike in energy prices triggers a risk-off repricing of 5-10% across major indices." }
      ],
      risks: [
        { name: "Geopolitical Escalation", sev: "high", desc: "Unexpected conflict escalation or sanctions expansion could disrupt trade flows and supply chains." },
        { name: "Inflation Reacceleration", sev: "medium", desc: "Services inflation proving stickier than expected may delay central bank easing cycles." },
        { name: "Liquidity Squeeze", sev: "low", desc: "Quantitative tightening reducing market liquidity may amplify drawdowns during stress events." }
      ],
      sources: [
        { name: "Wire Services", count: Math.round(40 + rand() * 30), type: "Real-time" },
        { name: "Financial Press", count: Math.round(30 + rand() * 25), type: "Editorial" },
        { name: "Government Data", count: Math.round(15 + rand() * 15), type: "Statistical" },
        { name: "Research Notes", count: Math.round(20 + rand() * 20), type: "Analyst" },
        { name: "Social Signals", count: Math.round(25 + rand() * 20), type: "Alternative" }
      ]
    };

    return {
      topic: q,
      stats: stats,
      summary: summary,
      sentiment: sentiment,
      news: news,
      explain: explain,
      report: report
    };
  };

  /* ── /api/crew mock ────────────────────────────────────────────────── */

  /**
   * Returns a CrewAI multi-agent pipeline initialization payload.
   * @param {string} topic - Analysis topic.
   * @returns {Object} Crew pipeline state with agents, logs, and topic.
   */
  Mock.crew = function (topic) {
    var t = topic || CFG.DEFAULT_QUERY;
    return {
      topic: t,
      result: "4 agents converged · dossier compiled with 94% agreement",
      agents: [
        { id: "researcher", name: "Researcher", role: "Source scanner & ranker", icon: "fa-magnifying-glass" },
        { id: "analyst", name: "Analyst", role: "Signal clusterer & mapper", icon: "fa-chart-pie" },
        { id: "forecaster", name: "Forecaster", role: "Ensemble model runner", icon: "fa-chart-line" },
        { id: "reporter", name: "Reporter", role: "Dossier writer & risk flagger", icon: "fa-file-pen" }
      ],
      logs: [
        "Initializing pipeline for: " + U.truncate(t, 48),
        "Loading 6 ensemble model seeds…",
        "Connecting to knowledge graph (8 entity nodes)…",
        "Ready — awaiting dispatch."
      ]
    };
  };

  /* ── /api/graph mock ───────────────────────────────────────────────── */

  /**
   * Returns D3 knowledge graph nodes and links for visualization.
   * @returns {Object} { nodes: Array, links: Array }
   */
  Mock.graph = function () {
    return {
      nodes: [
        { id: "q", label: "Query Focus", type: "query", radius: 24, color: C.violet },
        { id: "e1", label: "Federal Reserve", type: "entity", radius: 18, color: C.cyan },
        { id: "e2", label: "Inflation Rate", type: "metric", radius: 15, color: C.emerald },
        { id: "e3", label: "Tech Capex", type: "sector", radius: 16, color: C.pink },
        { id: "e4", label: "Yield Curve", type: "metric", radius: 14, color: C.amber },
        { id: "e5", label: "Labor Market", type: "entity", radius: 15, color: C.indigo },
        { id: "e6", label: "Energy Prices", type: "sector", radius: 14, color: C.red },
        { id: "e7", label: "Supply Chains", type: "concept", radius: 13, color: C.blue }
      ],
      links: [
        { source: "q", target: "e1", label: "Monitored by", weight: 3 },
        { source: "q", target: "e3", label: "Driven by", weight: 2 },
        { source: "e1", target: "e2", label: "Targets", weight: 2 },
        { source: "e1", target: "e4", label: "Influences", weight: 2 },
        { source: "e2", target: "e5", label: "Correlated", weight: 1 },
        { source: "e3", target: "e7", label: "Dependent on", weight: 2 },
        { source: "e6", target: "e2", label: "Pressures", weight: 2 },
        { source: "q", target: "e6", label: "Exposed to", weight: 1 }
      ]
    };
  };

  /* ── Export ─────────────────────────────────────────────────────────── */
  root.Newsana = root.Newsana || {};
  root.Newsana.mock = Mock;
})(window);
