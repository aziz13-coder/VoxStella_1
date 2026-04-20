from pathlib import Path
import sys
from datetime import datetime

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend import astro_clock_engine as ace_mod


class _StubHoraryEngine:
    def __init__(self):
        self.last_settings = None

    def judge(self, question, settings):
        self.last_settings = settings
        return {
            "question": question,
            "considerations": {"moon_void": False},
            "chart_data": {
                "planets": {
                    "Moon": {"longitude": 12.0, "sign": "Aries", "house": 1},
                }
            },
        }


def _build_engine(monkeypatch):
    monkeypatch.setattr(ace_mod, "HoraryEngine", _StubHoraryEngine)
    return ace_mod.AstroClockEngine()


def test_paused_mode_uses_effective_datetime(monkeypatch):
    eng = _build_engine(monkeypatch)
    paused_dt = datetime(2022, 6, 10, 14, 37, 45)

    eng.settings.mode = ace_mod.ClockMode.PAUSED
    eng.settings.paused_at = paused_dt
    eng.settings.location = "Jerusalem, Israel"

    eng._generate_chart_with_horary_engine(paused_dt)
    sent = eng.horary_engine.last_settings

    assert sent is not None
    assert sent["use_current_time"] is False
    assert sent["date"] == "2022-06-10"
    assert sent["time"] == "14:37"
    assert sent["include_internal_chart"] is True


def test_moon_state_uses_top_level_fallbacks(monkeypatch):
    eng = _build_engine(monkeypatch)
    chart_data = {
        "planets": {
            "Moon": {"longitude": 129.5, "sign": "Leo", "house": 5},
        }
    }
    chart_result = {
        "considerations": {"moon_void": True},
        "moon_last_aspect": {
            "planet": "Venus",
            "aspect": "Trine",
            "perfection_eta_days": 0.2,
            "perfection_eta_description": "a few hours",
            "applying": False,
        },
        "moon_next_aspect": {
            "planet": "Saturn",
            "aspect": "Square",
            "perfection_eta_days": 1.1,
            "perfection_eta_description": "about a day",
            "applying": True,
        },
    }

    planets = eng._extract_planet_positions(chart_data)
    moon_state = eng._calculate_moon_state(chart_data, planets, chart_result)

    assert moon_state.void_of_course is True
    assert isinstance(moon_state.next_aspect, dict)
    assert moon_state.next_aspect["planet"] == "Saturn"
    assert isinstance(moon_state.last_aspect, dict)
    assert moon_state.last_aspect["planet"] == "Venus"
