# Forensic Dashboard Golden Fixtures

- Command used: `python tests\fixtures\forensic_dashboard_goldens\generate_forensic_dashboard_goldens.py`
- Repo commit: `73b66c6eb4b774a67bc256c2290fef66ef98cebd`
- Successful cases: 46
- Failed/skipped cases: 0
- Source fixture files used:
  - `forensic_netflix_true_crime_2025_2026_cases.json`
  - `forensic_case_replay_slice_1.json`
  - `forensic_case_replay_slice_2.json`
  - `forensic_case_replay_slice_3.json`
  - `forensic_case_replay_slice_4.json`
  - `forensic_case_replay_slice_5.json`
  - `forensic_case_replay_slice_6.json`
  - `forensic_external_replay_slice_1.json`
  - `forensic_external_replay_slice_2.json`
  - `forensic_external_replay_slice_3.json`
  - `forensic_survivability_stratified_cases.json`

Frontend-derived fields:
- `replay_axes` are generated with `frontend/src/features/astroclock/forensicReplayAxes.mjs`.
- `metrics` are populated by mirroring the inline ForensicDashboard formulas in `frontend/src/features/astroclock/AstroClock.jsx`.
- `dossier_sections.metrics` and `dossier_sections.findings` are populated from the same compact dashboard/top-finding surface.
- `dossier_sections.victim`, `perpetrator`, `relationship`, `witnesses`, `deception`, and `outcome` are `null` because there is no exported frontend dossier builder for those sections.
