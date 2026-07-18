from pathlib import Path
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import almutens as almutens_module
from almutens import compute_almuten_for_longitude, compute_chart_almutens


CANONICAL_EGYPTIAN_TERMS = {
    "Aries": [("Jupiter", 0, 6), ("Venus", 6, 12), ("Mercury", 12, 20), ("Mars", 20, 25), ("Saturn", 25, 30)],
    "Taurus": [("Venus", 0, 8), ("Mercury", 8, 14), ("Jupiter", 14, 22), ("Saturn", 22, 27), ("Mars", 27, 30)],
    "Gemini": [("Mercury", 0, 6), ("Jupiter", 6, 12), ("Venus", 12, 17), ("Mars", 17, 24), ("Saturn", 24, 30)],
    "Cancer": [("Mars", 0, 7), ("Venus", 7, 13), ("Mercury", 13, 19), ("Jupiter", 19, 26), ("Saturn", 26, 30)],
    "Leo": [("Jupiter", 0, 6), ("Venus", 6, 11), ("Saturn", 11, 18), ("Mercury", 18, 24), ("Mars", 24, 30)],
    "Virgo": [("Mercury", 0, 7), ("Venus", 7, 17), ("Jupiter", 17, 21), ("Mars", 21, 28), ("Saturn", 28, 30)],
    "Libra": [("Saturn", 0, 6), ("Mercury", 6, 14), ("Jupiter", 14, 21), ("Venus", 21, 28), ("Mars", 28, 30)],
    "Scorpio": [("Mars", 0, 7), ("Venus", 7, 11), ("Mercury", 11, 19), ("Jupiter", 19, 24), ("Saturn", 24, 30)],
    "Sagittarius": [("Jupiter", 0, 12), ("Venus", 12, 17), ("Mercury", 17, 21), ("Saturn", 21, 26), ("Mars", 26, 30)],
    "Capricorn": [("Mercury", 0, 7), ("Jupiter", 7, 14), ("Venus", 14, 22), ("Saturn", 22, 26), ("Mars", 26, 30)],
    "Aquarius": [("Mercury", 0, 7), ("Venus", 7, 13), ("Jupiter", 13, 20), ("Mars", 20, 25), ("Saturn", 25, 30)],
    "Pisces": [("Venus", 0, 12), ("Jupiter", 12, 16), ("Mercury", 16, 19), ("Mars", 19, 28), ("Saturn", 28, 30)],
}


def _term_ruler_from_result(result):
    term_holders = [
        row["planet"]
        for row in result["candidates"]
        if row["breakdown"].get("term") == 2
    ]
    assert len(term_holders) == 1
    return term_holders[0]


def _longitude(sign, degree):
    return (almutens_module.SIGN_NAMES.index(sign) * 30.0) + float(degree)


def test_egyptian_terms_match_canonical_horary_configuration():
    config_path = Path(almutens_module.__file__).with_name("horary_constants.yaml")
    configured = yaml.safe_load(config_path.read_text(encoding="utf-8"))["reception"]["terms"]

    configured_lengths = {
        sign: [
            (entry["ruler"], float(entry["end"]) - float(entry["start"]))
            for entry in entries
        ]
        for sign, entries in configured.items()
    }

    assert almutens_module.TERMS == configured_lengths


@pytest.mark.parametrize(
    ("sign", "ruler", "start", "end"),
    [
        (sign, ruler, start, end)
        for sign, bounds in CANONICAL_EGYPTIAN_TERMS.items()
        for ruler, start, end in bounds
    ],
)
def test_egyptian_term_boundaries_are_start_inclusive_and_end_exclusive(sign, ruler, start, end):
    at_start = compute_almuten_for_longitude(_longitude(sign, start), True)
    before_end = compute_almuten_for_longitude(_longitude(sign, end - 1e-7), True)

    assert _term_ruler_from_result(at_start) == ruler
    assert _term_ruler_from_result(before_end) == ruler

    if end < 30:
        at_end = compute_almuten_for_longitude(_longitude(sign, end), True)
        next_ruler = next(
            next_ruler
            for next_ruler, next_start, _next_end in CANONICAL_EGYPTIAN_TERMS[sign]
            if next_start == end
        )
        assert _term_ruler_from_result(at_end) == next_ruler


def test_unknown_sect_withholds_triplicity_instead_of_assuming_day():
    unknown = compute_almuten_for_longitude(_longitude("Libra", 0.5), None)
    day = compute_almuten_for_longitude(_longitude("Libra", 0.5), True)
    unknown_saturn = next(row for row in unknown["candidates"] if row["planet"] == "Saturn")
    day_saturn = next(row for row in day["candidates"] if row["planet"] == "Saturn")

    assert unknown["calculation_status"] == "partial"
    assert unknown["withheld_dignities"] == ["triplicity"]
    assert all("triplicity" not in row["breakdown"] for row in unknown["candidates"])
    assert unknown_saturn["score"] == 6
    assert day_saturn["score"] == 9


def test_chart_reports_method_and_partial_status_when_sect_is_unknown(monkeypatch):
    monkeypatch.setattr(almutens_module, "compute_sect_info", lambda _chart: {"chart_sect": None})

    result = compute_chart_almutens({"houses": [index * 30.0 for index in range(12)]})

    assert result["sect"] is None
    assert result["calculation_status"] == "partial"
    assert result["withheld_dignities"] == ["triplicity"]
    assert result["method"] == {
        "id": "lilly_sect",
        "label": "Lilly · sect ruler",
        "terms": "Egyptian",
        "faces": "Chaldean",
        "weights": {
            "domicile": 5,
            "exaltation": 4,
            "triplicity": 3,
            "term": 2,
            "face": 1,
        },
    }
    assert all(point["calculation_status"] == "partial" for point in result["points"].values())


def test_chart_withholds_triplicity_when_sect_calculation_fails(monkeypatch):
    def _raise_sect_error(_chart):
        raise RuntimeError("sect unavailable")

    monkeypatch.setattr(almutens_module, "compute_sect_info", _raise_sect_error)

    result = compute_chart_almutens({"houses": [index * 30.0 for index in range(12)]})

    assert result["sect"] is None
    assert result["calculation_status"] == "partial"
    assert result["withheld_dignities"] == ["triplicity"]
    assert all(
        "triplicity" not in candidate["breakdown"]
        for point in result["points"].values()
        for candidate in point["candidates"]
    )


def test_chart_2026_07_18_jerusalem_matches_reviewed_day_results(monkeypatch):
    monkeypatch.setattr(almutens_module, "compute_sect_info", lambda _chart: {"chart_sect": "diurnal"})
    houses = [
        _longitude("Libra", 5 + (1 / 60)),
        _longitude("Scorpio", 2 + (49 / 60)),
        _longitude("Sagittarius", 3),
        _longitude("Capricorn", 5),
        _longitude("Aquarius", 6),
        _longitude("Pisces", 7),
        _longitude("Aries", 5 + (1 / 60)),
        _longitude("Taurus", 2 + (49 / 60)),
        _longitude("Gemini", 3),
        _longitude("Cancer", 5 + (22 / 60)),
        _longitude("Leo", 7 + (25 / 60)),
        _longitude("Virgo", 7 + (47 / 60)),
    ]

    result = compute_chart_almutens({"houses": houses})
    expected = {
        "ascendant": ("Saturn", 9, {"exaltation": 4, "triplicity": 3, "term": 2}),
        "midheaven": ("Moon", 5, {"domicile": 5}),
        "house_2": ("Mars", 8, {"domicile": 5, "term": 2, "face": 1}),
        "house_7": ("Sun", 7, {"exaltation": 4, "triplicity": 3}),
        "house_11": ("Sun", 8, {"domicile": 5, "triplicity": 3}),
        "house_12": ("Mercury", 9, {"domicile": 5, "exaltation": 4}),
    }

    assert result["sect"] == "Day"
    assert result["calculation_status"] == "complete"
    assert result["withheld_dignities"] == []
    for key, (leader, score, breakdown) in expected.items():
        assert result["points"][key]["leader"] == leader
        assert result["points"][key]["leader_score"] == score
        assert result["points"][key]["leader_breakdown"] == breakdown

    leo = result["points"]["house_11"]
    assert next(row for row in leo["candidates"] if row["planet"] == "Venus")["breakdown"]["term"] == 2
    assert "term" not in next(row for row in leo["candidates"] if row["planet"] == "Mercury")["breakdown"]


def test_tied_leaders_include_each_planets_own_breakdown():
    result = compute_almuten_for_longitude(_longitude("Aries", 20), True)

    assert result["leaders"] == ["Mars", "Sun"]
    assert result["leader_details"] == [
        {
            "planet": "Mars",
            "score": 7,
            "dignities": ["domicile", "term"],
            "breakdown": {"domicile": 5, "term": 2},
        },
        {
            "planet": "Sun",
            "score": 7,
            "dignities": ["exaltation", "triplicity"],
            "breakdown": {"exaltation": 4, "triplicity": 3},
        },
    ]
