from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import transits_morin


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
