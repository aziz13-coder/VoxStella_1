import sys
from pathlib import Path
from types import SimpleNamespace


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import astro_clock_api
from astro_clock_api import _compute_chart_for, _extend_chart_data_for_synastry, _synastry_point_capability
from synastry_engine import build_synastry_report


def _bundle(chart_data, label):
    return {"chart_data": chart_data, "meta": {"label": label}}


def test_synastry_helpers_configure_swisseph_to_use_resolved_ephemeris_path(monkeypatch):
    captured_paths = []

    fake_swe = SimpleNamespace(
        FLG_SWIEPH=1,
        FLG_SPEED=2,
        GREG_CAL=1,
        URANUS=7,
        NEPTUNE=8,
        PLUTO=9,
        CHIRON=15,
    )

    def julday(*_args):
        return 2461146.0

    def set_ephe_path(path):
        captured_paths.append(path)

    def calc_ut(_jd_ut, point_id, _flags):
        if point_id == fake_swe.CHIRON:
            return [45.0, 0.1, 0.0, 0.02], None
        return [120.0 + point_id, 0.0, 0.0, 0.01], None

    fake_swe.julday = julday
    fake_swe.set_ephe_path = set_ephe_path
    fake_swe.calc_ut = calc_ut

    monkeypatch.setattr(astro_clock_api, "_resolve_synastry_ephemeris_path", lambda: r"C:\SwissEph\ephemeris")
    monkeypatch.setitem(sys.modules, "swisseph", fake_swe)

    meta = {"timestamp": "2026-04-16T12:00:00+00:00"}
    capability = _synastry_point_capability(meta)
    enriched = _extend_chart_data_for_synastry(
        {"houses": [i * 30.0 for i in range(12)], "planets": {}},
        meta,
        include_modern=False,
        include_chiron=True,
    )

    assert capability["chiron_supported"] is True
    assert captured_paths == [
        r"C:\SwissEph\ephemeris",
        "",
        r"C:\SwissEph\ephemeris",
        "",
    ]
    assert "Chiron" in (enriched.get("planets") or {})


def test_live_synastry_point_enrichment_adds_modern_points_and_respects_chiron_capability():
    chart_data, meta = _compute_chart_for(
        "1997-08-10T17:25:00-07:00",
        "Los Angeles, California, USA",
        "America/Los_Angeles",
    )

    capability = _synastry_point_capability(meta)
    assert capability["modern_supported"] is True

    enriched = _extend_chart_data_for_synastry(
        chart_data,
        meta,
        include_modern=True,
        include_chiron=True,
    )

    planets = enriched.get("planets") or {}
    assert "Uranus" in planets
    assert "Neptune" in planets
    assert "Pluto" in planets
    if capability["chiron_supported"]:
        assert "Chiron" in planets
    else:
        assert "Chiron" not in planets


def test_live_synastry_report_includes_optional_points_and_orb_profile_moves_scores():
    chart_a, meta_a = _compute_chart_for(
        "1997-08-10T17:25:00-07:00",
        "Los Angeles, California, USA",
        "America/Los_Angeles",
    )
    chart_b, meta_b = _compute_chart_for(
        "1995-12-27T21:16:00-05:00",
        "Manhattan, New York, USA",
        "America/New_York",
    )
    capability_a = _synastry_point_capability(meta_a)
    capability_b = _synastry_point_capability(meta_b)
    chiron_supported = capability_a["chiron_supported"] and capability_b["chiron_supported"]

    chart_a = _extend_chart_data_for_synastry(chart_a, meta_a, include_modern=True, include_chiron=True)
    chart_b = _extend_chart_data_for_synastry(chart_b, meta_b, include_modern=True, include_chiron=True)

    common_chart_meta_a = {"id": "a", "label": "A", "effective_datetime": meta_a["timestamp"], "location": meta_a["location"]}
    common_chart_meta_b = {"id": "b", "label": "B", "effective_datetime": meta_b["timestamp"], "location": meta_b["location"]}

    tight = build_synastry_report(
        _bundle(chart_a, "A"),
        _bundle(chart_b, "B"),
        common_chart_meta_a,
        common_chart_meta_b,
        options={"include_modern": True, "include_nodes": True, "include_chiron": True, "orb_profile": "tight"},
    )
    wide = build_synastry_report(
        _bundle(chart_a, "A"),
        _bundle(chart_b, "B"),
        common_chart_meta_a,
        common_chart_meta_b,
        options={"include_modern": True, "include_nodes": True, "include_chiron": True, "orb_profile": "wide"},
    )

    active_points = set(tight["governance"]["active_points"])
    assert "Uranus" in active_points
    assert "Neptune" in active_points
    assert "Pluto" in active_points
    assert tight["governance"]["point_availability"]["modern_available"] is True
    assert tight["governance"]["point_availability"]["chiron_available"] is chiron_supported
    if chiron_supported:
        assert "Chiron" in active_points
    else:
        assert "Chiron" not in active_points

    tight_scores = {item["id"]: item["score"] for item in tight["categories"] if item.get("id")}
    wide_scores = {item["id"]: item["score"] for item in wide["categories"] if item.get("id")}
    assert tight_scores != wide_scores
