from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import astrocartography_atlas_engine as atlas_engine
from astrocartography_city_catalog import (
    ATLAS_SEARCH_RESOLUTIONS,
    find_exact_city_catalog_entries,
    get_city_catalog_entry_by_geonameid,
    list_city_catalog_entries,
    search_city_catalog,
)


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
    assert len(coarse) <= ATLAS_SEARCH_RESOLUTIONS["coarse"]["candidate_limit"]
    assert len(standard) <= ATLAS_SEARCH_RESOLUTIONS["standard"]["candidate_limit"]
    assert len(fine) <= ATLAS_SEARCH_RESOLUTIONS["fine"]["candidate_limit"]
    assert len(ultra) <= ATLAS_SEARCH_RESOLUTIONS["ultra"]["candidate_limit"]


def test_city_catalog_global_resolution_pools_are_bounded_near_prior_scale():
    pool_sizes = {
        resolution: len(search_city_catalog(resolution=resolution))
        for resolution in ("coarse", "standard", "fine", "ultra")
    }

    assert pool_sizes == {
        "coarse": 3200,
        "standard": 4000,
        "fine": 6500,
        "ultra": 22000,
    }
    mandatory_ids = {
        int(city["geonameid"])
        for city in list_city_catalog_entries()
        if str(city.get("feature_code") or "").upper() in {"PPLC", "PPLA"}
    }
    assert mandatory_ids
    for resolution in ("coarse", "standard", "fine", "ultra"):
        returned_ids = {
            int(city["geonameid"])
            for city in search_city_catalog(resolution=resolution)
        }
        assert mandatory_ids <= returned_ids


@pytest.mark.parametrize(
    ("query", "candidate_id"),
    [
        ("London UK", "geonames:2643743"),
        ("London, U.K.", "geonames:2643743"),
        ("Cambridge CA", "geonames:5913695"),
        ("San Jose CA", "geonames:5392171"),
        ("Springfield Illinois", "geonames:4250542"),
        ("Victoria BC", "geonames:6174041"),
        ("New York, NY, USA", "geonames:5128581"),
        ("México City", "geonames:3530597"),
    ],
)
def test_city_catalog_structured_queries_return_only_exact_identity(query, candidate_id):
    results = search_city_catalog(query=query, resolution="ultra", limit=10)

    assert [f"geonames:{item['geonameid']}" for item in results] == [candidate_id]


@pytest.mark.parametrize(
    ("name", "country_code", "candidate_id"),
    [
        ("Manchester", "GB", "geonames:2643123"),
        ("Cambridge", "GB", "geonames:2653941"),
        ("Oxford", "GB", "geonames:2640729"),
    ],
)
def test_city_catalog_includes_secondary_uk_admin_centers(
    name,
    country_code,
    candidate_id,
):
    matches = [
        city
        for city in find_exact_city_catalog_entries(name)
        if city.get("country_code") == country_code
    ]

    assert [f"geonames:{item['geonameid']}" for item in matches] == [candidate_id]
    assert matches[0]["admin1_name"] == "England"


@pytest.mark.parametrize(
    ("query", "candidate_id"),
    [
        ("London UK", "geonames:2643743"),
        ("Springfield Illinois", "geonames:4250542"),
        ("Victoria BC", "geonames:6174041"),
        ("Cambridge CA", "geonames:5913695"),
        ("San Jose CA", "geonames:5392171"),
    ],
)
def test_actual_atlas_query_uses_structured_city_identity(query, candidate_id):
    city = get_city_catalog_entry_by_geonameid(candidate_id)
    assert city is not None
    latitude = float(city["latitude"])
    longitude = float(city["longitude"])
    result = atlas_engine.rank_atlas_cities_for_goal(
        goal_id="love",
        natal_lines=[
            {
                "id": "Venus:DSC",
                "body": "Venus",
                "angle": "DSC",
                "label": "Venus DSC",
                "segments": [
                    [
                        [max(-89.0, latitude - 1.0), longitude],
                        [min(89.0, latitude + 1.0), longitude],
                    ]
                ],
            }
        ],
        query=query,
        resolution="fine",
        limit=1,
    )

    assert result["catalog_candidate_count"] == 1
    assert result["candidate_count"] == 1
    assert result["results"][0]["target"]["candidate_id"] == candidate_id


@pytest.mark.parametrize(
    ("query", "field", "expected"),
    [
        ("France", "country_code", "FR"),
        ("UK", "country_code", "GB"),
        ("Mexico", "country_code", "MX"),
        ("Europe", "continent_code", "EU"),
    ],
)
def test_actual_atlas_keyword_query_preserves_broad_filter_semantics(
    monkeypatch,
    query,
    field,
    expected,
):
    captured = {}

    def _capture_candidates(*, candidates, **_kwargs):
        captured["candidates"] = candidates
        return {
            "candidate_count": len(candidates),
            "shortlisted_count": 0,
            "viable_count": 0,
            "results": [],
            "ranking": [],
        }

    monkeypatch.setattr(
        atlas_engine,
        "rank_candidate_pool_for_goal",
        _capture_candidates,
    )

    result = atlas_engine.rank_atlas_cities_for_goal(
        goal_id="love",
        natal_lines=[],
        query=query,
        resolution="coarse",
        limit=1,
    )

    candidates = captured["candidates"]
    assert candidates
    assert all(str(city.get(field) or "") == expected for city in candidates)
    assert result["candidate_pool_policy"]["mandatory_candidates_preserved"] is True
    assert result["candidate_pool_policy"]["minimum_population"] == 500000
    assert result["candidate_pool_policy"]["population_floor_exceptions"] == ["PPLC", "PPLA"]
    assert "regardless of population" in result["resolution"]["description"]


def test_actual_atlas_prefix_keyword_excludes_timezone_substring_false_positives(
    monkeypatch,
):
    captured = {}

    def _capture_candidates(*, candidates, **_kwargs):
        captured["candidates"] = candidates
        return {
            "candidate_count": len(candidates),
            "shortlisted_count": 0,
            "viable_count": 0,
            "results": [],
            "ranking": [],
        }

    monkeypatch.setattr(
        atlas_engine,
        "rank_candidate_pool_for_goal",
        _capture_candidates,
    )

    atlas_engine.rank_atlas_cities_for_goal(
        goal_id="love",
        natal_lines=[],
        query="Lond",
        resolution="fine",
        limit=1,
    )

    candidates = captured["candidates"]
    assert candidates
    assert all(
        any(
            token.startswith("lond")
            for token in str(
                city.get("ascii_name") or city.get("name") or ""
            ).lower().split()
        )
        for city in candidates
    )
    assert all(str(city.get("ascii_name") or "") != "Dukinfield" for city in candidates)


def test_city_catalog_continent_filter_limits_results():
    results = search_city_catalog(continent_code="EU", limit=10)

    assert results
    assert all(str(item.get("continent_code") or "") == "EU" for item in results)


def test_derive_goal_search_filters_does_not_invent_signature_for_experimental_residual():
    bodies, angles = atlas_engine.derive_goal_search_filters("gambling_luck")

    assert bodies == []
    assert angles == []


def test_derive_goal_search_filters_keeps_signatureless_experimental_model_out_of_atlas():
    filter_meta = atlas_engine.describe_goal_search_filters(
        "gambling_luck",
        selected_bodies=["Chiron"],
        selected_angles=["NADIR"],
    )

    assert filter_meta["goal_has_signature"] is False
    assert filter_meta["excluded_by_filters"] is False
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


def test_equal_astrology_scores_use_stable_identity_not_population():
    tiny_alpha = {
        "target": {"candidate_id": "alpha-id", "label": "Alpha City"},
        "atlas_city": {"population": 1},
        "location_score": {"raw_score": 4.0, "score": 60},
    }
    huge_zeta = {
        "target": {"candidate_id": "zeta-id", "label": "Zeta City"},
        "atlas_city": {"population": 10_000_000},
        "location_score": {"raw_score": 4.0, "score": 60},
    }

    ordered = sorted(
        [huge_zeta, tiny_alpha],
        key=atlas_engine._scored_candidate_sort_key,
    )

    assert [item["target"]["candidate_id"] for item in ordered] == [
        "alpha-id",
        "zeta-id",
    ]
    assert atlas_engine.ASTROLOGY_RANKING_BASIS["population_used_for_ranking"] is False
    assert atlas_engine.ASTROLOGY_RANKING_BASIS["tie_breaker"] == "stable_label_then_candidate_id"


def test_geographic_diversity_prefers_distinct_regions_and_labels_every_result():
    rows = [
        {"target": {"candidate_id": "quito", "label": "Quito", "latitude": -0.1807, "longitude": -78.4678}},
        {"target": {"candidate_id": "ibarra", "label": "Ibarra", "latitude": 0.3517, "longitude": -78.1223}},
        {"target": {"candidate_id": "london", "label": "London", "latitude": 51.5074, "longitude": -0.1278}},
        {"target": {"candidate_id": "paris", "label": "Paris", "latitude": 48.8566, "longitude": 2.3522}},
    ]

    selected, metadata = atlas_engine.select_geographically_diverse_results(
        rows,
        limit=3,
        radius_km=250.0,
    )

    assert [item["target"]["candidate_id"] for item in selected] == ["quito", "london", "paris"]
    assert metadata["distinct_region_count"] == 3
    assert metadata["same_region_fill_count"] == 0
    assert all((item.get("geographic_group") or {}).get("label") for item in selected)
    assert all(item["ranking_basis"]["scope"] == "astrological_interpretation_only" for item in selected)
    assert all(item["practical_context"]["status"] == "not_assessed" for item in selected)
    assert all(item["suitability_assessed"] is False for item in selected)


def test_geographic_diversity_uses_labeled_same_region_fill_for_local_searches():
    rows = [
        {"target": {"candidate_id": "quito", "label": "Quito", "latitude": -0.1807, "longitude": -78.4678}},
        {"target": {"candidate_id": "ibarra", "label": "Ibarra", "latitude": 0.3517, "longitude": -78.1223}},
        {"target": {"candidate_id": "latacunga", "label": "Latacunga", "latitude": -0.9352, "longitude": -78.6155}},
    ]

    selected, metadata = atlas_engine.select_geographically_diverse_results(
        rows,
        limit=3,
        radius_km=250.0,
    )

    assert len(selected) == 3
    assert metadata["distinct_region_count"] == 1
    assert metadata["same_region_fill_count"] == 2
    assert [item["geographic_group"]["selection_pass"] for item in selected] == [
        "distinct_region",
        "same_region_fill",
        "same_region_fill",
    ]
    assert {item["geographic_group"]["label"] for item in selected} == {"Quito area"}


def test_diversity_keeps_global_astrology_rank_separate_from_display_rank():
    rows = [
        {
            "target": {"candidate_id": "a-strong", "label": "A Strong", "latitude": 0.0, "longitude": 0.0},
            "location_score": {"raw_score": 10.0, "score": 80},
        },
        {
            "target": {"candidate_id": "a-nearby", "label": "A Nearby", "latitude": 0.5, "longitude": 0.5},
            "location_score": {"raw_score": 9.0, "score": 75},
        },
        {
            "target": {"candidate_id": "b-distant", "label": "B Distant", "latitude": 30.0, "longitude": 30.0},
            "location_score": {"raw_score": 2.0, "score": 45},
        },
    ]

    selected, _metadata = atlas_engine.select_geographically_diverse_results(
        rows,
        limit=3,
        radius_km=250.0,
    )
    ranking = atlas_engine._build_scored_candidate_ranking(selected)

    assert [item["target"]["candidate_id"] for item in selected] == [
        "a-strong",
        "b-distant",
        "a-nearby",
    ]
    assert [item["astrology_rank"] for item in ranking] == [1, 3, 2]
    assert [item["rank"] for item in ranking] == [1, 3, 2]
    assert [item["display_rank"] for item in ranking] == [1, 2, 3]
    assert [item["selection_order"] for item in ranking] == [1, 2, 3]


def test_wide_time_stability_pool_is_bounded_and_keeps_displayed_outlier():
    rows = [
        {
            "target": {
                "candidate_id": f"city-{index:03d}",
                "label": f"City {index:03d}",
                "latitude": float((index % 80) - 40),
                "longitude": float((index * 3) % 180),
            },
            "location_score": {
                "raw_score": 100.0 - index,
                "score": 100 - index,
            },
        }
        for index in range(100)
    ]

    pool, policy = atlas_engine.build_bounded_stability_evaluation_pool(
        rows,
        required_rows=[rows[0], rows[-1]],
        requested_limit=8,
        time_sample_count=12,
    )

    assert len(pool) == 21
    assert rows[-1] in pool
    assert policy["candidate_cap"] == 21
    assert policy["planned_full_recalculations"] == 252
    assert policy["max_full_recalculations"] == 256
    assert policy["within_evaluation_cap"] is True
    assert policy["bounded_scope"] is True
    assert policy["required_displayed_candidates_preserved"] is True


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
    assert result["ranking_mode"] == "goal_specific_astrology"
    assert result["ranking_basis"]["scope"] == "astrological_interpretation_only"
    assert result["practical_context"]["status"] == "not_assessed"
    assert result["goal_selection"]["neutral_overview"]["ranked"] is False
    assert result["geographic_diversity"]["enabled"] is True
    assert all(row["suitability_assessed"] is False for row in result["ranking"])


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
    assert result["results"][0]["relocation"]["summary"]["prominent_houses"]


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
    stability_events = [event for event in progress_events if event["stage"] == "stability"]
    assert stability_events
    assert stability_events[-1]["message"] == "Rank stability evaluation complete"
    assert stability_events[-1]["max_full_recalculations"] == 256
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


def test_relocation_dependent_plan_never_uses_line_only_candidate_cutoff():
    plan = atlas_engine.resolve_goal_shortlist_plan(
        "love",
        relocation_limit=18,
        candidate_count=1250,
    )

    assert plan["strategy"] == atlas_engine.RELOCATION_PREPASS_SHORTLIST_STRATEGY
    assert plan["prepass_limit"] == 1250


def test_rank_candidate_pool_recovers_when_one_candidate_has_polar_house_failure(monkeypatch):
    candidates = [
        {
            "candidate_id": "geonames:1",
            "label": "Temperate City",
            "query": "Temperate City",
            "latitude": 40.0,
            "longitude": 2.0,
            "population": 100000,
        },
        {
            "candidate_id": "geonames:2",
            "label": "Polar City",
            "query": "Polar City",
            "latitude": 78.0,
            "longitude": 15.0,
            "population": 50000,
        },
    ]

    monkeypatch.setattr(
        atlas_engine,
        "resolve_goal_shortlist_plan",
        lambda *_args, **_kwargs: {
            "strategy": atlas_engine.RELOCATION_PREPASS_SHORTLIST_STRATEGY,
            "prepass_limit": 2,
        },
    )

    def fake_score_candidate(
        city,
        *,
        goal_id,
        natal_lines,
        transit_lines=None,
        relocation_features=None,
        relocation_status=None,
    ):
        unavailable = bool((relocation_status or {}).get("relocation_unavailable"))
        return {
            "target": {
                "candidate_id": city.get("candidate_id"),
                "label": city["label"],
                "query": city["query"],
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "coordinate_source": "atlas_candidate",
            },
            "atlas_city": {"population": city["population"]},
            "natal": {"reading": {"lead_line": {"label": "Mock"}}},
            "location_score": {
                "raw_score": 2.0,
                "score": 60,
                "top_supports": [{"score": 2.0}],
                "top_cautions": [],
            },
            "relocation": {
                "available": not unavailable,
                "relocation_unavailable": unavailable,
                "error": (relocation_status or {}).get("error"),
            },
        }

    monkeypatch.setattr(atlas_engine, "_score_candidate", fake_score_candidate)

    def resolver(item):
        if (item.get("target") or {}).get("candidate_id") == "geonames:2":
            raise RuntimeError("Unable to calculate astrological houses")
        return {"available": True, "chart_data": {"planets": {"Venus": {"house": 7}}}}

    result = atlas_engine.rank_candidate_pool_for_goal(
        goal_id="love",
        candidates=candidates,
        natal_lines=[],
        limit=2,
        relocation_limit=2,
        relocation_bundle_resolver=resolver,
    )

    assert result["relocation_unavailable_count"] == 1
    assert result["results"][0]["target"]["candidate_id"] == "geonames:1"
    assert all(item["target"]["candidate_id"] != "geonames:2" for item in result["results"])
    polar = result["relocation_unavailable"][0]
    assert polar["target"]["candidate_id"] == "geonames:2"
    assert polar["error"]["code"] == "relocation_calculation_failed"


def test_score_candidate_preserves_exact_catalog_identity_and_coordinate_source():
    result = atlas_engine._score_candidate(
        {
            "candidate_id": "geonames:2988507",
            "geonameid": 2988507,
            "label": "Paris, France",
            "query": "Paris, France",
            "latitude": 48.8566,
            "longitude": 2.3522,
            "coordinate_source": "bundled_geonames_catalog",
        },
        goal_id="love",
        natal_lines=[],
    )

    assert result["target"] == {
        "candidate_id": "geonames:2988507",
        "label": "Paris, France",
        "query": "Paris, France",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "coordinate_source": "bundled_geonames_catalog",
    }
    assert result["atlas_city"]["geonameid"] == 2988507


def test_exact_relocation_prepass_scores_each_candidate_once_without_debug(monkeypatch):
    candidates = [
        {
            "label": f"City {index}",
            "query": f"City {index}",
            "latitude": float(index),
            "longitude": float(index),
        }
        for index in range(3)
    ]
    monkeypatch.setattr(
        atlas_engine,
        "resolve_goal_shortlist_plan",
        lambda *_args, **_kwargs: {
            "strategy": atlas_engine.RELOCATION_PREPASS_SHORTLIST_STRATEGY,
            "prepass_limit": len(candidates),
        },
    )
    calls = []

    def fake_score_candidate(city, **kwargs):
        calls.append((city["label"], kwargs.get("relocation_features") is not None))
        return {
            **atlas_engine._candidate_identity_payload(city),
            "natal": {"reading": {}},
            "location_score": {
                "raw_score": 1.0,
                "score": 50,
                "ranking_eligible": True,
                "top_supports": [{"score": 1.0}],
                "top_cautions": [],
            },
            "relocation": {"available": True, "relocation_unavailable": False},
        }

    monkeypatch.setattr(atlas_engine, "_score_candidate", fake_score_candidate)

    result = atlas_engine.rank_candidate_pool_for_goal(
        goal_id="love",
        candidates=candidates,
        natal_lines=[],
        limit=3,
        relocation_limit=3,
        relocation_bundle_resolver=lambda _item: {
            "available": True,
            "chart_data": {"planets": {"Venus": {"house": 7}}},
        },
    )

    assert len(calls) == len(candidates)
    assert all(has_relocation for _label, has_relocation in calls)
    assert len(result["results"]) == len(candidates)


def test_atlas_query_does_not_match_unrelated_city_only_through_timezone(monkeypatch):
    fake_cities = [
        {
            "geonameid": 2643743,
            "name": "London",
            "ascii_name": "London",
            "label": "London, United Kingdom",
            "query": "London, United Kingdom",
            "country_code": "GB",
            "country_name": "United Kingdom",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "timezone": "Europe/London",
        },
        {
            "geonameid": 2655984,
            "name": "Belfast",
            "ascii_name": "Belfast",
            "label": "Belfast, United Kingdom",
            "query": "Belfast, United Kingdom",
            "country_code": "GB",
            "country_name": "United Kingdom",
            "latitude": 54.5968,
            "longitude": -5.9254,
            "timezone": "Europe/London",
        },
        {
            "geonameid": 6058560,
            "name": "London",
            "ascii_name": "London",
            "label": "London, Canada",
            "query": "London, Canada",
            "country_code": "CA",
            "country_name": "Canada",
            "latitude": 42.9834,
            "longitude": -81.233,
            "timezone": "America/Toronto",
        },
    ]
    monkeypatch.setattr(atlas_engine, "search_city_catalog", lambda **_kwargs: fake_cities)
    monkeypatch.setattr(
        atlas_engine,
        "search_live_location_candidates",
        lambda *_args, **_kwargs: fake_cities,
    )
    monkeypatch.setattr(
        atlas_engine,
        "rank_candidate_pool_for_goal",
        lambda **kwargs: {
            "candidate_count": len(kwargs["candidates"]),
            "results": [],
            "ranking": [],
        },
    )

    result = atlas_engine.rank_atlas_cities_for_goal(
        goal_id="love",
        natal_lines=[],
        query="London",
        country_code="GB",
        resolution="ultra",
    )

    assert result["catalog_candidate_count"] == 1
    assert result["live_candidate_count"] == 1
    assert result["candidate_count"] == 1
    assert atlas_engine._candidate_matches_identity_query(fake_cities[0], "London UK") is True
    assert atlas_engine._candidate_matches_identity_query(fake_cities[1], "London UK") is False
