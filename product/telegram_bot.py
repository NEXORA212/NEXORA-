"""Telegram-канал NEXORA (long polling, только стандартная библиотека).

Запуск:  TG_TOKEN=... python3 product/telegram_bot.py [config.json]
Заявки сохраняются и уходят владельцу так же, как из веб-виджета (см. server.py).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import engine  # noqa: E402
from server import notify, save_lead  # noqa: E402


def call(token: str, method: str, payload: dict, timeout: int = 40) -> dict:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        json.dumps(payload).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def keyboard(buttons: list[str]) -> dict:
    if not buttons:
        return {"remove_keyboard": True}
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return {"keyboard": rows, "resize_keyboard": True}


def main() -> None:
    token = os.environ.get("TG_TOKEN")
    if not token:
        sys.exit("Нужен TG_TOKEN (получить у @BotFather)")
    path = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "config.example.json"
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    sessions: dict[int, dict] = {}
    offset = 0
    print("NEXORA Telegram-бот запущен", flush=True)
    while True:
        try:
            updates = call(token, "getUpdates", {"offset": offset, "timeout": 30})["result"]
        except Exception as exc:
            print("getUpdates failed:", type(exc).__name__, flush=True)
            time.sleep(5)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            text, chat = message.get("text"), message.get("chat", {}).get("id")
            if not text or chat is None:
                continue
            session = sessions.setdefault(chat, engine.new_session())
            messages, buttons, lead = engine.handle(config, session, text)
            if lead:
                save_lead(lead)
                notify(lead)
            for i, msg in enumerate(messages):
                payload = {"chat_id": chat, "text": msg}
                if i == len(messages) - 1:
                    payload["reply_markup"] = keyboard(buttons)
                try:
                    call(token, "sendMessage", payload, timeout=10)
                except Exception as exc:
                    print("sendMessage failed:", type(exc).__name__, flush=True)


if __name__ == "__main__":
    main()
