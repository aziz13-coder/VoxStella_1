from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import astrocartography_atlas_engine as atlas_engine
from astrocartography_city_catalog import search_city_catalog


def test_city_catalog_query_returns_major_city():
    results = search_city_catalog(query="London", country_code="GB", limit=5)
    assert results
    assert any("london" in str(item.get("ascii_name") or item.get("name") or "").lower() for item in results)


def test_city_catalog_resolution_expands_candidate_pool():
    coarse = search_city_catalog(country_code="JP", resolution="coarse")
    standard = search_city_catalog(country_code="JP", resolution="standard")
    fine = search_city_catalog(country_code="JP", resolution="fine")
    ultra = search_city_catalog(country_code="JP", resolution="ultra")

    assert coarse
    assert len(coarse) <= len(standard) <= len(fine) <= len(ultra)


def test_city_catalog_continent_filter_limits_results():
    results = search_city_catalog(continent_code="EU", limit=10)

    assert results
    assert all(str(item.get("continent_code") or "") == "EU" for item in results)


def test_derive_goal_search_filters_uses_explicit_atlas_signature_for_gambling():
    bodies, angles = atlas_engine.derive_goal_search_filters("gambling_luck")

    assert set(bodies) == {
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
    }
    assert set(angles) == {"ASC", "DSC", "MC", "IC"}


def test_derive_goal_search_filters_respects_excluding_user_filters():
    filter_meta = atlas_engine.describe_goal_search_filters(
        "gambling_luck",
        selected_bodies=["Chiron"],
        selected_angles=["NADIR"],
    )

    assert filter_meta["goal_has_signature"] is True
    assert filter_meta["excluded_by_filters"] is True
    assert filter_meta["bodies"] == []
    assert filter_meta["angles"] == []


def test_build_location_score_sort_key_supports_warning_polarity():
    risky = {"raw_score": 8.0, "score": 80}
    safer = {"raw_score": 1.0, "score": 20}

    normal_order = sorted([safer, risky], key=lambda item: atlas_engine.build_location_score_sort_key(item))
    warning_order = sorted(
        [risky, safer],
        key=lambda item: atlas_engine.build_location_score_sort_key(
            item,
            score_polarity="higher_is_worse",
        ),
    )

    assert normal_order[0] == risky
    assert warning_order[0] == safer


def test_rank_candidate_pool_for_goal_ranks_lowest_score_first_for_warning_models(monkeypatch):
    fake_cities = [
        {"label": "Low Risk City", "query": "Low Risk City", "latitude": 0.0, "longitude": 0.0},
        {"label": "High Risk City", "query": "High Risk City", "latitude": 1.0, "longitude": 1.0},
    ]
    scores = {"Low Risk City": 1.0, "High Risk City": 8.0}

    monkeypatch.setattr(atlas_engine, "get_goal_score_polarity", lambda _goal_id: "higher_is_worse")
    monkeypatch.setattr(
        atlas_engine,
        "resolve_goal_shortlist_plan",
        lambda goal_id, relocation_limit, candidate_count: {
            "strategy": atlas_engine.DEFAULT_SHORTLIST_STRATEGY,
            "prepass_limit": candidate_count,
        },
    )

    def fake_score_candidate(city, *, goal_id, natal_lines, transit_lines=None, relocation_features=None):
        label = str(city.get("label") or "")
        raw_score = scores[label]
        return {
            "target": {"label": label, "query": label, "latitude": city["latitude"], "longitude": city["longitude"]},
            "atlas_city": {"population": 0},
            "natal": {"reading": {"lead_line": {"label": "Mock Lead"}}},
            "location_score": {
                "raw_score": raw_score,
                "score": int(raw_score * 10),
                "top_supports": [{"score": raw_score}],
                "top_cautions": [],
            },
        }

    monkeypatch.setattr(atlas_engine, "_score_candidate", fake_score_candidate)

    result = atlas_engine.rank_candidate_pool_for_goal(
        goal_id="health_risk",
        candidates=fake_cities,
        natal_lines=[],
        limit=2,
        relocation_limit=2,
    )

    assert result["score_polarity"] == "higher_is_worse"
    assert [row["label"] for row in result["ranking"]] == ["Low Risk City", "High Risk City"]


def test_rank_atlas_cities_for_goal_prefers_stronger_supported_city(monkeypatch):
    fake_cities = [
        {
            "label": "Heart City, United Kingdom",
            "query": "Heart City, United Kingdom",
            "latitude": 0.0,
            "longitude": 0.0,
            "country_code": "GB",
            "country_name": "United Kingdom",
            "admin1_code": "",
            "population": 500000,
            "timezone": "Europe/London",
            "feature_code": "PPL",
        },
        {
            "label": "Dry City, United Kingdom",
            "query": "Dry City, United Kingdom",
            "latitude": 0.0,
            "longitude": 40.0,
            "country_code": "GB",
            "country_name": "United Kingdom",
            "admin1_code": "",
            "population": 400000,
            "timezone": "Europe/London",
            "feature_code": "PPL",
        },
    ]

    calls = []

    def fake_search_city_catalog(**kwargs):
        calls.append(kwargs)
        return fake_cities

    monkeypatch.setattr(atlas_engine, "search_city_catalog", fake_search_city_catalog)

    natal_lines = [
        {
            "id": "Venus:DSC",
            "body": "Venus",
            "angle": "DSC",
            "label": "Venus DSC",
            "color": "#ec4899",
            "segments": [[[-10.0, 0.0], [10.0, 0.0]]],
        },
        {
            "id": "Moon:IC",
            "body": "Moon",
            "angle": "IC",
            "label": "Moon IC",
            "color": "#2563eb",
            "segments": [[[0.0, -10.0], [0.0, 10.0]]],
        },
        {
            "id": "Saturn:DSC",
            "body": "Saturn",
            "angle": "DSC",
            "label": "Saturn DSC",
            "color": "#111827",
            "segments": [[[-10.0, 40.0], [10.0, 40.0]]],
        },
    ]

    def relocation_bundle_resolver(item):
        label = str((item.get("target") or {}).get("label") or "")
        if label.startswith("Heart City"):
            return {
                "chart_data": {
                    "planets": {
                        "Venus": {"house": 7},
                        "Moon": {"house": 4},
                        "Jupiter": {"house": 5},
                    }
                }
            }
        return {
            "chart_data": {
                "planets": {
                    "Saturn": {"house": 7},
                    "Mars": {"house": 6},
                }
            }
        }

    result = atlas_engine.rank_atlas_cities_for_goal(
        goal_id="love",
        natal_lines=natal_lines,
        continent_code="EU",
        resolution="fine",
        limit=2,
        relocation_bundle_resolver=relocation_bundle_resolver,
    )

    assert calls and calls[0]["resolution"] == "fine"
    assert calls[0]["continent_code"] == "EU"
    assert result["ranking"]
    assert result["query"]["continent_code"] == "EU"
    assert result["query"]["resolution"] == "fine"
    assert result["resolution"]["id"] == "fine"
    assert result["viable_count"] == 1
    assert result["ranking"][0]["label"] == "Heart City, United Kingdom"
    assert len(result["ranking"]) == 1
    assert result["results"][0]["relocation"]["summary"]["angular_planets"]


def test_rank_atlas_cities_for_goal_merges_live_query_candidates(monkeypatch):
    fake_catalog = [
        {
            "label": "Catalog City, France",
            "query": "Catalog City, France",
            "latitude": 0.0,
            "longitude": 0.0,
            "country_code": "FR",
            "country_name": "France",
            "continent_code": "EU",
            "continent_name": "Europe",
            "admin1_code": "",
            "population": 500000,
            "timezone": "Europe/Paris",
            "feature_code": "PPL",
        }
    ]
    fake_live = [
        {
            "label": "Hidden Town, France",
            "query": "Hidden Town, France",
            "latitude": 1.0,
            "longitude": 1.0,
            "country_code": "FR",
            "country_name": "France",
            "admin1_code": "",
            "population": 0,
            "timezone": "",
            "feature_code": "LIVE",
            "live_source": "offline_city_catalog",
        }
    ]

    monkeypatch.setattr(atlas_engine, "search_city_catalog", lambda **kwargs: fake_catalog)
    monkeypatch.setattr(atlas_engine, "search_live_location_candidates", lambda *args, **kwargs: fake_live)

    natal_lines = [
        {
            "id": "Venus:DSC",
            "body": "Venus",
            "angle": "DSC",
            "label": "Venus DSC",
            "color": "#ec4899",
            "segments": [[[-10.0, 1.0], [10.0, 1.0]]],
        }
    ]

    result = atlas_engine.rank_atlas_cities_for_goal(
        goal_id="love",
        natal_lines=natal_lines,
        query="Hidden Town, France",
        resolution="ultra",
        limit=3,
        relocation_bundle_resolver=lambda item: {"chart_data": {}},
    )

    assert result["used_live_augmentation"] is True
    assert result["live_candidate_count"] == 1
    assert any(str(item.get("target", {}).get("label")) == "Hidden Town, France" for item in result["results"])


def test_rank_atlas_cities_for_goal_applies_signal_floor(monkeypatch):
    fake_cities = [
        {
            "label": "Quiet City, Israel",
            "query": "Quiet City, Israel",
            "latitude": 32.0,
            "longitude": 35.0,
            "country_code": "IL",
            "country_name": "Israel",
            "continent_code": "AS",
            "continent_name": "Asia",
            "admin1_code": "",
            "population": 500000,
            "timezone": "Asia/Jerusalem",
            "feature_code": "PPL",
        }
    ]

    monkeypatch.setattr(atlas_engine, "search_city_catalog", lambda **kwargs: fake_cities)
    monkeypatch.setattr(atlas_engine, "search_live_location_candidates", lambda *args, **kwargs: [])

    natal_lines = [
        {
            "id": "Saturn:MC",
            "body": "Saturn",
            "angle": "MC",
            "label": "Saturn MC",
            "color": "#111827",
            "segments": [[[0.0, -80.0], [0.0, -60.0]]],
        }
    ]

    result = atlas_engine.rank_atlas_cities_for_goal(
        goal_id="love",
        natal_lines=natal_lines,
        resolution="coarse",
        limit=5,
        relocation_bundle_resolver=lambda item: {"chart_data": {}},
    )

    assert result["candidate_count"] == 1
    assert result["shortlisted_count"] == 1
    assert result["viable_count"] == 0
    assert result["results"] == []
    assert result["ranking"] == []


def test_score_candidate_normalizes_malformed_target_fields():
    result = atlas_engine._score_candidate(
        {
            "label": "[object Object], Paris, France",
            "query": {"display_name": "Paris, France"},
            "latitude": 48.8566,
            "longitude": 2.3522,
            "country_code": "FR",
            "country_name": "France",
            "admin1_code": "",
            "population": 2000000,
            "timezone": "Europe/Paris",
            "feature_code": "PPL",
        },
        goal_id="love",
        natal_lines=[],
    )

    assert result["target"]["label"] == "Paris, France"
    assert result["target"]["query"] == "Paris, France"


def test_rank_atlas_cities_for_goal_emits_progress(monkeypatch):
    fake_cities = [
        {
            "label": "Alpha City, France",
            "query": "Alpha City, France",
            "latitude": 0.0,
            "longitude": 0.0,
            "country_code": "FR",
            "country_name": "France",
            "continent_code": "EU",
            "continent_name": "Europe",
            "admin1_code": "",
            "population": 300000,
            "timezone": "Europe/Paris",
            "feature_code": "PPL",
        },
        {
            "label": "Beta City, France",
            "query": "Beta City, France",
            "latitude": 1.0,
            "longitude": 1.0,
            "country_code": "FR",
            "country_name": "France",
            "continent_code": "EU",
            "continent_name": "Europe",
            "admin1_code": "",
            "population": 200000,
            "timezone": "Europe/Paris",
            "feature_code": "PPL",
        },
    ]

    monkeypatch.setattr(atlas_engine, "search_city_catalog", lambda **kwargs: fake_cities)
    monkeypatch.setattr(atlas_engine, "search_live_location_candidates", lambda *args, **kwargs: [])

    progress_events = []
    natal_lines = [
        {
            "id": "Moon:IC",
            "body": "Moon",
            "angle": "IC",
            "label": "Moon IC",
            "color": "#2563eb",
            "segments": [[[0.0, -3.0], [0.0, 3.0]]],
        }
    ]

    atlas_engine.rank_atlas_cities_for_goal(
        goal_id="home",
        natal_lines=natal_lines,
        continent_code="EU",
        resolution="standard",
        limit=2,
        relocation_bundle_resolver=lambda item: {"chart_data": {}},
        progress_callback=progress_events.append,
    )

    assert progress_events
    assert progress_events[0]["stage"] == "collect_candidates"
    assert progress_events[-1]["stage"] == "ready"
    assert progress_events[-1]["percent"] == 1.0


def test_rank_candidate_pool_for_goal_runs_relocation_prepass_before_final_shortlist(monkeypatch):
    fake_cities = [
        {
            "label": "Alpha City",
            "query": "Alpha City",
            "latitude": 0.0,
            "longitude": 0.0,
            "population": 500000,
            "country_name": "Testland",
        },
        {
            "label": "Beta City",
            "query": "Beta City",
            "latitude": 1.0,
            "longitude": 1.0,
            "population": 400000,
            "country_name": "Testland",
        },
        {
            "label": "Event City",
            "query": "Event City",
            "latitude": 2.0,
            "longitude": 2.0,
            "population": 300000,
            "country_name": "Testland",
        },
        {
            "label": "Gamma City",
            "query": "Gamma City",
            "latitude": 3.0,
            "longitude": 3.0,
            "population": 200000,
            "country_name": "Testland",
        },
    ]

    monkeypatch.setattr(
        atlas_engine,
        "resolve_goal_shortlist_plan",
        lambda goal_id, relocation_limit, candidate_count: {
            "strategy": atlas_engine.RELOCATION_PREPASS_SHORTLIST_STRATEGY,
            "prepass_limit": 3,
        },
    )

    line_only_scores = {
        "Alpha City": 10.0,
        "Beta City": 9.0,
        "Event City": 8.0,
        "Gamma City": 1.0,
    }
    relocation_scores = {
        "Alpha City": 5.0,
        "Beta City": 4.0,
        "Event City": 20.0,
        "Gamma City": 2.0,
    }

    def fake_score_candidate(city, *, goal_id, natal_lines, transit_lines=None, relocation_features=None):
        label = str(city.get("label") or city.get("query") or "")
        raw_score = relocation_scores[label] if relocation_features else line_only_scores[label]
        return {
            "target": {
                "label": label,
                "query": label,
                "latitude": float(city.get("latitude") or 0.0),
                "longitude": float(city.get("longitude") or 0.0),
            },
            "atlas_city": {
                "population": int(city.get("population") or 0),
                "country_name": city.get("country_name"),
            },
            "natal": {"reading": {"lead_line": {"label": "Mock Lead"}}},
            "location_score": {
                "raw_score": raw_score,
                "score": int(round(raw_score)),
                "top_supports": [{"score": max(raw_score, 0.0)}],
                "top_cautions": [],
            },
        }

    monkeypatch.setattr(atlas_engine, "_score_candidate", fake_score_candidate)

    result = atlas_engine.rank_candidate_pool_for_goal(
        goal_id="gambling_luck",
        candidates=fake_cities,
        natal_lines=[],
        limit=2,
        relocation_limit=2,
        relocation_bundle_resolver=lambda item: {"chart_data": {"label": (item.get("target") or {}).get("label")}},
        include_debug_ranking=True,
    )

    assert result["shortlist_strategy"] == atlas_engine.RELOCATION_PREPASS_SHORTLIST_STRATEGY
    assert result["relocation_prepass_count"] == 3
    assert result["shortlisted_count"] == 2
    assert result["ranking"][0]["label"] == "Event City"
    assert [row["label"] for row in result["debug"]["initial_ranking"][:3]] == ["Alpha City", "Beta City", "Event City"]
    assert result["debug"]["shortlisted_labels"] == ["Event City", "Alpha City"]


def test_rank_candidate_pool_for_goal_defaults_to_relocation_prepass_for_relocation_models():
    fake_cities = [
        {
            "label": f"Weak Line City {index}",
            "query": f"Weak Line City {index}",
            "latitude": float(index - 10),
            "longitude": 2.2,
            "population": 100000 - index,
            "country_name": "Testland",
        }
        for index in range(1, 20)
    ]
    fake_cities.append(
        {
            "label": "Relocation Gem",
            "query": "Relocation Gem",
            "latitude": 0.0,
            "longitude": 100.0,
            "population": 200000,
            "country_name": "Testland",
        }
    )
    natal_lines = [
        {
            "id": "Venus:DSC",
            "body": "Venus",
            "angle": "DSC",
            "label": "Venus DSC",
            "segments": [[[-89.0, 0.0], [89.0, 0.0]]],
        }
    ]

    def relocation_bundle_resolver(item):
        label = str((item.get("target") or {}).get("label") or "")
        if label == "Relocation Gem":
            return {
                "chart_data": {
                    "planets": {
                        "Venus": {"house": 7},
                        "Moon": {"house": 4},
                        "Jupiter": {"house": 5},
                    }
                }
            }
        return {"chart_data": {"planets": {}}}

    result = atlas_engine.rank_candidate_pool_for_goal(
        goal_id="love",
        candidates=fake_cities,
        natal_lines=natal_lines,
        limit=8,
        relocation_limit=18,
        relocation_bundle_resolver=relocation_bundle_resolver,
        include_debug_ranking=True,
    )

    assert result["shortlist_strategy"] == atlas_engine.RELOCATION_PREPASS_SHORTLIST_STRATEGY
    assert result["relocation_prepass_count"] == len(fake_cities)
    assert result["ranking"][0]["label"] == "Relocation Gem"
    assert "Relocation Gem" in result["debug"]["prepass_labels"]


def test_rank_candidate_pool_for_goal_scores_all_candidates_for_explicit_relocation_prepass(monkeypatch):
    fake_cities = [
        {
            "label": f"Line First City {index}",
            "query": f"Line First City {index}",
            "latitude": 0.0,
            "longitude": float(index),
            "population": 100000 + index,
            "country_name": "Testland",
        }
        for index in range(130)
    ]
    fake_cities.append(
        {
            "label": "Relocation Gem",
            "query": "Relocation Gem",
            "latitude": 0.0,
            "longitude": 171.0,
            "population": 90000,
            "country_name": "Testland",
        }
    )

    def fake_score_candidate(city, *, goal_id, natal_lines, transit_lines=None, relocation_features=None):
        label = str(city.get("label") or city.get("query") or "")
        if relocation_features:
            raw_score = 250.0 if label == "Relocation Gem" else 1.0
        else:
            raw_score = 0.1 if label == "Relocation Gem" else 200.0 - float(str(label).rsplit(" ", 1)[-1])
        return {
            "target": {
                "label": label,
                "query": label,
                "latitude": float(city.get("latitude") or 0.0),
                "longitude": float(city.get("longitude") or 0.0),
            },
            "atlas_city": {
                "population": int(city.get("population") or 0),
                "country_name": city.get("country_name"),
            },
            "natal": {"reading": {"lead_line": {"label": "Mock Lead"}}},
            "location_score": {
                "raw_score": raw_score,
                "score": int(round(raw_score)),
                "top_supports": [{"score": max(raw_score, 0.0)}],
                "top_cautions": [],
            },
        }

    monkeypatch.setattr(atlas_engine, "_score_candidate", fake_score_candidate)

    result = atlas_engine.rank_candidate_pool_for_goal(
        goal_id="gambling_luck",
        candidates=fake_cities,
        natal_lines=[],
        limit=1,
        relocation_limit=4,
        relocation_bundle_resolver=lambda item: {"chart_data": {"label": (item.get("target") or {}).get("label")}},
        include_debug_ranking=True,
    )

    assert result["shortlist_strategy"] == atlas_engine.RELOCATION_PREPASS_SHORTLIST_STRATEGY
    assert result["relocation_prepass_count"] == len(fake_cities)
    assert result["ranking"][0]["label"] == "Relocation Gem"
    assert "Relocation Gem" in result["debug"]["prepass_labels"]
