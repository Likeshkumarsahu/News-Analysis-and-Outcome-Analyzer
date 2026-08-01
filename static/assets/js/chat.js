/* ============================================================
   NEWSANA AI — CHAT ASSISTANT
   ============================================================ */
(function (root) {
  "use strict";

  var U = root.Newsana.utils;
  var CFG = root.NewsanaConfig;

  var SUGGESTIONS = ["Summarize today's markets", "Predict Fed decision", "Analyze the chip sector", "Top risks this week"];
  var history = [];

  function init() {
    var panel = U.$("#chatPanel");
    var fab = U.$("#fab");
    var close = U.$("#chatClose");
    var form = U.$("#chatForm");
    var input = U.$("#chatInput");
    var suggest = U.$("#chatSuggestions");

    renderSuggestions();

    U.on(fab, "click", toggle);
    U.on(close, "click", close);

    U.on(form, "submit", function (e) {
      e.preventDefault();
      var msg = input.value.trim();
      if (!msg) return;
      input.value = "";
      sendMessage(msg);
    });

    U.on(input, "keydown", function (e) {
      if (e.key === "Enter") {
        form.dispatchEvent(new Event("submit"));
      }
    });

    U.$$(".chip-quick[data-chat-open]").forEach(function (chip) {
      U.on(chip, "click", function () {
        open();
        input.focus();
      });
    });

    setTimeout(function () {
      var msgCount = U.$$(".msg", U.$("#chatMessages")).length;
      if (msgCount === 0 && !panel.classList.contains("open")) {
        open();
        botMessage("Hi " + CFG.USER.name.split(" ")[0] + " — I'm your Newsana analyst assistant. Ask me to <span class='msg-strong'>analyze a topic</span> or <span class='msg-strong'>predict an outcome</span>.", { first: true });
      }
    }, 2600);
  }

  function renderSuggestions() {
    var suggest = U.$("#chatSuggestions");
    if (!suggest) return;
    suggest.innerHTML = SUGGESTIONS.map(function (s) {
      return '<button class="chip" data-suggest="' + U.escapeHTML(s) + '"><i class="fa-solid fa-wand-magic-sparkles"></i>' + U.escapeHTML(s) + "</button>";
    }).join("");
    U.$$(".chip", suggest).forEach(function (chip) {
      U.on(chip, "click", function () {
        sendMessage(chip.dataset.suggest);
      });
    });
  }

  function toggle() {
    var panel = U.$("#chatPanel");
    var fab = U.$("#fab");
    if (!panel) return;
    var isOpen = panel.classList.contains("open");
    if (isOpen) {
      close();
    } else {
      open();
    }
  }

  function open() {
    var panel = U.$("#chatPanel");
    var fab = U.$("#fab");
    if (!panel) return;
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
    fab.classList.add("open");
    var messages = U.$("#chatMessages");
    if (messages) messages.scrollTop = messages.scrollHeight;
    setTimeout(function () {
      var input = U.$("#chatInput");
      if (input) input.focus();
    }, 350);
  }

  function close() {
    var panel = U.$("#chatPanel");
    var fab = U.$("#fab");
    if (!panel) return;
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    fab.classList.remove("open");
  }

  function appendMessage(role, html) {
    var messages = U.$("#chatMessages");
    if (!messages) return;
    var wrap = document.createElement("div");
    wrap.className = "msg " + role;
    var avatarIcon = role === "bot" ? "fa-robot" : "fa-user";
    wrap.innerHTML =
      '<span class="msg-avatar"><i class="fa-solid ' + avatarIcon + '"></i></span>' +
      '<div><div class="msg-bubble">' + html + "</div>" +
      '<div class="msg-time">' + U.formatClock() + "</div></div>";
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
    return wrap;
  }

  function botMessage(html, opts) {
    var o = opts || {};
    var messages = U.$("#chatMessages");
    var typing = document.createElement("div");
    typing.className = "msg bot";
    typing.innerHTML =
      '<span class="msg-avatar"><i class="fa-solid fa-robot"></i></span>' +
      '<div class="msg-bubble"><span class="typing"><i></i><i></i><i></i></span></div>';
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;

    var delay = o.delay == null ? U.rand(650, 1100) : o.delay;
    setTimeout(function () {
      typing.remove();
      var bubble = appendMessage("bot", html);
      history.push({ role: "bot", html: html });
      if (o.first) {
        setTimeout(function () {
          var input = U.$("#chatInput");
          if (input) input.focus();
        }, 200);
      }
    }, delay);
  }

  function userMessage(text) {
    history.push({ role: "user", text: text });
    appendMessage("user", U.escapeHTML(text));
  }

  function sendMessage(text) {
    if (!text) return;
    userMessage(text);
    botMessage("Running full pipeline on <span class='msg-strong'>“" + U.escapeHTML(text) + "”</span> — sources, signals and ensemble models are warming up…");

    root.Newsana.api.analyze(text).then(function (res) {
      var s = res.summary;
      var dirIcon = s.sentiment === "bull" ? "fa-arrow-trend-up" : s.sentiment === "bear" ? "fa-arrow-trend-down" : "fa-equals";
      botMessage(
        "<span class='msg-strong'>" + U.escapeHTML(res.topic) + "</span> — " + s.sentimentLabel.toLowerCase() + " with " + s.confidence + "% confidence.<br>" +
        U.escapeHTML(s.paragraphs[0]) +
        "<div class='chat-stat-row'>" +
        "<span class='chat-stat'><i class='fa-solid " + dirIcon + "'></i> " + U.escapeHTML(s.sentimentLabel) + "</span>" +
        "<span class='chat-stat'><i class='fa-solid fa-database'></i> " + U.formatInt(s.sources) + " sources</span>" +
        "<span class='chat-stat'><i class='fa-solid fa-wave-square'></i> " + U.formatInt(s.signals) + " signals</span>" +
        "<span class='chat-stat'><i class='fa-solid fa-gauge-high'></i> " + s.confidence + "%</span>" +
        "</div>",
        { delay: 700 }
      );
    });
  }

  root.Newsana = root.Newsana || {};
  root.Newsana.chat = {
    init: init,
    toggle: toggle,
    open: open,
    close: close,
    send: sendMessage
  };
})(window);
