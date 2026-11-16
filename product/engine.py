"""Диалоговый движок NEXORA: запись клиента и приём вопросов.

Не зависит от канала: сайт-виджет, Telegram и любой другой мессенджер
вызывают одну функцию handle(). Вся настройка под клиента — в JSON-конфиге.
"""
from __future__ import annotations

import datetime as dt
import re

BOOK, PRICES, INFO, ASK = "Записаться", "Цены", "Адрес и часы", "Задать вопрос"
MENU = [BOOK, PRICES, INFO, ASK]
BACK = "В меню"
CONSENT_YES = "Согласен"
WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def new_session() -> dict:
    return {"step": "start", "data": {}}


def normalize_phone(text: str) -> str | None:
    """Приводит российский номер к виду +7XXXXXXXXXX или возвращает None."""
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits[0] in "78":
        digits = digits[1:]
    if len(digits) != 10 or digits[0] not in "3489":
        return None
    return "+7" + digits


def available_days(config: dict, today: dt.date, count: int = 5) -> list[str]:
    """Ближайшие рабочие дни, начиная с завтра: 'чт 19.11'."""
    work_days = set(config.get("work_days", [0, 1, 2, 3, 4, 5]))
    days, day = [], today
    while len(days) < count:
        day += dt.timedelta(days=1)
        if day.weekday() in work_days:
            days.append(f"{WEEKDAYS[day.weekday()]} {day:%d.%m}")
    return days


def find_answer(config: dict, text: str) -> str | None:
    low = text.lower()
    for item in config.get("faq", []):
        if any(key in low for key in item["keywords"]):
            return item["answer"]
    return None


def _menu(config: dict, prefix: str = "") -> tuple[list[str], list[str]]:
    text = prefix or f"Здравствуйте! Это {config['name']}. Чем помочь?"
    return [text], MENU


def handle(config: dict, session: dict, text: str, today: dt.date | None = None):
    """Обрабатывает сообщение клиента.

    Возвращает (messages, buttons, lead). lead — словарь с заявкой, когда
    она собрана полностью, иначе None.
    """
    today = today or dt.date.today()
    text = text.strip()
    step, data = session["step"], session["data"]

    def go(new_step, messages, buttons=None, lead=None):
        session["step"] = new_step
        return messages, buttons or [], lead

    if step == "start" or text in (BACK, "/start"):
        session["data"] = {}
        return go("menu", *_menu(config))

    if step == "menu":
        if text == BOOK:
            names = [s["name"] for s in config["services"]]
            return go("service", ["Что нужно сделать?"], names + [BACK])
        if text == PRICES:
            lines = [f"• {s['name']} — {s['price']}" for s in config["services"]]
            return go("menu", ["\n".join(lines)], MENU)
        if text == INFO:
            return go("menu", [f"{config['address']}\n{config['hours']}"], MENU)
        if text == ASK:
            return go("question", ["Напишите вопрос одним сообщением."], [BACK])
        # Свободный текст в меню — пробуем ответить из базы знаний.
        answer = find_answer(config, text)
        if answer:
            return go("menu", [answer], MENU)
        return go("menu", *_menu(config, "Выберите вариант кнопкой ниже."))

    if step == "service":
        names = [s["name"] for s in config["services"]]
        if text not in names:
            return go("service", ["Выберите услугу из списка."], names + [BACK])
        data["service"] = text
        return go("day", ["На какой день?"], available_days(config, today) + [BACK])

    if step == "day":
        days = available_days(config, today)
        if text not in days:
            return go("day", ["Выберите день из списка."], days + [BACK])
        data["day"] = text
        return go("time", ["Во сколько удобно?"], config["slots"] + [BACK])

    if step == "time":
        if text not in config["slots"]:
            return go("time", ["Выберите время из списка."], config["slots"] + [BACK])
        data["time"] = text
        return go("name", ["Как к вам обращаться?"])

    if step == "question":
        data["question"] = text
        answer = find_answer(config, text)
        if answer:
            return go("menu", [answer], MENU)
        return go("name", ["Уточню у администратора и перезвоним. Как к вам обращаться?"])

    if step == "name":
        if not 2 <= len(text) <= 60:
            return go("name", ["Напишите, пожалуйста, имя."])
        data["name"] = text
        return go("phone", ["Номер телефона для связи?"])

    if step == "phone":
        phone = normalize_phone(text)
        if not phone:
            return go("phone", ["Не похоже на номер. Пример: +7 912 345-67-89"])
        data["phone"] = phone
        policy = config.get("privacy_url", "")
        note = f" Политика: {policy}" if policy else ""
        return go(
            "consent",
            [f"Согласны на обработку имени и телефона для связи с вами?{note}"],
            [CONSENT_YES, BACK],
        )

    if step == "consent":
        if text != CONSENT_YES:
            return go("consent", ["Без согласия не могу передать заявку."], [CONSENT_YES, BACK])
        lead = dict(data, type="booking" if "service" in data else "question")
        if lead["type"] == "booking":
            done = (
                f"Готово, {data['name']}! Записал: {data['service']}, "
                f"{data['day']} в {data['time']}. Администратор подтвердит по телефону."
            )
        else:
            done = f"Спасибо, {data['name']}! Перезвоним в рабочее время."
        session["data"] = {}
        return go("menu", [done], MENU, lead)

    session["data"] = {}
    return go("menu", *_menu(config))


def format_lead(lead: dict) -> str:
    """Текст уведомления для владельца бизнеса."""
    if lead["type"] == "booking":
        head = f"Новая запись: {lead['service']}, {lead['day']} в {lead['time']}"
    elif lead["type"] == "question":
        head = f"Вопрос клиента: {lead['question']}"
    else:
        head = "Заявка с лендинга: перезвонить"
    return f"{head}\n{lead['name']}, {lead['phone']}"
