/**
 * ============================================================================
 * NEWSANA AI — APPLICATION ENTRY POINT & BOOTSTRAP PIPELINE
 * ============================================================================
 * @file script.js
 * @description Main application controller and bootstrapper for Newsana AI.
 * Handles startup sequence, splash screen dismissal, UI initialization,
 * status checks, and data loading pipeline.
 *
 * Performance Features:
 * - Ultra-fast loader animation (20ms ticks)
 * - Immediate splash screen transition on backend status check
 * - Rapid non-blocking section rendering (20ms staggered updates)
 * ============================================================================
 */

(function (root) {
  "use strict";

  // Module scope local references to core singletons
  var U = root.Newsana.utils;         // DOM, string, and math utilities
  var CFG = root.NewsanaConfig;       // Global configuration settings
  var api = root.Newsana.api;         // HTTP API client layer
  var ui = root.Newsana.ui;           // UI event & render manager
  var charts = root.Newsana.charts;   // Chart.js visualization wrappers
  var currentAnalysis = null;        // Active query analysis cache
  var booted = false;                 // Boot guard flag to prevent re-entrancy

  /**
   * Bootstraps the web application.
   * Initializes utilities, API layer, UI state, charts, graph, and chat sub-systems.
   */
  function boot() {
    if (booted) return;
    booted = true;

    // 1. Render dynamic static text (greetings, footer year, version)
    U.renderStatic();

    // 2. Initialize subsystems
    api.init();
    ui.init();
    charts.init();

    if (root.Newsana.graph) root.Newsana.graph.init();
    if (root.Newsana.chat) root.Newsana.chat.init();

    // 3. Kick off splash loader animation pipeline
    animateLoader();
  }

  /**
   * Animates the splash screen loader progress bar rapidly.
   * Completes within ~100ms for fast initial page paint.
   */
  function animateLoader() {
    var bar = U.$("#loaderBar");
    var progress = 0;

    // Optimized fast loader animation loop (20ms tick rate)
    var barTimer = setInterval(function () {
      progress = Math.min(100, progress + U.rand(25, 45));
      if (bar) bar.style.width = progress + "%";

      if (progress >= 100) {
        clearInterval(barTimer);
        // Instantly transition to status check and dashboard render
        setTimeout(realize, 50);
      }
    }, 20);
  }

  /**
   * Fetches backend status and transitions from splash loader to the dashboard UI.
   */
  async function realize() {
    var loader = U.$("#appLoader");

    try {
      // Query backend status (/api/status) or fall back to mock
      var status = await api.getStatus();

      // Immediately hide loader overlay and reveal workspace
      if (loader) loader.classList.add("hidden");

      // Update header status indicators and trigger intro animation
      ui.renderStatus(status);
      intro();

      // Load initial dashboard intelligence data
      loadDashboard(status);
    } catch (err) {
      console.warn("Status check notice:", err);
      if (loader) loader.classList.add("hidden");
      intro();
      loadDashboard({ status: "error" });
    }
  }

  /**
   * Triggers GSAP entrance animation sequence for hero elements and main cards.
   */
  function intro() {
    if (typeof gsap === "undefined") {
      U.observeReveal();
      return;
    }
    var tl = gsap.timeline();
    tl.fromTo(
      ".hero",
      { opacity: 0, y: 34 },
      { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }
    );
    tl.fromTo(
      ".hero-greeting, .hero-title, .hero-sub",
      { opacity: 0, y: 16 },
      { opacity: 1, y: 0, duration: 0.35, stagger: 0.05, ease: "power2.out" },
      "-=0.3"
    );
    tl.fromTo(
      ".hero-search, .hero-quick",
      { opacity: 0, y: 18 },
      { opacity: 1, y: 0, duration: 0.35, stagger: 0.05, ease: "power2.out" },
      "-=0.2"
    );
    tl.fromTo(
      "#dashboard .section-head, #dashboard .stat-card, #dashboard .exec-card, #dashboard .gauge-card",
      { opacity: 0, y: 26 },
      { opacity: 1, y: 0, duration: 0.35, stagger: 0.04, ease: "power3.out" },
      "-=0.15"
    );
  }

  /**
   * Initializes dashboard contents with primary search query analysis.
   * @param {Object} status - Backend status object
   */
  async function loadDashboard(status) {
    var query = CFG.DEFAULT_QUERY;
    var mode = status && status.mode === "demo" ? "demo" : "live";

    // Set skeleton loading state on chart cards
    ["sentimentCard", "sectorCard", "radarCard", "sourcesCard"].forEach(function (id) {
      var el = U.$("#" + id);
      if (el) el.classList.add("is-loading");
    });

    // Execute default intelligence analysis asynchronously
    var analysis = await runAnalysis(query, { silent: true, skipToast: true });

    // Render report from cached result fast
    setTimeout(function () {
      renderReportFromCache();
    }, 100);

    // Initialize mock multi-agent crew state
    setTimeout(function () {
      var initial = root.Newsana.mock.crew(query);
      ui.renderCrewStatic(initial);
    }, 150);

    // Remove loading indicator from graph card
    setTimeout(function () {
      var graphCard = U.$("#graphCard");
      if (graphCard && graphCard.classList.contains("is-loading")) {
        graphCard.classList.remove("is-loading");
      }
    }, 200);

    // Show connection mode toast notification
    ui.toast(
      mode === "demo" ? "info" : "success",
      mode === "demo" ? "Demo mode active" : "Backend connected",
      mode === "demo"
        ? "Backend not reachable — showing simulated intelligence so you can explore the UI."
        : "Live pipeline online — status, analysis, crew, graph and ingest endpoints ready.",
      null
    );
  }

  /**
   * Renders research dossier report from active cached analysis payload.
   */
  function renderReportFromCache() {
    if (currentAnalysis) {
      ui.renderReport(currentAnalysis.report);
    }
  }

  /**
   * Submits a query for full intelligence analysis and updates UI widgets.
   * @param {string} query - Topic or question to analyze
   * @param {Object} [opts] - Analysis options (silent, skipToast)
   * @returns {Promise<Object>} Analysis results payload
   */
  async function runAnalysis(query, opts) {
    var o = opts || {};
    var heroInput = U.$("#heroInput");
    var submit = U.$("#heroSubmit");

    if (heroInput) heroInput.value = query;
    if (submit) {
      submit.disabled = true;
      submit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Analyzing…</span>';
    }

    if (!o.silent) {
      ui.toast("info", "Analyzing", "Newsana is synthesizing “" + U.truncate(query, 60) + "” across 1,200+ sources.");
    }

    // Call API analyze endpoint (falls back to mock automatically if offline)
    var res = await api.analyze(query, { horizon: "60d" });
    currentAnalysis = res;

    // Render results across dashboard widgets
    renderAnalysis(res, query);

    if (!o.skipToast) {
      ui.pushRecent(query);
    }

    if (submit) {
      submit.disabled = false;
      submit.innerHTML = '<i class="fa-solid fa-arrow-up"></i><span>Analyze</span>';
    }
    return res;
  }

  /**
   * Updates all UI dashboard cards and charts with fresh analysis data.
   * @param {Object} res - Analysis result data
   * @param {string} query - Query string
   */
  function renderAnalysis(res, query) {
    var sections = [
      ["execCard", function () { ui.renderExec(res.summary); }],
      ["statsGrid", function () { ui.renderStats(res.stats); }],
      ["sentimentCard", function () { charts.sentiment(res.sentiment.trend); }],
      ["sectorCard", function () { charts.sectors(res.sentiment.sectors); }],
      ["radarCard", function () { charts.radar(res.sentiment.radar); }],
      ["sourcesCard", function () { charts.sources(res.sentiment.sources); }],
      ["newsGrid", function () { ui.renderNews(res.news); }],
      ["reportCard", function () { ui.renderReport(res.report); }],
      ["explainCard", function () { ui.renderExplain(res.explain); }],
      ["signalsCard", function () { ui.renderExplain(res.explain); }]
    ];

    // Fast non-blocking section rendering (15ms stagger)
    sections.forEach(function (pair, i) {
      setTimeout(function () {
        var el = U.$("#" + pair[0]);
        if (el) el.classList.remove("is-loading");
        pair[1]();
      }, i * 15);
    });

    var topicEl = U.$("#reportTopic");
    if (topicEl) topicEl.textContent = "Generated dossier: " + res.topic;

    var filterAll = U.$('.filter-pill[data-filter="all"]');
    if (filterAll) filterAll.click();

    // Sync URL search parameter quietly
    try {
      var url = new URL(root.location.href);
      url.searchParams.set("q", query);
      root.history.replaceState({}, "", url.pathname + url.search);
    } catch (e) {}
  }

  /**
   * Triggers the multi-agent CrewAI pipeline run.
   */
  function runCrewFlow() {
    var btn = U.$("#runCrewBtn");
    var topic = currentAnalysis ? currentAnalysis.topic : CFG.DEFAULT_QUERY;

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running…';
    }

    api.runCrew(topic).then(function (crew) {
      ui.renderCrewStatic(crew);
      ui.simulateCrew(crew);
    });
  }

  // Bind boot listener on DOMContentLoaded or execute immediately if ready
  root.addEventListener("DOMContentLoaded", boot);
  if (document.readyState !== "loading") boot();

  // Export public namespace functions
  root.Newsana = root.Newsana || {};
  root.Newsana.runAnalysis = runAnalysis;
  root.Newsana.runCrewFlow = runCrewFlow;
  root.Newsana.getCurrentAnalysis = function () {
    return currentAnalysis;
  };
})(window);
