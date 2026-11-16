"""Веб-канал NEXORA: лендинг, чат-виджет и API. Только стандартная библиотека.

Запуск:  python3 product/server.py [config.json]
Переменные окружения (все необязательные):
  PORT                 порт, по умолчанию 8000
  NOTIFY_TG_TOKEN      токен Telegram-бота для уведомлений владельцу
  NOTIFY_TG_CHAT       chat_id владельца
  NOTIFY_WEBHOOK       URL, куда POST-ом уйдёт JSON заявки (CRM, MAX, почта)
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import engine  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATIC = {
    "/": (ROOT / "site" / "index.html", "text/html; charset=utf-8"),
    "/widget.js": (ROOT / "site" / "widget.js", "application/javascript; charset=utf-8"),
}
LEADS_FILE = Path(os.environ.get("LEADS_FILE", ROOT / "leads.csv"))
FIELDS = ["created", "type", "name", "phone", "service", "day", "time", "question"]
MAX_SESSIONS = 10_000

sessions: dict[str, dict] = {}
lock = threading.Lock()


def save_lead(lead: dict) -> None:
    row = dict(lead, created=dt.datetime.now().isoformat(timespec="seconds"))
    with lock:
        is_new = not LEADS_FILE.exists()
        with LEADS_FILE.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            if is_new:
                writer.writeheader()
            writer.writerow(row)


def _post_json(url: str, payload: dict) -> None:
    req = urllib.request.Request(
        url, json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req, timeout=10).close()


def notify(lead: dict) -> None:
    """Сообщает владельцу о заявке. Сбой уведомления не теряет заявку — она уже в CSV."""
    text = engine.format_lead(lead)
    print("LEAD:", text.replace("\n", " | "), flush=True)
    token, chat = os.environ.get("NOTIFY_TG_TOKEN"), os.environ.get("NOTIFY_TG_CHAT")
    targets = []
    if token and chat:
        targets.append(
            (f"https://api.telegram.org/bot{token}/sendMessage", {"chat_id": chat, "text": text})
        )
    if os.environ.get("NOTIFY_WEBHOOK"):
        targets.append((os.environ["NOTIFY_WEBHOOK"], dict(lead, text=text)))
    for url, payload in targets:
        try:
            _post_json(url, payload)
        except Exception as exc:  # уведомление вторично, заявка сохранена
            print("NOTIFY FAILED:", type(exc).__name__, flush=True)


def make_handler(config: dict):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            # Виджет встраивается на сайты клиентов, поэтому API открыт для любых доменов.
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._send(204, b"", "text/plain")

        def do_GET(self):
            entry = STATIC.get(self.path.split("?")[0])
            if not entry:
                return self._send(404, b"not found", "text/plain")
            self._send(200, entry[0].read_bytes(), entry[1])

        def do_POST(self):
            if self.path not in ("/api/chat", "/api/lead"):
                return self._send(404, b"not found", "text/plain")
            bad = lambda: self._send(400, b'{"error":"bad request"}', "application/json")
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length > 4096:
                    raise ValueError("too large")
                body = json.loads(self.rfile.read(length))
                if self.path == "/api/lead":
                    # Заявка с лендинга NEXORA: владелец бизнеса просит перезвонить.
                    name = str(body["name"]).strip()[:60]
                    phone = engine.normalize_phone(str(body["phone"]))
                    if not name or not phone:
                        return bad()
                    lead = {"type": "callback", "name": name, "phone": phone}
                    save_lead(lead)
                    notify(lead)
                    return self._send(200, b'{"ok":true}', "application/json")
                sid, text = str(body["sid"])[:64], str(body["text"])[:500]
            except (ValueError, KeyError, TypeError):
                return bad()
            with lock:
                if sid not in sessions and len(sessions) >= MAX_SESSIONS:
                    sessions.clear()
                session = sessions.setdefault(sid, engine.new_session())
                messages, buttons, lead = engine.handle(config, session, text)
            if lead:
                save_lead(lead)
                notify(lead)
            out = json.dumps({"messages": messages, "buttons": buttons}, ensure_ascii=False)
            self._send(200, out.encode(), "application/json; charset=utf-8")

        def log_message(self, *args):
            pass

    return Handler


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "config.example.json"
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    port = int(os.environ.get("PORT", 8000))
    print(f"NEXORA: http://localhost:{port}  (конфиг: {path})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), make_handler(config)).serve_forever()


if __name__ == "__main__":
    main()
