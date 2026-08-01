/**
 * ============================================================================
 * NEWSANA AI — CHARTS & VISUALIZATION MODULE
 * ============================================================================
 * @file charts.js
 * @description Renders Chart.js analytics graphs and dynamic SVG prediction gauges:
 *   1. Sentiment Trend Line Chart (with 7-day rolling average)
 *   2. Sector Distribution Doughnut Chart
 *   3. Sentiment Radar Spider Chart
 *   4. Article Volume Sources Bar Chart
 *   5. Outcome Probability Radial SVG Gauge with animated needle & counter.
 * ============================================================================
 */

(function (root) {
  "use strict";

  var U = root.Newsana.utils;
  var CFG = root.NewsanaConfig;
  var C = CFG.THEME.colors;

  /** Active Chart.js Instance Registry */
  var instances = {};

  /** Configures default global Chart.js typography, colors, and tooltip styles */
  function setupDefaults() {
    if (typeof Chart === "undefined") return;
    Chart.defaults.font.family = CFG.THEME.chartFont;
    Chart.defaults.font.size = 11;
    Chart.defaults.color = C.text;
    Chart.defaults.animation.duration = 900;
    Chart.defaults.animation.easing = "easeOutQuart";
    Chart.defaults.borderColor = C.grid;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 7;
    Chart.defaults.plugins.legend.labels.boxHeight = 7;
    Chart.defaults.plugins.legend.labels.padding = 16;
    Chart.defaults.plugins.tooltip.backgroundColor = "rgba(10,12,22,0.94)";
    Chart.defaults.plugins.tooltip.borderColor = "rgba(255,255,255,0.12)";
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.titleColor = C.textBright;
    Chart.defaults.plugins.tooltip.bodyColor = C.text;
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
    Chart.defaults.plugins.tooltip.boxPadding = 5;
    Chart.defaults.plugins.tooltip.titleFont = { weight: "700", size: 12 };
  }

  /**
   * Helper generating vertical canvas gradients for area fills.
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context.
   * @param {string} colorTop - Top gradient color stop.
   * @param {string} colorBottom - Bottom gradient color stop.
   * @param {number} [height=280] - Height of target canvas.
   * @returns {CanvasGradient} Formatted gradient.
   */
  function verticalGradient(ctx, colorTop, colorBottom, height) {
    var g = ctx.createLinearGradient(0, 0, 0, height || 280);
    g.addColorStop(0, colorTop);
    g.addColorStop(1, colorBottom);
    return g;
  }

  /** Default Tooltip Options */
  function makeTooltip() {
    return {
      displayColors: true,
      mode: "index",
      intersect: false
    };
  }

  /** Chart Factory Wrapper handling instance destruction & creation */
  function chart(id, config) {
    var el = U.$("#" + id);
    if (!el) return null;
    if (instances[id]) {
      instances[id].destroy();
    }
    if (typeof Chart === "undefined") return null;
    instances[id] = new Chart(el.getContext("2d"), config);
    return instances[id];
  }

  /** Render Sentiment Score Trend Line Chart */
  function renderSentiment(data) {
    var el = U.$("#chartSentiment");
    if (!el || typeof Chart === "undefined") return;
    var ctx = el.getContext("2d");
    var grad = verticalGradient(ctx, "rgba(139,92,246,0.35)", "rgba(139,92,246,0)", 320);
    var grad2 = verticalGradient(ctx, "rgba(34,211,238,0.25)", "rgba(34,211,238,0)", 320);
    return chart("chartSentiment", {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Composite score",
            data: data.values,
            borderColor: C.violet,
            backgroundColor: grad,
            fill: true,
            tension: 0.42,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: C.violet,
            pointHoverBorderColor: "#fff",
            pointHoverBorderWidth: 2
          },
          {
            label: "7-day rolling",
            data: data.rolling,
            borderColor: C.cyan,
            backgroundColor: grad2,
            fill: true,
            tension: 0.42,
            borderWidth: 2,
            borderDash: [1, 0],
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: C.cyan,
            pointHoverBorderColor: "#fff",
            pointHoverBorderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: makeTooltip(),
        plugins: {
          legend: { position: "top", align: "end" },
          tooltip: { callbacks: { label: function (c) { return " " + c.dataset.label + ": " + Number(c.parsed.y).toFixed(1); } } }
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
          y: { grid: { color: C.grid }, ticks: { maxTicksLimit: 5 } }
        }
      }
    });
  }

  /** Render Sector Breakdown Doughnut Chart */
  function renderSectors(data) {
    var palette = [C.violet, C.cyan, C.emerald, C.amber, C.red, C.pink, C.blue, C.indigo];
    return chart("chartSectors", {
      type: "doughnut",
      data: {
        labels: data.labels,
        datasets: [
          {
            data: data.values,
            backgroundColor: data.labels.map(function (_, i) { return palette[i % palette.length]; }),
            borderColor: "rgba(5,6,13,0.9)",
            borderWidth: 3,
            hoverOffset: 10,
            hoverBorderColor: "#fff"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: { position: "right", align: "center" },
          tooltip: { callbacks: { label: function (c) { return " " + c.label + ": " + c.parsed + "%"; } } }
        }
      }
    });
  }

  /** Render Radar Sentiment Metrics Chart */
  function renderRadar(data) {
    return chart("chartRadar", {
      type: "radar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Sentiment score",
            data: data.values,
            borderColor: C.cyan,
            backgroundColor: "rgba(34,211,238,0.16)",
            borderWidth: 2,
            pointBackgroundColor: C.cyan,
            pointBorderColor: "#fff",
            pointBorderWidth: 1.5,
            pointRadius: 3.5,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            grid: { color: C.grid },
            angleLines: { color: C.grid },
            pointLabels: { color: C.text, font: { size: 11, weight: "600" } },
            ticks: { stepSize: 25, backdropColor: "transparent", color: C.text }
          }
        }
      }
    });
  }

  /** Render News Sources Distribution Horizontal Bar Chart */
  function renderSources(data) {
    return chart("chartSources", {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Articles processed",
            data: data.values,
            backgroundColor: data.labels.map(function (label) {
              return U.paletteColor(label, [C.violet, C.indigo, C.cyan, C.emerald, C.amber, C.pink, C.blue, C.red]);
            }),
            borderRadius: 7,
            borderSkipped: false,
            barPercentage: 0.72,
            categoryPercentage: 0.85
          }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function (c) { return " " + c.parsed.x + " articles"; } } }
        },
        scales: {
          x: { grid: { color: C.grid }, ticks: { precision: 0 } },
          y: { grid: { display: false } }
        }
      }
    });
  }

  /** Destroy all active Chart.js instances */
  function destroyAll() {
    Object.keys(instances).forEach(function (id) {
      if (instances[id]) instances[id].destroy();
    });
    instances = {};
  }

  /** Batch update all analytics charts */
  function updateAll(data) {
    renderSentiment(data.trend);
    renderSectors(data.sectors);
    renderRadar(data.radar);
    renderSources(data.sources);
  }

  /** Gauge Animation State Memory */
  var lastGauge = { value: 0, dir: "hold" };

  /** Renders & Animates SVG Outcome Prediction Radial Gauge */
  function renderGauge(value, opts) {
    var o = opts || {};
    var target = U.clamp(value, 0, 100);
    var arc = root.Newsana.mock.gaugeArc(target);
    var arcEl = U.$("#gaugeArc");
    var needle = U.$("#gaugeNeedle");
    var needleGroup = U.$("#gaugeNeedleGroup");
    var numEl = U.$("#gaugeValue");
    var labelEl = U.$("#gaugeLabel");
    var tagsEl = U.$("#gaugeTags");
    if (!arcEl) return;

    arcEl.style.strokeDasharray = arc.total + " " + arc.total;
    arcEl.style.strokeDashoffset = arc.offset;
    arcEl.setAttribute("data-value", String(target));

    var dir = o.dir || (target >= 70 ? "bull" : target <= 40 ? "bear" : "hold");
    var label = o.label || (dir === "bull" ? "Constructive" : dir === "bear" ? "Cautionary" : "Balanced");
    var from = lastGauge.value;
    lastGauge = { value: target, dir: dir };

    var needleAngle = -90 + (target / 100) * 180;
    var fromAngle = -90 + (from / 100) * 180;

    if (needle && needleGroup) {
      needleGroup.style.transformOrigin = "100px 110px";
      needleGroup.style.transition = "none";
      needleGroup.style.transform = "rotate(" + fromAngle + "deg)";
      requestAnimationFrame(function () {
        needleGroup.style.transition = "transform 1.4s cubic-bezier(0.16,1,0.3,1)";
        needleGroup.style.transform = "rotate(" + needleAngle + "deg)";
      });
    }

    var startVal = from;
    var startTime = null;
    function count(t) {
      if (startTime === null) startTime = t;
      var prog = Math.min(1, (t - startTime) / 1300);
      var eased = 1 - Math.pow(1 - prog, 3);
      var v = Math.round(startVal + (target - startVal) * eased);
      if (numEl) numEl.textContent = v + "%";
      if (prog < 1) requestAnimationFrame(count);
    }
    requestAnimationFrame(count);

    if (labelEl) labelEl.textContent = label + " outlook";
    if (tagsEl) {
      var dirClass = dir === "bull" ? "tag-bull" : dir === "bear" ? "tag-bear" : "tag-hold";
      var dirIcon = dir === "bull" ? "fa-arrow-trend-up" : dir === "bear" ? "fa-arrow-trend-down" : "fa-equals";
      tagsEl.innerHTML =
        '<span class="tag ' + dirClass + '"><i class="fa-solid ' + dirIcon + '"></i> ' + label + "</span>" +
        '<span class="tag tag-cyan"><i class="fa-regular fa-clock"></i> ' + U.escapeHTML(o.sub || "60d horizon") + "</span>";
    }
  }

  root.Newsana = root.Newsana || {};
  root.Newsana.charts = {
    init: setupDefaults,
    sentiment: renderSentiment,
    sectors: renderSectors,
    radar: renderRadar,
    sources: renderSources,
    updateAll: updateAll,
    destroyAll: destroyAll,
    gauge: renderGauge
  };
})(window);
