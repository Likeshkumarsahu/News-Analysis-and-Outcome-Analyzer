/* ============================================================
   NEWSANA AI — UI ENGINE
   Renders every dashboard component and wires interactions.
   ============================================================ */
(function (root) {
  "use strict";

  var U = root.Newsana.utils;
  var CFG = root.NewsanaConfig;
  var C = CFG.THEME.colors;

  var settingsCache = null;
  var notifications = [
    { icon: "info", title: "Crew pipeline finished", text: "Research → Report completed in 42s for “Global economy outlook”.", time: "5m ago", unread: true },
    { icon: "done", title: "Confidence threshold passed", text: "Predictor v3.2 crossed 85% agreement on the Fed path.", time: "23m ago", unread: true },
    { icon: "warn", title: "New risk alert", text: "High-yield spreads widened 18bp overnight — flagged in dashboard.", time: "1h ago", unread: true },
    { icon: "info", title: "Ingestion complete", text: "36 new sources indexed from your watchlist (≈ 4,120 signals).", time: "3h ago", unread: false },
    { icon: "done", title: "Report exported", text: "Your PDF dossier was generated and sent to your inbox.", time: "Yesterday", unread: false }
  ];

  /* ======================= STATIC BINDINGS ======================= */
  function init() {
    bindSidebar();
    bindTopnav();
    bindModals();
    // bindToasts();
    bindHero();
    bindCrew();
    bindReport();
    bindNews();
    bindSettings();
    // bindNotifications();
    bindShortcuts();
    // bindIngest();
    U.observeReveal();

    var resizeTimer = null;
    U.on(window, "resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        if (root.Newsana.graph) root.Newsana.graph.resize();
      }, 250);
    });

    U.on(window, "scroll", U.throttle(function () {
      var nav = U.$("#topnav");
      if (nav) nav.classList.toggle("scrolled", window.scrollY > 10);
    }, 80));
  }

  /* ======================= SIDEBAR ======================= */
  function bindSidebar() {
    var toggle = U.$("#sidebarToggle");
    var close = U.$("#sidebarClose");
    var overlay = U.$("#sidebarOverlay");
    var body = document.body;

    function open() {
      body.classList.add("sidebar-open");
      if (overlay) overlay.classList.add("show");
    }
    function closeSide() {
      body.classList.remove("sidebar-open");
      if (overlay) overlay.classList.remove("show");
    }
    U.on(toggle, "click", function () {
      body.classList.contains("sidebar-open") ? closeSide() : open();
    });
    U.on(close, "click", closeSide);
    U.on(overlay, "click", closeSide);

    U.on(U.$("#upgradeBtn"), "click", function () {
      toast("success", "Newsana Pro", "You're already on the Pro plan — enjoy unlimited predictions.");
    });
    U.on(U.$("#sidebarUser"), "click", function () {
      openModal("settingsModal");
    });

    bindScrollspy();
  }

  function bindScrollspy() {
    var navItems = U.$$(".nav-item[data-nav]");
    var sections = navItems
      .map(function (item) {
        return U.$("#" + item.dataset.nav);
      })
      .filter(Boolean);

    var update = U.throttle(function () {
      var pos = window.scrollY + 120;
      var current = null;
      sections.forEach(function (sec) {
        if (sec.offsetTop <= pos) current = sec.id;
      });
      navItems.forEach(function (item) {
        var active = item.dataset.nav === current;
        item.classList.toggle("active", active);
        if (active) {
          var title = U.$("#navTitle");
          if (title) title.textContent = item.textContent.trim();
        }
      });
    }, 80);

    U.on(window, "scroll", update);
    update();

    navItems.forEach(function (item) {
      U.on(item, "click", function () {
        if (window.innerWidth <= 992) {
          document.body.classList.remove("sidebar-open");
          var overlay = U.$("#sidebarOverlay");
          if (overlay) overlay.classList.remove("show");
        }
      });
    });
  }

  /* ======================= TOP NAV ======================= */
  function bindTopnav() {
    bindDropdown(U.$("#notifBtn"), U.$("#notifPanel"));
    bindDropdown(U.$("#profileBtn"), U.$("#profileMenu"));

    U.on(U.$("#markAllRead"), "click", function (e) {
      e.preventDefault();
      notifications.forEach(function (n) {
        n.unread = false;
      });
      renderNotifications();
      var btn = U.$("#notifBtn");
      if (btn) btn.classList.remove("has-dot");
      toast("info", "Notifications", "All notifications marked as read.");
    });

    U.on(U.$("#settingsBtn"), "click", function () {
      openModal("settingsModal");
    });

    U.on(U.$("#globalSearch"), "keydown", function (e) {
      if (e.key === "Enter" && this.value.trim()) {
        var q = this.value.trim();
        this.value = "";
        closeDropdowns();
        root.Newsana.runAnalysis(q);
      }
    });

    var profileItems = U.$$("#profileMenu .menu-item");
    profileItems.forEach(function (item) {
      U.on(item, "click", function () {
        if (item.dataset.openModal) {
          openModal(item.dataset.openModal);
        } else if (item.classList.contains("menu-item-danger")) {
          toast("warn", "Signed out", "This is a demo workspace — you can sign back in anytime.");
        } else {
          toast("info", "Profile", "This section is part of the demo workspace.");
        }
        closeDropdowns();
      });
    });

    U.on(U.$("#refreshBtn"), "click", function () {
      toast("info", "Refreshing", "Re-synthesizing the latest signal flow…");
      root.Newsana.runAnalysis(settingsCache && settingsCache.lastQuery ? settingsCache.lastQuery : CFG.DEFAULT_QUERY, { silent: true });
    });

    U.on(U.$("#copySummary"), "click", function () {
      var body = U.$("#execBody");
      if (!body) return;
      var text = body.innerText;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          toast("success", "Copied", "Executive summary copied to clipboard.");
        });
      } else {
        toast("info", "Copy", "Select the summary text to copy it.");
      }
    });
  }

  function bindDropdown(btn, panel) {
    if (!btn || !panel) return;
    U.on(btn, "click", function (e) {
      e.stopPropagation();
      var isOpen = panel.classList.contains("open");
      closeDropdowns();
      if (!isOpen) panel.classList.add("open");
    });
  }

  function closeDropdowns() {
    U.$$(".dropdown.open").forEach(function (d) {
      d.classList.remove("open");
    });
  }

  /* ======================= MODALS ======================= */
  function bindModals() {
    var modal = U.$("#settingsModal");
    if (!modal) return;
    modal.addEventListener("click", function (e) {
      if (e.target.closest("[data-close-modal]")) closeModal("settingsModal");
      if (e.target.classList.contains("modal-backdrop")) closeModal("settingsModal");
    });
    U.on(document, "keydown", function (e) {
      if (e.key === "Escape") {
        closeDropdowns();
        closeModal("settingsModal");
        if (root.Newsana.chat) root.Newsana.chat.close();
      }
    });

    U.$$("[data-open-modal]").forEach(function (el) {
      U.on(el, "click", function (e) {
        e.preventDefault();
        openModal(el.dataset.openModal);
      });
    });

    U.on(U.$("#saveSettings"), "click", function () {
      saveSettings();
      closeModal("settingsModal");
      toast("success", "Settings saved", "Your workspace preferences are up to date.");
    });
  }

  function openModal(id) {
    var m = U.$("#" + id);
    if (!m) return;
    m.hidden = false;
    document.body.classList.add("modal-open");
    closeDropdowns();
    if (id === "settingsModal") renderSettings();
  }

  function closeModal(id) {
    var m = U.$("#" + id);
    if (!m) return;
    m.hidden = true;
    if (!U.$(".modal:not([hidden])")) document.body.classList.remove("modal-open");
  }

  /* ======================= TOASTS ======================= */
  function toast(type, title, message) {
    var wrap = U.$("#toastWrap");
    if (!wrap) return;
    var icons = { success: "fa-circle-check", error: "fa-circle-xmark", warn: "fa-triangle-exclamation", info: "fa-circle-info" };
    var el = document.createElement("div");
    el.className = "toast " + (type || "info");
    el.innerHTML =
      '<span class="toast-icon"><i class="fa-solid ' + (icons[type] || icons.info) + '"></i></span>' +
      '<div class="toast-body"><strong>' + U.escapeHTML(title) + "</strong><p>" + U.escapeHTML(message) + "</p></div>" +
      '<button class="toast-close" aria-label="Dismiss"><i class="fa-solid fa-xmark"></i></button>';
    wrap.appendChild(el);
    U.on(el.querySelector(".toast-close"), "click", function () {
      el.classList.add("leaving");
      setTimeout(function () {
        el.remove();
      }, 380);
    });
    setTimeout(function () {
      el.classList.add("leaving");
      setTimeout(function () {
        el.remove();
      }, 380);
    }, 5200);
  }

  /* ======================= STATUS PILL ======================= */
  function renderStatus(status) {
    var pill = U.$("#topnavStatus");
    var pillM = U.$("#topnavStatusMobile");
    var ok = status && status.status === "ok";
    var label = ok ? (status.mode === "demo" ? "Demo · offline" : "Live") : "Offline";
    if (pill) {
      var dot = pill.querySelector(".status-dot");
      dot.className = "status-dot " + (ok ? "online" : "offline");
      pill.querySelector(".status-text").textContent = label;
    }
    if (pillM) {
      pillM.querySelector(".status-dot").className = "status-dot " + (ok ? "online" : "offline");
    }
    var badge = U.$("#liveBadge");
    if (badge && status && status.mode === "demo") {
      badge.innerHTML = '<span class="dot"></span> Demo mode';
      badge.style.color = C.amber;
    }
    var ver = U.$("#footerVersion");
    if (ver && status && status.version) ver.textContent = "v" + status.version;
  }

  /* ======================= HERO + TRENDING + RECENT ======================= */
  function bindHero() {
    var form = U.$("#heroForm");
    var input = U.$("#heroInput");
    var suggestions = U.$("#suggestions");

    var cached = U.getPref(CFG.RECENT_KEY, []);

    renderTrending();
    renderRecent();

    U.on(input, "input", U.debounce(function () {
      var val = input.value.trim();
      if (!val) {
        suggestions.classList.remove("open");
        return;
      }
      var matches = root.Newsana.mock.SUGGESTIONS.filter(function (s) {
        return s.toLowerCase().indexOf(val.toLowerCase()) !== -1;
      }).slice(0, 5);
      if (!matches.length) {
        matches = [val];
      }
      suggestions.innerHTML = matches
        .map(function (s, i) {
          return '<button type="button" class="suggestion-item' + (i === 0 ? " active" : "") + '" data-query="' + U.escapeHTML(s) + '"><i class="fa-solid fa-magnifying-glass"></i><span>' + U.escapeHTML(s) + "</span><span class='suggestion-meta'>Analyze</span></button>";
        })
        .join("");
      suggestions.classList.add("open");
      U.$$(".suggestion-item", suggestions).forEach(function (item) {
        U.on(item, "click", function () {
          input.value = item.dataset.query;
          suggestions.classList.remove("open");
          form.dispatchEvent(new Event("submit"));
        });
      });
    }, 120));

    U.on(input, "keydown", function (e) {
      var items = U.$$(".suggestion-item", suggestions);
      if (!items.length) return;
      var idx = items.findIndex(function (it) {
        return it.classList.contains("active");
      });
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (idx >= 0) items[idx].classList.remove("active");
        if (idx < 0) idx = e.key === "ArrowDown" ? -1 : 0;
        var next = e.key === "ArrowDown" ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length;
        items[next].classList.add("active");
      }
    });

    U.on(input, "blur", function () {
      setTimeout(function () {
        suggestions.classList.remove("open");
      }, 160);
    });

    U.on(form, "submit", function (e) {
      e.preventDefault();
      var q = input.value.trim();
      if (!q) return;
      suggestions.classList.remove("open");
      input.blur();
      root.Newsana.runAnalysis(q);
    });

    U.on(U.$("#clearRecent"), "click", function () {
      U.setPref(CFG.RECENT_KEY, []);
      renderRecent();
      toast("info", "Cleared", "Recent searches cleared.");
    });

    U.$$(".chip-quick").forEach(function (chip) {
      U.on(chip, "click", function () {
        if (chip.dataset.chatOpen) {
          if (root.Newsana.chat) root.Newsana.chat.toggle();
        } else if (chip.dataset.runCrew) {
          root.Newsana.runCrewFlow();
        } else if (chip.dataset.ingest) {
          openModal("settingsModal");
          setTimeout(function () {
            var tab = U.$('.settings-tab[data-settings-tab="data"]');
            if (tab) tab.click();
          }, 60);
        }
      });
    });

    U.on(document, "keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        input.focus();
      }
    });
  }

  function renderTrending() {
    var row = U.$("#trendingRow");
    if (!row) return;
    row.innerHTML = root.Newsana.mock.TRENDING.map(function (t) {
      return '<button class="chip ' + (t.hot ? "trend-hot" : "") + '" data-query="' + U.escapeHTML(t.label) + '"><i class="fa-solid fa-fire-flame-curved"></i>' + U.escapeHTML(t.label) + "</button>";
    }).join("");
    U.$$(".chip", row).forEach(function (chip) {
      U.on(chip, "click", function () {
        var input = U.$("#heroInput");
        if (input) input.value = chip.dataset.query;
        root.Newsana.runAnalysis(chip.dataset.query);
      });
    });
  }

  function renderRecent() {
    var row = U.$("#recentRow");
    if (!row) return;
    var items = U.getPref(CFG.RECENT_KEY, []);
    var block = U.$("#recentBlock");
    if (block) block.style.display = items.length ? "" : "none";
    row.innerHTML = items
      .map(function (q) {
        return '<button class="chip" data-query="' + U.escapeHTML(q) + '"><i class="fa-solid fa-clock-rotate-left"></i>' + U.escapeHTML(q) + "</button>";
      })
      .join("");
    U.$$(".chip", row).forEach(function (chip) {
      U.on(chip, "click", function () {
        var input = U.$("#heroInput");
        if (input) input.value = chip.dataset.query;
        root.Newsana.runAnalysis(chip.dataset.query);
      });
    });
  }

  function pushRecent(query) {
    var items = U.getPref(CFG.RECENT_KEY, []);
    items = items.filter(function (q) {
      return q.toLowerCase() !== query.toLowerCase();
    });
    items.unshift(query);
    items = items.slice(0, CFG.MAX_RECENT);
    U.setPref(CFG.RECENT_KEY, items);
    renderRecent();
  }

  /* ======================= STATS ======================= */
  function renderStats(stats) {
    var grid = U.$("#statsGrid");
    if (!grid) return;
    var icons = { signals: "fa-wave-square", confidence: "fa-gauge-high", sources: "fa-database", models: "fa-microchip", alerts: "fa-triangle-exclamation" };
    stats.forEach(function (s) {
      var el = U.$('[data-stat="' + s.key + '"]');
      if (!el) return;
      var val = s.key === "confidence" ? s.value + "%" : s.key === "signals" || s.key === "sources" ? U.formatInt(s.value) : s.value;
      el.querySelector(".stat-value").textContent = val;
      el.querySelector(".stat-label").textContent = s.label;
      var delta = el.querySelector(".stat-delta");
      delta.textContent = (s.tone === "down" ? "" : "+") + s.delta;
      delta.className = "stat-delta " + s.tone;
      el.classList.remove("is-loading");
      el.classList.remove("skeleton-card");
      var ic = el.querySelector(".stat-icon");
      if (ic) ic.className = "fa-solid " + (icons[s.key] || "fa-circle") + " stat-icon";
      el.classList.add("hover-lift");
    });
    if (typeof gsap !== "undefined") {
      U.$$("#statsGrid .stat-card").forEach(function (card, i) {
        gsap.fromTo(card, { y: 22, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, delay: i * 0.07, ease: "power3.out" });
      });
    }
  }

  /* ======================= EXECUTIVE SUMMARY ======================= */
  function renderExec(summary) {
    var body = U.$("#execBody");
    var kpEl = U.$("#execKeypoints");
    var meta = U.$("#execMeta");
    var topic = U.$("#execTopic");
    var card = U.$("#execCard");
    var gaugeCard = U.$("#gaugeCard");
    if (!body) return;

    if (topic) topic.textContent = summary.topic + " · synthesized " + U.timeAgo(summary.generatedAt);

    var paras = summary.paragraphs.map(function (p, i) {
      var html = U.escapeHTML(p);
      if (i === 0) {
        html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      }
      return '<p class="exec-para">' + html + "</p>";
    }).join("");

    body.innerHTML = paras;

    kpEl.innerHTML = summary.keypoints
      .map(function (k) {
        return '<div class="exec-kp"><i class="fa-solid fa-check"></i><span>' + U.escapeHTML(k) + "</span></div>";
      })
      .join("");

    var sentClass = summary.sentiment === "bull" ? "sent-bull" : summary.sentiment === "bear" ? "sent-bear" : "sent-hold";
    var sentIcon = summary.sentiment === "bull" ? "fa-arrow-trend-up" : summary.sentiment === "bear" ? "fa-arrow-trend-down" : "fa-equals";
    meta.innerHTML =
      '<span class="meta-tag"><i class="fa-solid fa-database"></i> ' + U.formatInt(summary.sources) + " sources</span>" +
      '<span class="meta-tag"><i class="fa-solid fa-wave-square"></i> ' + U.formatInt(summary.signals) + " signals</span>" +
      '<span class="meta-tag ' + sentClass + '"><i class="fa-solid ' + sentIcon + '"></i> ' + U.escapeHTML(summary.sentimentLabel) + "</span>" +
      '<span class="meta-tag"><i class="fa-solid fa-clock"></i> ' + U.escapeHTML(summary.horizon) + ' horizon</span>';

    if (card) card.classList.remove("is-loading");
    if (gaugeCard) gaugeCard.classList.remove("is-loading");

    root.Newsana.charts.gauge(summary.confidence, {
      label: summary.sentimentLabel,
      dir: summary.sentiment,
      sub: summary.horizon + " outcome horizon"
    });

    if (typeof gsap !== "undefined" && card) {
      U.$$(".exec-para", body).forEach(function (p, i) {
        gsap.fromTo(p, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.55, delay: 0.15 + i * 0.14, ease: "power2.out" });
      });
      U.$$(".exec-kp", kpEl).forEach(function (kp, i) {
        gsap.fromTo(kp, { opacity: 0, x: -14 }, { opacity: 1, x: 0, duration: 0.45, delay: 0.5 + i * 0.08, ease: "power2.out" });
      });
    }
  }

  /* ======================= NEWS ======================= */
  function renderNews(articles) {
    var grid = U.$("#newsGrid");
    if (!grid) return;
    grid.innerHTML = articles
      .map(function (a) {
        var sentIcon = a.sent === "bull" ? "fa-arrow-trend-up" : a.sent === "bear" ? "fa-arrow-trend-down" : "fa-equals";
        var catIcon = "fa-newspaper";
        if (a.cat === "markets") catIcon = "fa-chart-line";
        else if (a.cat === "tech") catIcon = "fa-microchip";
        else if (a.cat === "macro") catIcon = "fa-earth-americas";
        else if (a.cat === "energy") catIcon = "fa-oil-well";
        else if (a.cat === "regulation") catIcon = "fa-scale-balanced";
        else if (a.cat === "geopolitics") catIcon = "fa-globe";
        else if (a.cat === "politics") catIcon = "fa-landmark";
        return (
          '<article class="news-card" data-cat="' + U.escapeHTML(a.cat) + '">' +
          '<div class="news-thumb" style="background:' + a.gradient + '"><i class="fa-solid ' + catIcon + '"></i>' +
          '<span class="news-cat">' + U.escapeHTML(a.cat) + "</span>" +
          '<span class="news-rel"><i class="fa-solid fa-bolt"></i> ' + a.rel + "%</span></div>" +
          '<div class="news-body">' +
          '<h4 class="news-title">' + U.escapeHTML(a.title) + "</h4>" +
          '<p class="news-excerpt">' + U.escapeHTML(a.excerpt) + "</p>" +
          '<div class="news-foot">' +
          '<span class="news-source"><i class="fa-solid fa-building-columns"></i> ' + U.escapeHTML(a.source) + " · " + U.timeAgo(a.time) + "</span>" +
          '<span class="news-sent ' + a.sent + '"><i class="fa-solid ' + sentIcon + '"></i> ' + a.sent + "</span>" +
          "</div></div></article>"
        );
      })
      .join("");

    U.$$(".news-card", grid).forEach(function (card, i) {
      if (typeof gsap !== "undefined") {
        gsap.fromTo(card, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.55, delay: i * 0.06, ease: "power3.out" });
      }
      U.on(card, "click", function () {
        toast("info", "Opening story", "Full article view connects to the Newsana reader workspace.");
      });
    });
  }

  function bindNews() {
    U.$$(".filter-pill").forEach(function (pill) {
      U.on(pill, "click", function () {
        U.$$(".filter-pill").forEach(function (p) {
          p.classList.remove("active");
        });
        pill.classList.add("active");
        var filter = pill.dataset.filter;
        U.$$(".news-card").forEach(function (card) {
          var show = filter === "all" || card.dataset.cat === filter;
          card.style.display = show ? "" : "none";
        });
      });
    });
  }

  /* ======================= RESEARCH REPORT ======================= */
  function bindReport() {
    U.$$(".report-tab").forEach(function (tab) {
      U.on(tab, "click", function () {
        U.$$(".report-tab").forEach(function (t) {
          t.classList.remove("active");
        });
        tab.classList.add("active");
        if (root.Newsana.mock) {
          var report = settingsCache && settingsCache.report ? settingsCache.report : root.Newsana.mock.analysis(CFG.DEFAULT_QUERY).report;
          renderReport(report, tab.dataset.tab);
        }
      });
    });

    U.on(U.$("#downloadReport"), "click", function () {
      toast("success", "Export started", "PDF dossier is being generated and will download shortly.");
    });
    U.on(U.$("#regenerateReport"), "click", function () {
      var topic = settingsCache && settingsCache.topic ? settingsCache.topic : CFG.DEFAULT_QUERY;
      toast("info", "Regenerating", "CrewAI Reporter agent is drafting a fresh dossier…");
      root.Newsana.runAnalysis(topic, { silent: true });
    });
  }

  function renderReport(report, tabName) {
    var content = U.$("#reportContent");
    if (!content) return;
    var tab = tabName || (U.$(".report-tab.active") ? U.$(".report-tab.active").dataset.tab : "exec");

    var html = "";
    if (tab === "exec") {
      html = "<div class='report-stat-row'>" +
        report.exec.stats.map(function (s) {
          return '<div class="report-stat"><strong>' + U.escapeHTML(s.value) + "</strong><span>" + U.escapeHTML(s.label) + "</span></div>";
        }).join("") +
        "</div>" +
        report.exec.paragraphs.map(function (p) {
          return "<p>" + U.escapeHTML(p) + "</p>";
        }).join("") +
        "<h4>Key takeaways</h4><ul>" +
        report.exec.bullets.map(function (b) {
          return "<li><i class='fa-solid fa-check'></i><span>" + U.escapeHTML(b) + "</span></li>";
        }).join("") +
        "</ul>";
    } else if (tab === "analysis") {
      html = report.analysis.map(function (a) {
        return "<h4>" + U.escapeHTML(a.h) + "</h4><p>" + U.escapeHTML(a.p) + "</p>";
      }).join("");
    } else if (tab === "forecast") {
      html = report.forecast.map(function (f) {
        return "<h4>" + U.escapeHTML(f.h) + "</h4><p>" + U.escapeHTML(f.p) + "</p>";
      }).join("");
    } else if (tab === "risks") {
      html =
        "<h4>Risk matrix</h4>" +
        '<table class="risk-table"><thead><tr><th>Risk</th><th>Severity</th><th>Description</th></tr></thead><tbody>' +
        report.risks.map(function (r) {
          return '<tr><td><strong>' + U.escapeHTML(r.name) + "</strong></td><td><span class='sev " + r.sev + "'>" + r.sev.toUpperCase() + "</span></td><td>" + U.escapeHTML(r.desc) + "</td></tr>";
        }).join("") +
        "</tbody></table>";
    } else if (tab === "sources") {
      html =
        "<h4>Evidence base</h4>" +
        '<table class="risk-table"><thead><tr><th>Source class</th><th>References</th><th>Type</th></tr></thead><tbody>' +
        report.sources.map(function (s) {
          return "<tr><td><strong>" + U.escapeHTML(s.name) + "</strong></td><td>" + U.formatInt(s.count) + "</td><td>" + U.escapeHTML(s.type) + "</td></tr>";
        }).join("") +
        "</tbody></table>";
    }
    content.innerHTML = html;
    if (typeof gsap !== "undefined") {
      gsap.fromTo(content, { opacity: 0.4, y: 10 }, { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" });
    }
  }

  /* ======================= EXPLAINABLE AI ======================= */
  function renderExplain(explain) {
    var featEl = U.$("#explainFeatures");
    var sigEl = U.$("#explainSignals");
    var card = U.$("#explainCard");
    var sigCard = U.$("#signalsCard");
    var model = U.$("#explainModel");
    var acc = U.$("#explainAcc");
    if (!featEl) return;

    if (model) model.textContent = "Model: " + explain.model + " · SHAP analysis";
    if (acc) acc.textContent = explain.accuracy + "% acc";

    var max = Math.max.apply(null, explain.features.map(function (f) {
      return Math.abs(f.value);
    }));

    featEl.innerHTML = explain.features
      .map(function (f) {
        var pct = (Math.abs(f.value) / max) * 100;
        var color = f.dir === "pos" ? C.emerald : C.red;
        var cls = f.dir === "pos" ? "pos" : "neg";
        var label = (f.dir === "pos" ? "+" : "") + f.value.toFixed(2);
        var glow = color + "aa";
        return (
          '<div class="feature-row">' +
          '<span class="feature-name" title="' + U.escapeHTML(f.name) + '">' + U.escapeHTML(f.name) + "</span>" +
          '<div class="feature-track"><div class="feature-fill" data-pct="' + pct + '" style="background:' + color + ";box-shadow:0 0 12px " + glow + '"></div></div>' +
          '<span class="feature-val ' + cls + '">' + label + "</span></div>"
        );
      })
      .join("");

    U.$$(".feature-fill", featEl).forEach(function (fill, i) {
      setTimeout(function () {
        fill.style.width = fill.dataset.pct + "%";
      }, 120 + i * 130);
    });

    sigEl.innerHTML = explain.signals
      .map(function (s) {
        var dirCls = s.dir === "pos" ? "pos" : "neg";
        var dirIcon = s.dir === "pos" ? "fa-arrow-trend-up" : "fa-arrow-trend-down";
        return (
          '<div class="signal-item">' +
          '<span class="signal-dir ' + dirCls + '"><i class="fa-solid ' + dirIcon + '"></i></span>' +
          '<div class="signal-body"><div class="signal-title">' + U.escapeHTML(s.title) + "</div>" +
          '<div class="signal-src">' + U.escapeHTML(s.src) + "</div></div>" +
          '<span class="signal-imp ' + dirCls + '">' + U.escapeHTML(s.impact) + "</span></div>"
        );
      })
      .join("");

    if (card) card.classList.remove("is-loading");
    if (sigCard) sigCard.classList.remove("is-loading");
  }

  /* ======================= CREW ======================= */
  function bindCrew() {
    U.on(U.$("#runCrewBtn"), "click", function () {
      root.Newsana.runCrewFlow();
    });
    U.on(U.$("#clearLog"), "click", function () {
      var log = U.$("#crewLog");
      if (log) log.innerHTML = "";
    });
  }

  function renderCrewStatic(crew) {
    var pipe = U.$("#crewPipeline");
    var agents = U.$("#crewAgents");
    var log = U.$("#crewLog");
    if (!pipe) return;

    var stepDefs = [
      { icon: "fa-magnifying-glass", name: "Research", desc: "Ingest & rank 1,200+ sources", key: "researcher" },
      { icon: "fa-chart-pie", name: "Analyze", desc: "Cluster signals & map entities", key: "analyst" },
      { icon: "fa-chart-line", name: "Predict", desc: "Run ensemble outcome models", key: "forecaster" },
      { icon: "fa-file-pen", name: "Report", desc: "Draft dossier & flag risks", key: "reporter" }
    ];

    pipe.innerHTML = stepDefs
      .map(function (s, i) {
        return (
          '<div class="pipe-step" data-step="' + s.key + '">' +
          '<span class="pipe-num">' + (i + 1) + "</span>" +
          '<div class="pipe-body">' +
          '<div class="pipe-name"><i class="fa-solid ' + s.icon + '"></i>' + s.name + "</div>" +
          '<div class="pipe-desc">' + s.desc + "</div>" +
          '<div class="pipe-status" data-status="' + s.key + '">idle</div>' +
          "</div></div>"
        );
      })
      .join("");

    agents.innerHTML = crew.agents
      .map(function (a) {
        return (
          '<div class="agent-card" data-agent="' + a.id + '">' +
          '<div class="agent-head">' +
          '<span class="agent-avatar"><i class="fa-solid ' + a.icon + '"></i></span>' +
          '<div><div class="agent-name">' + U.escapeHTML(a.name) + "</div><div class='agent-role'>" + U.escapeHTML(a.role) + "</div></div>" +
          '<span class="agent-state" data-state="' + a.id + '">idle</span></div>' +
          '<div class="agent-task" data-task="' + a.id + '">Awaiting dispatch</div>' +
          '<div class="progress"><div class="progress-bar" data-bar="' + a.id + '"></div></div>' +
          "</div>"
        );
      })
      .join("");

    log.innerHTML = crew.logs
      .map(function (l) {
        return "<div class='log-line'><span class='log-ts'>" + U.formatClock() + "</span><span class='log-agent'>crew</span><span>" + U.escapeHTML(l) + "</span></div>";
      })
      .join("");

    ["crewPipelineCard", "crewConsoleCard", "crewAgentsCard"].forEach(function (id) {
      var el = U.$("#" + id);
      if (el) el.classList.remove("is-loading");
    });
  }

  function logLine(text, cls, agent) {
    var log = U.$("#crewLog");
    if (!log) return;
    var line = document.createElement("div");
    line.className = "log-line" + (cls ? " " + cls : "");
    line.innerHTML = "<span class='log-ts'>" + U.formatClock() + "</span><span class='log-agent'>" + U.escapeHTML(agent || "crew") + "</span><span>" + U.escapeHTML(text) + "</span>";
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
    return line;
  }

  function simulateCrew(crew) {
    var steps = ["researcher", "analyst", "forecaster", "reporter"];
    var agentMeta = {
      researcher: { task: "Scanning 1,200 sources…", done: "12,480 signals mined & deduped" },
      analyst: { task: "Clustering by theme & computing sentiment…", done: "6,240 clusters · entity graph mapped" },
      forecaster: { task: "Running ensemble models across 6 seeds…", done: "4,900 Monte Carlo paths simulated" },
      reporter: { task: "Drafting dossier & flagging risks…", done: "Report compiled · 3 risks flagged" }
    };

    logLine("pipeline started · topic=" + crew.topic, "", "crew");
    logLine("dispatch order: " + steps.join(" → "), "", "crew");

    var stepIdx = 0;
    function runStep() {
      var key = steps[stepIdx];
      var agent = crew.agents.find(function (a) {
        return a.id === key;
      });
      var pipeStep = U.$('.pipe-step[data-step="' + key + '"]');
      var stateEl = U.$('[data-state="' + key + '"]');
      var taskEl = U.$('[data-task="' + key + '"]');
      var barEl = U.$('[data-bar="' + key + '"]');
      var card = U.$('[data-agent="' + key + '"]');

      if (pipeStep) pipeStep.classList.add("active");
      if (card) card.classList.add("working");
      if (stateEl) {
        stateEl.textContent = "working";
        stateEl.className = "agent-state working";
      }
      if (taskEl) taskEl.textContent = agentMeta[key].task;
      logLine("agent=" + key + " · " + agentMeta[key].task, "", key);

      var progress = 0;
      var timer = setInterval(function () {
        progress += U.rand(6, 16);
        if (progress >= 100) progress = 100;
        if (barEl) barEl.style.width = progress + "%";
        var statusEl = U.$('[data-status="' + key + '"]');
        if (statusEl) statusEl.innerHTML = '<span class="sp">working</span> ' + progress + "%";
        if (progress >= 100) {
          clearInterval(timer);
          if (pipeStep) {
            pipeStep.classList.remove("active");
            pipeStep.classList.add("done");
          }
          if (card) {
            card.classList.remove("working");
            card.classList.add("done");
          }
          if (stateEl) {
            stateEl.textContent = "done";
            stateEl.className = "agent-state done";
          }
          if (taskEl) taskEl.textContent = agentMeta[key].done;
          var statusEl2 = U.$('[data-status="' + key + '"]');
          if (statusEl2) statusEl2.innerHTML = '<span class="ok">done</span> 100%';
          logLine("agent=" + key + " complete · " + agentMeta[key].done, "ok", key);
          stepIdx++;
          if (stepIdx < steps.length) {
            runStep();
          } else {
            logLine("pipeline complete · " + crew.result, "ok", "crew");
            toast("success", "CrewAI pipeline complete", "4 agents finished · report ready in Research Report.");
            var runBtn = U.$("#runCrewBtn");
            if (runBtn) {
              runBtn.disabled = false;
              runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run pipeline';
            }
          }
        }
      }, U.rand(320, 560));
    }
    runStep();
  }

  /* ======================= SETTINGS ======================= */
  function defaultSettings() {
    return U.getPref(CFG.SETTINGS_KEY, {
      name: CFG.USER.name,
      email: CFG.USER.email,
      plan: CFG.USER.plan,
      apiBase: CFG.API_BASE,
      refreshMinutes: "15",
      range: "30",
      toggles: {
        sound: true,
        alerts: true,
        digest: false,
        autoRefresh: true,
        demoMode: false,
        telemetry: true
      }
    });
  }

  function bindSettings() {
    U.$$(".settings-tab").forEach(function (tab) {
      U.on(tab, "click", function () {
        U.$$(".settings-tab").forEach(function (t) {
          t.classList.remove("active");
        });
        tab.classList.add("active");
        renderSettings(tab.dataset.settingsTab);
      });
    });
  }

  function renderSettings(tabName) {
    var content = U.$("#settingsContent");
    if (!content) return;
    var s = settingsCache || defaultSettings();
    var tab = tabName || (U.$(".settings-tab.active") ? U.$(".settings-tab.active").dataset.settingsTab : "general");
    var t = s.toggles;
    var html = "";

    if (tab === "general") {
      html =
        '<div class="settings-group"><div class="settings-group-title">Profile</div>' +
        '<div class="form-row"><div><div class="form-label">Display name</div><div class="form-hint">Shown across the workspace</div></div>' +
        '<input class="form-input" type="text" data-set="name" value="' + U.escapeHTML(s.name) + '" /></div>' +
        '<div class="form-row"><div><div class="form-label">Email</div><div class="form-hint">Used for reports & alerts</div></div>' +
        '<input class="form-input" type="email" data-set="email" value="' + U.escapeHTML(s.email) + '" /></div>' +
        '<div class="form-row"><div><div class="form-label">Plan</div><div class="form-hint">Your current subscription tier</div></div>' +
        '<div><span class="plan-badge" style="margin-left:0"><i class="fa-solid fa-crown"></i> ' + U.escapeHTML(s.plan) + "</span></div></div></div>" +
        '<div class="settings-group"><div class="settings-group-title">Workspace</div>' +
        '<div class="form-row"><div><div class="form-label">Auto-refresh interval</div><div class="form-hint">How often signals are re-synthesized</div></div>' +
        '<select class="form-select" data-set="refreshMinutes"><option value="5">Every 5 min</option><option value="15"' + (s.refreshMinutes === "15" ? " selected" : "") + ">Every 15 min</option><option value=\"30\"" + (s.refreshMinutes === "30" ? " selected" : "") + ">Every 30 min</option><option value=\"60\"" + (s.refreshMinutes === "60" ? " selected" : "") + ">Hourly</option></select></div>" +
        '<div class="form-row"><div><div class="form-label">Default chart range</div><div class="form-hint">Applied to analytics panels</div></div>' +
        '<select class="form-select" data-set="range"><option value="7">7 days</option><option value="14">14 days</option><option value="30"' + (s.range === "30" ? " selected" : "") + ">30 days</option><option value=\"90\"" + (s.range === "90" ? " selected" : "") + ">90 days</option></select></div></div>";
    } else if (tab === "appearance") {
      html =
        '<div class="settings-group"><div class="settings-group-title">Theme</div>' +
        '<div class="form-row"><div><div class="form-label">Dark theme</div><div class="form-hint">Newsana runs in premium dark mode</div></div>' +
        '<span class="toggle"><input type="checkbox" checked disabled /><span class="toggle-slider"></span></span></div>' +
        '<div class="form-row"><div><div class="form-label">Animated background</div><div class="form-hint">Aurora glow & grid effects</div></div>' +
        '<span class="toggle"><input type="checkbox" data-set="toggles.aurora" checked /><span class="toggle-slider"></span></span></div>' +
        '<div class="form-row"><div><div class="form-label">Reduce motion</div><div class="form-hint">Minimize transitions & effects</div></div>' +
        '<span class="toggle"><input type="checkbox" data-set="toggles.reduceMotion" /><span class="toggle-slider"></span></span></div></div>' +
        '<div class="settings-group"><div class="settings-group-title">Layout</div>' +
        '<div class="form-row"><div><div class="form-label">Compact density</div><div class="form-hint">Tighter cards and spacing</div></div>' +
        '<span class="toggle"><input type="checkbox" data-set="toggles.compact" /><span class="toggle-slider"></span></span></div></div>';
    } else if (tab === "api") {
      html =
        '<div class="settings-group"><div class="settings-group-title">Backend connection</div>' +
        '<div class="form-row" style="flex-direction:column;align-items:stretch"><div><div class="form-label">API base URL</div><div class="form-hint">Same origin by default. Endpoints: /api/status · /api/analyze · /api/crew · /api/graph · /api/ingest</div></div>' +
        '<input class="form-input" style="width:100%;margin-top:10px" type="text" data-set="apiBase" value="' + U.escapeHTML(s.apiBase || "") + '" placeholder="https://api.newsana.ai" /></div>' +
        '<div class="form-row"><div><div class="form-label">Demo mode</div><div class="form-hint">Use the local simulation engine</div></div>' +
        '<span class="toggle"><input type="checkbox" data-set="toggles.demoMode" /><span class="toggle-slider"></span></span></div>' +
        '<div class="settings-group"><div class="settings-group-title">Models</div>' +
        '<div class="form-row"><div><div class="form-label">Enabled ensembles</div><div class="form-hint">Predictor · Sentiment Net · Signal Miner</div></div>' +
        '<span class="model-chip"><i class="fa-solid fa-check"></i> 6 active</span></div></div>' +
        '<p class="settings-footnote"><i class="fa-solid fa-circle-info"></i> Requests time out after 15s and automatically fall back to the demo engine if the backend is unreachable.</p>';
    } else if (tab === "notifications") {
      html =
        '<div class="settings-group"><div class="settings-group-title">Channels</div>' +
        '<div class="form-row"><div><div class="form-label">Risk alerts</div><div class="form-hint">Notify when a new risk crosses the threshold</div></div>' +
        '<span class="toggle"><input type="checkbox" data-set="toggles.alerts"' + (t.alerts ? " checked" : "") + ' /><span class="toggle-slider"></span></span></div>' +
        '<div class="form-row"><div><div class="form-label">Sound effects</div><div class="form-hint">Play a chime on pipeline completion</div></div>' +
        '<span class="toggle"><input type="checkbox" data-set="toggles.sound"' + (t.sound ? " checked" : "") + ' /><span class="toggle-slider"></span></span></div>' +
        '<div class="form-row"><div><div class="form-label">Daily digest</div><div class="form-hint">Morning briefing email</div></div>' +
        '<span class="toggle"><input type="checkbox" data-set="toggles.digest"' + (t.digest ? " checked" : "") + ' /><span class="toggle-slider"></span></span></div>' +
        '<div class="form-row"><div><div class="form-label">Auto-refresh status</div><div class="form-hint">Show banner when pipeline refreshes</div></div>' +
        '<span class="toggle"><input type="checkbox" data-set="toggles.autoRefresh"' + (t.autoRefresh ? " checked" : "") + ' /><span class="toggle-slider"></span></span></div></div>';
    } else if (tab === "data") {
      html =
        '<div class="settings-group"><div class="settings-group-title">Ingest a source</div>' +
        '<div class="form-row" style="flex-direction:column;align-items:stretch">' +
        '<div><div class="form-label">Source URL or text</div><div class="form-hint">Posts to POST /api/ingest</div></div>' +
        '<input class="form-input" style="width:100%;margin-top:10px" type="text" id="ingestUrl" placeholder="https://example.com/article" /></div>' +
        '<div class="form-row"><div><div class="form-label">Content type</div><div class="form-hint">How the source should be parsed</div></div>' +
        '<select class="form-select" id="ingestType"><option value="article">Article</option><option value="feed">RSS feed</option><option value="api">API endpoint</option><option value="raw">Raw text</option></select></div>' +
        '<div class="form-row"><div></div><button class="btn btn-primary btn-sm" id="ingestBtn"><i class="fa-solid fa-arrow-down-to-bracket"></i> Ingest now</button></div>' +
        '<div class="form-row"><div><div class="form-label">Clear recent searches</div><div class="form-hint">Remove locally stored history</div></div>' +
        '<button class="btn btn-ghost btn-sm" id="clearRecentData"><i class="fa-solid fa-broom"></i> Clear history</button></div>' +
        '<p class="settings-footnote"><i class="fa-solid fa-shield-halved"></i> Data is processed server-side; documents are chunked and embedded for the knowledge graph.</p>';
    }

    content.innerHTML = html;
    bindSettingsForm();
  }

  function bindSettingsForm() {
    var form = U.$("#settingsContent");
    if (!form) return;
    var s = settingsCache || defaultSettings();

    U.$$("input[data-set], select[data-set]", form).forEach(function (field) {
      U.on(field, "change", function () {
        var path = field.dataset.set.split(".");
        if (path[0] === "toggles") {
          s.toggles[path[1]] = field.checked;
        } else {
          s[path[0]] = field.value;
        }
        settingsCache = s;
      });
    });

    var ingestUrl = U.$("#ingestUrl");
    var ingestBtn = U.$("#ingestBtn");
    if (ingestBtn) {
      U.on(ingestBtn, "click", function () {
        var url = ingestUrl ? ingestUrl.value.trim() : "";
        if (!url) {
          toast("warn", "Missing source", "Enter a URL or text block to ingest.");
          return;
        }
        var type = U.$("#ingestType");
        ingestBtn.disabled = true;
        root.Newsana.api.ingest({ url: url, type: type ? type.value : "article" }).then(function (res) {
          ingestBtn.disabled = false;
          toast(res.accepted ? "success" : "error", "Ingest " + (res.accepted ? "queued" : "rejected"), (res.accepted ? res.metadata.simulated ? "Simulated " : "" : "") + "Processing “" + U.truncate(url, 48) + "” for the knowledge graph.");
          if (ingestUrl) ingestUrl.value = "";
        });
      });
    }

    var clearRecent = U.$("#clearRecentData");
    if (clearRecent) {
      U.on(clearRecent, "click", function () {
        U.setPref(CFG.RECENT_KEY, []);
        renderRecent();
        toast("info", "History cleared", "Recent searches have been removed.");
      });
    }
  }

  function saveSettings() {
    var s = settingsCache || defaultSettings();
    U.setPref(CFG.SETTINGS_KEY, s);
    if (s.toggles.demoMode && !CFG.DEMO_ONLY) {
      CFG.DEMO_ONLY = true;
      root.Newsana.api.setBase("");
    }
    root.Newsana.api.setBase(s.apiBase);
  }

  /* ======================= NOTIFICATIONS ======================= */
  function bindNotifications() {
    renderNotifications();
  }

  function renderNotifications() {
    var list = U.$("#notifList");
    if (!list) return;
    var anyUnread = notifications.some(function (n) {
      return n.unread;
    });
    var btn = U.$("#notifBtn");
    if (btn) btn.classList.toggle("has-dot", anyUnread);
    list.innerHTML = notifications
      .map(function (n) {
        return (
          '<button class="notif-item' + (n.unread ? " unread" : "") + '">' +
          '<span class="notif-icon ' + n.icon + '"><i class="fa-solid ' + (n.icon === "done" ? "fa-circle-check" : n.icon === "warn" ? "fa-triangle-exclamation" : "fa-circle-info") + '"></i></span>' +
          '<span class="notif-body"><strong>' + U.escapeHTML(n.title) + '</strong><p>' + U.escapeHTML(n.text) + "</p><time>" + U.escapeHTML(n.time) + "</time></span></button>"
        );
      })
      .join("");
  }

  /* ======================= SHORTCUTS ======================= */
  function bindShortcuts() {
    U.on(document, "keydown", function (e) {
      if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) {
        e.preventDefault();
        var hero = U.$("#heroInput");
        var global = U.$("#globalSearch");
        (hero || global).focus();
      }
    });
  }

  /* ======================= LOADING STATES ======================= */
  function loadSection(id, renderFn) {
    var el = U.$("#" + id);
    if (el) el.classList.add("is-loading");
    setTimeout(function () {
      renderFn();
    }, U.rand(650, 1000));
  }

  /* ======================= PUBLIC API ======================= */
  root.Newsana = root.Newsana || {};
  root.Newsana.ui = {
    init: init,
    toast: toast,
    renderStatus: renderStatus,
    renderStats: renderStats,
    renderExec: renderExec,
    renderNews: renderNews,
    renderReport: renderReport,
    renderExplain: renderExplain,
    renderCrewStatic: renderCrewStatic,
    simulateCrew: simulateCrew,
    pushRecent: pushRecent,
    loadSection: loadSection,
    openModal: openModal,
    closeModal: closeModal,
    logLine: logLine
  };
})(window);
