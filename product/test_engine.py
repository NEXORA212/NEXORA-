"""Тесты движка: python3 -m unittest discover product"""
import datetime as dt
import json
import unittest
from pathlib import Path

import engine

CONFIG = json.loads((Path(__file__).parent / "config.example.json").read_text(encoding="utf-8"))
MONDAY = dt.date(2026, 11, 16)


def talk(session, *texts):
    result = None
    for text in texts:
        result = engine.handle(CONFIG, session, text, today=MONDAY)
    return result


class EngineTest(unittest.TestCase):
    def test_phone(self):
        self.assertEqual(engine.normalize_phone("8 (912) 345-67-89"), "+79123456789")
        self.assertEqual(engine.normalize_phone("+7 912 345 67 89"), "+79123456789")
        self.assertEqual(engine.normalize_phone("9123456789"), "+79123456789")
        self.assertIsNone(engine.normalize_phone("12345"))
        self.assertIsNone(engine.normalize_phone("позвоните мне"))

    def test_days_skip_sunday(self):
        days = engine.available_days(CONFIG, dt.date(2026, 11, 20))  # пятница
        self.assertEqual(days[:3], ["сб 21.11", "пн 23.11", "вт 24.11"])

    def test_full_booking(self):
        s = engine.new_session()
        messages, buttons, lead = talk(
            s, "привет", "Записаться", "Диагностика", "вт 17.11", "12:00", "Иван", "89123456789"
        )
        self.assertIsNone(lead)
        self.assertIn("Согласен", buttons)
        messages, buttons, lead = talk(s, "Согласен")
        self.assertEqual(
            lead,
            {
                "type": "booking",
                "service": "Диагностика",
                "day": "вт 17.11",
                "time": "12:00",
                "name": "Иван",
                "phone": "+79123456789",
            },
        )
        self.assertIn("Записал", messages[0])
        self.assertEqual(s["data"], {})

    def test_no_lead_without_consent(self):
        s = engine.new_session()
        talk(s, "hi", "Записаться", "Шиномонтаж", "ср 18.11", "10:00", "Анна", "+79990001122")
        _, _, lead = talk(s, "нет")
        self.assertIsNone(lead)
        self.assertEqual(s["step"], "consent")

    def test_invalid_input_keeps_step(self):
        s = engine.new_session()
        talk(s, "hi", "Записаться", "Полёт на Луну")
        self.assertEqual(s["step"], "service")
        talk(s, "Диагностика", "вчера")
        self.assertEqual(s["step"], "day")

    def test_faq_and_unknown_question(self):
        s = engine.new_session()
        messages, _, _ = talk(s, "hi", "Задать вопрос", "А гарантия есть?")
        self.assertIn("6 месяцев", messages[0])
        talk(s, "Задать вопрос", "Красите бамперы?", "Олег", "89001112233")
        _, _, lead = talk(s, "Согласен")
        self.assertEqual(lead["type"], "question")
        self.assertEqual(lead["question"], "Красите бамперы?")
        self.assertIn("Красите бамперы?", engine.format_lead(lead))

    def test_back_resets(self):
        s = engine.new_session()
        talk(s, "hi", "Записаться", "Диагностика", "В меню")
        self.assertEqual((s["step"], s["data"]), ("menu", {}))


if __name__ == "__main__":
    unittest.main()
