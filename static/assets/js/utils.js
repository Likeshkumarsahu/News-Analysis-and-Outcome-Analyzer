/**
 * ============================================================================
 * NEWSANA AI — HELPER UTILITIES MODULE
 * ============================================================================
 * @file utils.js
 * @description Core JavaScript utility library providing DOM querying helpers,
 * event listeners, debouncing/throttling functions, HTML escaping, number/date
 * formatting, random seed utilities, localStorage wrappers, IntersectionObserver
 * scroll animation bindings, and static greeting generators.
 * ============================================================================
 */

(function (root) {
  "use strict";

  /** Utility Container Instance */
  function N() {}

  /**
   * DOM Query Selector Helper ($)
   * @param {string} sel - CSS Selector.
   * @param {HTMLElement} [ctx=document] - Parent element context.
   * @returns {HTMLElement|null} Matching DOM node.
   */
  N.$ = function (sel, ctx) {
    return (ctx || document).querySelector(sel);
  };

  /**
   * DOM Query Selector All Helper ($$)
   * @param {string} sel - CSS Selector.
   * @param {HTMLElement} [ctx=document] - Parent element context.
   * @returns {Array<HTMLElement>} Array of matching DOM elements.
   */
  N.$$ = function (sel, ctx) {
    return Array.prototype.slice.call((ctx || document).querySelectorAll(sel));
  };

  /**
   * Event Listener Wrapper
   * @param {HTMLElement} el - Target element.
   * @param {string} evt - Event type name (e.g. 'click').
   * @param {Function} fn - Callback function.
   * @param {Object} [opts] - AddEventListener options.
   */
  N.on = function (el, evt, fn, opts) {
    if (el) el.addEventListener(evt, fn, opts);
  };

  /**
   * Debounce Execution Helper
   * @param {Function} fn - Function to debounce.
   * @param {number} wait - Delay in milliseconds.
   * @returns {Function} Debounced function wrapper.
   */
  N.debounce = function (fn, wait) {
    var t;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(t);
      t = setTimeout(function () {
        fn.apply(ctx, args);
      }, wait);
    };
  };

  /**
   * Throttle Execution Helper
   * @param {Function} fn - Function to throttle.
   * @param {number} limit - Minimum interval between calls in ms.
   * @returns {Function} Throttled function wrapper.
   */
  N.throttle = function (fn, limit) {
    var last = 0;
    return function () {
      var now = Date.now();
      if (now - last >= limit) {
        last = now;
        fn.apply(this, arguments);
      }
    };
  };

  /**
   * Unique ID Generator
   * @returns {string} Unique alphanumeric ID.
   */
  N.uid = function () {
    return "id-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  };

  /**
   * Sanitize string against XSS script injection vulnerabilities.
   * @param {string} str - Raw string.
   * @returns {string} Escaped HTML string.
   */
  N.escapeHTML = function (str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  };

  /** Truncate long strings with trailing ellipsis */
  N.truncate = function (str, len) {
    if (!str) return "";
    return str.length > len ? str.slice(0, len).trimEnd() + "…" : str;
  };

  /** Format numerical values with unit suffixes (e.g. 1.5M, 20K) */
  N.formatNumber = function (num) {
    if (num == null || isNaN(num)) return "—";
    if (Math.abs(num) >= 1e9) return (num / 1e9).toFixed(1) + "B";
    if (Math.abs(num) >= 1e6) return (num / 1e6).toFixed(1) + "M";
    if (Math.abs(num) >= 1e3) return (num / 1e3).toFixed(1) + "K";
    return String(Math.round(num));
  };

  /** Format integer with US standard comma separators */
  N.formatInt = function (num) {
    if (num == null || isNaN(num)) return "—";
    return Number(num).toLocaleString("en-US");
  };

  /** Short date formatter (e.g. Jul 31) */
  N.formatDate = function (d) {
    var dt = d instanceof Date ? d : new Date(d);
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return months[dt.getMonth()] + " " + dt.getDate();
  };

  /** Humanized relative timestamp generator (e.g. '5m ago', '2h ago') */
  N.timeAgo = function (dateStr) {
    var then = new Date(dateStr).getTime();
    var diff = Date.now() - then;
    if (isNaN(diff) || diff < 0) diff = 0;
    var min = Math.floor(diff / 60000);
    if (min < 1) return "just now";
    if (min < 60) return min + "m ago";
    var hr = Math.floor(min / 60);
    if (hr < 24) return hr + "h ago";
    var day = Math.floor(hr / 24);
    if (day < 30) return day + "d ago";
    return "on " + N.formatDate(new Date(then));
  };

  /** Random Integer bound generator */
  N.rand = function (min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  };

  /** Random Float bound generator */
  N.randFloat = function (min, max) {
    return Math.random() * (max - min) + min;
  };

  /** Seeded Pseudo-Random Generator */
  N.seededRand = function (seed) {
    var s = seed;
    return function () {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };
  };

  /** Pick random item from an array */
  N.pick = function (arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  };

  /** Clamp numerical value within a range [min, max] */
  N.clamp = function (val, min, max) {
    return Math.min(max, Math.max(min, val));
  };

  /** Integer Hashing Algorithm for consistent string color mapping */
  N.hashString = function (str) {
    var h = 0;
    for (var i = 0; i < str.length; i++) {
      h = (h << 5) - h + str.charCodeAt(i);
      h |= 0;
    }
    return Math.abs(h);
  };

  /** Map string deterministically to palette color hex string */
  N.paletteColor = function (str, palette) {
    var p = palette || root.NewsanaConfig.THEME.palette;
    return p[N.hashString(str) % p.length];
  };

  /** Format Date clock time (e.g. 07:45 PM) */
  N.formatClock = function (date) {
    var d = date || new Date();
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  };

  /** Async Promise Timeout delay */
  N.pause = function (ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  };

  /** LocalStorage Preference Setter */
  N.setPref = function (key, val) {
    try {
      root.localStorage.setItem(key, JSON.stringify(val));
    } catch (e) {}
  };

  /** LocalStorage Preference Getter */
  N.getPref = function (key, fallback) {
    try {
      var v = root.localStorage.getItem(key);
      return v === null ? fallback : JSON.parse(v);
    } catch (e) {
      return fallback;
    }
  };

  /** IntersectionObserver Scroll Animation Inserter */
  N.observeReveal = function () {
    if (typeof IntersectionObserver === "undefined") {
      N.$$(".reveal, .reveal-left, .reveal-right").forEach(function (el) {
        el.classList.add("in");
      });
      return;
    }
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
    );
    N.$$(".reveal, .reveal-left, .reveal-right").forEach(function (el) {
      io.observe(el);
    });
  };

  /** Static Text DOM Injector (Greeting, Copyright Year, Version) */
  N.renderStatic = function () {
    var hour = new Date().getHours();
    var greet = "Good evening";
    if (hour < 5) greet = "Burning the midnight oil";
    else if (hour < 12) greet = "Good morning";
    else if (hour < 18) greet = "Good afternoon";
    var g = N.$("#greeting");
    if (g) g.textContent = greet + ", " + root.NewsanaConfig.USER.name.split(" ")[0];
    var fy = N.$("#footerYear");
    if (fy) fy.textContent = new Date().getFullYear();
    var ver = N.$("#footerVersion");
    if (ver) ver.textContent = "v" + root.NewsanaConfig.VERSION;
  };

  root.Newsana = root.Newsana || {};
  root.Newsana.utils = N;
})(window);
