from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import morin_aspects
import transits_morin


def test_julian_day_treats_naive_api_timestamp_as_utc():
    naive = morin_aspects._jd_from_iso("2026-01-01T12:00:00")
    utc = morin_aspects._jd_from_iso("2026-01-01T12:00:00Z")
    same_instant_with_offset = morin_aspects._jd_from_iso("2026-01-01T14:00:00+02:00")

    assert naive == pytest.approx(utc, abs=1e-10)
    assert same_instant_with_offset == pytest.approx(utc, abs=1e-10)


def test_julian_day_rejects_invalid_timestamp_instead_of_using_current_sky():
    with pytest.raises(ValueError):
        morin_aspects._jd_from_iso("not-a-date")


def test_julian_day_preserves_subsecond_precision():
    base = morin_aspects._jd_from_iso("2026-01-01T12:00:00Z")
    half_second = morin_aspects._jd_from_iso("2026-01-01T12:00:00.500000Z")

    assert half_second - base == pytest.approx(0.5 / 86400.0, abs=1e-9)


@pytest.mark.parametrize(
    ("orb", "expected"),
    [
        (0.9999, True),
        (1.0, True),
        (1.0001, False),
        (float("nan"), False),
        ("invalid", False),
    ],
)
def test_partile_uses_documented_one_degree_band(orb, expected):
    assert transits_morin._is_partile_orb(orb) is expected


def test_partile_metadata_does_not_duplicate_orb_closeness_bonus():
    base_hit = {
        "transiting": "Jupiter",
        "natal": "Sun",
        "target_type": "planet",
        "aspect": "Trine",
        "orb": 0.75,
        "max_orb": 6.0,
        "complete_platic": False,
        "bodily_contact": False,
    }

    non_partile_score, _ = transits_morin._score_hit(
        {**base_hit, "partile": False}, {}, {}
    )
    partile_score, breakdown = transits_morin._score_hit(
        {**base_hit, "partile": True}, {}, {}
    )

    assert partile_score == non_partile_score
    assert breakdown["partile"] == 0.0
    assert breakdown["bodily_contact"] == 0.0


def test_bodily_contact_retains_distinct_physical_contact_bonus():
    base_hit = {
        "transiting": "Jupiter",
        "natal": "Sun",
        "target_type": "planet",
        "aspect": "Trine",
        "orb": 0.01,
        "max_orb": 6.0,
        "partile": True,
        "complete_platic": False,
    }

    separated_score, _ = transits_morin._score_hit(
        {**base_hit, "bodily_contact": False}, {}, {}
    )
    contact_score, breakdown = transits_morin._score_hit(
        {**base_hit, "bodily_contact": True}, {}, {}
    )

    assert contact_score == pytest.approx(separated_score + 2.0)
    assert breakdown["bodily_contact"] == 2.0


def test_transit_history_contexts_are_request_local():
    first = transits_morin._new_transit_registry_context()
    second = transits_morin._new_transit_registry_context()
    entry = {"timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc)}

    transits_morin._register_registry_event(
        first["simultaneous"],
        "Asc",
        entry,
        horizon_days=2.5,
    )

    assert list(first["simultaneous"]["Asc"]) == [entry]
    assert "Asc" not in second["simultaneous"]


def test_step_selector_keeps_display_bounded_but_retains_asc_for_prediction():
    hits = [
        {
            "transiting": "Saturn",
            "target_label": label,
            "target_type": "cusp",
            "aspect": "Square",
        }
        for label in ("C2", "C3", "C4", "Asc", "Asc (antiscia)")
    ]

    top, prediction = transits_morin._select_morin_transit_step_candidates(
        hits,
        top_n_per_type=3,
        prediction_n_per_type=3,
    )

    assert [hit["target_label"] for hit in top] == ["C2", "C3", "C4"]
    assert [hit["target_label"] for hit in prediction] == [
        "C2",
        "C3",
        "C4",
        "Asc",
        "Asc (antiscia)",
    ]


def test_effective_window_uses_morin_partile_activation_periods():
    moon_window = transits_morin._estimate_effective_window(
        "2026-01-01T00:00:00Z",
        sep_now=1.0,
        sep_future=0.5,
        dt_days=0.5,
        max_orb=6.0,
        transiting="Moon",
    )
    saturn_window = transits_morin._estimate_effective_window(
        "2026-01-01T00:00:00Z",
        sep_now=1.0,
        sep_future=0.5,
        dt_days=0.5,
        max_orb=6.0,
        transiting="Saturn",
    )

    assert moon_window == {
        "start": "2026-01-01T18:00:00+00:00",
        "end": "2026-01-02T06:00:00+00:00",
        "exact_estimate": "2026-01-02T00:00:00+00:00",
        "basis": "morin_partile_activation",
    }
    assert saturn_window == {
        "start": "2026-01-01T00:00:00+00:00",
        "end": "2026-01-03T00:00:00+00:00",
        "exact_estimate": "2026-01-02T00:00:00+00:00",
        "basis": "morin_partile_activation",
    }


def test_effective_window_does_not_invent_stationary_exact_time():
    assert transits_morin._estimate_effective_window(
        "2026-01-01T00:00:00Z",
        sep_now=1.0,
        sep_future=1.0,
        dt_days=0.5,
        max_orb=6.0,
        transiting="Saturn",
    ) is None


def test_window_scan_normalizes_mixed_naive_and_aware_bounds(monkeypatch):
    monkeypatch.setattr(transits_morin, "swe", object())
    monkeypatch.setattr(
        transits_morin,
        "_prepare_natal_context",
        lambda *args, **kwargs: ({}, {}, {}, {}, {}, {}),
    )
    monkeypatch.setattr(
        transits_morin,
        "compute_morin_transits_to_natal",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        transits_morin,
        "enrich_hits_with_concordance",
        lambda _chart, hits, _timestamp, **kwargs: hits,
    )

    rows = transits_morin.scan_morin_transits_window(
        {},
        "2026-01-01T00:00:00",
        "2026-01-01T02:00:00Z",
        step_minutes=60,
    )

    assert [row["timestamp"] for row in rows] == [
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T01:00:00+00:00",
        "2026-01-01T02:00:00+00:00",
    ]
    assert all(
        datetime.fromisoformat(row["timestamp"]).tzinfo == timezone.utc
        for row in rows
    )


def test_window_scan_preserves_explicit_display_offset(monkeypatch):
    monkeypatch.setattr(transits_morin, "swe", object())
    monkeypatch.setattr(
        transits_morin,
        "_prepare_natal_context",
        lambda *args, **kwargs: ({}, {}, {}, {}, {}, {}),
    )
    monkeypatch.setattr(
        transits_morin,
        "compute_morin_transits_to_natal",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        transits_morin,
        "enrich_hits_with_concordance",
        lambda _chart, hits, _timestamp, **kwargs: hits,
    )

    rows = transits_morin.scan_morin_transits_window(
        {},
        "2026-01-01T00:00:00-05:00",
        "2026-01-01T02:00:00-05:00",
        step_minutes=60,
    )

    assert [row["timestamp"] for row in rows] == [
        "2026-01-01T00:00:00-05:00",
        "2026-01-01T01:00:00-05:00",
        "2026-01-01T02:00:00-05:00",
    ]


def test_window_scan_enriches_each_candidate_once_and_reuses_result(monkeypatch):
    monkeypatch.setattr(transits_morin, "swe", object())
    monkeypatch.setattr(
        transits_morin,
        "_prepare_natal_context",
        lambda *args, **kwargs: ({}, {}, {}, {}, {}, {}),
    )
    raw_hits = [
        {
            "transiting": "Saturn",
            "natal": f"C{index}",
            "target_label": f"C{index}",
            "target_type": "cusp",
            "aspect": "Square",
            "score": 10.0 - index,
        }
        for index in range(2, 6)
    ]
    monkeypatch.setattr(
        transits_morin,
        "compute_morin_transits_to_natal",
        lambda *args, **kwargs: [dict(hit) for hit in raw_hits],
    )
    enrich_calls = []

    def fake_enrich(_chart, hits, _timestamp, **kwargs):
        enrich_calls.append(
            {
                "count": len(hits),
                "registry_context": kwargs.get("registry_context"),
            }
        )
        return [
            {**hit, "enriched_batch_size": len(hits), "significance": hit["score"]}
            for hit in hits
        ]

    monkeypatch.setattr(transits_morin, "enrich_hits_with_concordance", fake_enrich)

    rows = transits_morin.scan_morin_transits_window(
        {},
        "2026-01-01T00:00:00Z",
        "2026-01-01T00:01:00Z",
        step_minutes=60,
        top_n_per_step=3,
        prediction_n_per_step=4,
    )

    assert len(enrich_calls) == 1
    assert enrich_calls[0]["count"] == 4
    assert isinstance(enrich_calls[0]["registry_context"], dict)
    assert len(rows) == 1
    assert len(rows[0]["top"]) == 3
    assert len(rows[0]["_prediction_hits"]) == 4
    assert all(hit["enriched_batch_size"] == 4 for hit in rows[0]["top"])
