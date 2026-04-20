from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.engine import HoraryEngine  # noqa: E402
import backend.horary_engine.engine as engine_module  # noqa: E402


def _judge_public_pet_replay(question: str, location: str, date: str, time: str, timezone: str):
    engine = HoraryEngine()
    settings = {
        "location": location,
        "date": date,
        "time": time,
        "timezone": timezone,
        "use_current_time": False,
    }

    with contextlib.redirect_stdout(io.StringIO()):
        return engine.judge(question, settings)


def test_valkyrie_lost_dog_replay_aligns_on_missing_pet_recovery(monkeypatch):
    """Replay a public lost-dog horary case with a confirmed outcome.

    Source:
    https://www.valkyrieastrology.com/Makeover/astroblogs/LostDog/LostDog02262025.htm

    The article publishes a horary chart for a missing dog (Valkyrie) cast for
    Naples, New York on January 6, 2025 at 11:19:45 PM, and reports the dog was
    later recovered.

    The article does not publish the literal question sentence, so this test
    uses a conservative replay prompt that matches the documented scenario:
    "Will my missing dog be found?"
    """

    monkeypatch.setattr(
        engine_module,
        "safe_geocode",
        lambda _location: (42.6152778, -77.4027778, "Naples, New York"),
    )

    result = _judge_public_pet_replay(
        "Will my missing dog be found?",
        "Naples, New York",
        "2025-01-06",
        "23:19",
        "America/New_York",
    )

    location_projection = result.get("lost_object_location") or {}
    reasoning_rules = [entry.get("rule", "") for entry in result.get("reasoning", [])]

    assert result["judgment"] == "YES"
    assert result["confidence"] >= 80
    assert result["question_analysis"]["question_type"] == "pet"
    assert result["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert result["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert location_projection.get("applies") is True
    assert len(location_projection.get("directional_cues") or []) >= 1
    assert any("6th-house pet significator" in rule or "pet significator" in rule for rule in reasoning_rules)
    assert any(
        "Reception between querent and pet significators supports the animal being found" in rule
        for rule in reasoning_rules
    )


def test_patrick_missing_cat_replay_respects_earlier_frustration_and_denies_alive_recovery(monkeypatch):
    """Replay Patrick Watson's missing-cat case against the real external outcome.

    Source:
    https://patrickwatsonastrology.com/the-horary-mystery-of-the-missing-cat/

    Patrick Watson reports receiving the question "Will I find my cat alive?"
    on August 3, 2021 at 2:46 AM in Phoenix, Arizona. The post explains that
    the apparent Moon-Jupiter trine is pre-empted by an earlier perfection to
    Mercury, and concludes the missing cat was not recovered alive.
    """

    monkeypatch.setattr(
        engine_module,
        "safe_geocode",
        lambda _location: (33.4484, -112.0740, "Phoenix, Arizona"),
    )

    result = _judge_public_pet_replay(
        "Will I find my cat alive?",
        "Phoenix, Arizona",
        "2021-08-03",
        "02:46",
        "America/Phoenix",
    )

    reasoning_rules = [entry.get("rule", "") for entry in result.get("reasoning", [])]

    assert result["judgment"] == "NO"
    assert result["question_analysis"]["question_type"] == "pet"
    assert result["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert result["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert any("pre-empts the apparent recovery route" in rule for rule in reasoning_rules)


def test_biggie_missing_dog_replay_aligns_on_same_day_return(monkeypatch):
    """Replay an Astrology Weekly missing-dog case with exact public metadata.

    Source:
    https://astrologyweekly.com/threads/missing-pet-horary.748/

    The thread includes the literal question "Where is my pet chow chow Biggie"
    and the chart metadata "12/28/06 1:18pm CST Opelousas, LA". The thread itself
    is dated December 28, 2005 and the follow-up recovery post is December 29,
    2005, so the year in the body is treated as an obvious typo and replayed as
    2005-12-28.

    Reported outcome:
    - "He came home tonight at 10:44pm with another dog (female)"
    """

    monkeypatch.setattr(
        engine_module,
        "safe_geocode",
        lambda _location: (30.5335, -92.0815, "Opelousas, Louisiana"),
    )

    result = _judge_public_pet_replay(
        "Where is my pet chow chow Biggie?",
        "Opelousas, Louisiana",
        "2005-12-28",
        "13:18",
        "America/Chicago",
    )

    location_projection = result.get("lost_object_location") or {}
    reasoning_rules = [entry.get("rule", "") for entry in result.get("reasoning", [])]
    primary_labels = [entry.get("label", "").lower() for entry in location_projection.get("primary_places", [])]

    assert result["judgment"] == "YES"
    assert result["question_analysis"]["question_type"] == "pet"
    assert result["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert result["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert location_projection.get("applies") is True
    assert any("nearby route" in label or "local streets" in label for label in primary_labels)
    assert location_projection.get("directional_cues", [{}])[0].get("label") == "East by South"
    assert any("6th-house pet significator" in rule or "pet significator" in rule for rule in reasoning_rules)


def test_frawley_missing_cat_replay_aligns_on_return_within_a_day(monkeypatch):
    """Replay the John Frawley missing-cat case as reproduced by Anthony Louis.

    Source:
    https://tonylouis.wordpress.com/2017/04/01/where-is-my-pet-is-he-okay/

    Anthony Louis reproduces John Frawley's missing-cat horary chart and
    reports that the cat returned less than 24 hours later, meowing at the
    door after sunset. This replay uses the published chart metadata for that
    case: 1993-08-30 09:20 in London.
    """

    monkeypatch.setattr(
        engine_module,
        "safe_geocode",
        lambda _location: (51.5074, -0.1278, "London, England"),
    )

    result = _judge_public_pet_replay(
        "Where is the missing cat?",
        "London, England",
        "1993-08-30",
        "09:20",
        "Europe/London",
    )

    location_projection = result.get("lost_object_location") or {}
    reasoning_rules = [entry.get("rule", "") for entry in result.get("reasoning", [])]
    primary_labels = [entry.get("label", "").lower() for entry in location_projection.get("primary_places", [])]

    assert result["judgment"] == "YES"
    assert result["question_analysis"]["question_type"] == "pet"
    assert result["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert result["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert location_projection.get("applies") is True
    assert any("hidden" in label or "difficult-to-reach" in label for label in primary_labels)
    assert location_projection.get("directional_cues", [{}])[0].get("label") == "West"
    assert any("angular, favoring quick visibility or return" in rule for rule in reasoning_rules)
    assert any(
        "Reception between querent and pet significators supports the animal being found" in rule
        for rule in reasoning_rules
    )


def test_pukka_missing_cat_replay_aligns_on_return_and_close_to_home_hiding(monkeypatch):
    """Replay the Pukka missing-cat case with exact public chart metadata.

    Source:
    http://astrological-mind.com/tag/horary-astrology/

    The article "Where is Pukka?" publishes the exact chart metadata as
    November 4 2007 at 16:48 AEDT in Melbourne, Australia and reports that the
    cat returned in three days after hiding near the querent's apartment block.
    """

    monkeypatch.setattr(
        engine_module,
        "safe_geocode",
        lambda _location: (-37.8136, 144.9631, "Melbourne, Australia"),
    )

    result = _judge_public_pet_replay(
        "Where is the cat?",
        "Melbourne, Australia",
        "2007-11-04",
        "16:48",
        "Australia/Melbourne",
    )

    location_projection = result.get("lost_object_location") or {}
    reasoning_rules = [entry.get("rule", "") for entry in result.get("reasoning", [])]
    secondary_labels = [entry.get("label", "").lower() for entry in location_projection.get("secondary_places", [])]
    environment_labels = [entry.get("label", "").lower() for entry in location_projection.get("environment_traits", [])]

    assert result["judgment"] == "YES"
    assert result["confidence"] >= 80
    assert result["question_analysis"]["question_type"] == "pet"
    assert result["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert result["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert location_projection.get("applies") is True
    assert location_projection.get("directional_cues", [{}])[0].get("label") == "West"
    assert any("close to home" in label or "yard" in label for label in secondary_labels)
    assert any("threshold" in label or "entrance" in label for label in environment_labels)
    assert any("angular, favoring quick visibility or return" in rule for rule in reasoning_rules)
