import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_external_case_candidates.json"
SLICE_SIX_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_case_replay_slice_6.json"


class ForensicExternalCaseCandidateTests(unittest.TestCase):
    def test_external_candidates_have_required_manual_review_fields(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(payload.get("sources") or []), 2)
        self.assertEqual({case["id"] for case in payload.get("cases") or []}, {"libby_abby_delphi", "idaho_four_murders"})

        for case in payload.get("cases") or []:
            self.assertEqual(case.get("execution_tier"), "tier_3_manual_review")
            self.assertIn(case.get("current_status"), {"manual_review_only", "exploratory_holdback", "promoted_to_external_replay_slice_1"})
            self.assertTrue(case.get("metadata_basis"))
            self.assertTrue(case.get("metadata_confidence"))
            self.assertTrue(case.get("not_replay_ready_reason"))
            self.assertTrue(case.get("recommended_next_step"))
            self.assertTrue(case.get("tested_anchors"))

            for anchor in case.get("tested_anchors") or []:
                self.assertEqual(anchor.get("status_code"), 200)
                self.assertTrue(anchor.get("success"))
                self.assertTrue(anchor.get("categories"))
                self.assertTrue(anchor.get("finding_titles"))

    def test_external_candidates_are_not_part_of_slice_six_replay(self):
        external_cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        slice_six = json.loads(SLICE_SIX_PATH.read_text(encoding="utf-8"))
        external_ids = {case["id"] for case in external_cases.get("cases") or []}
        slice_six_ids = {case["id"] for case in slice_six.get("cases") or []}
        self.assertFalse(external_ids & slice_six_ids)
        self.assertEqual(slice_six_ids, {"charles_whitman"})


if __name__ == "__main__":
    unittest.main()
