from backend.forensic.axis_assessment import assess_axes


def test_axis_assessment_uses_category_not_incidental_title_words() -> None:
    result = assess_axes(
        [
            {
                "id": "violence_rule",
                "title": "Hidden victim near water after vehicle movement",
                "category": "Violence",
                "weight": 3,
            }
        ]
    )

    assert result["predicted_axes"] == ["violence_homicide"]
    assert result["uses_free_text"] is False


def test_axis_assessment_excludes_context_only_rule_from_predictions() -> None:
    result = assess_axes(
        [
            {
                "id": "generic_neptune",
                "category": "Deception",
                "scoring_eligible": False,
            }
        ]
    )

    assert result["predicted_axes"] == []
    assert result["excluded_non_scoring_rule_ids"] == ["generic_neptune"]


def test_axis_assessment_adds_stable_secondary_axis_by_rule_id() -> None:
    result = assess_axes(
        [
            {
                "id": "vehicle_crash_or_transport_harm_pattern",
                "category": "Disaster",
                "weight": 4,
            }
        ]
    )

    assert result["predicted_axes"] == ["accident_or_disaster", "route_vehicle_transport"]
