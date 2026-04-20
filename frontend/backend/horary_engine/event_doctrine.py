from __future__ import annotations

from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


WEATHER_TOKENS = (
    "weather",
    "rain",
    "raining",
    "rainy",
    "cloud",
    "cloudy",
    "storm",
    "sun",
    "sunny",
    "wind",
    "windy",
    "snow",
    "snowy",
    "dry",
    "wet",
)

RELIGIOUS_EVENT_TOKENS = (
    "festival",
    "religious festival",
    "holy day",
    "feast day",
    "church",
    "ritual",
    "ceremony",
    "sabbat",
    "lughnasadh",
    "lammas",
    "easter",
    "christmas",
    "yule",
    "samhain",
    "beltane",
    "imbolc",
    "ostara",
    "mabon",
)

MARRIAGE_EVENT_TOKENS = (
    "wedding",
    "marriage ceremony",
    "wedding day",
    "bridal",
)

SECULAR_CELEBRATION_EVENT_TOKENS = (
    "party",
    "garden party",
    "birthday",
    "birthday party",
    "celebration",
    "reception",
    "banquet",
    "gala",
    "picnic",
    "ball",
)


def analyze_event_question_text(question: str, question_type: Any | None = None) -> Dict[str, Any] | None:
    q = (question or "").lower().strip()
    if not q or not any(token in q for token in WEATHER_TOKENS):
        return None

    if any(token in q for token in RELIGIOUS_EVENT_TOKENS):
        return {
            "family": "event_weather_religious",
            "category_override": Category.GENERAL,
            "relevant_houses": [9],
            "event_house": 9,
            "quesited_house": 9,
            "doctrine": "Weather for a religious festival is judged from the festival significator itself, which belongs to the 9th house.",
        }

    if any(token in q for token in MARRIAGE_EVENT_TOKENS):
        return {
            "family": "event_weather_marriage",
            "category_override": Category.GENERAL,
            "relevant_houses": [7],
            "event_house": 7,
            "quesited_house": 7,
            "doctrine": "Weather for a wedding or marriage ceremony is judged from the wedding as a 7th-house occasion.",
        }

    if any(token in q for token in SECULAR_CELEBRATION_EVENT_TOKENS):
        return {
            "family": "event_weather_celebration",
            "category_override": Category.GENERAL,
            "relevant_houses": [5],
            "event_house": 5,
            "quesited_house": 5,
            "doctrine": "Weather for a party or social celebration is judged from the event itself as a 5th-house pleasure and festivity matter.",
        }

    return None
