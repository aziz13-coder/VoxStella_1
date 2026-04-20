import json
from pathlib import Path
import unittest

from tests.forensic_case_replay_utils import make_forensic_replay_app


REPO_ROOT = Path(__file__).resolve().parents[1]
STRATIFIED_FIXTURE = REPO_ROOT / 'tests' / 'fixtures' / 'forensic_survivability_stratified_cases.json'


def load_cases():
    payload = json.loads(STRATIFIED_FIXTURE.read_text(encoding='utf-8'))
    return payload.get('cases') or []


class ForensicSurvivabilityStratifiedBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.cases = {case['id']: case for case in load_cases()}

    def _route_case(self, case_id):
        case = self.cases[case_id]
        response = self.client.get('/api/astro-clock/forensic', query_string=case['query'])
        self.assertEqual(response.status_code, 200, msg={'case_id': case_id, 'status': response.status_code})
        payload = response.get_json() or {}
        self.assertTrue(payload.get('success'), msg={'case_id': case_id, 'payload': payload})
        survivability = payload.get('survivability') or {}
        self.assertTrue(survivability, msg={'case_id': case_id, 'payload': payload})
        return case, survivability, payload

    def _assert_case_expectations(self, case_id):
        case, survivability, payload = self._route_case(case_id)
        self.assertIn(
            survivability.get('level'),
            set(case.get('expected_levels') or []),
            msg={
                'case_id': case_id,
                'family': case.get('family'),
                'survivability': survivability,
                'categories': payload.get('categories'),
                'findings': [f.get('title') for f in (payload.get('findings') or [])[:10]],
            },
        )
        self.assertIn(
            survivability.get('outcome_band'),
            set(case.get('expected_bands') or []),
            msg={
                'case_id': case_id,
                'family': case.get('family'),
                'survivability': survivability,
                'categories': payload.get('categories'),
                'findings': [f.get('title') for f in (payload.get('findings') or [])[:10]],
            },
        )
        self.assertIn('recovery_support', survivability.get('breakdown') or {})
        return case, survivability, payload

    def test_abduction_fatal_family_stays_lower(self):
        for case_id in ('lindbergh_kidnapping_fatal',):
            with self.subTest(case_id=case_id):
                self._assert_case_expectations(case_id)

    def test_nonfatal_violent_family_stays_out_of_fatal_band(self):
        for case_id in (
            'reagan_assassination_attempt_survived',
            'gabrielle_giffords_shooting_survived',
            'john_paul_ii_assassination_attempt_survived',
        ):
            with self.subTest(case_id=case_id):
                _case, survivability, _payload = self._assert_case_expectations(case_id)
                self.assertNotEqual(survivability.get('level'), 'Lower')
                self.assertNotEqual(survivability.get('outcome_band'), 'fatal_pressure_dominant')

    def test_known_person_homicide_family_stays_fatal(self):
        for case_id in (
            'phil_hartman_known_person_homicide',
            'marvin_gaye_known_person_homicide',
            'joey_comunale_party_monster',
            'sylvie_cachay_soho_horror',
            'lourdes_gonzalez_your_eyes_or_your_life',
        ):
            with self.subTest(case_id=case_id):
                self._assert_case_expectations(case_id)

    def test_mixed_family_avoids_clean_release_band(self):
        for case_id in (
            'scott_peterson_mixed_disappearance',
            'irene_silverman_mixed_disappearance',
            'natalie_wood_mixed_disappearance',
        ):
            with self.subTest(case_id=case_id):
                _case, survivability, _payload = self._assert_case_expectations(case_id)
                self.assertNotIn(survivability.get('outcome_band'), {'release_favored', 'nonfatal_tilt'})

    def test_recovery_support_lifts_reagan_out_of_forced_fatal_band(self):
        _case, survivability, payload = self._assert_case_expectations('reagan_assassination_attempt_survived')
        self.assertGreaterEqual(float((survivability.get('breakdown') or {}).get('recovery_support') or 0.0), 1.0)
        self.assertIn('Sun conjunction Venus +2.31', (survivability.get('evidence') or {}).get('support') or [])
        self.assertIn('Moon trine Jupiter +2.08', (survivability.get('evidence') or {}).get('support') or [])
        self.assertIn('violence or homicide', ' '.join((f.get('title') or '') for f in (payload.get('findings') or [])).lower())
        self.assertEqual(survivability.get('level'), 'Moderate')


if __name__ == '__main__':
    unittest.main()
