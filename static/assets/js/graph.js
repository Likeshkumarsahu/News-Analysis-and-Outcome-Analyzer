/* ============================================================
   NEWSANA AI — KNOWLEDGE GRAPH (D3 force simulation)
   ============================================================ */
(function (root) {
  "use strict";

  var U = root.Newsana.utils;
  var CFG = root.NewsanaConfig;
  var C = CFG.THEME.colors;

  var CATEGORY_COLORS = {
    Macro: C.violet,
    Markets: C.cyan,
    Sector: C.emerald,
    Geo: C.amber
  };

  var state = {
    svg: null,
    g: null,
    simulation: null,
    zoom: null,
    nodes: [],
    links: [],
    initialized: false
  };

  function buildLegend() {
    var legendEl = U.$("#graphLegend");
    if (!legendEl) return;
    var cats = Object.keys(CATEGORY_COLORS);
    legendEl.innerHTML = cats
      .map(function (c) {
        return '<span class="legend-item"><span class="legend-dot" style="background:' + CATEGORY_COLORS[c] + '"></span>' + c + "</span>";
      })
      .join("");
  }

  function radius(w) {
    w = Number(w);
    if (!Number.isFinite(w)) w = 1;
    return 8 + (w / 9) * 14;
  }

  function labelFor(n) {
    const label = n && n.label ? String(n.label) : "Unknown";
    return label.length > 16 ? label.slice(0, 15) + "…" : label;
  }

  function draw(data) {
    var container = U.$("#graphContainer");
    var tooltip = U.$("#graphTooltip");
    if (!container) return;

    var width = container.clientWidth || 800;
    var height = container.clientHeight || 470;

    container.innerHTML = "";
    state.svg = d3
      .select(container)
      .append("svg")
      .attr("width", "100%")
      .attr("height", "100%")
      .attr("viewBox", "0 0 " + width + " " + height)
      .attr("preserveAspectRatio", "xMidYMid meet");

    state.g = state.svg.append("g");

    var defs = state.svg.append("defs");

    var arrowMarker = defs
      .append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 0 10 10")
      .attr("refX", 20)
      .attr("refY", 5)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto-start-reverse");
    arrowMarker
      .append("path")
      .attr("d", "M 0 0 L 10 5 L 0 10 z")
      .attr("fill", "rgba(255,255,255,0.28)");

    var link = state.g
      .append("g")
      .selectAll("line")
      .data(data.links)
      .enter()
      .append("line")
      .attr("stroke", "rgba(255,255,255,0.16)")
      .attr("stroke-width", function (d) {
        return 0.6 + d.value * 1.6;
      })
      .attr("marker-end", "url(#arrow)");

    var node = state.g
      .append("g")
      .selectAll("g")
      .data(data.nodes)
      .enter()
      .append("g")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    node
      .append("circle")
      .attr("r", function (d) {
        return radius(d.weight);
      })
      .attr("fill", function (d) {
        return CATEGORY_COLORS[d.category] || C.violet;
      })
      .attr("fill-opacity", 0.32)
      .attr("stroke", function (d) {
        return CATEGORY_COLORS[d.category] || C.violet;
      })
      .attr("stroke-width", 1.6)
      .attr("class", "graph-node")
      .style("cursor", "pointer");

    node
      .append("text")
      .attr("dy", function (d) {
        return radius(d.weight) + 14;
      })
      .attr("text-anchor", "middle")
      .attr("class", "graph-label")
      .style("font-family", CFG.THEME.chartFont)
      .style("font-size", function (d) {
        return d.weight >= 7 ? "11px" : "10px";
      })
      .style("font-weight", function (d) {
        return d.weight >= 8 ? "700" : "500";
      })
      .style("fill", function (d) {
        return d.weight >= 8 ? C.textBright : C.text;
      })
      .style("pointer-events", "none")
      .text(function (d) {
        return labelFor(d);
      });

    node.on("mouseover", function (event, d) {
      d3.select(this).select("circle").attr("stroke-width", 3);
      showTooltip(event, d);
      highlight(d, true);
      d3.select(this).raise();
    });

    node.on("mousemove", function (event) {
      moveTooltip(event);
    });

    node.on("mouseout", function (event, d) {
      d3.select(this).select("circle").attr("stroke-width", 1.6);
      hideTooltip();
      highlight(d, false);
    });

    node.on("click", function (event, d) {
      focusNode(d);
    });

    state.simulation = d3
      .forceSimulation(data.nodes)
      .force(
        "link",
        d3
          .forceLink(data.links)
          .id(function (d) {
            return d.id;
          })
          .distance(function (d) {
            return 55 + (1 - d.value) * 85;
          })
          .strength(0.55)
      )
      .force("charge", d3.forceManyBody().strength(-340))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(function (d) {
        return radius(d.weight) + 10;
      }))
      .on("tick", function () {
        link
          .attr("x1", function (d) { return d.source.x; })
          .attr("y1", function (d) { return d.source.y; })
          .attr("x2", function (d) { return d.target.x; })
          .attr("y2", function (d) { return d.target.y; });
        node.attr("transform", function (d) {
          return "translate(" + d.x + "," + d.y + ")";
        });
      });

    state.zoom = d3.zoom().scaleExtent([0.3, 4]).on("zoom", function (event) {
      state.g.attr("transform", event.transform);
    });
    state.svg.call(state.zoom);

    bindControls();

    var count = U.$("#graphCount");
    var linkCount = U.$("#graphLinkCount");
    if (count) count.textContent = data.nodes.length + " nodes";
    if (linkCount) linkCount.textContent = data.links.length + " edges";

    state.initialized = true;
  }

  function showTooltip(event, d) {
    var tip = U.$("#graphTooltip");
    if (!tip) return;
    var rels = [];
    state.links.forEach(function (l) {
      if ((l.source.id || l.source) === d.id) rels.push(l.target.label || l.target);
      if ((l.target.id || l.target) === d.id) rels.push(l.source.label || l.source);
    });
    var color = CATEGORY_COLORS[d.category] || C.violet;
    tip.innerHTML =
      "<strong>" + U.escapeHTML(d.label) + "</strong>" +
      "<small>" + U.escapeHTML((rels.slice(0, 4).join(" · ")) || "Standalone entity") + "</small>" +
      '<span class="tt-tag" style="color:' + color + ';background:' + color + "1a;border:1px solid " + color + "55" + '">' + U.escapeHTML(d.category) + "</span>";
    tip.hidden = false;
    moveTooltip(event);
  }

  function moveTooltip(event) {
    var tip = U.$("#graphTooltip");
    var container = U.$("#graphContainer");
    if (!tip || !container) return;
    var rect = container.getBoundingClientRect();
    var x = event.clientX - rect.left + 16;
    var y = event.clientY - rect.top + 12;
    if (x + 240 > rect.width) x = event.clientX - rect.left - 250;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }

  function hideTooltip() {
    var tip = U.$("#graphTooltip");
    if (tip) tip.hidden = true;
  }

  function highlight(d, on) {
    var connected = new Set();
    state.links.forEach(function (l) {
      var s = l.source.id || l.source;
      var t = l.target.id || l.target;
      if (s === d.id) connected.add(t);
      if (t === d.id) connected.add(s);
    });
    d3.selectAll(".graph-node")
      .attr("fill-opacity", function (n) {
        if (n.id === d.id) return on ? 0.55 : 0.32;
        return connected.has(n.id) ? (on ? 0.42 : 0.32) : on ? 0.08 : 0.32;
      })
      .attr("stroke-opacity", function (n) {
        if (n.id === d.id) return 1;
        return on && !connected.has(n.id) ? 0.15 : 1;
      });
    d3.selectAll("line").attr("stroke-opacity", function (l) {
      var s = l.source.id || l.source;
      var t = l.target.id || l.target;
      return !on || connected.has(s) || connected.has(t) ? 1 : 0.08;
    });
    d3.selectAll(".graph-label").attr("fill-opacity", function (n) {
      return !on || n.id === d.id || connected.has(n.id) ? 1 : 0.25;
    });
  }

  function focusNode(d) {
    if (!state.simulation) return;
    var rect = U.$("#graphContainer").getBoundingClientRect();
    state.simulation.alphaTarget(0.35).restart();
    var x = rect.width / 2;
    var y = rect.height / 2;
    state.svg
      .transition()
      .duration(700)
      .call(state.zoom.transform, d3.zoomIdentity.translate(x - d.x, y - d.y).scale(1.15));
    highlight(d, true);
    setTimeout(function () {
      highlight(d, false);
    }, 2200);
  }

  function dragstarted(event, d) {
    if (!event.active) state.simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  function dragended(event, d) {
    if (!event.active) state.simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  function bindControls() {
    var zoomStep = function (k) {
      if (!state.svg || !state.zoom) return;
      var transform = d3.zoomTransform(state.svg.node());
      state.svg.transition().duration(400).call(state.zoom.scaleBy, k, [transform.x, transform.y]);
    };
    U.on(U.$("#graphZoomIn"), "click", function () {
      zoomStep(1.35);
    });
    U.on(U.$("#graphZoomOut"), "click", function () {
      zoomStep(1 / 1.35);
    });
    U.on(U.$("#graphReset"), "click", function () {
      if (!state.svg || !state.zoom) return;
      state.svg.transition().duration(600).call(state.zoom.transform, d3.zoomIdentity);
    });
  }

  function load() {
    if (!window.d3) return;
    buildLegend();
    root.Newsana.api.getGraph().then(function (data) {
      state.nodes = data.nodes;
      state.links = data.links;
      var card = U.$("#graphCard");
      if (card) card.classList.remove("is-loading");
      draw(data);
      console.log("graph");
      console.log(data.nodes);
      console.log(data.links);
      data.nodes.forEach((n, i) => {
          if (
              !n ||
              !n.id ||
              !n.label ||
              n.weight === undefined ||
              Number.isNaN(Number(n.weight))
          ) {
              console.log(i, n);
          }
      });

      console.log("Invalid links:");

      data.links.forEach((l, i) => {
          if (!l.source || !l.target) {
              console.log(i, l);
          }
      });
    });
  }

  function resize() {
    if (!state.initialized || !state.svg) return;
    var container = U.$("#graphContainer");
    if (!container) return;
    var width = container.clientWidth;
    var height = container.clientHeight;
    state.svg.attr("viewBox", "0 0 " + width + " " + height);
    if (state.simulation) {
      state.simulation.force("center", d3.forceCenter(width / 2, height / 2));
    }
  }

  root.Newsana = root.Newsana || {};
  root.Newsana.graph = {
    init: load,
    resize: resize,
    reload: function () {
      load();
    }
  };
})(window);
