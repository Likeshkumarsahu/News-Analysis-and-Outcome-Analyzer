/**
 * ============================================================================
 * NEWSANA AI — GLOBAL CONFIGURATION MODULE
 * ============================================================================
 * @file config.js
 * @description Central runtime configuration object mounted on the `window` scope.
 * Stores application metadata, API endpoint bases, localStorage keys, user profile
 * defaults, and UI theme color constants used by Chart.js and D3 visualizers.
 * ============================================================================
 */

(function (root) {
  "use strict";

  /** Parse URL search parameters for dynamic runtime overrides */
  var params = new URLSearchParams(root.location.search);

  /**
   * Safely retrieves an item from LocalStorage with a fallback value.
   * @param {string} key - LocalStorage key name.
   * @param {*} fallback - Default return value if key does not exist or fails.
   * @returns {string|*} Stored value or fallback.
   */
  function storageGet(key, fallback) {
    try {
      var v = root.localStorage.getItem(key);
      return v === null ? fallback : v;
    } catch (e) {
      return fallback;
    }
  }

  /** Global application configuration instance */
  root.NewsanaConfig = {
    /** Application metadata */
    APP_NAME: "Newsana AI",
    VERSION: "3.2.1",

    /** Network and API defaults */
    API_BASE: params.get("api") || storageGet("newsana_api_base", ""),
    TIMEOUT: 15000,
    DEFAULT_QUERY: "Global economy outlook and market direction",
    DEMO_ONLY: params.get("demo") === "1",

    /** Storage key definitions */
    RECENT_KEY: "newsana_recent",
    SETTINGS_KEY: "newsana_settings",
    MAX_RECENT: 8,

    /** Active User Profile Defaults */
    USER: {
      name: "Ava Chen",
      email: "ava@newsana.ai",
      role: "Principal Analyst",
      plan: "Pro"
    },

    /** Theme typography & color palettes for Chart.js / D3 rendering */
    THEME: {
      chartFont: "'Inter', system-ui, sans-serif",
      monoFont: "'JetBrains Mono', monospace",
      colors: {
        text: "#8b93a7",
        textBright: "#eef1f7",
        grid: "rgba(255,255,255,0.05)",
        violet: "#8b5cf6",
        indigo: "#6366f1",
        cyan: "#22d3ee",
        emerald: "#34d399",
        amber: "#fbbf24",
        red: "#f87171",
        pink: "#e879f9",
        blue: "#60a5fa"
      },
      palette: ["#8b5cf6", "#22d3ee", "#34d399", "#fbbf24", "#f87171", "#e879f9", "#60a5fa", "#6366f1"]
    }
  };
})(window);
