/**
 * ============================================================================
 * NEWSANA AI — API CLIENT INTERFACE & BACKEND CONNECTOR
 * ============================================================================
 * @file api.js
 * @description HTTP API wrapper interfacing with the Python Flask backend routes:
 *   - GET  /api/status  (System status & model version)
 *   - POST /api/analyze (AI multi-agent analysis request)
 *   - POST /api/crew    (CrewAI pipeline trigger)
 *   - GET  /api/graph   (D3 knowledge graph data fetch)
 *   - POST /api/ingest  (Data ingestion pipeline route)
 * Automatically falls back to local `mock.js` data generators if the Flask
 * server is unreachable or offline.
 * ============================================================================
 */

(function (root) {
  "use strict";

  var CFG = root.NewsanaConfig;
  var MOCK = root.Newsana.mock;

  /** Internal Connection State Tracker */
  var MODE = { real: false, demo: false };

  /**
   * Internal HTTP Request Wrapper with Abort Signal Timeout
   * @param {string} path - API route relative path.
   * @param {Object} [options] - Fetch parameters & headers.
   * @returns {Promise<Object>} Resolved JSON response.
   */
  function request(path, options) {
    var opts = options || {};
    var ctrl = new AbortController();
    var timer = setTimeout(function () {
      ctrl.abort();
    }, CFG.TIMEOUT);
    var headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    return fetch(CFG.API_BASE + path, {
      method: opts.method || "GET",
      headers: headers,
      body: opts.body,
      signal: ctrl.signal
    }).then(function (res) {
      clearTimeout(timer);
      if (!res.ok) {
        var err = new Error("HTTP " + res.status + " from " + path);
        err.status = res.status;
        throw err;
      }
      return res.json();
    });
  }

  /** Force Client into Demo Fallback Mode */
  function toDemo() {
    MODE.demo = true;
    MODE.real = false;
    return MODE;
  }

  /** Newsana Public API Methods Factory */
  function api() {
    return {
      get mode() {
        return MODE;
      },

      /** Initialize dynamic API base endpoint from LocalStorage */
      init: function () {
        var saved = null;
        try {
          saved = root.localStorage.getItem("newsana_api_base");
        } catch (e) {}
        if (saved) CFG.API_BASE = saved;
      },

      /** Override API Base URL */
      setBase: function (base) {
        CFG.API_BASE = (base || "").replace(/\/+$/, "");
        try {
          root.localStorage.setItem("newsana_api_base", CFG.API_BASE);
        } catch (e) {}
        MODE.real = false;
        MODE.demo = false;
        return CFG.API_BASE;
      },

      /** GET /api/status - Fetch Backend Server Health and Status */
      getStatus: function () {
        if (CFG.DEMO_ONLY) return Promise.resolve(MOCK.status());
        return request("/api/status")
          .then(function (data) {
            MODE.real = true;
            MODE.demo = false;
            return data;
          })
          .catch(function () {
            return MOCK.status();
          });
      },

      /** POST /api/analyze - Run Multi-Agent Prediction and Sentiment Engine */
      analyze: function (query, opts) {
        var payload = { query: query, options: opts || {} };
        if (CFG.DEMO_ONLY || MODE.demo) {
          return new Promise(function (resolve) {
            setTimeout(function () {
              resolve(MOCK.analysis(query, opts));
            }, 700);
          });
        }
        return request("/api/analyze", {
          method: "POST",
          body: JSON.stringify(payload)
        })
          .catch(function () {
            toDemo();
            return MOCK.analysis(query, opts);
          });
      },

      /** POST /api/crew - Run CrewAI Multi-Agent Pipeline Execution */
      runCrew: function (topic, opts) {
        var payload = { topic: topic, options: opts || {} };
        if (CFG.DEMO_ONLY || MODE.demo) {
          return new Promise(function (resolve) {
            setTimeout(function () {
              resolve(MOCK.crew(topic));
            }, 500);
          });
        }
        return request("/api/crew", {
          method: "POST",
          body: JSON.stringify(payload)
        }).catch(function () {
          toDemo();
          return MOCK.crew(topic);
        });
      },

      /** GET /api/graph - Fetch D3 Knowledge Graph Nodes & Links Payload */
      getGraph: function () {
        if (CFG.DEMO_ONLY || MODE.demo) {
          return new Promise(function (resolve) {
            setTimeout(function () {
              resolve(MOCK.graph());
            }, 500);
          });
        }
        return request("/api/graph").catch(function () {
          toDemo();
          return MOCK.graph();
        });
      },

      /** POST /api/ingest - Ingest Article URL / Payload for Vector Embedding */
      ingest: function (payload) {
        var body = payload || {};
        if (CFG.DEMO_ONLY || MODE.demo) {
          return new Promise(function (resolve) {
            setTimeout(function () {
              resolve({
                accepted: true,
                id: "ing-" + Date.now().toString(36),
                status: "queued",
                processed: 0,
                chunks: 0,
                source: body.url || body.source || "unknown",
                type: body.type || "article",
                metadata: { simulated: true }
              });
            }, 600);
          });
        }
        return request("/api/ingest", {
          method: "POST",
          body: JSON.stringify(body)
        }).catch(function () {
          toDemo();
          return {
            accepted: true,
            id: "ing-" + Date.now().toString(36),
            status: "queued",
            processed: 0,
            chunks: 0,
            source: body.url || body.source || "unknown",
            type: body.type || "article",
            metadata: { simulated: true }
          };
        });
      }
    };
  }

  root.Newsana = root.Newsana || {};
  root.Newsana.api = api();
})(window);
