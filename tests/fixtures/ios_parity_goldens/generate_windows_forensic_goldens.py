"""Generate compact Windows forensic golden outputs for iOS parity tests."""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
OUTPUT_DIR = FIXTURE_DIR / "ios_parity_goldens"
SUCCESS_PATH = OUTPUT_DIR / "windows_forensic_golden_outputs.json"
FAILURE_PATH = OUTPUT_DIR / "windows_forensic_golden_failures.json"
README_PATH = OUTPUT_DIR / "README.md"

SOURCE_FIXTURES = [
    "forensic_netflix_true_crime_2025_2026_cases.json",
    "forensic_case_replay_slice_1.json",
    "forensic_case_replay_slice_2.json",
    "forensic_case_replay_slice_3.json",
    "forensic_case_replay_slice_4.json",
    "forensic_case_replay_slice_5.json",
    "forensic_case_replay_slice_6.json",
    "forensic_external_replay_slice_1.json",
    "forensic_external_replay_slice_2.json",
    "forensic_external_replay_slice_3.json",
    "forensic_survivability_stratified_cases.json",
]

QUERY_KEYS = [
    "mode",
    "timezone",
    "location",
    "latitude",
    "longitude",
    "house_system_code",
    "case_type",
    "abduction",
    "origin",
    "line_zones",
    "corridor_deg",
]

NODE_DERIVATION_SCRIPT = r"""
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const repoRoot = process.cwd();
const mod = await import(pathToFileURL(path.join(repoRoot, 'frontend/src/features/astroclock/forensicReplayAxes.mjs')).href);
const {
  deriveForensicReplayAxes,
  getForensicReplayTailoring,
  forensicFindingMatchesAxis,
  cleanForensicDisplayText,
} = mod;

function selectTopFindings(payload, replayAxes) {
  const rawFindings = Array.isArray(payload?.findings)
    ? payload.findings.filter((finding) => finding && typeof finding === 'object')
    : [];
  if (!rawFindings.length) return [];

  const tailoring = getForensicReplayTailoring(payload || {});
  const weighted = rawFindings
    .map((finding, index) => {
      const base = Number(finding?.weight);
      let displayWeight = Number.NaN;
      if (Number.isFinite(base)) {
        displayWeight = base;
        if (tailoring.domesticFatalContext) {
          if (forensicFindingMatchesAxis(finding, 'abduction_missing_person')) displayWeight -= 100;
          if (forensicFindingMatchesAxis(finding, 'water_disappearance_or_drowning')) displayWeight -= 100;
          if (
            forensicFindingMatchesAxis(finding, 'violence_homicide') ||
            forensicFindingMatchesAxis(finding, 'family_involvement') ||
            forensicFindingMatchesAxis(finding, 'domestic_partner_involvement')
          ) {
            displayWeight += 20;
          }
        }
        if (tailoring.fatalPressureDominant && forensicFindingMatchesAxis(finding, 'violence_homicide')) {
          displayWeight += 10;
        }
        if (tailoring.childContext && forensicFindingMatchesAxis(finding, 'child_victim')) {
          displayWeight += 8;
        }
      }
      return { finding, index, weight: base, displayWeight };
    })
    .filter((item) => Number.isFinite(item.displayWeight) && item.displayWeight > -50);

  if (weighted.length) {
    return [...weighted]
      .sort((a, b) => (b.displayWeight - a.displayWeight) || (b.weight - a.weight) || (a.index - b.index))
      .slice(0, 6)
      .map((item) => item.finding);
  }

  const selected = [];
  const selectedIndexes = new Set();
  replayAxes.forEach((axis) => {
    const index = rawFindings.findIndex((finding, idx) => (
      !selectedIndexes.has(idx) && forensicFindingMatchesAxis(finding, axis)
    ));
    if (index >= 0) {
      selectedIndexes.add(index);
      selected.push(rawFindings[index]);
    }
  });
  rawFindings.forEach((finding, index) => {
    if (selected.length >= 6 || selectedIndexes.has(index)) return;
    selectedIndexes.add(index);
    selected.push(finding);
  });
  return selected;
}

function compactFinding(finding) {
  const weight = Number(finding?.weight);
  return {
    id: finding?.id == null ? null : String(finding.id),
    title: cleanForensicDisplayText(finding?.title || ''),
    category: cleanForensicDisplayText(finding?.category || ''),
    weight: Number.isFinite(weight) ? weight : null,
  };
}

function dossierFindingRow(finding, index) {
  return {
    number: String(index + 1).padStart(2, '0'),
    ...compactFinding(finding),
  };
}

let input = '';
process.stdin.setEncoding('utf8');
for await (const chunk of process.stdin) input += chunk;
const payloads = JSON.parse(input || '[]');
const out = payloads.map((payload) => {
  const replayAxes = deriveForensicReplayAxes(payload || {});
  const topFindings = selectTopFindings(payload || {}, replayAxes);
  return {
    replay_axes: replayAxes,
    top_findings: topFindings.map(compactFinding),
    finding_rows: topFindings.map(dossierFindingRow),
  };
});
process.stdout.write(JSON.stringify(out));
"""


def _ensure_import_paths() -> None:
    for path in (REPO_ROOT, REPO_ROOT / "backend"):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def _make_forensic_app():
    _ensure_import_paths()
    from flask import Flask
    import backend.astro_clock_api as astro_clock_api

    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def _load_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for fixture_name in SOURCE_FIXTURES:
        fixture_path = FIXTURE_DIR / fixture_name
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        for case in payload.get("cases") or []:
            cases.append(
                {
                    "source_fixture": fixture_name,
                    "case": case,
                    "case_id": str(case.get("id") or ""),
                }
            )
    return sorted(cases, key=lambda item: (item["source_fixture"], item["case_id"]))


def _build_route_query(case: Dict[str, Any]) -> Dict[str, str]:
    raw_query = dict(case.get("query") or {})
    query: Dict[str, str] = {}
    datetime_value = raw_query.get("datetime") or raw_query.get("datetime_local")
    if datetime_value is not None:
        query["datetime"] = str(datetime_value)
    for key in QUERY_KEYS:
        value = raw_query.get(key)
        if value is None:
            continue
        query[key] = str(value)
    if "mode" not in query:
        query["mode"] = "manual"
    if "house_system_code" not in query:
        query["house_system_code"] = "R"
    return query


def _record_query(route_query: Dict[str, str]) -> Dict[str, str]:
    ordered_keys = [
        "mode",
        "datetime",
        "timezone",
        "location",
        "latitude",
        "longitude",
        "house_system_code",
        "case_type",
        "abduction",
        "origin",
        "line_zones",
        "corridor_deg",
    ]
    return {key: route_query[key] for key in ordered_keys if key in route_query}


def _sort_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_nested(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_nested(item) for item in value]
    return value


def _num(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return number


def _js_round(value: float) -> int:
    return int(math.floor(value + 0.5))


def _clamp_metric(value: Any, minimum: float = 0, maximum: float = 100) -> float:
    number = _num(value)
    return max(minimum, min(maximum, number))


def _compute_frontend_metrics(payload: Dict[str, Any]) -> Dict[str, Any]:
    categories = payload.get("categories") if isinstance(payload.get("categories"), dict) else {}
    survivability = payload.get("survivability") if isinstance(payload.get("survivability"), dict) else {}
    breakdown = survivability.get("breakdown") if isinstance(survivability.get("breakdown"), dict) else {}

    def category_count(name: str) -> float:
        return _num(categories.get(name))

    fatal_pressure_value = _num(breakdown.get("fatal_pressure"))
    danger_value = _num(breakdown.get("danger"))
    fatal_pressure_dominant = bool(
        fatal_pressure_value >= 4.5
        or survivability.get("outcome_band") == "fatal_pressure_dominant"
        or re.search(r"fatal pressure", str(survivability.get("note") or ""), re.IGNORECASE)
    )
    survival_score = survivability.get("score")
    survival_score_number = _num(survival_score)
    survival_score_available = survival_score is not None

    violence_index = _js_round(
        _clamp_metric((category_count("Violence") * 12) + (danger_value * 8) + (fatal_pressure_value * 3), 0, 99)
    )
    deception_index = _js_round(
        _clamp_metric((category_count("Deception") * 8) + (category_count("Stressors") * 3), 0, 99)
    )
    case_signal_score = _js_round(
        _clamp_metric(
            (fatal_pressure_value * 8.5)
            + (danger_value * 7)
            + (category_count("Violence") * 6)
            + (category_count("Deception") * 3)
            + (10 if fatal_pressure_dominant else 0),
            0,
            100,
        )
    )
    survivability_percent = _js_round(
        _clamp_metric(50 + (survival_score_number * 6) if survival_score_available else 50, 5, 95)
    )

    return {
        "case_signal_score": case_signal_score,
        "violence_index": violence_index,
        "deception_index": deception_index,
        "survivability_percent": survivability_percent,
    }


def _compact_survivability(payload: Dict[str, Any]) -> Dict[str, Any]:
    survivability = payload.get("survivability") if isinstance(payload.get("survivability"), dict) else {}
    return {
        "level": survivability.get("level"),
        "score": survivability.get("score"),
        "outcome_band": survivability.get("outcome_band"),
        "breakdown": _sort_nested(survivability.get("breakdown")),
        "evidence": _sort_nested(survivability.get("evidence")),
    }


def _frontend_derivations(payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", NODE_DERIVATION_SCRIPT],
        cwd=REPO_ROOT,
        input=json.dumps(payloads, ensure_ascii=True),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Node frontend derivation failed: "
            + (completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}")
        )
    return json.loads(completed.stdout or "[]")


def _call_route_for_cases() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    app = _make_forensic_app()
    successes: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    with app.test_client() as client:
        for item in _load_cases():
            case = item["case"]
            fixture_name = item["source_fixture"]
            case_id = str(case.get("id") or "")
            route_query = _build_route_query(case)
            try:
                response = client.get("/api/astro-clock/forensic", query_string=route_query)
                try:
                    payload = response.get_json() or {}
                except Exception as exc:
                    payload = {"success": False, "error": f"Could not decode JSON response: {exc}"}
                status_code = int(response.status_code)
            except Exception as exc:
                status_code = 0
                payload = {"success": False, "error": str(exc)}

            if status_code == 200 and payload.get("success") is True:
                successes.append(
                    {
                        "schema_version": 1,
                        "generated_at": generated_at,
                        "source_fixture": fixture_name,
                        "case_id": case_id,
                        "case_title": case.get("title"),
                        "query": _record_query(route_query),
                        "success": True,
                        "_payload": payload,
                    }
                )
            else:
                failures.append(
                    {
                        "source_fixture": fixture_name,
                        "case_id": case_id,
                        "case_title": case.get("title"),
                        "status_code": status_code,
                        "error": str(payload.get("error") or payload.get("message") or "Forensic route failed"),
                    }
                )
    return successes, failures


def _materialize_success_records(route_successes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    derivations = _frontend_derivations([record["_payload"] for record in route_successes])
    if len(derivations) != len(route_successes):
        raise RuntimeError("Frontend derivation count did not match successful route payload count.")

    records: List[Dict[str, Any]] = []
    for record, frontend in zip(route_successes, derivations):
        payload = record.pop("_payload")
        metrics = _compute_frontend_metrics(payload)
        records.append(
            {
                "schema_version": record["schema_version"],
                "generated_at": record["generated_at"],
                "source_fixture": record["source_fixture"],
                "case_id": record["case_id"],
                "case_title": record["case_title"],
                "query": record["query"],
                "success": True,
                "metrics": metrics,
                "survivability": _compact_survivability(payload),
                "categories": _sort_nested(payload.get("categories") or {}),
                "replay_axes": frontend.get("replay_axes") or [],
                "top_findings": frontend.get("top_findings") or [],
                "dossier_sections": {
                    "metrics": metrics,
                    "findings": frontend.get("finding_rows") or [],
                    "victim": None,
                    "perpetrator": None,
                    "relationship": None,
                    "witnesses": None,
                    "deception": None,
                    "outcome": None,
                },
            }
        )
    return sorted(records, key=lambda item: (item["source_fixture"], item["case_id"]))


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_readme(successes: List[Dict[str, Any]], failures: List[Dict[str, Any]]) -> None:
    command = r"python tests\fixtures\ios_parity_goldens\generate_windows_forensic_goldens.py"
    lines = [
        "# Windows Forensic iOS Parity Goldens",
        "",
        f"- Command used: `{command}`",
        f"- Repo commit: `{_git_commit()}`",
        f"- Successful cases: {len(successes)}",
        f"- Failed/skipped cases: {len(failures)}",
        "- Source fixture files used:",
    ]
    lines.extend(f"  - `{name}`" for name in SOURCE_FIXTURES)
    lines.extend(
        [
            "",
            "Frontend-derived fields:",
            "- `replay_axes` are generated with `frontend/src/features/astroclock/forensicReplayAxes.mjs`.",
            "- `metrics` are populated by mirroring the inline ForensicDashboard formulas in `frontend/src/features/astroclock/AstroClock.jsx`.",
            "- `dossier_sections.metrics` and `dossier_sections.findings` are populated from the same compact dashboard/top-finding surface.",
            "- `dossier_sections.victim`, `perpetrator`, `relationship`, `witnesses`, `deception`, and `outcome` are `null` because there is no exported frontend dossier builder for those sections.",
        ]
    )
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_outputs(success_path: Path = SUCCESS_PATH, failure_path: Path = FAILURE_PATH) -> None:
    successes = json.loads(success_path.read_text(encoding="utf-8"))
    json.loads(failure_path.read_text(encoding="utf-8"))

    required = {"case_id", "query", "categories", "replay_axes", "top_findings", "survivability"}
    for index, record in enumerate(successes):
        missing = sorted(key for key in required if key not in record)
        if missing:
            raise AssertionError(f"success record {index} missing required keys: {missing}")

    shirilla = [record for record in successes if record.get("case_id") == "mackenzie_shirilla_the_crash"]
    if not shirilla:
        raise AssertionError("mackenzie_shirilla_the_crash record was not generated")
    for record in shirilla:
        sent_datetime = str((record.get("query") or {}).get("datetime") or "")
        if sent_datetime != "2022-07-31T05:30:00":
            raise AssertionError(f"Shirilla datetime must be 2022-07-31T05:30:00, got {sent_datetime}")
        if "05:36" in json.dumps(record, ensure_ascii=True):
            raise AssertionError("Shirilla record contains the rejected 05:36 timestamp")

    seen_pairs = set()
    for record in successes:
        pair = (record.get("case_id"), record.get("source_fixture"))
        if pair in seen_pairs:
            raise AssertionError(f"duplicate case_id/source_fixture pair: {pair}")
        seen_pairs.add(pair)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    route_successes, failures = _call_route_for_cases()
    successes = _materialize_success_records(route_successes)
    failures = sorted(failures, key=lambda item: (item["source_fixture"], item["case_id"]))
    _write_json(SUCCESS_PATH, successes)
    _write_json(FAILURE_PATH, failures)
    _write_readme(successes, failures)
    validate_outputs()
    print(f"Wrote {len(successes)} success records to {SUCCESS_PATH}")
    print(f"Wrote {len(failures)} failure records to {FAILURE_PATH}")
    print(f"Wrote README to {README_PATH}")
    print("Validation passed.")


if __name__ == "__main__":
    main()
