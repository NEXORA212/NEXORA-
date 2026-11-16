/* Чат-виджет NEXORA. Встраивание на сайт клиента одной строкой:
   <script src="https://ВАШ-СЕРВЕР/widget.js" data-title="Запись онлайн"></script> */
(function () {
  var script = document.currentScript;
  var api = new URL("/api/chat", script.src).href;
  var title = script.dataset.title || "Запись онлайн";
  var sid = Math.random().toString(36).slice(2) + Date.now().toString(36);
  var started = false;

  var css =
    ".nx-btn{position:fixed;right:20px;bottom:20px;z-index:99999;border:0;border-radius:999px;" +
    "padding:14px 22px;background:#1f6feb;color:#fff;font:600 15px system-ui,sans-serif;" +
    "cursor:pointer;box-shadow:0 6px 24px rgba(0,0,0,.25)}" +
    ".nx-box{position:fixed;right:20px;bottom:80px;z-index:99999;width:340px;max-width:calc(100vw - 32px);" +
    "height:480px;max-height:calc(100vh - 110px);display:none;flex-direction:column;background:#fff;" +
    "color:#111;border-radius:16px;overflow:hidden;box-shadow:0 12px 48px rgba(0,0,0,.3);" +
    "font:14px/1.45 system-ui,sans-serif}" +
    ".nx-box.nx-open{display:flex}" +
    ".nx-head{padding:14px 16px;background:#1f6feb;color:#fff;font-weight:600}" +
    ".nx-log{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;background:#f4f6f9}" +
    ".nx-msg{max-width:85%;padding:9px 12px;border-radius:14px;white-space:pre-wrap;word-wrap:break-word}" +
    ".nx-bot{background:#fff;align-self:flex-start;border:1px solid #e3e7ee}" +
    ".nx-me{background:#1f6feb;color:#fff;align-self:flex-end}" +
    ".nx-opts{display:flex;flex-wrap:wrap;gap:6px;padding:8px 12px;background:#f4f6f9}" +
    ".nx-opts button{border:1px solid #1f6feb;background:#fff;color:#1f6feb;border-radius:999px;" +
    "padding:7px 12px;font:inherit;cursor:pointer}" +
    ".nx-form{display:flex;border-top:1px solid #e3e7ee}" +
    ".nx-form input{flex:1;border:0;padding:13px;font:inherit;outline:none;min-width:0;background:#fff;color:#111}" +
    ".nx-form button{border:0;background:none;color:#1f6feb;font:600 14px system-ui;padding:0 16px;cursor:pointer}";
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  }

  var button = el("button", "nx-btn", title);
  var box = el("div", "nx-box");
  var log = el("div", "nx-log");
  var opts = el("div", "nx-opts");
  var form = el("form", "nx-form");
  var input = el("input");
  input.placeholder = "Сообщение…";
  input.setAttribute("aria-label", "Сообщение");
  form.append(input, el("button", "", "Отправить"));
  box.append(el("div", "nx-head", title), log, opts, form);
  document.body.append(box, button);

  function add(text, cls) {
    log.appendChild(el("div", "nx-msg " + cls, text));
    log.scrollTop = log.scrollHeight;
  }

  function send(text, silent) {
    if (!silent) add(text, "nx-me");
    opts.replaceChildren();
    fetch(api, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sid: sid, text: text }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        data.messages.forEach(function (m) { add(m, "nx-bot"); });
        data.buttons.forEach(function (b) {
          var option = el("button", "", b);
          option.type = "button";
          option.onclick = function () { send(b); };
          opts.appendChild(option);
        });
        log.scrollTop = log.scrollHeight;
      })
      .catch(function () { add("Нет связи. Попробуйте ещё раз.", "nx-bot"); });
  }

  function open() {
    box.classList.add("nx-open");
    if (!started) { started = true; send("/start", true); }
    input.focus();
  }

  button.onclick = function () {
    if (box.classList.contains("nx-open")) box.classList.remove("nx-open");
    else open();
  };
  form.onsubmit = function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (text) { input.value = ""; send(text); }
  };
  window.NexoraWidget = { open: open };
})();
