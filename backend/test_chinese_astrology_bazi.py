from datetime import date, datetime, timezone
from pathlib import Path
import json
import os
import sys

import pytest

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import chinese_astrology as chinese_astrology_module
import chinese_astrology.bazi as bazi_module
import chinese_astrology.interpretation as interpretation_module
from chinese_astrology.auxiliary_stars import build_auxiliary_stars
from chinese_astrology.bazi import BirthContext, SOLAR_TERMS, _element_balance, _strength_evidence, _term_payload, build_bazi_profile, sexagenary_day_index
from chinese_astrology.curation import GOLDEN_FIXTURE_MANIFEST, RULE_NOTES, SOURCE_ANCHORS
from chinese_astrology.interpretation import DAY_STEM_MONTH_CLIMATE_STEMS, _source_climate_rows, build_ten_god_profile, build_useful_element_recommendations
from chinese_astrology.oracle import cast_iching_oracle
from chinese_astrology.palaces import build_palace_context
from chinese_astrology.relationships import RELATIONSHIP_CONTEXT_PROFILES, analyze_pair_relationships, analyze_relationships
from chinese_astrology.tables import BRANCHES, STEMS
from chinese_astrology.validation import (
    VALIDATION_FIXTURES,
    VALIDATION_PHASES,
    released_yong_shen_families,
    validation_fixtures_for_phase,
    validation_summary,
    yong_shen_family_gate,
)


class _FakeSnapStore:
    def __init__(self, snaps=None):
        self._snaps = {str(item.get("id")): item for item in (snaps or []) if isinstance(item, dict)}

    def get(self, snap_id):
        return self._snaps.get(str(snap_id))


def _sexagenary_day_name(day):
    index = sexagenary_day_index(day)
    return STEMS[index % 10]["key"], BRANCHES[index % 12]["key"]


def _relationship_fixture_pillars(branches, stems=None):
    stems = list(stems or ["Jia", "Bing", "Wu", "Geng"])
    branch_list = list(branches)
    while len(branch_list) < 4:
        branch_list.append(branch_list[-1] if branch_list else "Zi")
    return {
        pillar: {
            "stem": stems[index % len(stems)],
            "branch": branch_list[index],
            "branch_element": BRANCHES[next(i for i, item in enumerate(BRANCHES) if item["key"] == branch_list[index])]["element"],
            "hidden_stems": [],
        }
        for index, pillar in enumerate(("year", "month", "day", "hour"))
    }


def _profile(
    iso_datetime,
    *,
    timezone_name="UTC",
    longitude=0.0,
    latitude=0.0,
    calculation_sex=None,
    include_luck_pillars=False,
    use_true_solar_time=False,
    day_boundary_rule="civil_midnight",
    hour_pillar_variant="standard_zi_hour",
    luck_direction_rule="year_stem_polarity",
    hour_known=True,
):
    return build_bazi_profile(
        BirthContext(
            dt_utc=datetime.fromisoformat(iso_datetime),
            timezone=timezone_name,
            latitude=latitude,
            longitude=longitude,
            calculation_sex=calculation_sex,
            include_luck_pillars=include_luck_pillars,
            use_true_solar_time=use_true_solar_time,
            day_boundary_rule=day_boundary_rule,
            hour_pillar_variant=hour_pillar_variant,
            luck_direction_rule=luck_direction_rule,
            hour_known=hour_known,
            time_precision="exact" if hour_known else "unknown",
        ),
        reference_dt_utc=datetime(2026, 5, 11, tzinfo=timezone.utc),
    )


def _value_at(payload, path):
    current = payload
    for part in str(path).split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current


def _profile_from_validation_fixture(fixture):
    fixture_input = fixture.get("input") or {}
    options = fixture.get("options") or {}
    return _profile(
        fixture_input["datetime_utc"],
        timezone_name=fixture_input.get("timezone") or "UTC",
        longitude=fixture_input.get("longitude", 0.0),
        latitude=fixture_input.get("latitude", 0.0),
        calculation_sex=options.get("calculation_sex"),
        include_luck_pillars=bool(options.get("include_luck_pillars", False)),
        use_true_solar_time=bool(options.get("use_true_solar_time", False)),
        day_boundary_rule=options.get("day_boundary_rule", "civil_midnight"),
        hour_pillar_variant=options.get("hour_pillar_variant", "standard_zi_hour"),
        luck_direction_rule=options.get("luck_direction_rule", "year_stem_polarity"),
        hour_known=bool(fixture_input.get("hour_known", True)),
    )


def _assert_expected_profile_fixture(fixture, profile):
    expected = fixture.get("expected") or {}
    for pillar_name, expected_pair in (expected.get("pillars") or {}).items():
        pillar = profile["pillars"].get(pillar_name)
        if expected_pair is None:
            assert pillar is None, f"{fixture['id']} expected no {pillar_name} pillar"
            continue
        expected_stem, expected_branch = str(expected_pair).split(" ", 1)
        assert pillar["stem"] == expected_stem, f"{fixture['id']} {pillar_name} stem"
        assert pillar["branch"] == expected_branch, f"{fixture['id']} {pillar_name} branch"
    for path, expected_value in (expected.get("paths") or {}).items():
        assert _value_at(profile, path) == expected_value, f"{fixture['id']} {path}"
    for warning_text in expected.get("warnings_contain") or []:
        assert any(warning_text in warning for warning in profile["debug"]["warnings"]), fixture["id"]


def test_sexagenary_day_cycle_matches_known_almanac_dates():
    assert _sexagenary_day_name(date(2000, 1, 1)) == ("Wu", "Wu")
    assert _sexagenary_day_name(date(1984, 2, 3)) == ("Ding", "Mao")


def test_chinese_astrology_bazi_route_uses_saved_snap_context(monkeypatch):
    client = app_module.app.test_client()
    snap = {
        "id": "snap-bazi",
        "label": "Saved BaZi Subject",
        "effective_datetime": "2000-01-01T12:00:00+00:00",
        "location": "Jerusalem, Israel",
        "timezone": "Asia/Jerusalem",
        "latitude": 31.778,
        "longitude": 35.235,
        "dashboard": {
            "timestamp": "2000-01-01T12:00:00+00:00",
            "location": "Jerusalem, Israel",
            "timezone": "Asia/Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
        },
    }

    def _unexpected_geocode(*_args, **_kwargs):
        raise AssertionError("saved snap BaZi route should use stored snap coordinates")

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore([snap]))
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", _unexpected_geocode)

    response = client.post("/api/astro-clock/chinese-astrology/bazi", json={"snap_id": "snap-bazi"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert data["source_snap_id"] == "snap-bazi"
    assert data["snap_label"] == "Saved BaZi Subject"
    assert data["birth"]["timezone"] == "Asia/Jerusalem"
    assert data["pillars"]["year"]["stem"] == "Ji"
    assert data["pillars"]["year"]["branch"] == "Mao"
    assert data["pillars"]["month"]["stem"] == "Bing"
    assert data["pillars"]["month"]["branch"] == "Zi"
    assert data["pillars"]["day"]["stem"] == "Wu"
    assert data["pillars"]["day"]["branch"] == "Wu"
    assert data["pillars"]["day"]["ten_god"] == "Day Master"
    assert data["day_master"]["stem"] == "Wu"
    assert all(row["pillar"] != "day" for row in data["ten_gods"]["visible"])
    assert data["ten_gods"]["factor_profile"]["status"] == "source_based_preview"
    assert data["ten_gods"]["factor_profile"]["source_basis"][0]["id"] == "local.destiny_code_five_factors"
    assert data["debug"]["snap_source"] == "saved_snap"
    assert data["debug"]["solar_term_source"] == "swiss_ephemeris"
    assert data["interpretation"]["status"] == "source_based_preview"
    assert data["analysis"]["method"] == "season_root_formation_v2"
    assert data["analysis"]["strength_model"]["season"]["season"] == "Winter"
    assert data["useful_elements"]["status"] in {"provisional", "withheld"}
    assert isinstance(data["useful_elements"]["element_integrity"], list)
    assert isinstance(data["useful_elements"]["integrity_summary"], dict)
    assert data["auxiliary_stars"]["peach_blossom"]["status"] == "source_based_preview"
    assert data["auxiliary_stars"]["peach_blossom"]["target_branch"] == "Mao"
    assert data["palace_context"]["status"] == "source_based_preview"
    assert data["palace_context"]["palaces"][2]["pillar"] == "day"
    assert data["palace_context"]["palaces"][2]["life_stage"] == "Adulthood"
    assert data["life_areas"]["status"] == "source_gated_context"
    assert data["life_areas"]["method"] == "bazi_life_areas_v1"
    assert {"career_authority", "wealth_assets", "relationships_family", "health_body"} <= {
        area["id"] for area in data["life_areas"]["areas"]
    }
    assert data["life_areas"]["context_requirements"] == []
    assert data["life_areas"]["limits"] == []
    assert isinstance(data["relationships"]["events"], list)


def test_chinese_astrology_rejects_uncertain_legacy_saved_context_but_allows_direct_input(
    monkeypatch,
):
    client = app_module.app.test_client()
    legacy_snap = {
        "id": "legacy-synthetic",
        "label": "Synthetic legacy chart",
        "effective_datetime": "2000-02-29",
        "location": "Paris, France",
        "timezone": "Europe/Paris",
        "timezone_label": "Europe/Paris (UTC+01:00)",
        "coords": [48.85341, 2.3488],
        "dashboard": {
            "timestamp": "2000-02-29",
            "location": "Paris, France",
            "timezone": "Europe/Paris",
        },
    }
    monkeypatch.setattr(
        astro_clock_api,
        "_snaps",
        lambda: _FakeSnapStore([legacy_snap]),
    )

    saved_response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={"snap_id": "legacy-synthetic"},
    )
    saved_payload = saved_response.get_json()

    assert saved_response.status_code == 400
    assert saved_payload["success"] is False
    assert "Confirm/correct the saved context first" in saved_payload["error"]

    direct_response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={
            "datetime": "2000-02-29T11:34:00+00:00",
            "location": "Paris, France",
            "timezone": "Europe/Paris",
            "latitude": 48.85341,
            "longitude": 2.3488,
        },
    )

    assert direct_response.status_code == 200
    assert direct_response.get_json()["success"] is True


def test_chinese_astrology_compatibility_route_compares_two_saved_snaps(monkeypatch):
    client = app_module.app.test_client()
    snap_a = {
        "id": "snap-a",
        "label": "Primary BaZi Subject",
        "effective_datetime": "2000-01-01T12:00:00+00:00",
        "location": "Greenwich, UK",
        "timezone": "UTC",
        "latitude": 51.4769,
        "longitude": 0.0,
        "dashboard": {
            "timestamp": "2000-01-01T12:00:00+00:00",
            "location": "Greenwich, UK",
            "timezone": "UTC",
            "latitude": 51.4769,
            "longitude": 0.0,
        },
    }
    snap_b = {
        "id": "snap-b",
        "label": "Relationship BaZi Subject",
        "effective_datetime": "2000-01-04T12:00:00+00:00",
        "location": "Greenwich, UK",
        "timezone": "UTC",
        "latitude": 51.4769,
        "longitude": 0.0,
        "dashboard": {
            "timestamp": "2000-01-04T12:00:00+00:00",
            "location": "Greenwich, UK",
            "timezone": "UTC",
            "latitude": 51.4769,
            "longitude": 0.0,
        },
    }

    def _unexpected_geocode(*_args, **_kwargs):
        raise AssertionError("compatibility route should use stored snap coordinates")

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore([snap_a, snap_b]))
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", _unexpected_geocode)

    response = client.post(
        "/api/astro-clock/chinese-astrology/compatibility",
        json={
            "primary_snap_id": "snap-a",
            "relationship_snap_id": "snap-b",
            "relationship_context": "romantic",
            "primary_calculation_sex": "female",
            "relationship_calculation_sex": "male",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    compatibility = data["compatibility"]
    spouse_star_directions = {
        row["direction"]: row
        for row in compatibility["doctrine"]["layers"]["natal_spouse_star"]["directions"]
    }
    assert data["primary"]["birth"]["calculation_sex"] == "female"
    assert data["relationship"]["birth"]["calculation_sex"] == "male"
    assert spouse_star_directions["primary_context"]["calculation_sex"] == "female"
    assert spouse_star_directions["primary_context"]["sex_based_role"] == "husband_star"
    assert spouse_star_directions["relationship_context"]["calculation_sex"] == "male"
    assert spouse_star_directions["relationship_context"]["sex_based_role"] == "wife_star"
    assert compatibility["method"] == "bazi_pair_qualitative_doctrine_v1"
    assert compatibility["status"] == "qualitative_evidence_only"
    assert compatibility["subjects"]["primary"]["source_snap_id"] == "snap-a"
    assert compatibility["subjects"]["relationship"]["source_snap_id"] == "snap-b"
    assert compatibility["day_master_exchange"]["status"] == "available"
    assert compatibility["timing_alignment"]["primary"]["spouse_palace"]["branch"] == "Wu"
    assert compatibility["timing_alignment"]["relationship"]["spouse_palace"]["branch"] == "You"
    assert compatibility["timing_alignment"]["primary"]["counts"]["day_events"] > 0
    assert compatibility["relationship_context"] == "romantic"
    assert compatibility["doctrine"]["method"] == "bazi_pair_qualitative_doctrine_v1"
    assert compatibility["doctrine"]["relationship_context"] == "romantic"
    assert compatibility["doctrine"]["context_profile"]["evidence_order"][:2] == [
        "natal_spouse_palace",
        "natal_spouse_star",
    ]
    assert compatibility["doctrine"]["aggregate_policy"]["mode"] == "none"
    assert compatibility["doctrine"]["layers"]["cross_chart_overlay"]["outcome_authority"] == "none"
    assert compatibility["doctrine"]["layers"]["natal_spouse_palace"]["status"] == "available"
    assert "scoring" not in compatibility
    assert "judgement" not in compatibility
    assert compatibility["interpretation"]["status"] == "qualitative_evidence_only"
    assert compatibility["interpretation"]["focus"] in {
        "individual_timing_context",
        "individual_natal_relationship_context",
    }
    assert compatibility["summary"]["total"] > 0
    assert any(
        {point["subject"] for point in event["points"]} == {"primary", "relationship"}
        for event in compatibility["events"]
    )
    assert any(event["intensity"] in {"day_partner_palace", "partner_palace_contact"} for event in compatibility["events"])

    legacy_response = client.post(
        "/api/astro-clock/chinese-astrology/compatibility",
        json={
            "primary_snap_id": "snap-a",
            "relationship_snap_id": "snap-b",
            "calculation_sex": "female",
        },
    )
    legacy_data = legacy_response.get_json()["data"]
    assert legacy_response.status_code == 200
    assert legacy_data["primary"]["birth"]["calculation_sex"] == "female"
    assert legacy_data["relationship"]["birth"]["calculation_sex"] == "female"

    primary_only_response = client.post(
        "/api/astro-clock/chinese-astrology/compatibility",
        json={
            "primary_snap_id": "snap-a",
            "relationship_snap_id": "snap-b",
            "primary_calculation_sex": "female",
        },
    )
    primary_only_data = primary_only_response.get_json()["data"]
    primary_only_directions = {
        row["direction"]: row
        for row in primary_only_data["compatibility"]["doctrine"]["layers"]["natal_spouse_star"]["directions"]
    }
    assert primary_only_response.status_code == 200
    assert primary_only_data["primary"]["birth"]["calculation_sex"] == "female"
    assert primary_only_data["relationship"]["birth"]["calculation_sex"] is None
    assert primary_only_directions["relationship_context"]["sex_based_role"] == "unknown"


def test_chinese_astrology_compatibility_route_rejects_same_snap(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore([]))

    response = client.post(
        "/api/astro-clock/chinese-astrology/compatibility",
        json={"primary_snap_id": "snap-a", "relationship_snap_id": "snap-a"},
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "different saved snaps" in payload["error"]


def test_chinese_astrology_compatibility_route_returns_withheld_boundary_contract(monkeypatch):
    client = app_module.app.test_client()
    snaps = [
        {
            "id": snap_id,
            "label": label,
            "effective_datetime": timestamp,
            "location": "Greenwich, UK",
            "timezone": "UTC",
            "latitude": 0.0,
            "longitude": 0.0,
        }
        for snap_id, label, timestamp in (
            ("snap-a", "Boundary subject", "2000-01-01T12:00:00+00:00"),
            ("snap-b", "Stable subject", "2000-01-04T12:00:00+00:00"),
        )
    ]
    uncertain = _profile("2000-01-01T12:00:00+00:00", calculation_sex="female")
    uncertain = {
        **uncertain,
        "calculation_status": "uncertain_birth_time_boundary",
        "uncertainty": {
            "birth_time": {
                "status": "uncertain",
                "affected_pillars": ["month"],
                "candidate_count": 2,
            },
        },
    }
    stable = _profile("2000-01-04T12:00:00+00:00", calculation_sex="male")
    profiles = iter((uncertain, stable))

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore(snaps))
    monkeypatch.setattr(chinese_astrology_module, "build_bazi_profile", lambda _context: next(profiles))

    response = client.post(
        "/api/astro-clock/chinese-astrology/compatibility",
        json={
            "primary_snap_id": "snap-a",
            "relationship_snap_id": "snap-b",
            "relationship_context": "romantic",
        },
    )
    report = response.get_json()["data"]["compatibility"]

    assert response.status_code == 200
    assert report["status"] == "withheld"
    assert report["reason_code"] == "birth_time_boundary_uncertainty"
    assert report["ambiguity"]["affected_subjects"][0]["subject"] == "primary"
    assert "doctrine" not in report
    assert "scoring" not in report
    assert "judgement" not in report


@pytest.mark.parametrize(("failed_call", "expected_participant"), ((1, "primary"), (2, "relationship")))
def test_chinese_astrology_compatibility_solar_term_503_identifies_participant(
    monkeypatch,
    failed_call,
    expected_participant,
):
    client = app_module.app.test_client()
    snaps = [
            {
                "id": snap_id,
                "effective_datetime": timestamp,
                "location": "Greenwich, UK",
                "timezone": "UTC",
                "latitude": 0.0,
                "longitude": 0.0,
                "dashboard": {
                    "timestamp": timestamp,
                    "location": "Greenwich, UK",
                    "timezone": "UTC",
                    "latitude": 0.0,
                "longitude": 0.0,
            },
        }
        for snap_id, timestamp in (
            ("snap-a", "2000-01-01T12:00:00+00:00"),
            ("snap-b", "2000-01-04T12:00:00+00:00"),
        )
    ]
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _FakeSnapStore(snaps))
    call_count = 0

    def _build_or_fail(_context):
        nonlocal call_count
        call_count += 1
        if call_count == failed_call:
            raise bazi_module.SolarTermCalculationError(
                year=2000,
                term_key="xiao_han",
                reason="solar_longitude_solver_failed",
            )
        return {"calculation_status": "complete"}

    monkeypatch.setattr(chinese_astrology_module, "build_bazi_profile", _build_or_fail)
    response = client.post(
        "/api/astro-clock/chinese-astrology/compatibility",
        json={"primary_snap_id": "snap-a", "relationship_snap_id": "snap-b"},
    )
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["error"] == "solar_term_calculation_unavailable"
    assert payload["participant"] == expected_participant
    assert payload["calculation_error"]["participant"] == expected_participant
    assert "incident_id" not in payload


def test_iching_oracle_manual_lines_resolve_primary_and_relating_hexagrams():
    oracle = cast_iching_oracle(
        method="manual",
        lines=[6, 7, 8, 9, 7, 8],
        question="What is the clean next step?",
    )

    assert oracle["method"] == "iching_oracle_v1"
    assert oracle["line_order"] == "bottom_to_top"
    assert oracle["primary"]["number"] == 60
    assert oracle["primary"]["title"] == "Limitation"
    assert oracle["relating"]["number"] == 47
    assert oracle["relating"]["title"] == "Oppression"
    assert oracle["nuclear"]["number"] == 50
    assert oracle["nuclear"]["title"] == "The Cauldron"
    assert oracle["nuclear"]["derivation"]["lower_nuclear_lines"] == [2, 3, 4]
    assert oracle["reading"]["policy"]["id"] == "zhu_xi_seven_rule_line_policy"
    assert oracle["reading"]["policy"]["focus"] == "two_moving_lines_upper_primary"
    assert oracle["reading"]["policy"]["primary_line"] == 4
    assert oracle["changing_lines"] == [1, 4]
    assert [line["value"] for line in oracle["lines"]] == [6, 7, 8, 9, 7, 8]
    assert oracle["lines"][0]["moving"] is True
    assert oracle["lines"][3]["changes_to"] == 8
    assert {row["source_id"] for row in oracle["source_evidence"]} >= {
        "local.iching_huang",
        "local.iching_source_audit_2026_05_11",
        "public.iching_divination_method",
        "public.king_wen_hexagram_list",
        "public.nuclear_hexagram_structure",
        "classic.zhu_xi_seven_rule_line_policy",
    }


def test_iching_oracle_core_hexagrams_use_bottom_to_top_line_order():
    qian = cast_iching_oracle(method="manual", lines=[7, 7, 7, 7, 7, 7])
    kun = cast_iching_oracle(method="manual", lines=[8, 8, 8, 8, 8, 8])

    assert qian["primary"]["number"] == 1
    assert qian["primary"]["title"] == "The Creative"
    assert qian["relating"] is None
    assert kun["primary"]["number"] == 2
    assert kun["primary"]["title"] == "The Receptive"
    assert kun["relating"] is None


def test_iching_oracle_supports_yarrow_probability_and_all_line_policy():
    yarrow = cast_iching_oracle(method="yarrow", seed="fixture-yarrow")

    assert yarrow["casting_method"] == "yarrow_probability"
    assert yarrow["cast_source"] == "seeded_yarrow_probability_generator"
    assert yarrow["random_model"] == "yarrow_stalk_probability_1_5_7_3"
    assert len(yarrow["lines"]) == 6
    assert {line["value"] for line in yarrow["lines"]} <= {6, 7, 8, 9}
    assert "iching.oracle.yarrow_probability_model" in yarrow["validation"]["fixture_ids"]

    qian_all_nines = cast_iching_oracle(method="manual", lines=[9, 9, 9, 9, 9, 9])
    assert qian_all_nines["primary"]["number"] == 1
    assert qian_all_nines["relating"]["number"] == 2
    assert qian_all_nines["reading"]["policy"]["focus"] == "qian_all_nines_dynamic_line"

    kun_all_sixes = cast_iching_oracle(method="manual", lines=[6, 6, 6, 6, 6, 6])
    assert kun_all_sixes["primary"]["number"] == 2
    assert kun_all_sixes["relating"]["number"] == 1
    assert kun_all_sixes["reading"]["policy"]["focus"] == "kun_all_sixes_dynamic_line"


def test_chinese_astrology_iching_oracle_route_casts_coin_values():
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/chinese-astrology/iching-oracle",
        json={
            "question": "How should we proceed?",
            "method": "coins",
            "coin_value_scheme": "heads_2_tails_3",
            "coins": [
                ["heads", "heads", "heads"],
                ["heads", "heads", "tails"],
                ["heads", "tails", "tails"],
                ["tails", "tails", "tails"],
                ["heads", "heads", "tails"],
                ["heads", "tails", "tails"],
            ],
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    oracle = payload["data"]["oracle"]
    assert oracle["casting_method"] == "three_coin"
    assert oracle["coin_value_scheme"] == "heads_2_tails_3"
    assert [line["value"] for line in oracle["lines"]] == [6, 7, 8, 9, 7, 8]
    assert oracle["primary"]["number"] == 60
    assert oracle["relating"]["number"] == 47
    assert oracle["validation"]["status"] == "fixture_backed"


def test_chinese_astrology_iching_oracle_route_rejects_bad_payloads():
    client = app_module.app.test_client()

    non_object = client.post(
        "/api/astro-clock/chinese-astrology/iching-oracle",
        json=["not", "an", "object"],
    )
    assert non_object.status_code == 400
    assert "JSON object body is required" in non_object.get_json()["error"]

    short_lines = client.post(
        "/api/astro-clock/chinese-astrology/iching-oracle",
        json={"method": "manual", "lines": [7, 7]},
    )
    assert short_lines.status_code == 400
    assert "exactly six lines" in short_lines.get_json()["error"]

    bad_coin = client.post(
        "/api/astro-clock/chinese-astrology/iching-oracle",
        json={"method": "coins", "coins": [["heads", "tails"]]},
    )
    assert bad_coin.status_code == 400
    assert "six throws" in bad_coin.get_json()["error"]

    bad_scheme = client.post(
        "/api/astro-clock/chinese-astrology/iching-oracle",
        json={"method": "coins", "coin_value_scheme": "unknown"},
    )
    assert bad_scheme.status_code == 400
    assert "coin_value_scheme" in bad_scheme.get_json()["error"]


def test_pair_context_profiles_order_qualitative_doctrine_without_aggregate():
    primary = _profile("2000-01-01T12:00:00+00:00", calculation_sex="female", include_luck_pillars=True)
    relationship = _profile("2000-01-04T12:00:00+00:00", calculation_sex="female", include_luck_pillars=True)

    general = analyze_pair_relationships(primary, relationship, relationship_context="general")
    romantic = analyze_pair_relationships(primary, relationship, relationship_context="romantic")
    family = analyze_pair_relationships(primary, relationship, relationship_context="family")
    business = analyze_pair_relationships(primary, relationship, relationship_context="business")

    assert {"general", "romantic", "family", "business"} <= set(RELATIONSHIP_CONTEXT_PROFILES)
    assert all(report["status"] == "qualitative_evidence_only" for report in (general, romantic, family, business))
    assert all(report["doctrine"]["aggregate_policy"]["mode"] == "none" for report in (general, romantic, family, business))
    assert general["doctrine"]["relationship_context"] == "general"
    assert general["doctrine"]["context_profile"]["conditional_evidence"] == [
        "natal_spouse_palace",
        "natal_spouse_star",
    ]
    assert romantic["doctrine"]["context_profile"]["evidence_order"][:2] == [
        "natal_spouse_palace",
        "natal_spouse_star",
    ]
    assert family["doctrine"]["context_profile"]["excluded_evidence"] == [
        "natal_spouse_palace",
        "natal_spouse_star",
    ]
    assert business["doctrine"]["context_profile"]["excluded_evidence"] == [
        "natal_spouse_palace",
        "natal_spouse_star",
    ]
    assert family["doctrine"]["fixture_ids"][0] == "compatibility.doctrine_family_scope_guard_v1"
    assert business["doctrine"]["fixture_ids"][0] == "compatibility.doctrine_business_scope_guard_v1"
    assert all("scoring" not in report and "judgement" not in report for report in (general, romantic, family, business))


def test_compatibility_uses_sex_based_natal_spouse_star_before_comparison_context():
    primary = _profile("2000-01-01T12:00:00+00:00", calculation_sex="male", include_luck_pillars=True)
    relationship = _profile("2000-01-04T12:00:00+00:00", calculation_sex="female", include_luck_pillars=True)

    report = analyze_pair_relationships(primary, relationship, relationship_context="romantic")
    spouse_star = report["doctrine"]["layers"]["natal_spouse_star"]
    directions = {row["direction"]: row for row in spouse_star["directions"]}

    assert spouse_star["method"] == "sex_based_spouse_star_context_v3"
    assert directions["primary_context"]["factor"] == "Wealth"
    assert directions["relationship_context"]["factor"] == "Influence"
    assert directions["primary_context"]["compared_chart_element_presence"]["inventory_basis"] == "unweighted_element_presence"
    assert directions["primary_context"]["compared_chart_element_presence"]["outcome_authority"] == "none"
    assert report["doctrine"]["evidence_order"][1]["key"] == "natal_spouse_star"


def test_pair_doctrine_is_withheld_for_unresolved_birth_time_boundary():
    primary = _profile("2000-01-01T12:00:00+00:00", calculation_sex="male")
    relationship = _profile("2000-01-04T12:00:00+00:00", calculation_sex="female")
    primary = {
        **primary,
        "calculation_status": "uncertain_birth_time_boundary",
        "uncertainty": {
            "birth_time": {
                "status": "uncertain",
                "affected_pillars": ["month"],
                "candidate_count": 2,
            },
        },
    }

    report = analyze_pair_relationships(primary, relationship, relationship_context="romantic")

    assert report["status"] == "withheld"
    assert report["reason_code"] == "birth_time_boundary_uncertainty"
    assert report["reason"] == "A recorded birth-time range crosses a BaZi pillar boundary."
    assert report["ambiguity"]["status"] == "requires_resolved_birth_time"
    assert report["ambiguity"]["affected_subjects"][0]["subject"] == "primary"
    assert "doctrine" not in report
    assert "scoring" not in report
    assert "judgement" not in report


def test_chinese_astrology_profile_exposes_phase_1_curation_payload():
    profile = _profile("2000-01-01T12:00:00+00:00", calculation_sex="female", include_luck_pillars=True)

    assert profile["curation"]["status"] == "phase_5_6_curation_and_workflow_foundation"
    assert profile["curation"]["validation"]["status"] == "validation_fixture_ledger_seeded"
    assert profile["curation"]["validation"]["phase_count"] == 7
    assert profile["curation"]["rule_note_count"] >= 10
    assert profile["curation"]["fixture_count"] >= 8
    assert any(note["id"] == "useful_elements.preview" for note in profile["curation"]["active_rule_notes"])
    assert {tag["key"] for tag in profile["source_confidence"]} >= {
        "local_source",
        "computed_rule",
        "provisional_model",
        "needs_validation",
    }
    assert profile["interpretation"]["sections"][0]["source_confidence"]
    assert profile["useful_elements"]["source_confidence"]
    assert "currently reading as" in profile["interpretation"]["summary"]
    profile_text = json.dumps(profile, ensure_ascii=False)
    assert "source-based evidence preview" not in profile_text
    assert "current preview" not in profile_text
    assert "source-backed previews" not in profile_text
    assert "favorable-element preview" not in profile_text
    assert "strength preview" not in profile_text


def test_phase_1_rule_notes_and_fixture_manifest_cover_required_areas():
    rule_areas = {note["area"] for note in RULE_NOTES}
    fixture_areas = {fixture["area"] for fixture in GOLDEN_FIXTURE_MANIFEST}
    anchor_areas = {anchor["area"] for anchor in SOURCE_ANCHORS}

    assert {
        "pillars",
        "solar_terms",
        "true_solar_time",
        "ten_gods",
        "strength",
        "useful_elements",
        "relationships",
        "compatibility",
        "timing",
        "auxiliary_stars",
    } <= rule_areas
    assert {
        "solar_terms",
        "hour_pillar",
        "true_solar_time",
        "missing_inputs",
        "luck_pillars",
        "relationships",
        "compatibility",
    } <= fixture_areas
    assert {
        "solar_terms",
        "true_solar_time",
        "ten_gods",
        "strength",
        "relationships",
        "timing",
        "useful_elements",
        "auxiliary_stars",
    } <= anchor_areas
    assert all(anchor.get("implementation_ids") for anchor in SOURCE_ANCHORS)
    assert all(anchor.get("page_refs") or anchor.get("external_refs") for anchor in SOURCE_ANCHORS)


def test_augier_four_pillars_anchors_are_page_tightened():
    anchors = {anchor["id"]: anchor for anchor in SOURCE_ANCHORS}
    strength_anchor = anchors["anchor.strength.roots_season"]
    hidden_anchor = anchors["anchor.pillars.hidden_stems"]
    ten_gods_anchor = anchors["anchor.ten_gods.five_factors"]

    strength_pages = {
        page
        for ref in strength_anchor["page_refs"]
        if "ba-zi-the-four-pillars-of-destiny.pages.jsonl" in ref["path"]
        for page in ref["pages"]
    }
    assert {43, 44, 45, 46, 66} <= strength_pages
    assert {"normal root", "secret root", "formation", "eight palaces"} <= set(strength_anchor["keywords"])
    assert hidden_anchor["source_id"] == "local.four_pillars_strength"
    assert {"hidden heavenly stems", "major stem", "supporting stems"} <= set(hidden_anchor["keywords"])
    assert any(49 in ref["pages"] for ref in ten_gods_anchor["page_refs"])


def test_validation_summary_covers_all_current_feature_risks():
    summary = validation_summary()

    assert {phase["id"] for phase in VALIDATION_PHASES} == {"V1", "V2", "V3", "V4", "V5", "V6", "V7"}
    assert summary["status"] == "validation_fixture_ledger_seeded"
    assert summary["phase_count"] == 7
    assert summary["fixture_count"] == len(VALIDATION_FIXTURES)
    assert summary["p0_fixture_count"] >= 10
    assert {
        "solar_terms",
        "true_solar_time",
        "luck_pillars",
        "timing_rhythm",
        "strength",
        "useful_elements",
        "relationships",
        "compatibility",
        "frontend_workflow",
        "release",
        "iching_oracle",
        "changing_lines",
        "timing_rhythm",
    } <= set(summary["areas"])
    assert any(gate["id"] == "backend_chinese_astrology_tests" for gate in summary["release_gates"])
    narrative_only_families = {
        "strong_balancing",
        "weak_support",
        "climate_override",
        "dominant_element",
        "follow_structure",
        "transformation_structure",
        "damaged_alternate",
        "tong_guan",
    }
    assert summary["released_yong_shen_families"] == []
    assert narrative_only_families | {"timing_assisted"} <= {
        family["family"]
        for family in summary["blocked_yong_shen_families"]
    }


def test_yong_shen_rule_family_gates_require_executable_chart_fixtures():
    narrative_only_families = {
        "strong_balancing",
        "weak_support",
        "climate_override",
        "dominant_element",
        "follow_structure",
        "transformation_structure",
        "damaged_alternate",
        "tong_guan",
    }

    for family in narrative_only_families:
        gate = yong_shen_family_gate(family)
        assert gate["released"] is False
        assert gate["positive_fixture_count"] >= 3
        assert gate["negative_fixture_count"] >= 3
        assert gate["executable_fixture_qualification"] == "chart_input_and_assertions_v1"
        assert gate["executable_positive_fixture_count"] == 0
        assert gate["executable_negative_fixture_count"] == 0
        assert gate["non_executable_fixture_ids"]
        assert "executable_positive_fixture_gate" in gate["blockers"]
        assert "executable_negative_fixture_gate" in gate["blockers"]

    assert released_yong_shen_families() == []


def test_validation_fixture_ledger_has_every_phase_and_source_anchor_status():
    fixture_phases = {fixture["phase"] for fixture in VALIDATION_FIXTURES}
    fixture_areas = {fixture["area"] for fixture in VALIDATION_FIXTURES}

    assert {phase["id"] for phase in VALIDATION_PHASES} <= fixture_phases
    assert {
        "solar_terms",
        "day_cycle",
        "hour_pillar",
        "true_solar_time",
        "late_zi",
        "luck_pillars",
        "timing_rhythm",
        "strength",
        "useful_elements",
        "relationships",
        "palaces",
        "auxiliary_stars",
        "compatibility",
        "frontend_workflow",
        "reading_history",
        "release",
        "iching_oracle",
        "changing_lines",
    } <= fixture_areas
    assert all(fixture.get("source_anchor") for fixture in VALIDATION_FIXTURES)
    assert validation_fixtures_for_phase("V1")
    assert {
        "yong_shen.strong_balancing_family",
        "yong_shen.weak_support_family",
        "yong_shen.climate_override_family",
        "yong_shen.damage_withheld_family",
        "yong_shen.special_structure_withheld_family",
        "yong_shen.balanced_withheld_family",
    } <= {fixture["id"] for fixture in VALIDATION_FIXTURES}


def test_validation_profile_fixture_table_matches_current_engine():
    profile_fixtures = [fixture for fixture in VALIDATION_FIXTURES if fixture.get("kind") == "profile"]

    assert len(profile_fixtures) >= 15
    for fixture in profile_fixtures:
        profile = _profile_from_validation_fixture(fixture)
        _assert_expected_profile_fixture(fixture, profile)


def test_validation_day_cycle_fixture_table_matches_engine():
    day_fixtures = [fixture for fixture in VALIDATION_FIXTURES if fixture.get("kind") == "day_cycle"]

    assert day_fixtures
    for fixture in day_fixtures:
        expected_stem, expected_branch = fixture["expected"]["day"].split(" ", 1)
        assert _sexagenary_day_name(date.fromisoformat(fixture["input"]["date"])) == (expected_stem, expected_branch)


def test_validation_solar_term_reference_set_matches_hko_minute_table():
    reference_sets = [fixture for fixture in VALIDATION_FIXTURES if fixture.get("kind") == "solar_term_reference_set"]
    term_by_key = {term["key"]: term for term in SOLAR_TERMS}

    assert reference_sets
    for fixture in reference_sets:
        year = int(fixture["input"]["year"])
        tolerance_seconds = int(fixture.get("tolerance_seconds") or 0)
        for term_key, expected_iso in fixture["expected_terms_utc"].items():
            actual = _term_payload(year, term_by_key[term_key])["datetime_utc"]
            expected = datetime.fromisoformat(expected_iso)
            assert abs((actual - expected).total_seconds()) <= tolerance_seconds, f"{fixture['id']} {term_key}"


def test_validation_luck_pillar_start_age_fixtures_match_hko_jie_table():
    hko_terms = next(
        fixture["expected_terms_utc"]
        for fixture in VALIDATION_FIXTURES
        if fixture.get("id") == "solar_terms.hko_2026_jie_reference_set"
    )
    luck_fixtures = [
        fixture
        for fixture in VALIDATION_FIXTURES
        if (fixture.get("expected") or {}).get("hko_adjacent_term_utc")
    ]

    assert luck_fixtures
    for fixture in luck_fixtures:
        profile = _profile_from_validation_fixture(fixture)
        timing = profile["timing"]
        expected = fixture["expected"]
        expected_paths = expected.get("paths") or {}
        term_key = expected_paths["timing.debug.solar_term.key"]
        tolerance = expected.get("tolerance") or {}
        actual_term = datetime.fromisoformat(timing["debug"]["solar_term"]["datetime_utc"])
        expected_term = datetime.fromisoformat(expected["hko_adjacent_term_utc"])
        birth_dt = datetime.fromisoformat(fixture["input"]["datetime_utc"])
        source_distance_days = abs((expected_term - birth_dt).total_seconds()) / 86400.0

        assert hko_terms[term_key] == expected["hko_adjacent_term_utc"], fixture["id"]
        assert abs((actual_term - expected_term).total_seconds()) <= tolerance["term_seconds"], fixture["id"]
        assert abs(source_distance_days - expected["distance_days"]) <= 0.0001, fixture["id"]
        assert abs(timing["debug"]["distance_days"] - expected["distance_days"]) <= tolerance["distance_days"], fixture["id"]
        assert abs(timing["start_age"] - expected["start_age"]) <= tolerance["start_age"], fixture["id"]
        assert abs(timing["debug"]["start_age_years"] - expected["start_age"]) <= tolerance["start_age"], fixture["id"]


def test_validation_pair_fixture_table_matches_current_qualitative_doctrine():
    pair_fixtures = [fixture for fixture in VALIDATION_FIXTURES if fixture.get("kind") == "pair_doctrine"]

    assert pair_fixtures
    for fixture in pair_fixtures:
        options = fixture.get("options") or {}
        primary = _profile(
            fixture["primary_input"]["datetime_utc"],
            timezone_name=fixture["primary_input"].get("timezone") or "UTC",
            calculation_sex=options.get("calculation_sex"),
            include_luck_pillars=bool(options.get("include_luck_pillars", False)),
        )
        relationship = _profile(
            fixture["relationship_input"]["datetime_utc"],
            timezone_name=fixture["relationship_input"].get("timezone") or "UTC",
            calculation_sex=options.get("calculation_sex"),
            include_luck_pillars=bool(options.get("include_luck_pillars", False)),
        )
        report = analyze_pair_relationships(
            primary,
            relationship,
            relationship_context=options.get("relationship_context", "general"),
        )
        for path, expected_value in (fixture.get("expected") or {}).get("paths", {}).items():
            assert _value_at(report, path) == expected_value, f"{fixture['id']} {path}"
        assert "scoring" not in report
        assert "judgement" not in report


def test_golden_fixture_li_chun_year_boundary():
    before = _profile("2000-02-03T12:00:00+00:00")
    after = _profile("2000-02-06T12:00:00+00:00")

    assert (before["pillars"]["year"]["stem"], before["pillars"]["year"]["branch"]) == ("Ji", "Mao")
    assert (after["pillars"]["year"]["stem"], after["pillars"]["year"]["branch"]) == ("Geng", "Chen")


def test_golden_fixture_jing_zhe_month_boundary():
    before = _profile("2000-03-04T12:00:00+00:00")
    after = _profile("2000-03-07T12:00:00+00:00")

    assert before["pillars"]["month"]["branch"] == "Yin"
    assert after["pillars"]["month"]["branch"] == "Mao"


def test_unknown_time_on_ordinary_date_has_one_stable_solar_term_candidate():
    profile = _profile("2000-01-01T12:00:00+00:00", hour_known=False)
    uncertainty = profile["uncertainty"]["birth_time"]

    assert uncertainty["status"] == "stable"
    assert uncertainty["affected_pillars"] == []
    assert len(uncertainty["candidates"]) == 1
    assert uncertainty["candidates"][0]["position"] == "only_candidate"
    assert uncertainty["candidates"][0]["selected"] is True
    assert uncertainty["selected_candidate"] == 0
    assert uncertainty["interval"] == {
        "start_local": "2000-01-01T00:00:00+00:00",
        "end_local_exclusive": "2000-01-02T00:00:00+00:00",
        "start_utc": "2000-01-01T00:00:00+00:00",
        "end_utc_exclusive": "2000-01-02T00:00:00+00:00",
    }
    assert profile["pillars"]["year"] is not None
    assert profile["pillars"]["month"] is not None
    assert profile["birth"]["datetime_utc"] is None
    assert profile["birth"]["local_datetime"] is None
    assert profile["birth"]["representative_datetime_utc"] == "2000-01-01T12:00:00+00:00"
    assert profile["withheld_outputs"] == []


def test_unknown_time_local_date_crossing_li_chun_returns_two_candidates_and_withholds_dependents():
    crossing = _term_payload(2000, next(term for term in SOLAR_TERMS if term["key"] == "li_chun"))["datetime_utc"]
    local_noon_utc = datetime(
        crossing.year,
        crossing.month,
        crossing.day,
        4,
        tzinfo=timezone.utc,
    )
    profile = _profile(
        local_noon_utc.isoformat(),
        timezone_name="Asia/Shanghai",
        hour_known=False,
    )
    uncertainty = profile["uncertainty"]["birth_time"]

    assert profile["calculation_status"] == "uncertain_birth_time_boundary"
    assert uncertainty["status"] == "uncertain"
    assert uncertainty["affected_pillars"] == ["year", "month"]
    assert [item["key"] for item in uncertainty["boundaries"]] == ["li_chun"]
    assert [candidate["position"] for candidate in uncertainty["candidates"]] == [
        "before_boundary",
        "after_boundary",
    ]
    assert {
        (candidate["pillars"]["year"]["stem"], candidate["pillars"]["year"]["branch"])
        for candidate in uncertainty["candidates"]
    } == {("Ji", "Mao"), ("Geng", "Chen")}
    assert {
        (candidate["pillars"]["month"]["stem"], candidate["pillars"]["month"]["branch"])
        for candidate in uncertainty["candidates"]
    } == {("Ding", "Chou"), ("Wu", "Yin")}
    assert uncertainty["provenance"] == {
        "source": "swiss_ephemeris",
        "method": "swiss_ephemeris_solar_longitude_bisection_v1",
        "tolerance_seconds": 1.0,
        "error": None,
    }
    assert profile["pillars"]["year"] is None
    assert profile["pillars"]["month"] is None
    assert profile["birth"]["datetime_utc"] is None
    assert profile["birth"]["local_datetime"] is None
    assert profile["birth"]["representative_datetime_utc"] == local_noon_utc.isoformat()
    assert profile["debug"]["bazi_year"] is None
    assert profile["debug"]["solar_year_boundary"] is None
    assert profile["debug"]["month_solar_term"] is None
    assert profile["debug"]["representative_candidate_calculation"]["status"] == "non_authoritative_reference_only"
    for section in (
        "element_balance",
        "ten_gods",
        "analysis",
        "useful_elements",
        "auxiliary_stars",
        "palace_context",
        "life_areas",
        "classical_extras",
        "interpretation",
        "relationships",
        "timing",
    ):
        assert profile[section]["status"] == "withheld", section
        assert profile[section]["reason_code"] == "unknown_birth_time_solar_term_boundary", section
    assert profile["luck_pillars"] == []
    assert uncertainty["downstream"]["status"] == "withheld"


def test_unknown_time_local_date_crossing_jie_withholds_month_but_keeps_year():
    crossing = _term_payload(2000, next(term for term in SOLAR_TERMS if term["key"] == "jing_zhe"))["datetime_utc"]
    profile = _profile(
        datetime(crossing.year, crossing.month, crossing.day, 12, tzinfo=timezone.utc).isoformat(),
        hour_known=False,
    )
    uncertainty = profile["uncertainty"]["birth_time"]

    assert uncertainty["status"] == "uncertain"
    assert uncertainty["affected_pillars"] == ["month"]
    assert [item["key"] for item in uncertainty["boundaries"]] == ["jing_zhe"]
    assert {
        candidate["pillars"]["month"]["branch"]
        for candidate in uncertainty["candidates"]
    } == {"Yin", "Mao"}
    assert profile["pillars"]["year"] is not None
    assert profile["pillars"]["month"] is None
    assert profile["analysis"]["status"] == "withheld"
    assert profile["timing"]["status"] == "withheld"


def test_golden_fixture_hour_boundary_and_unknown_time():
    zi_hour = _profile("2000-01-01T00:30:00+00:00")
    chou_hour = _profile("2000-01-01T01:30:00+00:00")
    unknown = _profile("2000-01-01T12:00:00+00:00", hour_known=False)

    assert zi_hour["pillars"]["hour"]["branch"] == "Zi"
    assert chou_hour["pillars"]["hour"]["branch"] == "Chou"
    assert unknown["pillars"]["hour"] is None
    assert any("Birth time is unknown" in warning for warning in unknown["debug"]["warnings"])


def test_golden_fixture_true_solar_hour_flip():
    civil = _profile("2000-01-01T00:30:00+00:00", longitude=45.0)
    true_solar = _profile("2000-01-01T00:30:00+00:00", longitude=45.0, use_true_solar_time=True)

    assert civil["debug"]["hour_pillar_comparison"]["mode"] == "civil_local_time"
    assert true_solar["debug"]["hour_pillar_comparison"]["mode"] == "true_solar_time"
    assert true_solar["debug"]["hour_pillar_comparison"]["changed"] is True
    assert civil["debug"]["hour_pillar_comparison"]["civil"]["branch"] == "Zi"
    assert true_solar["pillars"]["hour"]["branch"] == "Yin"


def test_phase_3_true_solar_day_boundary_can_change_day_pillar():
    civil = _profile("2000-01-01T00:30:00+00:00", longitude=-45.0)
    solar_day = _profile(
        "2000-01-01T00:30:00+00:00",
        longitude=-45.0,
        day_boundary_rule="true_solar_midnight",
    )

    comparison = solar_day["debug"]["day_pillar_comparison"]
    assert comparison["rule"] == "true_solar_midnight"
    assert comparison["true_solar_day_boundary_applied"] is True
    assert comparison["changed"] is True
    assert solar_day["birth"]["day_basis"]["basis"] == "true_solar_time"
    assert solar_day["pillars"]["day"]["stem"] != civil["pillars"]["day"]["stem"]


def test_phase_3_late_zi_next_day_variant_advances_day_pillar():
    standard = _profile("2000-01-01T23:30:00+00:00")
    late_zi = _profile("2000-01-01T23:30:00+00:00", hour_pillar_variant="late_zi_next_day")

    assert standard["debug"]["day_pillar_comparison"]["late_zi_next_day_applied"] is False
    assert late_zi["debug"]["day_pillar_comparison"]["late_zi_next_day_applied"] is True
    assert late_zi["birth"]["day_basis"]["date"] == "2000-01-02"
    assert late_zi["pillars"]["day"]["stem"] != standard["pillars"]["day"]["stem"]


def test_late_zi_uses_selected_true_solar_clock_when_civil_time_is_22():
    civil_clock = _profile(
        "2000-04-15T22:30:00+00:00",
        longitude=15.0,
        hour_pillar_variant="late_zi_next_day",
    )
    solar_clock = _profile(
        "2000-04-15T22:30:00+00:00",
        longitude=15.0,
        use_true_solar_time=True,
        hour_pillar_variant="late_zi_next_day",
    )

    comparison = solar_clock["debug"]["day_pillar_comparison"]
    assert solar_clock["pillars"]["hour"]["branch"] == "Zi"
    assert comparison["late_zi_clock_basis"] == "true_solar_time"
    assert comparison["late_zi_next_day_applied"] is True
    assert solar_clock["birth"]["day_basis"]["date"] == "2000-04-16"
    assert solar_clock["pillars"]["day"]["stem"] != civil_clock["pillars"]["day"]["stem"]


def test_late_zi_does_not_advance_when_selected_true_solar_clock_is_22():
    standard = _profile(
        "2000-04-15T23:30:00+00:00",
        longitude=-15.0,
        use_true_solar_time=True,
    )
    late_zi = _profile(
        "2000-04-15T23:30:00+00:00",
        longitude=-15.0,
        use_true_solar_time=True,
        hour_pillar_variant="late_zi_next_day",
    )

    comparison = late_zi["debug"]["day_pillar_comparison"]
    assert late_zi["pillars"]["hour"]["branch"] == "Hai"
    assert comparison["late_zi_clock_basis"] == "true_solar_time"
    assert comparison["late_zi_next_day_applied"] is False
    assert late_zi["birth"]["day_basis"]["date"] == "2000-04-15"
    assert late_zi["pillars"]["day"] == standard["pillars"]["day"]


def test_phase_3_solar_term_fixture_payload_covers_all_jie_terms():
    terms = [_term_payload(2000, term) for term in SOLAR_TERMS]

    assert [term["key"] for term in terms] == [term["key"] for term in SOLAR_TERMS]
    assert len(terms) == 12
    assert {term["source"] for term in terms} == {"swiss_ephemeris"}
    assert {term["calculation_status"] for term in terms} == {"authoritative"}
    assert {term["method"] for term in terms} == {"swiss_ephemeris_solar_longitude_bisection_v1"}
    assert {term["tolerance_seconds"] for term in terms} == {1.0}
    assert all(terms[index]["datetime_utc"] < terms[index + 1]["datetime_utc"] for index in range(len(terms) - 1))


def test_solar_term_unavailability_raises_typed_uncached_error_instead_of_approximation(monkeypatch):
    bazi_module._term_crossing_utc.cache_clear()
    monkeypatch.setattr(bazi_module, "swe", None)

    with pytest.raises(bazi_module.SolarTermCalculationError) as caught:
        _term_payload(2000, next(term for term in SOLAR_TERMS if term["key"] == "li_chun"))

    assert caught.value.to_payload() == {
        "code": "solar_term_calculation_unavailable",
        "status": "unavailable",
        "reason": "swiss_ephemeris_unavailable",
        "year": 2000,
        "term_key": "li_chun",
        "source": "swiss_ephemeris",
        "method": "swiss_ephemeris_solar_longitude_bisection_v1",
        "tolerance_seconds": 1.0,
        "retryable": True,
    }
    assert bazi_module._term_crossing_utc.cache_info().currsize == 0
    bazi_module._term_crossing_utc.cache_clear()


def test_solar_term_solver_failure_is_explicit_and_never_returns_fixed_midnight(monkeypatch):
    bazi_module._term_crossing_utc.cache_clear()
    monkeypatch.setattr(bazi_module, "swe", object())

    def _failed_longitude(_value):
        raise RuntimeError("transient ephemeris failure")

    monkeypatch.setattr(bazi_module, "_solar_longitude", _failed_longitude)
    with pytest.raises(bazi_module.SolarTermCalculationError) as caught:
        _term_payload(2000, next(term for term in SOLAR_TERMS if term["key"] == "jing_zhe"))

    assert caught.value.reason == "solar_longitude_solver_failed"
    assert bazi_module._term_crossing_utc.cache_info().currsize == 0
    bazi_module._term_crossing_utc.cache_clear()


def test_golden_fixture_luck_direction_rule_seed():
    yang_year_male = _profile(
        "2000-02-06T12:00:00+00:00",
        calculation_sex="male",
        include_luck_pillars=True,
    )
    yang_year_female = _profile(
        "2000-02-06T12:00:00+00:00",
        calculation_sex="female",
        include_luck_pillars=True,
    )

    assert yang_year_male["timing"]["direction"] == "forward"
    assert yang_year_female["timing"]["direction"] == "reverse"
    assert yang_year_male["timing"]["direction_rule_key"] == "year_stem_polarity"


def test_phase_3_luck_direction_variant_payload_uses_requested_source():
    variant = _profile(
        "2000-02-06T12:00:00+00:00",
        calculation_sex="male",
        include_luck_pillars=True,
        luck_direction_rule="day_stem_polarity",
    )

    assert variant["timing"]["direction_rule_key"] == "day_stem_polarity"
    assert variant["timing"]["polarity_source"] == "day_stem"
    assert variant["timing"]["debug"]["day_stem"] == variant["day_master"]["stem"]


def test_bazi_timing_rhythm_exposes_source_safe_flow_layers():
    profile = _profile(
        "2000-02-06T12:00:00+00:00",
        calculation_sex="male",
        include_luck_pillars=True,
    )

    rhythm = profile["timing"]["rhythm"]
    layers = {row["layer"]: row for row in rhythm["layers"]}

    assert rhythm["status"] == "source_based_preview"
    assert rhythm["method"] == "bazi_timing_rhythm_v1"
    assert rhythm["scope"] == "bazi_timing_not_branded_fortune_cycle"
    assert {"da_yun", "liu_nian", "flowing_month", "flowing_day", "flowing_hour"} <= set(layers)
    assert layers["da_yun"]["ten_god"]["stem"]
    assert layers["da_yun"]["layer_weighting"]["branch_weight"] > layers["da_yun"]["layer_weighting"]["stem_weight"]
    assert layers["liu_nian"]["layer_weighting"]["stem_weight"] > layers["liu_nian"]["layer_weighting"]["branch_weight"]
    assert {
        effect["kind"]
        for effect in layers["da_yun"]["interpretive_effects"]
    } <= {"activate", "rescue", "damage", "movement", "pressure", "arrival", "expose"}
    assert layers["liu_nian"]["growth_stage"]["status"] == "source_backed_preview"
    assert layers["flowing_month"]["source_strength"] == "computed_no_worked_example"
    assert layers["flowing_month"]["release_gate"] == "preview_only_until_worked_examples_curated"
    assert layers["flowing_month"]["calculation_basis"]["source_page_refs"]
    assert layers["flowing_month"]["growth_stage"]["page_ref"]["pages"] == [63]
    assert isinstance(layers["flowing_month"]["relationship_events"], list)
    assert rhythm["calibration"]["release_gate"] == "timing_assisted_finalization_blocked"
    assert rhythm["event_activation"]["method"] == "bazi_ying_qi_activation_v1"
    assert isinstance(rhythm["event_activation"]["primary_triggers"], list)
    assert layers["liu_nian"]["ying_qi"]["activation_role"] == "visible_trigger"
    assert layers["da_yun"]["ying_qi"]["activation_role"] == "field"
    assert "not Six-Star Divination" in " ".join(rhythm["limits"])
    assert {row["id"] for row in rhythm["source_basis"]} >= {
        "anchor.timing.luck_pillars",
        "anchor.timing.growth_stages",
    }
    assert profile["timing"]["flowing_month_pillar"]["period"]["solar_term"]["key"]
    assert profile["timing"]["flowing_day_pillar"]["period"]["local_date"] == "2026-05-11"
    assert profile["relationships"]["summary"]["flowing_month"] == 3
    assert profile["relationships"]["summary"]["flowing_day"] == 3
    assert profile["relationships"]["summary"]["flowing_hour"] == 2


def test_profile_exposes_classical_extras_body_balance_and_aux_timing():
    profile = _profile(
        "2000-02-06T12:00:00+00:00",
        calculation_sex="female",
        include_luck_pillars=True,
    )

    extras = profile["classical_extras"]
    assert extras["status"] == "source_based_preview"
    assert extras["tai_yuan"]["pillar"]["stem"]
    assert extras["ming_gong"]["status"] in {"school_variant_preview", "withheld"}
    assert len(extras["na_yin"]["pillars"]) >= 3
    assert all("na_yin" in row for row in extras["na_yin"]["pillars"])

    health = next(area for area in profile["life_areas"]["areas"] if area["id"] == "health_body")
    body = health["body_balance"]
    assert body["method"] == "element_presence_body_context_v2"
    assert body["element_presence_measure"] == "unweighted_presence_count"
    assert body["qi_strength_inferred"] is False
    assert body["hidden_stem_counts"]
    assert body["symbolic_body_correspondences"]
    assert body["element_excess"] == []
    assert body["element_deficiency"] == []
    assert "unweighted_presence_not_qi_strength" in body["limits"]

    markers = profile["auxiliary_stars"]["markers"]
    assert markers
    assert all(marker.get("source_page_refs") for marker in markers)
    assert any("flowing_activations" in marker for marker in markers)


def test_relationship_fixture_matrix_seed_covers_support_and_friction():
    pillars = {
        "year": {"stem": "Jia", "branch": "Zi", "branch_element": "Water"},
        "month": {"stem": "Ji", "branch": "Wu", "branch_element": "Fire"},
        "day": {"stem": "Bing", "branch": "Mao", "branch_element": "Wood"},
        "hour": {"stem": "Xin", "branch": "You", "branch_element": "Metal"},
    }

    report = analyze_relationships(pillars)
    event_types = {event["type"] for event in report["events"]}

    assert "stem_combination" in event_types
    assert "branch_clash" in event_types
    assert report["source_confidence"]


def test_phase_5_relationship_fixture_matrix_covers_every_event_type():
    cases = [
        ("stem_combination", _relationship_fixture_pillars(["Zi", "Yin", "Chen", "Wu"], stems=["Jia", "Ji", "Bing", "Geng"])),
        ("branch_combination", _relationship_fixture_pillars(["Zi", "Chou", "Chen", "Wu"])),
        ("branch_clash", _relationship_fixture_pillars(["Zi", "Wu", "Chen", "Shen"])),
        ("branch_harm", _relationship_fixture_pillars(["Zi", "Wei", "Chen", "Shen"])),
        ("branch_destruction", _relationship_fixture_pillars(["Zi", "You", "Chen", "Shen"])),
        ("branch_punishment", _relationship_fixture_pillars(["Yin", "Si", "Chen", "Wu"])),
        ("self_punishment", _relationship_fixture_pillars(["Chen", "Chen", "Zi", "Wu"])),
        ("three_harmony_combination", _relationship_fixture_pillars(["Yin", "Wu", "Xu", "Zi"])),
        ("seasonal_combination", _relationship_fixture_pillars(["Yin", "Mao", "Chen", "Zi"])),
        ("branch_cross", _relationship_fixture_pillars(["Zi", "Wu", "You", "Mao"])),
    ]

    for expected_type, pillars in cases:
        report = analyze_relationships(pillars)
        event_types = {event["type"] for event in report["events"]}
        assert expected_type in event_types, f"{expected_type} missing from {event_types}"


def test_uncivilized_punishment_is_zi_mao_and_not_mao_si():
    zi_mao = analyze_relationships({
        "year": {"stem": "Jia", "branch": "Zi", "branch_element": "Water"},
        "month": {"stem": "Bing", "branch": "Mao", "branch_element": "Wood"},
    })
    mao_si = analyze_relationships({
        "year": {"stem": "Jia", "branch": "Mao", "branch_element": "Wood"},
        "month": {"stem": "Bing", "branch": "Si", "branch_element": "Fire"},
    })

    zi_mao_punishments = [
        event for event in zi_mao["events"]
        if event["type"] == "branch_punishment"
    ]
    mao_si_punishments = [
        event for event in mao_si["events"]
        if event["type"] == "branch_punishment"
    ]
    assert [event["label"] for event in zi_mao_punishments] == ["Zi-Mao uncivilized punishment"]
    assert mao_si_punishments == []


def test_annual_duplicate_activates_natal_self_punishment():
    pillars = _relationship_fixture_pillars(["Zi", "Yin", "Chen", "Wu"])
    report = analyze_relationships(
        pillars,
        {
            "annual_pillar": {
                "stem": "Ren",
                "branch": "Chen",
                "stem_element": "Water",
                "branch_element": "Earth",
                "hidden_stems": [],
            }
        },
    )

    events = [
        event for event in report["events"]
        if event["type"] == "self_punishment" and event["scope"] == "annual"
    ]
    assert len(events) == 1
    assert events[0]["label"] == "Chen self-punishment"
    assert any(point.get("layer") == "annual" for point in events[0]["points"])


def test_day_master_strength_prioritizes_spring_season_and_root():
    pillars = {
        "year": {
            "stem_element": "Water",
            "branch": "Hai",
            "branch_element": "Water",
            "hidden_stems": [{"element": "Water"}],
        },
        "month": {
            "stem_element": "Wood",
            "branch": "Mao",
            "branch_element": "Wood",
            "hidden_stems": [{"element": "Wood"}],
        },
        "day": {
            "stem_element": "Wood",
            "branch": "Yin",
            "branch_element": "Wood",
            "hidden_stems": [{"element": "Wood"}, {"element": "Fire"}, {"element": "Earth"}],
        },
        "hour": {
            "stem_element": "Water",
            "branch": "Hai",
            "branch_element": "Water",
            "hidden_stems": [{"element": "Water"}, {"element": "Wood"}],
        },
    }

    result = _strength_evidence(0, pillars, {"total": {}})

    assert result["label"] == "strong"
    assert result["method"] == "season_root_formation_v2"
    assert result["model"]["model_id"] == "augier_school_heuristic_70_25_5_v1"
    assert result["model"]["model_status"] == "product_defined_uncalibrated"
    assert result["model"]["parameter_provenance"]["pillar_root_weights"]["status"] == "product_defined"
    assert result["model"]["earth_reconciliation_policy"]["status"] == "school_ambiguity_product_policy"
    assert result["model"]["season"]["state"] == "prosperous"
    assert result["model"]["root"]["normal_root"] is True
    assert result["model"]["root"]["secret_root"] is True
    assert result["model"]["root"]["root_grade"] in {"normal_root", "normal_and_secret_root"}
    assert any(row["relationship"] == "same_element_root" for row in result["model"]["root"]["root_details"])
    assert {43, 44, 45, 46, 66} <= set(result["model"]["source_page_refs"][0]["pages"])
    assert {"normal root", "secret root", "hidden stems"} <= set(result["model"]["source_keywords"])
    assert any("normal root" in item for item in result["model"]["root"]["evidence"])
    assert any("secret root" in item for item in result["model"]["root"]["evidence"])


def test_day_master_strength_can_stay_weak_despite_some_counts_when_out_of_season():
    pillars = {
        "year": {
            "stem_element": "Fire",
            "branch": "Wu",
            "branch_element": "Fire",
            "hidden_stems": [{"element": "Fire"}, {"element": "Earth"}],
        },
        "month": {
            "stem_element": "Metal",
            "branch": "You",
            "branch_element": "Metal",
            "hidden_stems": [{"element": "Metal"}],
        },
        "day": {
            "stem_element": "Wood",
            "branch": "Wu",
            "branch_element": "Fire",
            "hidden_stems": [{"element": "Fire"}, {"element": "Earth"}],
        },
        "hour": {
            "stem_element": "Earth",
            "branch": "Wei",
            "branch_element": "Earth",
            "hidden_stems": [{"element": "Earth"}, {"element": "Fire"}],
        },
    }

    result = _strength_evidence(0, pillars, {"total": {}})

    assert result["label"] == "weak"
    assert result["model"]["season"]["season"] == "Autumn"
    assert result["model"]["season"]["state"] == "dead"
    assert result["model"]["root"]["normal_root"] is False


def test_element_presence_inventory_is_not_qi_strength_and_placement_changes_the_result():
    spring_month = {
        "year": {
            "stem_element": "Metal",
            "branch": "You",
            "branch_element": "Metal",
            "hidden_stems": [{"element": "Metal", "rank": 1}],
        },
        "month": {
            "stem_element": "Fire",
            "branch": "Mao",
            "branch_element": "Wood",
            "hidden_stems": [{"element": "Wood", "rank": 1}],
        },
        "day": {
            "stem_element": "Wood",
            "branch": "Zi",
            "branch_element": "Water",
            "hidden_stems": [{"element": "Water", "rank": 1}],
        },
        "hour": {
            "stem_element": "Earth",
            "branch": "Wu",
            "branch_element": "Fire",
            "hidden_stems": [
                {"element": "Fire", "rank": 1},
                {"element": "Earth", "rank": 2},
            ],
        },
    }
    autumn_month = {
        **spring_month,
        "year": spring_month["month"],
        "month": spring_month["year"],
    }

    spring_presence = _element_balance(spring_month)
    autumn_presence = _element_balance(autumn_month)
    spring_strength = _strength_evidence(0, spring_month, spring_presence)
    autumn_strength = _strength_evidence(0, autumn_month, autumn_presence)

    assert spring_presence["model_id"] == "element_presence_inventory_v1"
    assert spring_presence["measure"] == "unweighted_presence_count"
    assert spring_presence["semantics"]["is_qi_strength"] is False
    assert spring_presence["counts"] == spring_presence["total"]
    assert spring_presence["branch_bodies"] == spring_presence["branches"]
    assert spring_presence["elements"]["Wood"] == {
        "visible_stem_count": 1,
        "branch_body_count": 1,
        "hidden_stem_count": 1,
        "presence_count": 3,
        "present": True,
    }
    assert spring_presence["counts"] == autumn_presence["counts"]

    assert spring_strength["label"] == "strong"
    assert autumn_strength["label"] == "weak"
    assert spring_strength["measure"] == "day_master_seasonal_rooted_qi_strength"
    assert spring_strength["scope"] == {"subject": "day_master", "element": "Wood"}
    separation = spring_strength["model"]["count_strength_separation"]
    assert separation["element_presence_model_id"] == "element_presence_inventory_v1"
    assert separation["presence_counts_used_in_qi_score"] is False
    assert separation["qi_strength_inputs"] == [
        "month_season",
        "hidden_stem_roots",
        "visible_and_branch_formation",
    ]
    assert spring_strength["presence_counts"] == spring_presence["counts"]


def test_root_grade_evidence_marks_storage_roots_and_three_gain_layers():
    pillars = {
        "year": {
            "stem": "Geng",
            "stem_element": "Metal",
            "branch": "Shen",
            "branch_element": "Metal",
            "hidden_stems": [
                {"key": "Geng", "element": "Metal", "rank": 1},
                {"key": "Ren", "element": "Water", "rank": 2},
                {"key": "Wu", "element": "Earth", "rank": 3},
            ],
        },
        "month": {
            "stem": "Xin",
            "stem_element": "Metal",
            "branch": "You",
            "branch_element": "Metal",
            "hidden_stems": [{"key": "Xin", "element": "Metal", "rank": 1}],
        },
        "day": {
            "stem": "Ding",
            "stem_element": "Fire",
            "branch": "Xu",
            "branch_element": "Earth",
            "hidden_stems": [
                {"key": "Wu", "element": "Earth", "rank": 1},
                {"key": "Xin", "element": "Metal", "rank": 2},
                {"key": "Ding", "element": "Fire", "rank": 3},
            ],
        },
        "hour": {
            "stem": "Ji",
            "stem_element": "Earth",
            "branch": "Chou",
            "branch_element": "Earth",
            "hidden_stems": [
                {"key": "Ji", "element": "Earth", "rank": 1},
                {"key": "Gui", "element": "Water", "rank": 2},
                {"key": "Xin", "element": "Metal", "rank": 3},
            ],
        },
    }

    result = _strength_evidence(3, pillars, {"total": {}})
    root = result["model"]["root"]
    evidence = result["model"]["root_grade_evidence"]

    assert evidence["method"] == "root_grade_evidence_v1"
    assert evidence["de_ling"]["status"] == "lost"
    assert evidence["de_di"]["status"] == "partial"
    assert evidence["de_di"]["root_grade"] == root["root_grade"]
    assert any(
        row["pillar"] == "day"
        and row["stem"] == "Ding"
        and row["rank"] == 3
        and row["root_class"] == "storage_root"
        for row in root["root_details"]
    )
    assert any("hidden-stem rank 3" in row for row in evidence["evidence_rows"])


def test_resource_roots_do_not_replace_real_day_master_root():
    pillars = {
        "year": {
            "stem": "Gui",
            "stem_element": "Water",
            "branch": "Zi",
            "branch_element": "Water",
            "hidden_stems": [{"key": "Gui", "element": "Water", "rank": 1}],
        },
        "month": {
            "stem": "Ren",
            "stem_element": "Water",
            "branch": "Zi",
            "branch_element": "Water",
            "hidden_stems": [{"key": "Gui", "element": "Water", "rank": 1}],
        },
        "day": {
            "stem": "Jia",
            "stem_element": "Wood",
            "branch": "Zi",
            "branch_element": "Water",
            "hidden_stems": [{"key": "Gui", "element": "Water", "rank": 1}],
        },
        "hour": {
            "stem": "Geng",
            "stem_element": "Metal",
            "branch": "Shen",
            "branch_element": "Metal",
            "hidden_stems": [
                {"key": "Geng", "element": "Metal", "rank": 1},
                {"key": "Ren", "element": "Water", "rank": 2},
                {"key": "Wu", "element": "Earth", "rank": 3},
            ],
        },
    }

    result = _strength_evidence(0, pillars, {"total": {}})
    root = result["model"]["root"]
    evidence = result["model"]["root_grade_evidence"]

    assert root["same_element_root_score"] == 0
    assert root["resource_root_score"] > 0
    assert evidence["de_di"]["status"] == "resource_only"
    assert evidence["resource_substitute_limit"]["active"] is True
    assert "Resource does not fully replace a real root" in evidence["resource_substitute_limit"]["note"]


def test_useful_elements_report_presence_timing_and_relationship_pressure():
    pillars = {
        "year": {
            "stem": "Ren",
            "stem_element": "Water",
            "branch": "Hai",
            "branch_element": "Water",
            "hidden_stems": [{"key": "Ren", "element": "Water"}, {"key": "Jia", "element": "Wood"}],
        },
        "month": {
            "stem": "Yi",
            "stem_element": "Wood",
            "branch": "Mao",
            "branch_element": "Wood",
            "hidden_stems": [{"key": "Yi", "element": "Wood"}],
        },
        "day": {
            "stem": "Jia",
            "stem_element": "Wood",
            "branch": "Mao",
            "branch_element": "Wood",
            "hidden_stems": [{"key": "Yi", "element": "Wood"}],
        },
        "hour": {
            "stem": "Gui",
            "stem_element": "Water",
            "branch": "Hai",
            "branch_element": "Water",
            "hidden_stems": [{"key": "Ren", "element": "Water"}, {"key": "Jia", "element": "Wood"}],
        },
    }
    relationships = {
        "events": [
            {
                "type": "branch_clash",
                "label": "Chen-Xu clash",
                "scope": "natal",
                "scope_label": "Natal",
                "intensity": "direct",
                "symbols": ["Chen", "Xu"],
                "points": [
                    {"pillar": "month", "branch": "Chen"},
                    {"pillar": "day", "branch": "Xu"},
                ],
                "affected_palaces": ["Month", "Day"],
            }
        ]
    }
    timing = {
        "annual_pillar": {
            "stem": "Bing",
            "stem_element": "Fire",
            "branch": "Wu",
            "branch_element": "Fire",
            "hidden_stems": [{"key": "Ding", "element": "Fire"}],
        }
    }

    result = build_useful_element_recommendations(
        day_stem_index=0,
        analysis={
            "strength": "strong",
            "support_score": 7,
            "pressure_score": 2,
            "strength_model": {
                "confidence": "medium",
                "season": {"season": "Spring", "month_branch": "Mao"},
            },
        },
        balance={"total": {"Wood": 7, "Fire": 0, "Earth": 0, "Metal": 0, "Water": 5}},
        pillars=pillars,
        relationships=relationships,
        timing=timing,
    )

    earth = next(item for item in result["favorable"] if item["element"] == "Earth")
    fire = next(item for item in result["favorable"] if item["element"] == "Fire")

    assert earth["integrity"]["availability"] == "missing"
    assert earth["integrity"]["pressure"] == "pressured"
    assert earth["integrity"]["event_impacts"][0]["label"] == "Chen-Xu clash"
    assert fire["integrity"]["availability"] == "timing_supported"
    assert result["integrity_summary"]["favorable_pressured"] == 1
    assert any(item["element"] == "Earth" for item in result["element_integrity"])
    assert result["climate_adjustment"]["status"] == "source_based_preview"
    assert result["climate_adjustment"]["season"] == "Spring"
    assert any(item["element"] == "Metal" for item in result["climate_adjustment"]["recommendations"])
    earth_damage = next(item for item in result["damage_assessment"] if item["element"] == "Earth")
    assert earth_damage["status"] == "damaged"
    assert result["damage_summary"]["damaged"] == 1
    assert result["useful_god"]["final_status"] == "withheld"
    assert result["useful_god"]["candidate_status"] == "candidate_preview"
    assert result["useful_god"]["decision_path"] == "yong_shen.damage_withheld"
    assert "damage_pattern_not_source_backed" in result["useful_god"]["blocking_reasons"]
    assert result["useful_god"]["evidence"]["strength"]["label"] == "strong"
    assert "local.destiny_code_favorable_elements" in result["useful_god"]["source_ids"]
    assert result["special_structure_screen"]["status"] in {"candidate_flags", "screened_not_classified"}
    assert result["element_presence"]["is_qi_strength"] is False
    assert earth["presence_measure"] == "unweighted_presence_count"
    assert earth["qi_strength_status"] == "not_evaluated"


def _useful_result(
    *,
    day_stem_index=0,
    strength="strong",
    support_score=7,
    pressure_score=2,
    season="Spring",
    month_branch="Chen",
    balance=None,
    pillars=None,
    relationships=None,
    timing=None,
):
    return build_useful_element_recommendations(
        day_stem_index=day_stem_index,
        analysis={
            "strength": strength,
            "support_score": support_score,
            "pressure_score": pressure_score,
            "strength_model": {"confidence": "high", "season": {"season": season, "month_branch": month_branch}},
        },
        balance={"total": balance or {"Wood": 2, "Fire": 1, "Earth": 2, "Metal": 2, "Water": 2}},
        pillars=pillars or {},
        relationships=relationships or {"events": []},
        timing=timing or {"luck_pillars_enabled": False},
    )


def test_day_master_reference_is_not_companion_presence_or_candidate_qi():
    result = _useful_result(
        strength="weak",
        support_score=2,
        pressure_score=7,
        season="Autumn",
        month_branch="You",
        balance={"Wood": 1, "Fire": 2, "Earth": 2, "Metal": 2, "Water": 2},
        pillars={
            "year": {"stem": "Geng", "stem_element": "Metal", "branch": "Shen", "branch_element": "Metal", "hidden_stems": [{"key": "Geng", "element": "Metal"}]},
            "month": {"stem": "Ren", "stem_element": "Water", "branch": "Zi", "branch_element": "Water", "hidden_stems": [{"key": "Gui", "element": "Water"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Si", "branch_element": "Fire", "hidden_stems": [{"key": "Bing", "element": "Fire"}]},
            "hour": {"stem": "Wu", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
        },
    )

    companion = next(row for row in result["favorable"] if row["role"] == "Companion")
    companion_check = next(row for row in result["damage_assessment"] if row["role"] == "Companion")

    assert companion["presence_count"] == 1
    assert companion["candidate_presence_count"] == 0
    assert companion["integrity"]["availability"] == "missing"
    assert companion["integrity"]["day_master_reference_excluded"] is True
    assert companion["integrity"]["day_master_reference_excluded_count"] == 1
    assert companion["integrity"]["qi_strength_status"] == "not_evaluated"
    assert companion["integrity"]["decision_authority"] == "none"
    assert companion_check["status"] == "presence_missing"
    assert companion_check["functional_state"] == "qi_strength_unresolved"
    assert result["useful_god"]["decision_path"] == "yong_shen.weak_support"
    assert "candidate_qi_strength_unresolved" in result["useful_god"]["blocking_reasons"]


def test_count_only_dominance_cannot_change_the_yong_shen_decision_path():
    pillars = {
        "year": {"stem_element": "Water", "branch_element": "Water", "hidden_stems": [{"element": "Water"}]},
        "month": {"stem_element": "Metal", "branch_element": "Metal", "hidden_stems": [{"element": "Metal"}]},
        "day": {"stem_element": "Wood", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
        "hour": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
    }
    distributed = _useful_result(
        season="Unknown",
        month_branch="Unknown",
        balance={"Wood": 2, "Fire": 2, "Earth": 1, "Metal": 2, "Water": 2},
        pillars=pillars,
    )
    count_dominant = _useful_result(
        season="Unknown",
        month_branch="Unknown",
        balance={"Wood": 1, "Fire": 1, "Earth": 8, "Metal": 1, "Water": 1},
        pillars=pillars,
    )

    assert count_dominant["special_structure_screen"]["primary_structure"]["classification"] == "suspected_presence_only"
    assert count_dominant["special_structure_screen"]["presence_only_decision_authority"] == "none"
    assert distributed["useful_god"]["decision_path"] == count_dominant["useful_god"]["decision_path"] == "yong_shen.strong_balancing"
    assert distributed["useful_god"]["element"] == count_dominant["useful_god"]["element"] == "Earth"
    assert distributed["useful_god"]["role"] == count_dominant["useful_god"]["role"] == "Wealth"
    assert distributed["useful_god"]["blocking_reasons"] == count_dominant["useful_god"]["blocking_reasons"]
    assert "special_structure_review_required" not in count_dominant["useful_god"]["blocking_reasons"]
    assert "candidate_qi_strength_unresolved" in count_dominant["useful_god"]["blocking_reasons"]


def test_narrative_only_strong_balancing_family_stays_candidate_only():
    pillars = {
        "year": {"stem_element": "Water", "branch_element": "Water", "hidden_stems": [{"element": "Water"}]},
        "month": {"stem_element": "Earth", "branch_element": "Earth", "hidden_stems": [{"element": "Earth"}]},
        "day": {"stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
        "hour": {"stem_element": "Fire", "branch_element": "Metal", "hidden_stems": [{"element": "Metal"}]},
    }

    result = build_useful_element_recommendations(
        day_stem_index=0,
        analysis={
            "strength": "strong",
            "support_score": 7,
            "pressure_score": 2,
            "strength_model": {"confidence": "high", "season": {"season": "Spring", "month_branch": "Chen"}},
        },
        balance={"total": {"Wood": 2, "Fire": 1, "Earth": 2, "Metal": 2, "Water": 2}},
        pillars=pillars,
        relationships={"events": []},
        timing={"luck_pillars_enabled": False},
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.strong_balancing"
    assert useful_god["role"] == "Wealth"
    assert useful_god["fixture_ids"]
    assert useful_god["evidence"]["fixture_gate"]["released"] is False
    assert "family_fixture_gate_blocked" in useful_god["blocking_reasons"]


def test_narrative_only_weak_support_family_stays_candidate_only():
    pillars = {
        "year": {"stem_element": "Water", "branch_element": "Water", "hidden_stems": [{"element": "Water"}]},
        "month": {"stem_element": "Metal", "branch_element": "Metal", "hidden_stems": [{"element": "Metal"}]},
        "day": {"stem_element": "Wood", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
        "hour": {"stem_element": "Earth", "branch_element": "Earth", "hidden_stems": [{"element": "Earth"}]},
    }

    result = build_useful_element_recommendations(
        day_stem_index=0,
        analysis={
            "strength": "weak",
            "support_score": 2,
            "pressure_score": 7,
            "strength_model": {"confidence": "high", "season": {"season": "Spring", "month_branch": "Yin"}},
        },
        balance={"total": {"Wood": 1, "Fire": 2, "Earth": 2, "Metal": 2, "Water": 2}},
        pillars=pillars,
        relationships={"events": []},
        timing={"luck_pillars_enabled": False},
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.weak_support"
    assert useful_god["role"] == "Resource"
    assert useful_god["fixture_ids"]
    assert useful_god["evidence"]["fixture_gate"]["released"] is False
    assert "family_fixture_gate_blocked" in useful_god["blocking_reasons"]


def test_source_table_climate_override_stays_candidate_until_executable_fixtures():
    pillars = {
        "year": {"stem_element": "Water", "branch_element": "Fire", "hidden_stems": [{"element": "Water"}]},
        "month": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
        "day": {"stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
        "hour": {"stem_element": "Earth", "branch_element": "Metal", "hidden_stems": [{"element": "Earth"}]},
    }

    result = build_useful_element_recommendations(
        day_stem_index=0,
        analysis={
            "strength": "strong",
            "support_score": 7,
            "pressure_score": 2,
            "strength_model": {"confidence": "high", "season": {"season": "Summer", "month_branch": "Wu"}},
        },
        balance={"total": {"Wood": 2, "Fire": 2, "Earth": 2, "Metal": 1, "Water": 1}},
        pillars=pillars,
        relationships={"events": []},
        timing={"luck_pillars_enabled": False},
    )

    useful_god = result["useful_god"]
    climate = result["climate_adjustment"]
    primary = climate["recommendations"][0]

    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.climate_override"
    assert useful_god["element"] == "Water"
    assert useful_god["role"] == "regulating"
    assert useful_god["evidence"]["fixture_gate"]["released"] is False
    assert "family_fixture_gate_blocked" in useful_god["blocking_reasons"]
    assert climate["method"] == "day_stem_month_climate_regulating_v1"
    assert climate["source_table_status"] == "day_stem_month_rule"
    assert climate["day_stem"] == "Jia"
    assert primary["stem"] == "Gui"
    assert "lu_zhiji_fate_search:p240" in primary["source_page_refs"]


def test_climate_override_stays_withheld_when_regulating_element_is_absent():
    pillars = {
        "year": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
        "month": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
        "day": {"stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
        "hour": {"stem_element": "Earth", "branch_element": "Metal", "hidden_stems": [{"element": "Earth"}]},
    }

    result = build_useful_element_recommendations(
        day_stem_index=0,
        analysis={
            "strength": "strong",
            "support_score": 7,
            "pressure_score": 2,
            "strength_model": {"confidence": "high", "season": {"season": "Summer", "month_branch": "Wu"}},
        },
        balance={"total": {"Wood": 2, "Fire": 2, "Earth": 2, "Metal": 2, "Water": 0}},
        pillars=pillars,
        relationships={"events": []},
        timing={"luck_pillars_enabled": False},
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.climate_override"
    assert useful_god["element"] == "Water"
    assert result["climate_adjustment"]["source_table_status"] == "day_stem_month_rule"
    assert result["climate_adjustment"]["recommendations"][0]["stem"] == "Gui"
    assert "climate_candidate_absent" in useful_god["blocking_reasons"]


def test_bing_fire_hai_month_uses_day_stem_month_climate_table():
    result = build_useful_element_recommendations(
        day_stem_index=2,
        analysis={
            "strength": "weak",
            "support_score": 2,
            "pressure_score": 7,
            "strength_model": {"confidence": "high", "season": {"season": "Winter", "month_branch": "Hai"}},
        },
        balance={"total": {"Wood": 2, "Fire": 1, "Earth": 1, "Metal": 1, "Water": 4}},
        pillars={
            "year": {"stem": "Jia", "stem_element": "Wood", "branch": "Yin", "branch_element": "Wood", "hidden_stems": [{"key": "Jia", "element": "Wood"}]},
            "month": {"stem": "Ren", "stem_element": "Water", "branch": "Hai", "branch_element": "Water", "hidden_stems": [{"key": "Ren", "element": "Water"}, {"key": "Jia", "element": "Wood"}]},
            "day": {"stem": "Bing", "stem_element": "Fire", "branch": "Xu", "branch_element": "Earth", "hidden_stems": [{"key": "Ding", "element": "Fire"}]},
            "hour": {"stem": "Geng", "stem_element": "Metal", "branch": "Shen", "branch_element": "Metal", "hidden_stems": [{"key": "Geng", "element": "Metal"}]},
        },
        relationships={"events": []},
        timing={"luck_pillars_enabled": False},
    )

    climate = result["climate_adjustment"]
    primary = climate["recommendations"][0]

    assert climate["source_table_status"] == "day_stem_month_rule"
    assert climate["day_stem"] == "Bing"
    assert climate["month_branch"] == "Hai"
    assert primary["stem"] == "Jia"
    assert primary["condition"] == "Use Jia when Hai-month Water is excessive, transforming it through Wood."
    assert "transforming excessive Water through Wood" in primary["reason"]


def test_page_checked_tiao_hou_rows_match_exact_source_order_conditions_and_confidence():
    expected = {
        ("Yi", "Si"): [
            (
                "Gui",
                "primary",
                "Use Gui exclusively to regulate the urgent heat and dryness of Si month.",
            ),
        ],
        ("Yi", "Wei"): [
            ("Gui", "primary", "Gui moistens Earth and nourishes Yi Wood in Wei month."),
            (
                "Bing",
                "secondary",
                "Use Bing first when the pillars contain abundant Metal and Water in Wei month.",
            ),
        ],
        ("Bing", "Hai"): [
            ("Jia", "primary", "Use Jia when Hai-month Water is excessive, transforming it through Wood."),
            (
                "Wu",
                "conditional",
                "Use Wu when both the Bing Day Master and killing-water are strong in Hai month.",
            ),
            ("Geng", "conditional", "Use Geng only when Wood is excessive in Hai month."),
            ("Ren", "conditional", "Use Ren only when Fire is excessive in Hai month."),
        ],
        ("Geng", "Yin"): [
            ("Wu", "primary", "Use Wu when Fire is excessive in Yin month."),
            ("Jia", "secondary", "Use Jia when thick Earth risks burying Geng Metal in Yin month."),
            ("Ren", "conditional", "Use Ren when the branches form a Fire configuration in Yin month."),
            ("Bing", "conditional", "Use Bing to warm Geng Metal in Yin month."),
            (
                "Ding",
                "conditional",
                "Use Ding only as the source-listed additional Fire regulator after the Yin-month warming and structural checks.",
            ),
        ],
        ("Gui", "Si"): [
            ("Xin", "primary", "Use Xin as the source that sustains Gui Water in Si month."),
            ("Geng", "conditional", "Use Geng only when Xin is absent in Si month."),
        ],
        ("Gui", "Shen"): [
            (
                "Ding",
                "primary",
                "Use Ding to control Geng Metal in Shen month; Ding is most effective when rooted in Wu, Xu, or Wei.",
            ),
        ],
        ("Gui", "Chou"): [
            (
                "Bing",
                "primary",
                "Use Bing to thaw winter cold in Chou month; rooting in Yin, Si, Wu, Wei, or Xu strengthens it.",
            ),
            (
                "Ding",
                "secondary",
                "Ding follows Bing as the second source-listed regulator for Gui Water in Chou month.",
            ),
            (
                "Geng",
                "conditional",
                "Use Geng only when the branches form a Fire configuration in Chou month.",
            ),
            (
                "Xin",
                "conditional",
                "Use Xin only when the branches form a Fire configuration in Chou month.",
            ),
        ],
    }
    counts = {element: 0 for element in ("Wood", "Fire", "Earth", "Metal", "Water")}

    for (day_stem, month_branch), expected_rows in expected.items():
        table_rows = DAY_STEM_MONTH_CLIMATE_STEMS[day_stem][month_branch]
        assert [(row[0], row[2], row[3]) for row in table_rows] == expected_rows

        status, emitted_rows, _ = _source_climate_rows(
            day_stem_key=day_stem,
            month_branch=month_branch,
            counts=counts,
            pillars={},
            relationships={"events": []},
            timing={"luck_pillars_enabled": False},
        )
        assert status == "day_stem_month_rule"
        assert [(row["stem"], row["priority"], row["condition"]) for row in emitted_rows] == expected_rows
        assert all(row["needs_page_image_check"] is False for row in emitted_rows)
        assert all(
            all(tag["key"] != "needs_validation" for tag in row["source_confidence"])
            for row in emitted_rows
        )


def test_geng_metal_winter_needs_fire_before_ordinary_logic():
    result = build_useful_element_recommendations(
        day_stem_index=6,
        analysis={
            "strength": "strong",
            "support_score": 7,
            "pressure_score": 2,
            "strength_model": {"confidence": "high", "season": {"season": "Winter", "month_branch": "Zi"}},
        },
        balance={"total": {"Wood": 1, "Fire": 1, "Earth": 2, "Metal": 3, "Water": 3}},
        pillars={
            "year": {"stem": "Ding", "stem_element": "Fire", "branch": "Wu", "branch_element": "Fire", "hidden_stems": [{"key": "Ding", "element": "Fire"}]},
            "month": {"stem": "Bing", "stem_element": "Fire", "branch": "Zi", "branch_element": "Water", "hidden_stems": [{"key": "Gui", "element": "Water"}]},
            "day": {"stem": "Geng", "stem_element": "Metal", "branch": "Shen", "branch_element": "Metal", "hidden_stems": [{"key": "Geng", "element": "Metal"}]},
            "hour": {"stem": "Jia", "stem_element": "Wood", "branch": "Yin", "branch_element": "Wood", "hidden_stems": [{"key": "Jia", "element": "Wood"}]},
        },
        relationships={"events": []},
        timing={"luck_pillars_enabled": False},
    )

    useful_god = result["useful_god"]
    climate = result["climate_adjustment"]

    assert climate["source_table_status"] == "day_stem_month_rule"
    assert climate["recommendations"][0]["stem"] == "Ding"
    assert climate["recommendations"][0]["element"] == "Fire"
    assert useful_god["decision_path"] == "yong_shen.climate_override"
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["element"] == "Fire"
    assert "family_fixture_gate_blocked" in useful_god["blocking_reasons"]
    assert "before ordinary Wealth/Output logic" in climate["recommendations"][0]["reason"]


def test_full_tiao_hou_day_stem_month_table_is_available():
    stems = {stem["key"] for stem in STEMS}
    branches = {branch["key"] for branch in BRANCHES}

    assert stems <= set(DAY_STEM_MONTH_CLIMATE_STEMS)
    for stem in stems:
        assert branches <= set(DAY_STEM_MONTH_CLIMATE_STEMS[stem])
        for branch in branches:
            rows = DAY_STEM_MONTH_CLIMATE_STEMS[stem][branch]
            assert rows, f"{stem} {branch} has no regulating row"
            assert all(row[0] in stems for row in rows)


def test_full_tiao_hou_rows_emit_structured_conditions_taboos_and_row_refs():
    counts = {element: 0 for element in ("Wood", "Fire", "Earth", "Metal", "Water")}

    for stem in (stem_row["key"] for stem_row in STEMS):
        for branch in (branch_row["key"] for branch_row in BRANCHES):
            status, rows, page_refs = _source_climate_rows(
                day_stem_key=stem,
                month_branch=branch,
                counts=counts,
                pillars={},
                relationships={"events": []},
                timing={"luck_pillars_enabled": False},
            )
            assert status == "day_stem_month_rule"
            assert page_refs
            assert rows
            for row in rows:
                assert row["source_table_key"] == f"{stem}:{branch}:{row['stem']}:{row['priority']}"
                assert row["table_row_ref"] == {
                    "day_stem": stem,
                    "month_branch": branch,
                    "regulating_stem": row["stem"],
                    "priority": row["priority"],
                }
                assert row["condition"]
                assert row["taboos"]
                assert row["source_page_refs"]


def test_climate_rows_requiring_page_check_cannot_be_override_candidates(monkeypatch):
    monkeypatch.setattr(
        interpretation_module,
        "DAY_STEM_MONTH_CLIMATE_UNCERTAIN_ROWS",
        {("Jia", "Wu")},
    )
    status, rows, _ = _source_climate_rows(
        day_stem_key="Jia",
        month_branch="Wu",
        counts={"Wood": 2, "Fire": 2, "Earth": 2, "Metal": 1, "Water": 1},
        pillars={},
        relationships={"events": []},
        timing={"luck_pillars_enabled": False},
    )

    primary = next(row for row in rows if row["priority"] == "primary")
    assert status == "day_stem_month_rule"
    assert primary["needs_page_image_check"] is True
    assert primary["override_candidate"] is False

    result = _useful_result(
        season="Summer",
        month_branch="Wu",
        balance={"Wood": 2, "Fire": 2, "Earth": 2, "Metal": 1, "Water": 1},
    )
    assert result["useful_god"]["decision_path"] != "yong_shen.climate_override"


def test_presence_only_special_structure_cannot_block_climate_review():
    pillars = {
        "year": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
        "month": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
        "day": {"stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
        "hour": {"stem_element": "Water", "branch_element": "Fire", "hidden_stems": [{"element": "Water"}]},
    }

    result = build_useful_element_recommendations(
        day_stem_index=0,
        analysis={
            "strength": "strong",
            "support_score": 7,
            "pressure_score": 2,
            "strength_model": {"confidence": "high", "season": {"season": "Summer", "month_branch": "Wu"}},
        },
        balance={"total": {"Wood": 1, "Fire": 6, "Earth": 1, "Metal": 0, "Water": 1}},
        pillars=pillars,
        relationships={"events": []},
        timing={"luck_pillars_enabled": False},
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["decision_path"] == "yong_shen.climate_override"
    assert "special_structure_review_required" not in useful_god["blocking_reasons"]
    assert "candidate_qi_strength_unresolved" in useful_god["blocking_reasons"]
    assert result["special_structure_screen"]["structure_status"] in {"classified", "suspected"}


def test_month_command_structure_selection_keeps_counted_damage_as_presence_watch():
    clean = _useful_result(
        month_branch="You",
        balance={"Wood": 2, "Fire": 1, "Earth": 2, "Metal": 3, "Water": 1},
        pillars={
            "year": {"stem": "Gui", "stem_element": "Water", "branch": "Hai", "branch_element": "Water", "hidden_stems": [{"key": "Ren", "element": "Water"}]},
            "month": {"stem": "Xin", "stem_element": "Metal", "branch": "You", "branch_element": "Metal", "hidden_stems": [{"key": "Xin", "element": "Metal"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Yin", "branch_element": "Wood", "hidden_stems": [{"key": "Jia", "element": "Wood"}]},
            "hour": {"stem": "Wu", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
        },
    )
    damaged = _useful_result(
        month_branch="You",
        balance={"Wood": 2, "Fire": 2, "Earth": 1, "Metal": 3, "Water": 1},
        pillars={
            "year": {"stem": "Ding", "stem_element": "Fire", "branch": "Wu", "branch_element": "Fire", "hidden_stems": [{"key": "Ding", "element": "Fire"}]},
            "month": {"stem": "Xin", "stem_element": "Metal", "branch": "You", "branch_element": "Metal", "hidden_stems": [{"key": "Xin", "element": "Metal"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Yin", "branch_element": "Wood", "hidden_stems": [{"key": "Jia", "element": "Wood"}]},
            "hour": {"stem": "Bing", "stem_element": "Fire", "branch": "Si", "branch_element": "Fire", "hidden_stems": [{"key": "Bing", "element": "Fire"}]},
        },
    )

    assert clean["structure_selection"]["primary_structure"]["key"] == "direct_officer"
    assert clean["structure_selection"]["primary_structure"]["use_mode"] == "shun_yong"
    assert clean["structure_selection"]["primary_structure"]["status"] == "usable"
    assert clean["useful_god"]["evidence"]["structure_selection"]["primary_structure"]["label"] == "Direct Officer Structure"
    damaged_structure = damaged["structure_selection"]["primary_structure"]
    assert damaged_structure["status"] == "usable"
    assert damaged_structure["success_failure"] == "usable"
    assert damaged_structure["damage_patterns"] == []
    assert damaged_structure["damage_presence_watches"][0]["type"] == "officer_damaged_by_output"
    assert damaged_structure["damage_presence_watches"][0]["status"] == "presence_only_unclassified"
    assert damaged_structure["damage_presence_watches"][0]["qi_strength_status"] == "not_evaluated"
    assert damaged_structure["ten_god_count_semantics"]["is_qi_strength"] is False


def test_wealth_structure_does_not_count_visible_day_master_as_companion():
    clean_pillars = {
        "year": {"stem": "Ding", "stem_element": "Fire", "branch": "Wu", "branch_element": "Fire", "hidden_stems": [{"key": "Ding", "element": "Fire"}, {"key": "Ji", "element": "Earth"}]},
        "month": {"stem": "Ji", "stem_element": "Earth", "branch": "Chou", "branch_element": "Earth", "hidden_stems": [{"key": "Ji", "element": "Earth"}, {"key": "Gui", "element": "Water"}, {"key": "Xin", "element": "Metal"}]},
        "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Si", "branch_element": "Fire", "hidden_stems": [{"key": "Bing", "element": "Fire"}, {"key": "Wu", "element": "Earth"}, {"key": "Geng", "element": "Metal"}]},
        "hour": {"stem": "Bing", "stem_element": "Fire", "branch": "Wu", "branch_element": "Fire", "hidden_stems": [{"key": "Ding", "element": "Fire"}, {"key": "Ji", "element": "Earth"}]},
    }
    peer_pillars = {
        **clean_pillars,
        "year": {**clean_pillars["year"], "stem": "Yi", "stem_element": "Wood"},
    }

    clean = _useful_result(month_branch="Chou", pillars=clean_pillars)
    peer = _useful_result(month_branch="Chou", pillars=peer_pillars)
    clean_structure = clean["structure_selection"]["primary_structure"]
    peer_structure = peer["structure_selection"]["primary_structure"]

    assert clean_structure["key"] == "direct_wealth"
    assert clean_structure["ten_god_counts"].get("Companion", 0) == 0
    assert clean_structure["damage_patterns"] == []
    assert clean_structure["status"] == "usable"
    assert peer_structure["ten_god_counts"]["Rob Wealth"] >= 1
    assert peer_structure["status"] == "usable"
    assert peer_structure["damage_patterns"] == []
    assert peer_structure["damage_presence_watches"][0]["type"] == "wealth_damaged_by_companion"
    assert peer_structure["damage_presence_watches"][0]["decision_candidate"] is False


def test_qu_zhi_presence_ratio_stays_unclassified_and_withheld():
    result = _useful_result(
        strength="strong",
        support_score=9,
        pressure_score=1,
        month_branch="Mao",
        balance={"Wood": 8, "Fire": 1, "Earth": 0, "Metal": 0, "Water": 2},
        pillars={
            "year": {"stem": "Gui", "stem_element": "Water", "branch": "Hai", "branch_element": "Water", "hidden_stems": [{"key": "Ren", "element": "Water"}, {"key": "Jia", "element": "Wood"}]},
            "month": {"stem": "Yi", "stem_element": "Wood", "branch": "Mao", "branch_element": "Wood", "hidden_stems": [{"key": "Yi", "element": "Wood"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Wei", "branch_element": "Earth", "hidden_stems": [{"key": "Yi", "element": "Wood"}]},
            "hour": {"stem": "Jia", "stem_element": "Wood", "branch": "Yin", "branch_element": "Wood", "hidden_stems": [{"key": "Jia", "element": "Wood"}]},
        },
    )

    useful_god = result["useful_god"]
    structure = result["special_structure_screen"]["primary_structure"]

    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.strong_balancing"
    assert "special_structure_review_required" not in useful_god["blocking_reasons"]
    assert "candidate_qi_strength_unresolved" in useful_god["blocking_reasons"]
    assert structure["type"] == "qu_zhi"
    assert structure["classification"] == "suspected_presence_only"
    assert structure["presence_ratio"] > 0.7
    assert structure["ratio_measure"] == "unweighted_presence_count"
    assert structure["qi_strength_status"] == "not_evaluated"
    assert structure["decision_authority"] == "none"
    assert structure["structural_conditions_met"] is True


def test_cong_cai_presence_ratio_cannot_classify_follow_structure():
    result = _useful_result(
        strength="very weak",
        support_score=1,
        pressure_score=9,
        season="Late Season",
        month_branch="Chen",
        balance={"Wood": 1, "Fire": 1, "Earth": 8, "Metal": 1, "Water": 0},
        pillars={
            "year": {"stem": "Wu", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "month": {"stem": "Wu", "stem_element": "Earth", "branch": "Xu", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Si", "branch_element": "Fire", "hidden_stems": [{"key": "Bing", "element": "Fire"}]},
            "hour": {"stem": "Wu", "stem_element": "Earth", "branch": "Chou", "branch_element": "Earth", "hidden_stems": [{"key": "Ji", "element": "Earth"}]},
        },
    )

    useful_god = result["useful_god"]
    structure = result["special_structure_screen"]["primary_structure"]

    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.weak_support"
    assert "special_structure_review_required" not in useful_god["blocking_reasons"]
    assert "candidate_qi_strength_unresolved" in useful_god["blocking_reasons"]
    assert structure["role"] == "cong_cai"
    assert structure["element"] == "Earth"
    assert structure["classification"] == "suspected_presence_only"
    assert structure["structural_conditions_met"] is True
    assert structure["qi_strength_status"] == "not_evaluated"
    assert structure["decision_authority"] == "none"
    assert structure["false_follow_blockers"] == []


def test_false_follow_with_return_to_root_stays_withheld():
    result = _useful_result(
        strength="very weak",
        support_score=1,
        pressure_score=9,
        month_branch="Chen",
        balance={"Wood": 2, "Fire": 1, "Earth": 7, "Metal": 1, "Water": 0},
        pillars={
            "year": {"stem": "Wu", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "month": {"stem": "Ji", "stem_element": "Earth", "branch": "Xu", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Yin", "branch_element": "Wood", "hidden_stems": [{"key": "Jia", "element": "Wood"}]},
            "hour": {"stem": "Wu", "stem_element": "Earth", "branch": "Chou", "branch_element": "Earth", "hidden_stems": [{"key": "Ji", "element": "Earth"}]},
        },
    )

    useful_god = result["useful_god"]
    structure = result["special_structure_screen"]["primary_structure"]

    assert useful_god["final_status"] == "withheld"
    assert useful_god["decision_path"] == "yong_shen.special_structure_withheld"
    assert structure["classification"] == "false_follow"
    assert "day_master_root_present" in structure["false_follow_blockers"]


def test_hour_branch_secret_root_blocks_follow_structure():
    result = _useful_result(
        strength="weak",
        support_score=1,
        pressure_score=9,
        month_branch="Chen",
        balance={"Wood": 1, "Fire": 1, "Earth": 8, "Metal": 1, "Water": 0},
        pillars={
            "year": {"stem": "Wu", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "month": {"stem": "Ji", "stem_element": "Earth", "branch": "Xu", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Si", "branch_element": "Fire", "hidden_stems": [{"key": "Bing", "element": "Fire"}]},
            "hour": {"stem": "Wu", "stem_element": "Earth", "branch": "Hai", "branch_element": "Water", "hidden_stems": [{"key": "Ren", "element": "Water"}, {"key": "Jia", "element": "Wood"}]},
        },
    )

    structure = result["special_structure_screen"]["primary_structure"]
    assert structure["family"] == "follow_structure"
    assert structure["classification"] == "false_follow"
    assert "day_master_root_present" in structure["false_follow_blockers"]


def test_hua_qi_transformation_is_classified_but_final_is_gated():
    result = _useful_result(
        strength="strong",
        support_score=7,
        pressure_score=2,
        month_branch="Chen",
        balance={"Wood": 1, "Fire": 1, "Earth": 6, "Metal": 1, "Water": 1},
        pillars={
            "year": {"stem": "Bing", "stem_element": "Fire", "branch": "Xu", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "month": {"stem": "Ji", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Chou", "branch_element": "Earth", "hidden_stems": [{"key": "Ji", "element": "Earth"}]},
            "hour": {"stem": "Wu", "stem_element": "Earth", "branch": "Wei", "branch_element": "Earth", "hidden_stems": [{"key": "Ji", "element": "Earth"}]},
        },
    )

    useful_god = result["useful_god"]
    structure = result["special_structure_screen"]["primary_structure"]

    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.transformation_structure"
    assert useful_god["role"] == "hua_qi"
    assert useful_god["element"] == "Earth"
    assert structure["classification"] == "classified"
    assert structure["month_support"] is True
    assert "family_fixture_gate_blocked" in useful_god["blocking_reasons"]


def test_hour_branch_secret_root_blocks_stem_transformation():
    result = _useful_result(
        strength="strong",
        month_branch="Chen",
        balance={"Wood": 1, "Fire": 1, "Earth": 6, "Metal": 1, "Water": 1},
        pillars={
            "year": {"stem": "Bing", "stem_element": "Fire", "branch": "Xu", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "month": {"stem": "Ji", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Chou", "branch_element": "Earth", "hidden_stems": [{"key": "Ji", "element": "Earth"}]},
            "hour": {"stem": "Wu", "stem_element": "Earth", "branch": "Hai", "branch_element": "Water", "hidden_stems": [{"key": "Ren", "element": "Water"}, {"key": "Jia", "element": "Wood"}]},
        },
    )

    structure = result["special_structure_screen"]["primary_structure"]
    assert structure["family"] == "transformation_structure"
    assert structure["classification"] == "failed_transformation"
    assert "return_to_root_blocker" in structure["blockers"]


def test_wealth_presence_count_does_not_create_damage_or_reroute():
    result = _useful_result(
        balance={"Wood": 5, "Fire": 2, "Earth": 2, "Metal": 1, "Water": 1},
        pillars={
            "year": {"stem": "Yi", "stem_element": "Wood", "branch": "Mao", "branch_element": "Wood", "hidden_stems": [{"key": "Yi", "element": "Wood"}]},
            "month": {"stem": "Wu", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"key": "Wu", "element": "Earth"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch": "Yin", "branch_element": "Wood", "hidden_stems": [{"key": "Jia", "element": "Wood"}]},
            "hour": {"stem": "Bing", "stem_element": "Fire", "branch": "Si", "branch_element": "Fire", "hidden_stems": [{"key": "Bing", "element": "Fire"}]},
        },
    )

    useful_god = result["useful_god"]
    earth_damage = next(item for item in result["damage_assessment"] if item["element"] == "Earth")

    assert earth_damage["status"] == "presence_only"
    assert earth_damage["functional_state"] == "qi_strength_unresolved"
    assert earth_damage["source_pattern"] is False
    assert earth_damage["presence_damage_watch"]["watch_type"] == "wealth_damaged_by_companion"
    assert earth_damage["presence_damage_watch"]["status"] == "presence_only_unclassified"
    assert earth_damage["presence_damage_watch"]["qi_strength_status"] == "not_evaluated"
    assert result["damage_summary"]["source_pattern_damaged"] == 0
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] != "yong_shen.damaged_alternate"


def test_suspected_dominant_element_stays_withheld_until_classified():
    result = _useful_result(
        balance={"Wood": 2, "Fire": 5, "Earth": 1, "Metal": 1, "Water": 1},
        pillars={
            "year": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
            "month": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
            "day": {"stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
            "hour": {"stem_element": "Earth", "branch_element": "Metal", "hidden_stems": [{"element": "Water"}]},
        },
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.strong_balancing"
    assert "special_structure_review_required" not in useful_god["blocking_reasons"]
    assert "candidate_qi_strength_unresolved" in useful_god["blocking_reasons"]
    assert result["special_structure_screen"]["primary_structure"]["classification"] == "suspected_presence_only"


def test_suspected_follow_structure_stays_withheld_until_classified():
    result = _useful_result(
        strength="weak",
        support_score=2,
        pressure_score=7,
        season="Autumn",
        month_branch="You",
        balance={"Wood": 1, "Fire": 5, "Earth": 1, "Metal": 2, "Water": 1},
        pillars={
            "year": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
            "month": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
            "day": {"stem_element": "Wood", "branch": "Si", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
            "hour": {"stem_element": "Earth", "branch_element": "Metal", "hidden_stems": [{"element": "Water"}]},
        },
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.weak_support"
    assert "special_structure_review_required" not in useful_god["blocking_reasons"]
    assert "candidate_qi_strength_unresolved" in useful_god["blocking_reasons"]
    assert result["special_structure_screen"]["primary_structure"]["classification"] == "suspected_presence_only"


def test_failed_transformation_structure_stays_withheld():
    result = _useful_result(
        balance={"Wood": 1, "Fire": 1, "Earth": 4, "Metal": 1, "Water": 1},
        pillars={
            "year": {"stem": "Ji", "stem_element": "Earth", "branch_element": "Earth", "hidden_stems": [{"element": "Earth"}]},
            "month": {"stem": "Bing", "stem_element": "Fire", "branch": "Zi", "branch_element": "Water", "hidden_stems": [{"element": "Water"}]},
            "day": {"stem": "Jia", "stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
            "hour": {"stem": "Xin", "stem_element": "Metal", "branch_element": "Water", "hidden_stems": [{"element": "Water"}]},
        },
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.special_structure_withheld"
    assert "special_structure_review_required" in useful_god["blocking_reasons"]
    assert result["special_structure_screen"]["primary_structure"]["classification"] == "failed_transformation"
    assert result["special_structure_screen"]["primary_structure"]["month_support"] is False


def test_generic_relationship_damage_does_not_promote_presence_only_alternate():
    relationships = {
        "events": [
            {
                "type": "branch_clash",
                "label": "Chen-Xu clash",
                "scope": "natal",
                "scope_label": "Natal",
                "intensity": "direct",
                "symbols": ["Chen", "Xu"],
                "points": [
                    {"pillar": "month", "branch": "Chen"},
                    {"pillar": "day", "branch": "Xu"},
                ],
            }
        ]
    }
    result = _useful_result(
        balance={"Wood": 4, "Fire": 1, "Earth": 1, "Metal": 1, "Water": 1},
        pillars={
            "year": {"stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
            "month": {"stem_element": "Earth", "branch": "Chen", "branch_element": "Earth", "hidden_stems": [{"element": "Earth"}]},
            "day": {"stem_element": "Wood", "branch": "Xu", "branch_element": "Earth", "hidden_stems": [{"element": "Earth"}]},
            "hour": {"stem_element": "Fire", "branch_element": "Metal", "hidden_stems": [{"element": "Fire"}]},
        },
        relationships=relationships,
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.damage_withheld"
    assert useful_god["element"] == "Earth"
    assert useful_god["role"] == "Wealth"
    assert useful_god["evidence"]["damage"]["status"] == "damaged"
    assert useful_god["evidence"]["fixture_gate"]["released"] is False
    assert "damage_pattern_not_source_backed" in useful_god["blocking_reasons"]
    assert "primary_candidate_damaged" in useful_god["blocking_reasons"]
    assert "candidate_qi_strength_unresolved" in useful_god["blocking_reasons"]


def test_timing_assisted_family_remains_visible_but_blocked_from_final_yong_shen():
    result = _useful_result(
        balance={"Wood": 4, "Fire": 1, "Earth": 0, "Metal": 1, "Water": 1},
        pillars={
            "year": {"stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
            "month": {"stem_element": "Metal", "branch_element": "Metal", "hidden_stems": [{"element": "Metal"}]},
            "day": {"stem_element": "Wood", "branch_element": "Wood", "hidden_stems": [{"element": "Wood"}]},
            "hour": {"stem_element": "Fire", "branch_element": "Fire", "hidden_stems": [{"element": "Fire"}]},
        },
        timing={
            "luck_pillars_enabled": True,
            "active_luck_pillar": {"stem": "Wu", "stem_element": "Earth", "branch": "Chen", "branch_element": "Earth"},
            "annual_pillar": {"stem": "Bing", "stem_element": "Fire", "branch": "Wu", "branch_element": "Fire"},
        },
    )

    useful_god = result["useful_god"]
    assert useful_god["final_status"] == "withheld"
    assert useful_god["candidate_status"] == "candidate_preview"
    assert useful_god["decision_path"] == "yong_shen.timing_assisted"
    assert "timing_assisted_final_not_released" in useful_god["blocking_reasons"]
    assert "family_fixture_gate_blocked" in useful_god["blocking_reasons"]
    assert useful_god["evidence"]["fixture_gate"]["released"] is False
    assert useful_god["evidence"]["timing"]["status"] == "active"


def test_ten_god_profile_summarizes_five_factor_visibility_and_favorability():
    result = build_ten_god_profile(
        day_stem_index=0,
        ten_gods={
            "visible": [
                {"pillar": "year", "stem": "Wu", "factor": "Wealth", "god": "Direct Wealth"},
                {"pillar": "month", "stem": "Ding", "factor": "Output", "god": "Hurting Officer"},
            ],
            "hidden": [
                {"pillar": "day", "stem": "Wu", "rank": 1, "factor": "Wealth", "god": "Direct Wealth"},
                {"pillar": "hour", "stem": "Gui", "rank": 1, "factor": "Resource", "god": "Direct Resource"},
            ],
        },
        analysis={"strength": "strong"},
        useful_elements={
            "status": "provisional",
            "favorable": [{"role": "Wealth", "element": "Earth"}],
            "unfavorable": [{"role": "Resource", "element": "Water"}],
        },
    )

    wealth = next(item for item in result["factors"] if item["factor"] == "Wealth")
    resource = next(item for item in result["factors"] if item["factor"] == "Resource")

    assert result["method"] == "five_factor_profile_v1"
    assert wealth["element"] == "Earth"
    assert wealth["visible_count"] == 1
    assert wealth["hidden_count"] == 1
    assert wealth["layer_status"] == "surface_and_hidden"
    assert wealth["favorability"] == "favorable"
    assert wealth["functional_status"] == "favorable_candidate"
    assert wealth["status_label"] == "Useful"
    assert "favorable-element direction" in wealth["summary"]
    assert resource["favorability"] == "caution"
    assert resource["functional_status"] == "caution"
    assert wealth["layer_label"] == "visible and hidden"
    assert resource["layer_label"] == "hidden-stem placement"
    assert "rooted" not in resource["summary"]
    assert any("hidden-count presence alone does not establish rooted qi" in note for note in result["notes"])
    assert all("not counted as a separate visible Ten God" not in item for item in result["notes"])
    assert all("quantity is evidence, not a prediction" not in item for item in result["notes"])
    assert result["source_basis"][0]["id"] == "local.destiny_code_five_factors"


def test_ten_god_profile_replaces_generic_favorability_warning_with_computed_status():
    result = build_ten_god_profile(
        day_stem_index=0,
        ten_gods={
            "visible": [
                {"pillar": "year", "stem": "Wu", "factor": "Wealth", "god": "Direct Wealth"},
            ],
            "hidden": [],
        },
        analysis={"strength": "balanced"},
        useful_elements={
            "status": "withheld",
            "day_master_strength": "balanced",
            "favorable": [],
            "unfavorable": [],
            "useful_god": {
                "final_status": "withheld",
                "candidate_status": "withheld",
                "element": None,
                "role": None,
            },
        },
    )

    wealth = next(item for item in result["factors"] if item["factor"] == "Wealth")

    assert wealth["favorability"] == "unresolved"
    assert wealth["functional_status"] == "balanced_watch"
    assert wealth["status_label"] == "Topic"
    assert wealth["summary"] == (
        "Wealth (Earth) is visible on the stems, so it is easier to read as outward behavior or visible circumstance."
    )
    assert wealth["decision_basis"] == []
    assert "Final favorability needs strength" not in wealth["summary"]
    assert "topic evidence rather than a useful-element priority" not in wealth["summary"]
    assert all("role map, not a final ruling" not in item["summary"] for item in result["factors"])


def test_peach_blossom_profile_uses_day_branch_and_pressure_context():
    pillars = {
        "year": {"stem": "Xin", "branch": "You", "animal": "Rooster", "branch_element": "Metal"},
        "month": {"stem": "Yi", "branch": "Mao", "animal": "Rabbit", "branch_element": "Wood"},
        "day": {"stem": "Jia", "branch": "Shen", "animal": "Monkey", "branch_element": "Metal"},
        "hour": {"stem": "Bing", "branch": "Zi", "animal": "Rat", "branch_element": "Water"},
    }
    timing = {
        "annual_pillar": {"stem": "Yi", "branch": "You", "animal": "Rooster", "branch_element": "Metal"},
        "active_luck_pillar": {"stem": "Ding", "branch": "Wu", "animal": "Horse", "branch_element": "Fire"},
    }
    relationships = {
        "events": [
            {
                "type": "branch_clash",
                "label": "Mao-You clash",
                "scope": "natal",
                "scope_label": "Natal",
                "intensity": "direct",
                "symbols": ["Mao", "You"],
                "points": [
                    {"pillar": "month", "branch": "Mao"},
                    {"pillar": "year", "branch": "You"},
                ],
                "affected_palaces": ["Month", "Year"],
                "affected_domains": ["Family / career structure", "Ancestry / outer world"],
            }
        ]
    }

    result = build_auxiliary_stars(pillars=pillars, timing=timing, relationships=relationships)
    peach = result["peach_blossom"]

    assert peach["method"] == "day_branch_personal_peach_blossom_v1"
    assert peach["day_branch"] == "Shen"
    assert peach["target_branch"] == "You"
    assert peach["natal_count"] == 1
    assert peach["timing_count"] == 1
    assert peach["pressure"]["status"] == "pressured"
    assert peach["pressure"]["event_impacts"][0]["label"] == "Mao-You clash"
    assert peach["branch_family"]["present_count"] == 4
    assert peach["branch_family"]["all_four_present"] is True
    assert peach["source_basis"][0]["id"] == "local.destiny_code_peach_blossom"
    markers = {marker["id"]: marker for marker in result["markers"]}
    assert markers["peach_blossom"]["marker_state"] == "pressured"
    assert markers["general_star"]["target_summary"] == "Zi Rat"
    assert markers["general_star"]["marker_state"] == "active"
    assert markers["tian_yi"]["target_summary"] == "Chou Ox / Wei Goat"
    assert markers["tian_de"]["target_summary"] == "Shen Monkey"
    assert markers["yue_de"]["target_summary"] == "Jia"
    assert markers["yang_ren"]["marker_state"] == "pressured"
    assert markers["gan_lu"]["target_summary"] == "Yin Tiger"
    assert markers["hong_yan"]["marker_state"] == "active"
    assert markers["kong_wang"]["target_summary"] == "Wu Horse / Wei Goat"
    assert result["source_confidence"]
    assert all(item["key"] != "needs_validation" for item in result["source_confidence"])


def test_peach_blossom_pressure_can_be_mixed_when_support_and_challenge_touch_branch():
    pillars = {
        "year": {"stem": "Xin", "branch": "You", "animal": "Rooster", "branch_element": "Metal"},
        "month": {"stem": "Yi", "branch": "Mao", "animal": "Rabbit", "branch_element": "Wood"},
        "day": {"stem": "Jia", "branch": "Shen", "animal": "Monkey", "branch_element": "Metal"},
        "hour": {"stem": "Bing", "branch": "Zi", "animal": "Rat", "branch_element": "Water"},
    }
    relationships = {
        "events": [
            {"type": "branch_clash", "label": "Mao-You clash", "symbols": ["Mao", "You"], "points": []},
            {"type": "branch_combination", "label": "Chen-You combination", "symbols": ["Chen", "You"], "points": []},
        ]
    }

    peach = build_auxiliary_stars(pillars=pillars, relationships=relationships)["peach_blossom"]

    assert peach["target_branch"] == "You"
    assert peach["pressure"]["status"] == "mixed"
    assert peach["branch_family"]["present"] == ["Zi", "Mao", "You"]


def test_yi_day_stem_hong_yan_uses_wu_branch_from_local_source_table():
    pillars = {
        "year": {"stem": "Jia", "branch": "Wu", "animal": "Horse", "branch_element": "Fire"},
        "month": {"stem": "Bing", "branch": "Mao", "animal": "Rabbit", "branch_element": "Wood"},
        "day": {"stem": "Yi", "branch": "Chou", "animal": "Ox", "branch_element": "Earth"},
        "hour": {"stem": "Ding", "branch": "Hai", "animal": "Pig", "branch_element": "Water"},
    }

    markers = {
        marker["id"]: marker
        for marker in build_auxiliary_stars(pillars=pillars)["markers"]
    }

    assert markers["hong_yan"]["target_summary"] == "Wu Horse"
    assert markers["hong_yan"]["marker_state"] == "active"
    assert "Jia/Yi->Wu" in markers["hong_yan"]["formula"]
    assert markers["hong_yan"]["source_page_refs"] == ["lu_zhiji_fate_search:p133"]


def test_kui_gang_and_san_qi_auxiliary_markers_are_detected():
    pillars = {
        "year": {"stem": "Jia", "branch": "Zi", "animal": "Rat", "stem_element": "Wood", "branch_element": "Water"},
        "month": {"stem": "Wu", "branch": "Chen", "animal": "Dragon", "stem_element": "Earth", "branch_element": "Earth"},
        "day": {"stem": "Geng", "branch": "Chen", "animal": "Dragon", "stem_element": "Metal", "branch_element": "Earth"},
        "hour": {"stem": "Bing", "branch": "Yin", "animal": "Tiger", "stem_element": "Fire", "branch_element": "Wood"},
    }

    markers = {marker["id"]: marker for marker in build_auxiliary_stars(pillars=pillars)["markers"]}

    assert markers["kui_gang"]["marker_state"] == "active"
    assert markers["kui_gang"]["target_summary"] == "Geng-Chen / Geng-Xu / Ren-Chen / Wu-Xu"
    assert markers["kui_gang"]["timing_activation_status"] == "unsupported_with_current_sources"
    assert markers["san_qi"]["marker_state"] == "active"
    assert markers["san_qi"]["order_state"] == "ordered"
    assert markers["san_qi"]["target_summary"] == "Jia-Wu-Geng / Yi-Bing-Ding / Ren-Gui-Xin"


def test_kui_gang_does_not_promote_a_matching_timing_pillar_without_source_support():
    pillars = {
        "year": {"stem": "Jia", "branch": "Zi"},
        "month": {"stem": "Bing", "branch": "Yin"},
        "day": {"stem": "Yi", "branch": "Mao"},
        "hour": {"stem": "Ding", "branch": "Si"},
    }
    timing = {"annual_pillar": {"stem": "Geng", "branch": "Chen"}}

    markers = {
        marker["id"]: marker
        for marker in build_auxiliary_stars(pillars=pillars, timing=timing)["markers"]
    }

    assert markers["kui_gang"]["marker_state"] == "quiet"
    assert markers["kui_gang"]["timing_count"] == 0
    assert markers["kui_gang"]["timing_activation_status"] == "unsupported_with_current_sources"


def test_palace_context_maps_life_domains_and_relationship_events():
    pillars = {
        "year": {"stem": "Xin", "branch": "You", "animal": "Rooster", "stem_element": "Metal", "branch_element": "Metal"},
        "month": {"stem": "Yi", "branch": "Mao", "animal": "Rabbit", "stem_element": "Wood", "branch_element": "Wood"},
        "day": {"stem": "Jia", "branch": "Shen", "animal": "Monkey", "stem_element": "Wood", "branch_element": "Metal"},
        "hour": {"stem": "Bing", "branch": "Zi", "animal": "Rat", "stem_element": "Fire", "branch_element": "Water"},
    }
    relationships = {
        "events": [
            {
                "id": "natal:branch_clash:mao:you:year:month",
                "type": "branch_clash",
                "label": "Mao-You clash",
                "scope": "natal",
                "scope_label": "Natal",
                "intensity": "direct",
                "symbols": ["Mao", "You"],
                "points": [
                    {"pillar": "month", "pillar_label": "Month", "branch": "Mao"},
                    {"pillar": "year", "pillar_label": "Year", "branch": "You"},
                ],
            }
        ]
    }
    auxiliary_stars = build_auxiliary_stars(pillars=pillars, relationships=relationships)

    result = build_palace_context(
        pillars=pillars,
        relationships=relationships,
        auxiliary_stars=auxiliary_stars,
    )

    year = result["palaces"][0]
    month = result["palaces"][1]
    day = result["palaces"][2]

    assert result["method"] == "four_pillar_palace_context_v1"
    assert year["life_stage"] == "Childhood"
    assert year["relationship_event_count"] == 1
    assert year["relationship_events"][0]["placement_note"] == "adjacent palace contact"
    assert year["auxiliary_hits"][0]["label"] == "Peach Blossom"
    assert month["relationship_events"][0]["other_palaces"] == ["Year"]
    assert day["life_stage"] == "Adulthood"
    assert result["focus"]["primary_pillar"] == "year"
    assert result["source_basis"][0]["id"] == "local.four_pillars_palace_context"



def test_chinese_astrology_bazi_route_handles_unknown_birth_time():
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={"date": "2000-01-01", "location": "Greenwich, UK", "timezone": "UTC"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert data["birth"]["time_precision"] == "unknown"
    assert data["pillars"]["hour"] is None
    assert data["uncertainty"]["birth_time"]["status"] == "stable"
    assert data["uncertainty"]["birth_time"]["method"] == "unknown_local_civil_day_solar_term_candidates_v1"
    assert any("Birth time is unknown" in item for item in data["debug"]["warnings"])


def test_chinese_astrology_bazi_route_exposes_unknown_time_boundary_candidates_and_withholding():
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={"date": "2000-02-04", "timezone": "Asia/Shanghai"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    uncertainty = data["uncertainty"]["birth_time"]
    assert uncertainty["status"] == "uncertain"
    assert uncertainty["affected_pillars"] == ["year", "month"]
    assert len(uncertainty["candidates"]) == 2
    assert data["pillars"]["year"] is None
    assert data["pillars"]["month"] is None
    assert data["analysis"]["status"] == "withheld"
    assert data["useful_elements"]["status"] == "withheld"
    assert data["relationships"]["status"] == "withheld"
    assert data["life_areas"]["status"] == "withheld"
    assert data["interpretation"]["status"] == "withheld"
    assert data["timing"]["status"] == "withheld"
    assert data["luck_pillars"] == []


def test_chinese_astrology_bazi_route_returns_structured_503_when_solar_terms_are_unavailable(monkeypatch):
    client = app_module.app.test_client()
    bazi_module._term_crossing_utc.cache_clear()
    monkeypatch.setattr(bazi_module, "swe", None)

    response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={"date": "2000-01-01", "time": "12:00", "timezone": "UTC"},
    )
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["success"] is False
    assert payload["error"] == "solar_term_calculation_unavailable"
    assert payload["calculation_error"]["status"] == "unavailable"
    assert payload["calculation_error"]["source"] == "swiss_ephemeris"
    assert payload["calculation_error"]["method"] == "swiss_ephemeris_solar_longitude_bisection_v1"
    assert payload["calculation_error"]["tolerance_seconds"] == 1.0
    assert payload["calculation_error"]["retryable"] is True
    bazi_module._term_crossing_utc.cache_clear()


def test_chinese_astrology_bazi_route_returns_luck_pillars_when_requested():
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={
            "date": "2000-01-01",
            "time": "12:00",
            "location": "Greenwich, UK",
            "timezone": "UTC",
            "calculation_sex": "female",
            "include_luck_pillars": True,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert data["timing"]["luck_pillars_enabled"] is True
    assert data["timing"]["direction"] == "forward"
    assert data["timing"]["start_age"] > 0
    assert data["timing"]["debug"]["solar_term"]["key"] == "xiao_han"
    assert data["luck_pillars"][0]["stem"] == "Ding"
    assert data["luck_pillars"][0]["branch"] == "Chou"
    assert data["timing"]["annual_pillar"]["stem"]


def test_chinese_astrology_bazi_route_prompts_for_luck_pillar_direction_basis():
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={
            "date": "2000-01-01",
            "time": "12:00",
            "location": "Greenwich, UK",
            "timezone": "UTC",
            "include_luck_pillars": True,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert data["timing"]["luck_pillars_enabled"] is False
    assert data["luck_pillars"] == []
    assert any(item["field"] == "calculation_sex" for item in data["missing_inputs"])


def test_chinese_astrology_bazi_route_can_apply_true_solar_hour_pillar():
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={
            "date": "2000-01-01",
            "time": "01:20",
            "timezone": "Europe/Madrid",
            "latitude": 40.4168,
            "longitude": -3.7038,
            "use_true_solar_time": True,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert data["birth"]["true_solar_time"]["requested"] is True
    assert data["birth"]["true_solar_time"]["applied"] is True
    assert data["debug"]["hour_pillar_comparison"]["changed"] is True
    assert data["debug"]["hour_pillar_comparison"]["civil"]["branch"] == "Chou"
    assert data["pillars"]["hour"]["branch"] == "Zi"
    assert "true solar" in data["debug"]["hour_rule"]


def test_chinese_astrology_bazi_route_flags_true_solar_without_longitude():
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={
            "date": "2000-01-01",
            "time": "00:30",
            "timezone": "UTC",
            "use_true_solar_time": True,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert data["birth"]["true_solar_time"]["requested"] is True
    assert data["birth"]["true_solar_time"]["applied"] is False
    assert any(item["field"] == "longitude" for item in data["missing_inputs"])


def test_chinese_astrology_relationship_codes_include_natal_branch_events():
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/chinese-astrology/bazi",
        json={"date": "2000-01-01", "time": "12:00", "location": "Greenwich, UK", "timezone": "UTC"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    events = payload["data"]["relationships"]["events"]
    zi_wu_events = [
        event for event in events
        if event["type"] == "branch_clash" and set(event["symbols"]) == {"Zi", "Wu"}
    ]
    assert zi_wu_events
    assert zi_wu_events[0]["scope"] == "natal"
    assert "Month" in zi_wu_events[0]["affected_palaces"]
    assert "Day" in zi_wu_events[0]["affected_palaces"]


def test_chinese_astrology_relationship_codes_include_annual_dynamic_events():
    from chinese_astrology import BirthContext, build_bazi_profile
    from datetime import datetime, timezone

    profile = build_bazi_profile(
        BirthContext(
            dt_utc=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
            timezone="UTC",
            location="Greenwich, UK",
            hour_known=True,
        ),
        reference_dt_utc=datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
    )
    events = profile["relationships"]["events"]
    annual_events = [event for event in events if event["scope"] == "annual"]

    assert annual_events
    assert any(point["pillar"] == "annual" for event in annual_events for point in event["points"])
