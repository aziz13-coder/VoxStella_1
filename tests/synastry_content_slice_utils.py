import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_content_slice_1.json"

for path in (REPO_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from synastry_engine import build_synastry_report


def load_synastry_content_slice(path=FIXTURE_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def content_runnable_cases(content_slice):
    out = []
    for case in content_slice.get("cases") or []:
        if case.get("chart_data_a") and case.get("chart_data_b") and case.get("chart_meta_a") and case.get("chart_meta_b"):
            out.append(case)
    return out


def replay_synastry_content_case(case):
    bundle_a = {"chart_data": case["chart_data_a"], "meta": {"label": case["partner_a"]}}
    bundle_b = {"chart_data": case["chart_data_b"], "meta": {"label": case["partner_b"]}}
    return build_synastry_report(
        bundle_a,
        bundle_b,
        case["chart_meta_a"],
        case["chart_meta_b"],
        options=case.get("options") or None,
    )


def summarize_synastry_content_case(case, report=None):
    summary = {
        "case_id": case["id"],
        "title": case["title"],
        "usage_lane": case.get("usage_lane"),
        "calibration_eligible": bool(case.get("calibration_eligible")),
        "content_eligible": bool(case.get("content_eligible")),
        "content_status": case.get("content_status") or ("captured" if report else "needs_chart_capture"),
        "content_angle": case.get("content_angle") or "",
        "timed_data_confidence": str((case.get("birth_data_summary") or {}).get("timed_data_confidence") or ""),
        "source_references": list(case.get("source_references") or []),
        "what_to_trust": list(case.get("what_to_trust") or []),
        "what_not_to_trust": list(case.get("what_not_to_trust") or []),
    }
    if report:
        categories = {
            item["id"]: item["score"]
            for item in (report.get("categories") or [])
            if item.get("id")
        }
        summary["report_status"] = "ready"
        summary["category_scores"] = categories
        summary["summary_lines"] = report.get("summary", {}).get("summary_lines") or []
        summary["top_supportive_titles"] = [
            item.get("title") or item.get("label")
            for item in (report.get("top_supportive_links") or [])[:5]
            if item.get("title") or item.get("label")
        ]
        summary["top_challenging_titles"] = [
            item.get("title") or item.get("label")
            for item in (report.get("top_challenging_links") or [])[:5]
            if item.get("title") or item.get("label")
        ]
    else:
        summary["report_status"] = "capture_required"
        summary["capture_requirements"] = list(case.get("capture_requirements") or [])
    return summary
