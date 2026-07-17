from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

import forensic_asc_ruler_benchmark_runner as runner


def test_h2_material_tone_maps_to_trafficking_or_possession_axis():
    axes = runner.derive_asc_ruler_axes({"house": 2, "risk_tone": "material"})

    assert axes == ["trafficking_or_possession_context"]


def test_source_doctrine_maps_each_house_to_dedicated_axis():
    expected = {
        1: "immediate_scene_or_vicinity_context",
        2: "trafficking_or_possession_context",
        3: "communication_vehicle_short_distance_context",
        4: "family_home_end_matter_context",
        5: "party_entertainment_context",
        6: "routine_disruption_stalker_context",
        7: "suspect_territory_context",
        8: "death_financial_entanglement_context",
        9: "far_distance_departure_context",
        10: "public_authority_witness_context",
        11: "friends_social_circle_context",
        12: "hidden_captive_kidnapped_context",
    }

    for house, axis in expected.items():
        assert runner.derive_asc_ruler_source_doctrine_axes({"house": house}) == [axis]


def test_asc_ruler_metrics_score_support_and_contradictions():
    rows = [
        {
            "case_id": "hidden_abduction",
            "expected_axes": ["abduction_missing_person"],
            "contradictory_axes": ["child_victim"],
            "asc_ruler_placement": {"house": 12, "risk_tone": "hidden"},
        },
        {
            "case_id": "public_authority",
            "expected_axes": ["authority_or_public_case"],
            "contradictory_axes": ["domestic_partner_involvement"],
            "asc_ruler_placement": {"house": 10, "risk_tone": "public"},
        },
        {
            "case_id": "false_associate",
            "expected_axes": ["route_vehicle_transport"],
            "contradictory_axes": ["friend_or_close_associate"],
            "asc_ruler_placement": {"house": 11, "risk_tone": "associate"},
        },
    ]

    metrics = runner.compute_asc_ruler_metrics(rows)

    assert metrics["case_count"] == 3
    assert metrics["supported_case_count"] == 2
    assert metrics["contradicted_case_count"] == 1
    assert metrics["support_rate"] == 0.6667
    assert metrics["contradiction_rate"] == 0.3333
    assert metrics["promotion_recommended"] is False
    assert metrics["per_tone"]["hidden"]["support_rate"] == 1.0
    assert metrics["per_tone"]["associate"]["contradiction_rate"] == 1.0


def test_asc_ruler_runner_uses_curated_case_list_and_route_payload(monkeypatch, tmp_path):
    fixture = tmp_path / "asc_cases.json"
    fixture.write_text(
        """
        {
          "benchmark_id": "unit_asc",
          "promotion_thresholds": {
            "min_case_count": 1,
            "support_rate": 0.75,
            "contradiction_rate_max": 0.0
          },
          "cases": [
            {
              "case_id": "case_one",
              "curation_note": "Known hidden abduction context."
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    captured_queries = []

    def fake_load_cases(_paths):
        return [
            {
                "case_id": "case_one",
                "dataset_path": "fixture.json",
                "dataset_name": "fixture.json",
                "case": {"title": "Case One"},
                "expected_axes": ["abduction_missing_person"],
                "contradictory_axes": ["accident_or_disaster"],
                "query": {"mode": "manual", "datetime": "2020-01-01T00:00:00"},
                "expected_survivability": {"levels": ["Moderate"], "bands": ["risk_loaded_survival"]},
                "expected_relationship_labels": ["stranger_public"],
            }
        ]

    def fake_route(query):
        captured_queries.append(dict(query))
        return {
            "status_code": 200,
            "payload": {
                "success": True,
                "asc_ruler_placement": {
                    "ruler": "Jupiter",
                    "house": 12,
                    "label": "Hidden Or Captive",
                    "risk_tone": "hidden",
                    "summary": "Hidden testimony.",
                },
                "survivability": {
                    "level": "Moderate",
                    "outcome_band": "risk_loaded_survival",
                    "score": -2.0,
                },
            },
        }

    monkeypatch.setattr(runner, "load_statistical_cases", fake_load_cases)
    monkeypatch.setattr(runner, "_call_forensic_route", fake_route)

    report = runner.run_asc_ruler_benchmark_suite(asc_fixture_path=fixture)

    assert report["benchmark_id"] == "unit_asc"
    assert report["case_count"] == 1
    assert report["route_error_count"] == 0
    assert report["metrics"]["support_rate"] == 1.0
    assert report["metrics"]["promotion_recommended"] is True
    assert captured_queries[0]["secondary_factors"] == "0"
    assert report["case_results"][0]["asc_ruler_placement"]["house"] == 12

    markdown = runner.render_markdown_report(report)
    assert "# ASC-Ruler Placement Benchmark Report" in markdown
    assert "Promotion recommendation: yes" in markdown
    assert "case_one" in markdown


def test_asc_ruler_runner_reports_direct_h2_source_doctrine_case(monkeypatch, tmp_path):
    fixture = tmp_path / "asc_cases.json"
    fixture.write_text(
        """
        {
          "benchmark_id": "unit_asc_h2",
          "cases": [],
          "source_doctrine_cases": [
            {
              "case_id": "mcintosh_h2_trafficking_doctrine",
              "source_note": "If the ruler of the victim is in the 2nd house consider trafficking because the person is made a possession.",
              "asc_ruler_placement": {
                "ruler": "Venus",
                "house": 2,
                "label": "Possession Or Value Motive",
                "risk_tone": "material"
              },
              "expected_context_axes": ["trafficking_or_possession_context"],
              "contradictory_context_axes": ["accident_or_disaster"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    monkeypatch.setattr(runner, "load_statistical_cases", lambda _paths: [])

    report = runner.run_asc_ruler_benchmark_suite(asc_fixture_path=fixture)

    assert report["case_count"] == 0
    assert report["source_doctrine_case_count"] == 1
    assert report["source_doctrine_metrics"]["support_rate"] == 1.0
    assert report["source_doctrine_metrics"]["promotion_applicability"] == "not_applicable_source_doctrine_check"
    assert report["source_doctrine_results"][0]["derived_axes"] == ["trafficking_or_possession_context"]
    assert report["source_doctrine_results"][0]["supported_axes"] == ["trafficking_or_possession_context"]

    markdown = runner.render_markdown_report(report)
    assert "Source Doctrine Checks" in markdown
    assert "trafficking_or_possession_context" in markdown


def test_default_asc_ruler_fixture_curates_unique_case_ids():
    fixture = runner._load_asc_fixture(runner.DEFAULT_ASC_FIXTURE_PATH)
    case_ids = [item.get("case_id") for item in fixture.get("cases") or []]
    doctrine_cases = fixture.get("source_doctrine_cases") or []
    doctrine_ids = [item.get("case_id") for item in doctrine_cases]
    doctrine_houses = sorted((item.get("asc_ruler_placement") or {}).get("house") for item in doctrine_cases)

    assert fixture["benchmark_id"] == "forensic_asc_ruler_placement_v1"
    assert len(case_ids) >= 24
    assert len(case_ids) == len(set(case_ids))
    assert len(doctrine_ids) == 12
    assert doctrine_houses == list(range(1, 13))
    assert "mcintosh_h2_trafficking_possession_doctrine" in doctrine_ids
    assert fixture["promotion_thresholds"]["support_rate"] >= 0.6
