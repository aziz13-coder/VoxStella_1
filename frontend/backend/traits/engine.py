# -*- coding: utf-8 -*-
"""
Trait Profile Engine

Evaluates trait rules (stored as JSON) against the computed astro metrics.
"""

from __future__ import annotations

import json
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple


def _candidate_backend_roots() -> List[str]:
    import sys

    roots: List[str] = []
    try:
        roots.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
    except Exception:
        pass

    try:
        cwd = os.getcwd()
        roots.append(os.path.normpath(cwd))
        roots.append(os.path.normpath(os.path.join(cwd, "backend")))
    except Exception:
        pass

    env_backend = os.environ.get("HORARY_BACKEND_DIR")
    if env_backend:
        roots.append(os.path.normpath(env_backend))

    try:
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                roots.append(os.path.normpath(meipass))
                roots.append(os.path.normpath(os.path.join(meipass, "backend")))
            exe_dir = os.path.dirname(sys.executable)
            if exe_dir:
                roots.append(os.path.normpath(exe_dir))
                roots.append(os.path.normpath(os.path.join(exe_dir, "backend")))
    except Exception:
        pass

    out: List[str] = []
    seen = set()
    for root in roots:
        if not root:
            continue
        key = os.path.normcase(os.path.normpath(root))
        if key in seen:
            continue
        seen.add(key)
        out.append(root)
    return out


_TRAITS_CATALOG_CACHE: Dict[str, Tuple[Dict[str, Any], Dict[str, float]]] = {}
_TRAITS_CATALOG_LOCK = threading.RLock()


def _resolve_traits_base_dir(root: Optional[str] = None) -> str:
    import sys

    candidates: List[str] = []

    if root:
        if os.path.basename(root.rstrip(os.sep)) == "traits":
            candidates.append(root)
        else:
            candidates.append(os.path.join(root, "traits"))

    candidates.append(os.path.join(os.path.dirname(__file__)))

    try:
        candidates.append(os.path.join(os.getcwd(), "traits"))
    except Exception:
        pass

    env_backend = os.environ.get("HORARY_BACKEND_DIR")
    if env_backend:
        candidates.append(os.path.join(env_backend, "traits"))

    try:
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(os.path.join(meipass, "traits"))
    except Exception:
        pass

    for cand in candidates:
        if not cand:
            continue
        if os.path.isdir(os.path.join(cand, "catalog")) or os.path.exists(os.path.join(cand, "traits.json")):
            return cand

    return os.path.join(os.path.dirname(__file__))


def _traits_catalog_snapshot(base_dir: str) -> Dict[str, float]:
    snapshot: Dict[str, float] = {}
    catalog_dir = os.path.join(base_dir, "catalog")
    if os.path.isdir(catalog_dir):
        for root_dir, _dirs, files in os.walk(catalog_dir):
            for fname in files:
                if not fname.lower().endswith(".json"):
                    continue
                fpath = os.path.join(root_dir, fname)
                try:
                    snapshot[os.path.abspath(fpath)] = os.path.getmtime(fpath)
                except Exception:
                    continue
    path = os.path.join(base_dir, "traits.json")
    if os.path.exists(path):
        try:
            snapshot[os.path.abspath(path)] = os.path.getmtime(path)
        except Exception:
            pass
    return snapshot


def _load_traits_catalog(root: Optional[str] = None) -> Dict[str, Any]:
    """Load traits from the JSON catalog, with robust path fallbacks.

    Search order (first hit wins):
      1) Explicit root (treated as the traits/ directory if it exists)
      2) Directory of this file (…/backend/traits)
      3) Current working directory + /traits (useful when running packaged exe with cwd at resources/backend)
      4) HORARY_BACKEND_DIR env var + /traits
      5) PyInstaller temp (sys._MEIPASS) + /traits
    """
    import sys

    candidates: List[str] = []

    if root:
        # Accept either a traits directory or a backend root containing traits/
        if os.path.basename(root.rstrip(os.sep)) == "traits":
            candidates.append(root)
        else:
            candidates.append(os.path.join(root, "traits"))

    # Repo/development default
    candidates.append(os.path.join(os.path.dirname(__file__)))  # …/backend/traits

    # Packaged exe usually runs with cwd at resources/backend
    try:
        candidates.append(os.path.join(os.getcwd(), "traits"))
    except Exception:
        pass

    # Environment-provided location (set by Electron main)
    env_backend = os.environ.get("HORARY_BACKEND_DIR")
    if env_backend:
        candidates.append(os.path.join(env_backend, "traits"))

    # PyInstaller MEIPASS (if bundled as data)
    try:
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(os.path.join(meipass, "traits"))
    except Exception:
        pass

    # Pick the first candidate that looks valid
    base_dir = None
    for cand in candidates:
        if not cand:
            continue
        if os.path.isdir(os.path.join(cand, "catalog")) or os.path.exists(os.path.join(cand, "traits.json")):
            base_dir = cand
            break

    if base_dir is None:
        # Fallback to this file's directory to avoid exceptions downstream
        base_dir = os.path.join(os.path.dirname(__file__))

    # Prefer loading multiple JSON files under catalog/
    catalog_dir = os.path.join(base_dir, "catalog")
    traits: List[Dict[str, Any]] = []
    if os.path.isdir(catalog_dir):
        for root_dir, _dirs, files in os.walk(catalog_dir):
            for fname in sorted(files):
                if not fname.lower().endswith(".json"):
                    continue
                fpath = os.path.join(root_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        obj = json.load(f)
                    if isinstance(obj, dict) and obj:
                        if obj.get("traits") and isinstance(obj["traits"], list):
                            traits.extend(obj["traits"])  # allow bulk file
                        else:
                            traits.append(obj)  # single-trait file
                except Exception:
                    continue
    # Also load monolithic traits.json if present (fallback/override)
    path = os.path.join(base_dir, "traits.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for t in data.get("traits", []) or []:
                    traits.append(t)
        except Exception:
            pass
    # Deduplicate by id (fallback to name) — prefer first seen (catalog wins over monolith)
    dedup: Dict[str, Dict[str, Any]] = {}
    for t in traits:
        key = str(t.get("id") or t.get("name") or "").strip().lower()
        if not key:
            continue
        if key in dedup:
            continue  # skip duplicates
        dedup[key] = t
    return {"version": "1.0", "traits": list(dedup.values())}


_load_traits_catalog_uncached = _load_traits_catalog


def _load_traits_catalog(root: Optional[str] = None) -> Dict[str, Any]:
    """Load traits catalog with base-dir snapshot caching."""
    base_dir = _resolve_traits_base_dir(root)
    cache_key = os.path.normcase(os.path.normpath(base_dir))
    snapshot = _traits_catalog_snapshot(base_dir)
    with _TRAITS_CATALOG_LOCK:
        cached = _TRAITS_CATALOG_CACHE.get(cache_key)
        if cached is not None:
            cached_catalog, cached_snapshot = cached
            if cached_snapshot == snapshot:
                return cached_catalog
    catalog = _load_traits_catalog_uncached(base_dir)
    with _TRAITS_CATALOG_LOCK:
        _TRAITS_CATALOG_CACHE[cache_key] = (catalog, snapshot)
    return catalog


def _normalize_logic_fragment(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize_logic_fragment(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, list):
        normalized = [_normalize_logic_fragment(v) for v in value]
        try:
            return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=True))
        except Exception:
            return normalized
    return value


def _logic_signature_key(logic: Dict[str, Any]) -> str:
    try:
        normalized = _normalize_logic_fragment(logic or {})
        return json.dumps(normalized, sort_keys=True, ensure_ascii=True)
    except Exception:
        return ""


_PROVISIONAL_MARKERS = (
    "placeholder",
    "tbd",
    "to extract",
    "to add",
    "to refine",
    "provisional",
)

_MORIN_SOURCE_MARKERS = (
    "morin",
    "astrologia gallica",
)

_CLASSICAL_SOURCE_MARKERS = (
    "schoner",
    "schöner",
    "montulmo",
    "khayat",
    "abu ali",
    "bonatti",
)

_MODERN_SOURCE_MARKERS = (
    "arroyo",
)

_SOURCE_LINEAGE_PRIORITY = {
    "morin": 5,
    "classical": 4,
    "carter": 3,
    "modern": 2,
    "editorial": 1,
    "provisional": 0,
}


_SUMMARY_SPECIALIZED_DOMAINS = {
    "anatomy_correspondence",
    "anatomy_disease",
    "constitution",
    "environmental_risk",
    "motif",
    "pathology",
    "pathophysiology",
    "physique",
    "physique_injury",
    "reproductive_tendency",
    "risk_theme",
}

_SUMMARY_CAUTION_DOMAINS = {
    "affect_loss_processing",
    "affect_negative",
    "behavioral_risk",
    "cognitive_limitation",
    "cognitive_shadow",
    "compulsion_addiction",
    "ego_expression_shadow",
    "energy_shadow",
    "ethic_shadow",
    "ethical_shadow",
    "psychological",
    "relationship_risk",
    "shadow_affect",
    "shadow_of_belief",
    "shadow_of_will",
    "shadow_tendency",
    "social_shadow",
    "temperament_defensive",
    "temperament_negative",
    "temperament_shadow",
}

_PUBLIC_FIGURE_SUMMARY_CONTEXTS = {
    "public_figure",
    "public_figure_biography",
    "public_life",
    "public-life",
    "biography",
}

_CRIMINAL_BIOGRAPHY_SUMMARY_CONTEXTS = {
    "criminal",
    "criminal_biography",
    "criminal-figure",
    "criminal_figure",
    "criminals-bio",
    "crime_biography",
}

_PUBLIC_FIGURE_TRAIT_PRIORITIES = {
    # Public office, authority, and visible leadership.
    "leadership_executive": 9,
    "government_authority": 9,
    "kingship_leadership_display": 8,
    "capricorn_ambition": 7,
    "domination_capricorn": 7,
    # Institutional, policy, legal, and administrative signals.
    "responsibility": 8,
    "organization_capricorn": 8,
    "legal_mind": 9,
    "justice_advocacy": 8,
    "zeal_for_reform": 8,
    "calculation": 8,
    "judgment_sound": 7,
    "precision": 7,
    "rationality": 7,
    "zeal_for_service": 7,
    # Public persuasion, coalition work, and social reach.
    "eloquence": 9,
    "mediation": 8,
    "tact": 8,
    "cooperation": 8,
    "sociability": 7,
    "quick_wittedness": 7,
    "wit": 7,
    "humour": 7,
    "frankness": 7,
    # Drive, courage, endurance, and conflict style.
    "enterprise_initiative": 8,
    "self_assertion": 8,
    "courage_aries": 8,
    "valor": 8,
    "fortitude": 8,
    "perseverance": 8,
    "resilience": 8,
    "endurance": 8,
    "steadiness": 9,
    "pugnacity": 7,
    "willfulness": 7,
    "ruthlessness": 7,
    "severity": 7,
    "rebellion": 9,
    "disruptiveness": 8,
    "unconventionality": 7,
    # Public service and humanitarian reputation.
    "humanitarianism": 9,
    "philanthropy": 8,
    "compassion_universalism": 8,
    "charity": 8,
    "unselfishness": 7,
    "piety": 7,
    "empathy": 8,
    # Science, craft, arts, sport, and cultural performance.
    "invention_discovery": 8,
    "genius_inventive_scientific": 8,
    "scholarship": 8,
    "intelligence_general": 8,
    "vision_big_picture": 7,
    "curiosity": 7,
    "industriousness": 7,
    "creativity": 8,
    "craftsmanship": 8,
    "grace_artistic": 9,
    "imagination": 7,
    "transformation": 8,
    "venturesomeness": 8,
    "travel_inclination": 8,
    "yearning_for_travel": 8,
    "recklessness": 8,
    "temperance": 6,
    "sincerity": 6,
    "reliability": 6,
    "tenacity": 8,
    "conservatism": 8,
    "worldliness": 6,
}

_CRIMINAL_BIOGRAPHY_TRAIT_PRIORITIES = {
    # Directly biographical conflict, violence, and harm signals.
    "destructiveness": 10,
    "ruthlessness": 10,
    "severity": 10,
    "pugnacity": 9,
    "warlike": 9,
    "wrath": 9,
    "disruptiveness": 9,
    "recklessness": 9,
    "rashness": 8,
    "turbulence": 8,
    "danger_watery_catastrophes": 7,
    # Domination, defiance, and ideological fixation.
    "tyranny": 9,
    "domination_capricorn": 9,
    "willfulness": 8,
    "rebellion": 8,
    "self_assertion": 8,
    "zealotry": 8,
    "zeal_for_status": 7,
    "greed_covetousness": 7,
    "egoism_egotism": 7,
    # Planning, deception, concealment, and predatory social strategy.
    "cunning": 10,
    "calculation": 9,
    "lying_falsehood": 9,
    "subtlety": 8,
    "reticence": 8,
    "watchfulness": 8,
    "reserve_social_style": 7,
    "worldliness": 7,
    # Organized-crime and command biographies often hinge on enterprise and control.
    "leadership_executive": 8,
    "government_authority": 8,
    "enterprise_initiative": 8,
    "conservatism": 7,
    "tenacity": 7,
    "endurance": 7,
    "perseverance": 7,
    "fortitude": 7,
    "transformation": 7,
    # Obsessive, compulsive, and risk biographies.
    "restlessness": 7,
    "libido_sexual_drive_style": 7,
    "compassion_universalism": 1,
    "humanitarianism": 1,
    "philanthropy": 1,
    "charity": 1,
    "empathy": 1,
}

_PUBLIC_FIGURE_DOMAIN_PRIORITIES = {
    "role_capacity": 7,
    "role_vocation_theme": 7,
    "role_expression": 7,
    "vocation_cognition": 7,
    "work_style": 6,
    "work_habit_positive": 6,
    "executive_function": 6,
    "social_action": 6,
    "social_function": 6,
    "social_orientation": 6,
    "social_skill": 6,
    "social_style": 6,
    "communication_skill": 6,
    "communication_style": 6,
    "affect_communication": 5,
    "action_tendency": 6,
    "drive": 6,
    "drive_assertion": 6,
    "fortitude": 6,
    "virtue_resilience": 6,
    "courage": 6,
    "cognition": 6,
    "cognition_creativity": 6,
    "cognition_originality": 6,
    "cognitive_style": 5,
    "cognition_decision_quality": 5,
    "aesthetics_performance": 6,
    "self_expression": 6,
    "transformative_capacity": 5,
    "religious_attitude": 5,
    "care_orientation": 5,
    "affect_social_feeling": 5,
    "risk_taking": 5,
    "life_pattern": 5,
}

_CRIMINAL_BIOGRAPHY_DOMAIN_PRIORITIES = {
    "behavioral_risk": 8,
    "cognitive_shadow": 8,
    "compulsion_addiction": 7,
    "ego_expression_shadow": 8,
    "energy_shadow": 8,
    "ethic_shadow": 9,
    "ethical_shadow": 9,
    "psychological": 6,
    "relationship_risk": 7,
    "shadow_affect": 7,
    "shadow_of_belief": 7,
    "shadow_of_will": 8,
    "shadow_tendency": 8,
    "social_shadow": 8,
    "temperament_defensive": 6,
    "temperament_negative": 8,
    "temperament_shadow": 8,
    "risk_taking": 7,
    "action_tendency": 6,
    "drive_assertion": 6,
    "executive_function": 5,
}


def _trait_source_status(trait: Dict[str, Any]) -> str:
    try:
        explicit = str(trait.get("source_status") or "").strip().lower()
        if explicit in {"curated", "provisional"}:
            return explicit
    except Exception:
        pass
    if bool(trait.get("provisional")):
        return "provisional"

    text_parts: List[str] = []
    try:
        if trait.get("description"):
            text_parts.append(str(trait.get("description")))
    except Exception:
        pass
    try:
        for src in (trait.get("sources") or []):
            if src:
                text_parts.append(str(src))
    except Exception:
        pass
    combined = " | ".join(text_parts).lower()
    if any(marker in combined for marker in _PROVISIONAL_MARKERS):
        return "provisional"
    return "curated"


def _trait_source_lineage(trait: Dict[str, Any], source_status: Optional[str] = None) -> Tuple[str, str]:
    try:
        explicit = str(trait.get("source_lineage") or "").strip().lower()
        if explicit:
            label_map = {
                "morin": "Morin-linked",
                "classical": "Classical source",
                "carter": "Carter-derived",
                "modern": "Modern source",
                "editorial": "Editorial",
                "provisional": "Provisional source",
            }
            return explicit, label_map.get(explicit, explicit.title())
    except Exception:
        pass

    normalized_status = str(source_status or _trait_source_status(trait) or "").strip().lower()
    if normalized_status == "provisional":
        return "provisional", "Provisional source"

    text_parts: List[str] = []
    try:
        if trait.get("description"):
            text_parts.append(str(trait.get("description")))
    except Exception:
        pass
    try:
        for src in (trait.get("sources") or []):
            if src:
                text_parts.append(str(src))
    except Exception:
        pass
    combined = " | ".join(text_parts).lower()

    if any(marker in combined for marker in _MORIN_SOURCE_MARKERS):
        return "morin", "Morin-linked"
    if any(marker in combined for marker in _CLASSICAL_SOURCE_MARKERS):
        return "classical", "Classical source"
    if "carter" in combined:
        return "carter", "Carter-derived"
    if any(marker in combined for marker in _MODERN_SOURCE_MARKERS):
        return "modern", "Modern source"
    return "editorial", "Editorial"


def _trait_source_priority(trait: Dict[str, Any]) -> int:
    lineage = str(trait.get("source_lineage") or "").strip().lower()
    return int(_SOURCE_LINEAGE_PRIORITY.get(lineage, 1))


def _trait_score_tier(trait: Dict[str, Any]) -> int:
    try:
        return int(float(trait.get("score", 0) or 0) // 5)
    except Exception:
        return 0


def _trait_summary_surface(trait: Dict[str, Any]) -> str:
    try:
        explicit = str(trait.get("summary_surface") or "").strip().lower()
        if explicit in {"general", "caution", "specialized"}:
            return explicit
    except Exception:
        pass

    domain = str(trait.get("domain") or "").strip().lower()
    confidence = str(trait.get("confidence") or "").strip().lower()
    if domain.startswith("disease_") or domain in _SUMMARY_SPECIALIZED_DOMAINS:
        return "specialized"
    if domain in _SUMMARY_CAUTION_DOMAINS:
        return "caution"
    if confidence == "low" and domain in {"life_pattern", "behavioral_state", "affect_attachment"}:
        return "caution"
    return "general"


def _trait_summary_bucket(trait: Dict[str, Any]) -> str:
    try:
        explicit = str(trait.get("summary_bucket") or "").strip().lower()
        if explicit:
            return explicit
    except Exception:
        pass

    domain = str(trait.get("domain") or "").strip().lower()
    name = str(trait.get("name") or "").strip().lower()
    trait_id = str(trait.get("id") or "").strip().lower()
    text = " ".join(part for part in (domain, name, trait_id) if part)

    if any(token in domain for token in ("temperament", "character", "virtue", "ethical", "ethic", "quality_modality", "modality", "habit", "orientation")):
        return "character"
    if any(token in text for token in ("cognit", "intellect", "scholar", "wisdom", "knowledge", "communicat", "question", "invention", "genius", "scientific")):
        return "cognition"
    if any(token in text for token in ("creativity", "art", "beauty", "grace", "appearance", "aesthetic")):
        return "aesthetic"
    if any(token in text for token in ("social", "relationship", "relational", "charity", "hospitality", "care_", "care ", "unity", "friend")):
        return "social"
    if any(token in text for token in ("affect", "emotion", "mood", "attachment", "compassion", "tender", "love", "pleasure")):
        return "affective"
    if any(token in text for token in ("career", "work", "profession", "vocation", "executive")):
        return "vocation"
    if any(token in text for token in ("valor", "will", "volition", "drive", "action", "assert", "energy", "tempo", "fortitude", "initiative")):
        return "drive"
    if any(token in text for token in ("outlook", "belief", "faith", "spirit", "meaning", "worldview")):
        return "worldview"
    if any(token in text for token in ("material", "wealth", "money", "luxury", "property", "home", "domestic", "security")):
        return "material"
    return "character"


def _trait_summary_priority(trait: Dict[str, Any], bucket: Optional[str] = None) -> int:
    try:
        explicit = trait.get("summary_priority")
        if explicit is not None:
            return int(explicit)
    except Exception:
        pass

    bucket_name = str(bucket or _trait_summary_bucket(trait) or "").strip().lower()
    domain = str(trait.get("domain") or "").strip().lower()
    trait_id = str(trait.get("id") or "").strip().lower()

    if bucket_name == "cognition":
        if trait_id in {
            "invention_discovery",
            "genius_inventive_scientific",
            "scholarship",
            "wisdom",
            "intelligence_general",
            "knowledge_general_intellect",
            "questioning_mind",
            "vision_big_picture",
        }:
            return 3
        if domain in {
            "cognition_originality",
            "cognition_creativity",
            "cognitive_style",
            "cognitive_virtue",
            "cognition",
            "executive_function",
            "outlook",
        }:
            return 2
        if domain in {"communication", "communication_style", "cognitive_affective"}:
            return 1
    return 0


def _normalize_summary_context(summary_context: Optional[str]) -> str:
    normalized = str(summary_context or "default").strip().lower()
    return normalized or "default"


def _is_public_figure_summary_context(summary_context: Optional[str]) -> bool:
    return _normalize_summary_context(summary_context) in _PUBLIC_FIGURE_SUMMARY_CONTEXTS


def _is_criminal_biography_summary_context(summary_context: Optional[str]) -> bool:
    return _normalize_summary_context(summary_context) in _CRIMINAL_BIOGRAPHY_SUMMARY_CONTEXTS


def _uses_contextual_summary_priority(summary_context: Optional[str]) -> bool:
    return _is_public_figure_summary_context(summary_context) or _is_criminal_biography_summary_context(summary_context)


def _trait_public_figure_priority(trait: Dict[str, Any]) -> int:
    trait_id = str(trait.get("id") or "").strip().lower()
    if trait_id in _PUBLIC_FIGURE_TRAIT_PRIORITIES:
        return int(_PUBLIC_FIGURE_TRAIT_PRIORITIES[trait_id])
    domain = str(trait.get("domain") or "").strip().lower()
    if domain in _PUBLIC_FIGURE_DOMAIN_PRIORITIES:
        return int(_PUBLIC_FIGURE_DOMAIN_PRIORITIES[domain])
    bucket = str(trait.get("summary_bucket") or "").strip().lower()
    if bucket in {"vocation", "social", "cognition", "aesthetic", "drive"}:
        return 3
    return 0


def _trait_criminal_biography_priority(trait: Dict[str, Any]) -> int:
    trait_id = str(trait.get("id") or "").strip().lower()
    if trait_id in _CRIMINAL_BIOGRAPHY_TRAIT_PRIORITIES:
        return int(_CRIMINAL_BIOGRAPHY_TRAIT_PRIORITIES[trait_id])
    domain = str(trait.get("domain") or "").strip().lower()
    if domain in _CRIMINAL_BIOGRAPHY_DOMAIN_PRIORITIES:
        return int(_CRIMINAL_BIOGRAPHY_DOMAIN_PRIORITIES[domain])
    bucket = str(trait.get("summary_bucket") or "").strip().lower()
    if bucket in {"drive", "shadow", "risk", "character", "social"}:
        return 3
    return 0


def _trait_summary_context_priority(trait: Dict[str, Any], summary_context: Optional[str]) -> int:
    if _is_criminal_biography_summary_context(summary_context):
        return _trait_criminal_biography_priority(trait)
    if _is_public_figure_summary_context(summary_context):
        return _trait_public_figure_priority(trait)
    return 0


def _trait_surface_order(trait: Dict[str, Any]) -> int:
    surface = str(trait.get("summary_surface") or "").strip().lower()
    if surface == "general":
        return 0
    if surface == "caution":
        return 1
    if surface == "specialized":
        return 2
    return 3


def _trait_group_head_key(trait: Dict[str, Any], summary_context: Optional[str]) -> Tuple[Any, ...]:
    if _uses_contextual_summary_priority(summary_context):
        return (
            -int(trait.get("summary_context_priority") or 0),
            _trait_surface_order(trait),
            -int(trait.get("summary_priority") or 0),
            -_trait_source_priority(trait),
            -_trait_score_tier(trait),
            -float(trait.get("score", 0) or 0),
            str(trait.get("id") or ""),
        )
    return (
        -int(trait.get("summary_priority") or 0),
        -_trait_score_tier(trait),
        -_trait_source_priority(trait),
        -float(trait.get("score", 0) or 0),
        str(trait.get("id") or ""),
    )


def _trait_bucket_head_key(trait: Dict[str, Any], summary_context: Optional[str]) -> Tuple[Any, ...]:
    if _uses_contextual_summary_priority(summary_context):
        return (
            -int(trait.get("summary_context_priority") or 0),
            _trait_surface_order(trait),
            -_trait_source_priority(trait),
            -int(trait.get("summary_priority") or 0),
            -_trait_score_tier(trait),
            -float(trait.get("score", 0) or 0),
            str(trait.get("id") or ""),
        )
    return (
        -_trait_score_tier(trait),
        -_trait_source_priority(trait),
        -int(trait.get("summary_priority") or 0),
        -float(trait.get("score", 0) or 0),
        str(trait.get("id") or ""),
    )


def _trait_summary_rank_key(trait: Dict[str, Any], summary_context: Optional[str]) -> Tuple[Any, ...]:
    if _uses_contextual_summary_priority(summary_context):
        return (
            -int(trait.get("summary_context_priority") or 0),
            _trait_surface_order(trait),
            -int(trait.get("summary_priority") or 0),
            -_trait_source_priority(trait),
            -_trait_score_tier(trait),
            -float(trait.get("score", 0) or 0),
            str(trait.get("id") or ""),
        )
    return (
        -int(trait.get("summary_priority") or 0),
        -_trait_score_tier(trait),
        -_trait_source_priority(trait),
        -float(trait.get("score", 0) or 0),
        str(trait.get("id") or ""),
    )


def _pair_key(a: str, b: str) -> Tuple[str, str]:
    a1, b1 = str(a), str(b)
    return tuple(sorted((a1, b1)))


class TraitEngine:
    def __init__(self, root: Optional[str] = None) -> None:
        self.root = root
        self.catalog = _load_traits_catalog(root)

    # ---------- condition helpers ----------
    def _share(self, part: float, total: float) -> float:
        if not total or total <= 0:
            return 0.0
        return float(part) / float(total)

    def _element_share(self, metrics: Dict[str, Any], element: str) -> float:
        eb = metrics.get("element_balance") or {}
        total = sum(float(eb.get(k, 0) or 0) for k in ("Fire","Earth","Air","Water"))
        return self._share(float(eb.get(element, 0) or 0), total)

    def _modality_share(self, metrics: Dict[str, Any], modality: str) -> float:
        mb = metrics.get("modality_balance") or {}
        total = sum(float(mb.get(k, 0) or 0) for k in ("Cardinal","Fixed","Mutable"))
        return self._share(float(mb.get(modality, 0) or 0), total)

    def _sign_emphasis_val(self, metrics: Dict[str, Any], sign: str) -> float:
        se = metrics.get("sign_emphasis") or {}
        try:
            return float(se.get(sign, 0) or 0)
        except Exception:
            return 0.0

    def _sign_group_emphasis_val(self, metrics: Dict[str, Any], group: List[str]) -> float:
        se = metrics.get("sign_emphasis") or {}
        return sum(float(se.get(s, 0) or 0) for s in group)

    def _planet_status(self, metrics: Dict[str, Any], planet: str) -> Dict[str, Any]:
        ps = metrics.get("planet_status") or {}
        return ps.get(planet, {})

    def _find_aspect(self, metrics: Dict[str, Any], p1: str, p2: str, hard_only: bool = True) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        pairs = metrics.get("planetary_aspects") or []
        for a in pairs:
            a_p1 = a.get("planet1")
            a_p2 = a.get("planet2")
            if {a_p1, a_p2} == {p1, p2}:
                if hard_only:
                    if a.get("afflicting") is True:
                        out.append(a)
                else:
                    out.append(a)
        return out

    # ----- sign helpers -----
    _SIGN_INDEX = {
        "Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3, "Leo": 4, "Virgo": 5,
        "Libra": 6, "Scorpio": 7, "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11,
    }

    def _planet_sign(self, metrics: Dict[str, Any], planet: str) -> Optional[str]:
        ps = metrics.get("planet_signs") or {}
        s = ps.get(planet)
        return s

    def _sign_relation(self, sign_a: str, sign_b: str) -> Optional[str]:
        ia = self._SIGN_INDEX.get(sign_a)
        ib = self._SIGN_INDEX.get(sign_b)
        if ia is None or ib is None:
            return None
        d = abs(ia - ib)
        d = min(d, 12 - d)  # wrap around
        deg = d * 30
        rel = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}.get(deg)
        return rel

    def _find_angle_aspects(self, metrics: Dict[str, Any], planet: str, hard_only: bool = True) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        items = metrics.get("angle_aspects") or []
        for a in items:
            if a.get("planet") == planet:
                if hard_only:
                    if a.get("afflicting") is True:
                        out.append(a)
                else:
                    out.append(a)
        return out

    def _house_emphasis_total(self, metrics: Dict[str, Any], houses: List[int]) -> int:
        he = (metrics.get("house") or {}).get("emphasis") or {}
        total = 0
        for h in houses:
            total += int(he.get(str(h), 0) or 0)
        return total

    def _any_house_afflicted(self, metrics: Dict[str, Any], houses: List[int]) -> bool:
        ha = (metrics.get("house") or {}).get("afflicted") or {}
        for h in houses:
            if bool(ha.get(str(h))):
                return True
        return False

    def _degree_hits(self, metrics: Dict[str, Any], labels: List[str]) -> int:
        dh = (metrics.get("degree_hits") or {}).get("items") or []
        count = 0
        for it in dh:
            if it.get("degree") in labels:
                count += int(it.get("count", 0) or 0)
        return count

    # ---------- evaluation ----------
    def _eval_condition(self, metrics: Dict[str, Any], cond: Dict[str, Any]) -> Tuple[bool, float, Optional[str]]:
        kind = cond.get("kind")
        weight = float(cond.get("weight", 0) or 0)

        if kind == "element":
            share = self._element_share(metrics, cond.get("element", ""))
            if share >= float(cond.get("min_share", 0)):
                return True, weight, f"{cond.get('element')} {int(share*100)}%"
            return False, 0.0, None

        if kind == "modality":
            share = self._modality_share(metrics, cond.get("modality", ""))
            if share >= float(cond.get("min_share", 0)):
                return True, weight, f"{cond.get('modality')} {int(share*100)}%"
            return False, 0.0, None

        if kind == "sign_emphasis":
            val = self._sign_emphasis_val(metrics, cond.get("sign", ""))
            if val >= float(cond.get("min", 0)):
                return True, weight, f"{cond.get('sign')} {val:.1f}"
            return False, 0.0, None

        if kind == "sign_group_emphasis":
            group = cond.get("group") or []
            val = self._sign_group_emphasis_val(metrics, group)
            if val >= float(cond.get("min", 0)):
                return True, weight, f"{'+'.join(group)} {val:.1f}"
            return False, 0.0, None

        if kind == "planet_status":
            st = self._planet_status(metrics, cond.get("planet"))
            strong_req = cond.get("strong")
            afflicted_req = cond.get("afflicted")
            ok = True
            if strong_req is not None:
                ok = ok and bool(st.get("strong") is True) == bool(strong_req)
            if afflicted_req is not None:
                ok = ok and bool(st.get("afflicted") is True) == bool(afflicted_req)
            if ok:
                return True, weight, f"{cond.get('planet')} status"
            return False, 0.0, None

        if kind == "aspect":
            p1, p2 = cond.get("pair", [None, None])
            cond_type = (cond.get("type") or "hard").lower()
            hard_only = cond_type == "hard"
            aspects = self._find_aspect(metrics, str(p1), str(p2), hard_only=hard_only)
            if not aspects:
                return False, 0.0, None
            # Check severities/orb
            max_orb = float(cond.get("max_orb") or 999)
            allowed_names = [str(x) for x in (cond.get("allowed_names") or []) if x]
            if cond_type == "any":
                for a in aspects:
                    if allowed_names and str(a.get("aspect")) not in allowed_names:
                        continue
                    orb = float(a.get("orb") or 999)
                    if orb <= max_orb:
                        return True, weight, f"{p1}-{p2} {a.get('aspect')} {orb:.2f}°"
                return False, 0.0, None
            if cond_type == "soft":
                for a in aspects:
                    if a.get("afflicting") is True:
                        continue
                    if allowed_names and str(a.get("aspect")) not in allowed_names:
                        continue
                    orb = float(a.get("orb") or 999)
                    if orb <= max_orb:
                        return True, weight, f"{p1}-{p2} soft {orb:.2f}°"
            else:
                min_sev = (cond.get("min_severity") or "").lower() or None
                for a in aspects:
                    sev = str(a.get("severity") or "").lower()
                    if allowed_names and str(a.get("aspect")) not in allowed_names:
                        continue
                    orb = float(a.get("orb") or 999)
                    sev_rank = {"mild":1, "moderate":2, "severe":3}.get(sev, 0)
                    min_rank = {"mild":1, "moderate":2, "severe":3}.get(min_sev or "mild", 1)
                    if sev_rank >= min_rank and orb <= max_orb:
                        return True, weight, f"{p1}-{p2} {sev} {orb:.2f}°"
            return False, 0.0, None

        if kind == "angle_aspect":
            planet = cond.get("planet")
            cond_type = (cond.get("type") or "hard").lower()
            hard_only = cond_type == "hard"
            aspects = self._find_angle_aspects(metrics, str(planet), hard_only=hard_only)
            if not aspects:
                return False, 0.0, None
            target_angle = cond.get("angle")
            allowed_names = [str(x) for x in (cond.get("allowed_names") or []) if x]
            max_orb = float(cond.get("max_orb") or 999)
            if cond_type == "any":
                for a in aspects:
                    if target_angle and str(a.get('angle')) != target_angle:
                        continue
                    if allowed_names and str(a.get("aspect")) not in allowed_names:
                        continue
                    orb = float(a.get("orb") or 999)
                    if orb <= max_orb:
                        return True, weight, f"{planet}-{a.get('angle')} {a.get('aspect')} {orb:.2f}°"
                return False, 0.0, None
            if cond_type == "soft":
                for a in aspects:
                    if target_angle and str(a.get('angle')) != target_angle:
                        continue
                    if a.get("afflicting") is True:
                        continue
                    if allowed_names and str(a.get("aspect")) not in allowed_names:
                        continue
                    orb = float(a.get("orb") or 999)
                    if orb <= max_orb:
                        return True, weight, f"{planet}-{a.get('angle')} soft {orb:.2f}°"
            else:
                min_sev = (cond.get("min_severity") or "").lower() or None
                for a in aspects:
                    if target_angle and str(a.get('angle')) != target_angle:
                        continue
                    if allowed_names and str(a.get("aspect")) not in allowed_names:
                        continue
                    sev = str(a.get("severity") or "").lower()
                    sev_rank = {"mild":1, "moderate":2, "severe":3}.get(sev, 0)
                    min_rank = {"mild":1, "moderate":2, "severe":3}.get(min_sev or "mild", 1)
                    if sev_rank >= min_rank:
                        return True, weight, f"{planet}-{a.get('angle')} {sev}"
            return False, 0.0, None

        if kind == "house_emphasis":
            houses = cond.get("houses") or []
            total = self._house_emphasis_total(metrics, houses)
            if total >= int(cond.get("min_total", 0) or 0):
                return True, weight, f"H{','.join(str(h) for h in houses)}={total}"
            return False, 0.0, None

        if kind == "house_afflicted":
            houses = cond.get("houses") or []
            any_flag = cond.get("any", True)
            hit = self._any_house_afflicted(metrics, houses)
            if (any_flag and hit) or (not any_flag and hit and self._house_emphasis_total(metrics, houses) >= 1):
                return True, weight, f"H{','.join(str(h) for h in houses)} afflicted"
            return False, 0.0, None

        if kind == "solar":
            # Engine-agnostic solar overlay condition using metrics['solar']
            solar = metrics.get('solar') or {}
            cond_map = solar.get('conditions') or {}
            dist_map = solar.get('distance_deg') or {}
            phase_map = solar.get('phase') or {}

            planets = cond.get('planets')
            planet = cond.get('planet')
            targets = []
            if isinstance(planets, list):
                targets = [str(x) for x in planets]
            elif isinstance(planet, str):
                targets = [planet]
            else:
                return False, 0.0, None

            want_cond = (cond.get('condition') or '').strip().lower() or None
            want_phase = (cond.get('phase') or '').strip().lower() or None
            max_dist = cond.get('max_dist')
            min_dist = cond.get('min_dist')

            def _norm_cond(s: str) -> str:
                s = (s or '').strip().lower()
                if s.startswith('under'):
                    return 'under the beams'
                return s

            # Validate each target
            for t in targets:
                c = _norm_cond(str(cond_map.get(t, '')))
                p = (phase_map.get(t) or '').strip().lower()
                d = dist_map.get(t)
                if want_cond and c != want_cond:
                    return False, 0.0, None
                if want_phase and p != want_phase:
                    return False, 0.0, None
                if max_dist is not None:
                    try:
                        if not (d is not None and float(d) <= float(max_dist)):
                            return False, 0.0, None
                    except Exception:
                        return False, 0.0, None
                if min_dist is not None:
                    try:
                        if not (d is not None and float(d) >= float(min_dist)):
                            return False, 0.0, None
                    except Exception:
                        return False, 0.0, None

            # Optional scaling by distance closeness within classical orb
            if bool(cond.get('scale_by_distance')) and want_cond and len(targets) == 1:
                try:
                    t = targets[0]
                    d = float(dist_map.get(t)) if dist_map.get(t) is not None else None
                    if d is not None:
                        max_orb = {
                            'cazimi': 0.283,  # 17 arcminutes
                            'combustion': 8.5,
                            'under the beams': 17.0,
                        }.get(want_cond, None)
                        if max_orb:
                            factor = max(0.0, min(1.0, (max_orb - float(d)) / max_orb))
                            sw = weight * factor
                            why = f"{t} {want_cond} {want_phase or ''} {d:.2f}° (x{factor:.2f})".strip()
                            return True, sw, why
                except Exception:
                    pass
            return True, weight, f"solar {want_cond or ''} {want_phase or ''} {', '.join(targets)}".strip()

        if kind == "degree_hit":
            labels = cond.get("labels") or []
            hits = self._degree_hits(metrics, labels)
            min_hits = int(cond.get("min_hits", 1) or 1)
            if hits >= min_hits:
                mult = float(cond.get("multiplier", 1.0) or 1.0)
                return True, weight * mult, f"degree hits {hits}"
            return False, 0.0, None

        if kind == "planet_area":
            # Morin-aware: require a planet's determination to specific life areas
            try:
                ps = (metrics.get('planet_area_scores') or {})
                planet = str(cond.get('planet') or '')
                if not planet or planet not in ps:
                    return False, 0.0, None
                areas = cond.get('areas') or []
                mode = str(cond.get('mode') or 'max').lower()
                vals: List[float] = []
                if areas and isinstance(areas, list):
                    for a in areas:
                        try:
                            vals.append(float(ps[planet].get(str(a), 0.0) or 0.0))
                        except Exception:
                            vals.append(0.0)
                else:
                    try:
                        vals = [float(v or 0.0) for v in (ps[planet] or {}).values()]
                    except Exception:
                        vals = []
                if not vals:
                    return False, 0.0, None
                agg = max(vals) if mode == 'max' else sum(vals)
                min_req = float(cond.get('min') or 0.5)
                if agg >= min_req:
                    areas_str = ','.join([str(a) for a in (areas or [])]) or 'any'
                    return True, weight, f"{planet} area[{areas_str}] {agg:.2f}"
            except Exception:
                return False, 0.0, None
            return False, 0.0, None

        if kind == "planet_in_sign":
            planet = cond.get("planet")
            sign = cond.get("sign")
            p_sign = self._planet_sign(metrics, str(planet))
            if p_sign and sign and p_sign.lower() == str(sign).lower():
                return True, weight, f"{planet} in {sign}"
            return False, 0.0, None

        if kind == "planet_in_house":
            planet = cond.get("planet")
            try:
                ph_map = metrics.get("planet_houses") or {}
                ph = int(ph_map.get(str(planet)) or 0)
            except Exception:
                ph = 0
            target: set = set()
            try:
                for h in (cond.get("houses") or []):
                    try:
                        target.add(int(h))
                    except Exception:
                        continue
            except Exception:
                pass
            try:
                if cond.get("house") is not None:
                    target.add(int(cond.get("house")))
            except Exception:
                pass
            if bool(cond.get("cadent")):
                target.update({3, 6, 9, 12})
            if bool(cond.get("angular")):
                target.update({1, 4, 7, 10})
            if bool(cond.get("succedent")):
                target.update({2, 5, 8, 11})

            if ph in target and ph != 0:
                return True, weight, f"{planet} in H{ph}"
            return False, 0.0, None

        if kind == "planet_sign_relation":
            planet = cond.get("planet")
            target_sign = cond.get("sign")
            relation = (cond.get("relation") or "").lower()
            p_sign = self._planet_sign(metrics, str(planet))
            if p_sign and target_sign:
                rel = self._sign_relation(p_sign, str(target_sign))
                if rel and rel.lower() == relation:
                    return True, weight, f"{planet} in {p_sign} {relation} {target_sign}"
            return False, 0.0, None

        if kind in ("planet_afflicted_by", "planet_afflicted"):
            planet = str(cond.get("planet") or "")
            if not planet:
                return False, 0.0, None
            by_list = cond.get("by") or []
            if not by_list:
                by_list = ["Mars", "Saturn", "Uranus", "Neptune", "Pluto"]
            by_set = {str(x) for x in by_list}
            min_sev = (cond.get("min_severity") or "").strip().lower() or None
            allowed_names = None
            if cond.get("aspect_names"):
                try:
                    allowed_names = {str(x) for x in cond.get("aspect_names")}
                except Exception:
                    allowed_names = None
            max_orb = float(cond.get("max_orb") or 999)
            min_count = int(cond.get("min_count") or 1)

            hits = 0
            for a in (metrics.get("planetary_aspects") or []):
                p1 = str(a.get("planet1") or "")
                p2 = str(a.get("planet2") or "")
                if planet not in (p1, p2):
                    continue
                other = p2 if p1 == planet else p1
                if other not in by_set:
                    continue
                if not a.get("afflicting"):
                    continue
                if allowed_names and str(a.get("aspect")) not in allowed_names:
                    continue
                if min_sev:
                    sev = str(a.get("severity") or "").strip().lower()
                    rank = {"mild":1, "moderate":2, "severe":3}.get(sev, 0)
                    need = {"mild":1, "moderate":2, "severe":3}.get(min_sev, 1)
                    if rank < need:
                        continue
                try:
                    orb = float(a.get("orb") or 999)
                except Exception:
                    orb = 999
                if orb > max_orb:
                    continue
                hits += 1
                if hits >= min_count:
                    return True, weight, f"{planet} afflicted by {','.join(sorted(by_set))}"
            return False, 0.0, None

        if kind == "sect":
            # Support checks against chart sect roles and per-planet flags
            sect = metrics.get('sect') or {}
            if not sect:
                return False, 0.0, None
            role = (cond.get('role') or '').strip().lower() or None
            planet = str(cond.get('planet') or '')
            if role:
                # role in {'benefic_of_sect','malefic_of_sect'}
                if role in {'benefic_of_sect','malefic_of_sect'}:
                    who = sect.get('benefic_of_sect') if role == 'benefic_of_sect' else sect.get('malefic_of_sect')
                    if planet and who == planet:
                        return True, weight, f"sect {role}={who}"
                    return False, 0.0, None
            # Per-planet flags: in_sect / hayz
            want_in_sect = cond.get('in_sect')
            want_hayz = cond.get('hayz')
            if planet:
                try:
                    rows = sect.get('planets') or []
                    row = next((r for r in rows if str(r.get('planet')) == planet), None)
                except Exception:
                    row = None
                if not row:
                    return False, 0.0, None
                ok = True
                if want_in_sect is not None:
                    ok = ok and (bool(row.get('in_sect')) == bool(want_in_sect))
                if want_hayz is not None:
                    ok = ok and (bool(row.get('hayz')) == bool(want_hayz))
                if ok:
                    why_bits = []
                    if want_in_sect is not None:
                        why_bits.append('in-sect' if want_in_sect else 'out-of-sect')
                    if want_hayz is not None:
                        why_bits.append('hayz' if want_hayz else 'non-hayz')
                    return True, weight, f"{planet} sect {' & '.join(why_bits)}".strip()
            return False, 0.0, None

        if kind == "flag":
            name = cond.get("name")
            if name and bool((metrics.get("flags") or {}).get(name)):
                eff = str(cond.get("effect", "")).strip()
                if eff.startswith("+"):
                    try:
                        bonus = float(eff[1:])
                    except Exception:
                        bonus = 5.0
                else:
                    bonus = 5.0
                return True, bonus, f"flag:{name}"
            return False, 0.0, None

        return False, 0.0, None

    def evaluate(
        self,
        metrics: Dict[str, Any],
        limit: int = 10,
        min_score: float = 18.0,
        summary_context: Optional[str] = "default",
    ) -> Dict[str, Any]:
        normalized_summary_context = _normalize_summary_context(summary_context)
        traits = []
        # Load Morin keywords dictionary (optional)
        mk = _load_morin_keywords_safe()
        corpus = _load_trait_corpus_support(self.root)
        for t in self.catalog.get("traits", []):
            logic = t.get("logic") or {}
            family_key = _logic_signature_key(logic)
            source_status = _trait_source_status(t)
            source_lineage, source_lineage_label = _trait_source_lineage(t, source_status)
            provisional = source_status == "provisional"
            summary_surface = _trait_summary_surface(t)
            summary_eligible = summary_surface != "specialized"
            summary_bucket = _trait_summary_bucket(t)
            summary_priority = _trait_summary_priority(t, summary_bucket)
            summary_context_priority = _trait_summary_context_priority(t, normalized_summary_context)
            base = float(logic.get("base", 0) or 0)
            total = base
            positive_hits = 0
            dampener_hits = 0
            evidence: List[str] = []
            max_support = max(0.0, base)
            support_total = 0

            for b in logic.get("boosts", []) or []:
                try:
                    max_support += max(0.0, float(b.get("weight", 0) or 0))
                except Exception:
                    pass
                try:
                    if float(b.get("weight", 0) or 0) > 0:
                        support_total += 1
                except Exception:
                    pass
                ok, w, why = self._eval_condition(metrics, b)
                if ok:
                    total += w
                    if w > 0:
                        positive_hits += 1
                    if why:
                        evidence.append(f"+ {why} ({w:+.0f})")
            for d in logic.get("dampeners", []) or []:
                ok, w, why = self._eval_condition(metrics, d)
                if ok:
                    total += w  # note: weight is negative in schema for dampeners
                    dampener_hits += 1
                    if why:
                        evidence.append(f"{why} ({w:+.0f})")
            for e in logic.get("escalators", []) or []:
                try:
                    max_support += max(0.0, float(e.get("weight", 0) or 0))
                except Exception:
                    pass
                try:
                    if float(e.get("weight", 0) or 0) > 0:
                        support_total += 1
                except Exception:
                    pass
                ok, w, why = self._eval_condition(metrics, e)
                if ok:
                    total += w
                    if w > 0:
                        positive_hits += 1
                    if why:
                        evidence.append(f"↑ {why} ({w:+.0f})")

            # Normalize against each trait's own attainable positive support.
            raw_score = max(0.0, total)
            if max_support > 0:
                score = max(0.0, min(100.0, (raw_score / max_support) * 100.0))
            else:
                score = 0.0

            # Require corroboration before a trait graduates to the strongest bands.
            if score >= 70 and positive_hits >= 2:
                band = "strong"
            elif score >= 50 and (positive_hits >= 2 or score >= 85):
                band = "likely"
            elif score >= 30 and positive_hits >= 1:
                band = "possible"
            else:
                band = "weak"

            morin_keywords = _derive_trait_keywords(evidence, metrics, mk)
            traits.append({
                "id": t.get("id"),
                "name": t.get("name"),
                "domain": t.get("domain"),
                "description": t.get("description"),
                "confidence": t.get("confidence"),
                "sources": t.get("sources"),
                "family_key": family_key,
                "source_status": source_status,
                "source_lineage": source_lineage,
                "source_lineage_label": source_lineage_label,
                "provisional": provisional,
                "summary_surface": summary_surface,
                "summary_eligible": summary_eligible,
                "summary_bucket": summary_bucket,
                "summary_priority": summary_priority,
                "summary_context_priority": summary_context_priority,
                "score": round(score, 1),
                "raw_score": round(raw_score, 1),
                "max_score": round(max_support, 1),
                "support_hits": positive_hits,
                "support_total": support_total,
                "dampener_hits": dampener_hits,
                "band": band,
                "polarity": t.get("polarity"),
                "evidence": evidence,
                # Trait-level Morin keywords (3–5 tags, non-scoring)
                "keywords": morin_keywords,
            })

        traits_sorted = sorted(traits, key=lambda x: (-x["score"], x.get("id") or ""))
        # Return traits that meet minimum indication threshold (default >=18)
        try:
            thr = float(min_score)
        except Exception:
            thr = 18.0
        indicated = [t for t in traits_sorted if float(t.get("score", 0)) >= thr]
        for trait in indicated:
            morin_keywords = list(trait.get("keywords") or [])
            citations = _build_corpus_citations(trait, morin_keywords, list(trait.get("evidence") or []), corpus, limit=3)
            keyword_layers = _keyword_layers_from_citations(morin_keywords, citations)
            trait["keyword_layers"] = keyword_layers
            trait["citations"] = citations
            trait["citation_summary"] = _citation_summary(citations)
            trait["enrichment_status"] = {
                "morin_keywords": "present" if keyword_layers.get("morin") else "missing",
                "corpus_keywords": "present" if any(keyword_layers.get(layer) for layer in ("classical", "modern", "textbook")) else "missing",
                "citations": "present" if citations else "missing",
            }
        family_groups: Dict[str, List[Dict[str, Any]]] = {}
        family_reps: List[Dict[str, Any]] = []
        for trait in indicated:
            key = str(trait.get("family_key") or trait.get("id") or "")
            family_groups.setdefault(key, []).append(trait)
        for group in family_groups.values():
            if _uses_contextual_summary_priority(normalized_summary_context):
                rep = sorted(
                    group,
                    key=lambda trait: _trait_summary_rank_key(trait, normalized_summary_context),
                )[0]
            else:
                rep = group[0]
            related = [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "polarity": item.get("polarity"),
                    "score": item.get("score"),
                }
                for item in group
                if item is not rep
            ]
            for item in group:
                item["family_size"] = len(group)
                item["family_representative"] = item is rep
                item["related_traits"] = related if item is rep else []
            family_reps.append(rep)
        top_limit = max(3, min(limit, 10))
        curated_reps = [t for t in family_reps if not t.get("provisional")]
        summary_candidates = curated_reps or family_reps
        preferred = [t for t in summary_candidates if t.get("band") != "weak"]
        if not preferred:
            preferred = summary_candidates
        surfaced = [t for t in preferred if t.get("summary_eligible") is not False]
        if not surfaced:
            surfaced = preferred or indicated
        general = [t for t in surfaced if str(t.get("summary_surface") or "") == "general"]
        caution = [t for t in surfaced if str(t.get("summary_surface") or "") == "caution"]
        summary_pool = (general + caution) if (general or caution) else surfaced
        bucket_groups: Dict[str, List[Dict[str, Any]]] = {}
        for trait in summary_pool:
            bucket_groups.setdefault(str(trait.get("summary_bucket") or "character"), []).append(trait)
        bucket_heads = []
        for group in bucket_groups.values():
            rep = sorted(
                group,
                key=lambda trait: _trait_group_head_key(trait, normalized_summary_context),
            )[0]
            bucket_heads.append(rep)
        bucket_heads = sorted(
            bucket_heads,
            key=lambda trait: _trait_bucket_head_key(trait, normalized_summary_context),
        )
        summary_traits = sorted(
            summary_pool,
            key=lambda trait: _trait_summary_rank_key(trait, normalized_summary_context),
        )
        top_traits: List[Dict[str, Any]] = []
        seen_ids = set()
        for trait in bucket_heads:
            top_traits.append(trait)
            seen_ids.add(str(trait.get("id") or ""))
            if len(top_traits) >= top_limit:
                break
        if len(top_traits) < top_limit:
            fill_pool = (
                summary_traits
                if _uses_contextual_summary_priority(normalized_summary_context)
                else summary_pool
            )
            for trait in fill_pool:
                trait_id = str(trait.get("id") or "")
                if trait_id in seen_ids:
                    continue
                top_traits.append(trait)
                seen_ids.add(trait_id)
                if len(top_traits) >= top_limit:
                    break
        top_traits_by_polarity = {
            polarity: [
                trait
                for trait in summary_traits
                if str(trait.get("polarity") or "").strip().lower() == polarity
            ][:top_limit]
            for polarity in ("positive", "neutral", "negative")
        }
        summary = {
            "dominant_element": max((metrics.get("element_balance") or {}).items(), key=lambda kv: kv[1])[0] if metrics.get("element_balance") else None,
            "dominant_modality": max((metrics.get("modality_balance") or {}).items(), key=lambda kv: kv[1])[0] if metrics.get("modality_balance") else None,
            "flags": metrics.get("flags"),
        }
        guidance = compute_guidance(metrics)
        return {
            "summary": summary,
            "top_traits": top_traits,
            "summary_traits": summary_traits,
            "top_traits_by_polarity": top_traits_by_polarity,
            "traits": indicated,
            "guidance": guidance,
            "trait_enrichment_meta": {
                "summary_context": normalized_summary_context,
                "morin_keywords_policy": "canonical_non_scoring",
                "corpus_enrichment_policy": "parallel_non_scoring",
                "corpus_index_path": corpus.get("index_path"),
                "enabled_layers": ["morin", "classical", "modern", "textbook"],
                "citation_limit_per_trait": 3,
                "version": 1,
            },
        }


# ---------- Guidance (Do/Don't) from dictionary CSV ----------
def _load_dictionary_csv() -> List[Dict[str, str]]:
    try:
        rows: List[Dict[str, str]] = []
        import csv
        candidates: List[str] = []
        for root in _candidate_backend_roots():
            candidates.extend(
                [
                    os.path.join(root, 'Phsychology traits', 'astrology_dictionary_starter.csv'),
                    os.path.join(root, 'Psychology traits', 'astrology_dictionary_starter.csv'),
                    os.path.join(root, 'traits', 'knowledge', 'astrology_dictionary_starter.csv'),
                ]
            )
        seen = set()
        for csv_path in candidates:
            norm = os.path.normcase(os.path.normpath(csv_path))
            if norm in seen or not os.path.exists(csv_path):
                continue
            seen.add(norm)
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(r)
            if rows:
                return rows
        return rows
    except Exception:
        return []


def _dict_by_category(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, Dict[str, str]]]:
    out: Dict[str, Dict[str, Dict[str, str]]] = {}
    for r in rows:
        cat = (r.get('Category') or '').strip()
        term = (r.get('Term') or '').strip()
        if not cat or not term:
            continue
        out.setdefault(cat, {})[term] = r
    return out


def compute_guidance(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = _load_dictionary_csv()
    if not rows:
        # If CSV missing, still allow Morin-based guidance additions below
        rows = []
    dic = _dict_by_category(rows)
    suggestions: List[Dict[str, Any]] = []

    # Strong and afflicted planets
    ps = metrics.get('planet_status') or {}
    strong = [p for p, st in ps.items() if st.get('strong')]
    afflicted = [p for p, st in ps.items() if st.get('afflicted')]
    for p in strong[:2]:
        row = (dic.get('Planet') or {}).get(p)
        if row:
            suggestions.append({ 'category': 'Planet', 'term': p, 'do': row.get('Do'), 'dont': row.get("Don't") })
    for p in afflicted[:2]:
        row = (dic.get('Planet') or {}).get(p)
        if row:
            suggestions.append({ 'category': 'Planet', 'term': p, 'do': row.get('Do'), 'dont': row.get("Don't") })

    # Top sign by emphasis
    se = metrics.get('sign_emphasis') or {}
    if se:
        top_sign = max(se.items(), key=lambda kv: kv[1])[0]
        row = (dic.get('Sign') or {}).get(top_sign)
        if row:
            suggestions.append({ 'category': 'Sign', 'term': top_sign, 'do': row.get('Do'), 'dont': row.get("Don't") })

    # Top emphasized house
    he = (metrics.get('house') or {}).get('emphasis') or {}
    if he:
        top_house = max(he.items(), key=lambda kv: int(kv[1] or 0))[0]
        term = f"{top_house}st House" if top_house == '1' else (f"{top_house}nd House" if top_house == '2' else (f"{top_house}rd House" if top_house == '3' else f"{top_house}th House"))
        row = (dic.get('House') or {}).get(term)
        if row:
            suggestions.append({ 'category': 'House', 'term': term, 'do': row.get('Do'), 'dont': row.get("Don't") })

    # Tightest hard aspect
    pairs = metrics.get('planetary_aspects') or []
    hard = [a for a in pairs if a.get('afflicting')]
    if hard:
        tight = min(hard, key=lambda a: abs(float(a.get('orb') or 999)))
        aname = str(tight.get('aspect') or '')
        # Map common names to dictionary terms
        name_map = {
            'Square': 'Square (90°)', 'Opposition': 'Opposition (180°)', 'Conjunction': 'Conjunction (0°)', 'Trine': 'Trine (120°)', 'Sextile': 'Sextile (60°)'
        }
        term = name_map.get(aname, aname)
        row = (dic.get('Aspect') or {}).get(term)
        if row:
            suggestions.append({ 'category': 'Aspect', 'term': term, 'do': row.get('Do'), 'dont': row.get("Don't") })

    # --- Morin-based extensions (non-replacing) ---
    try:
        mk = _load_morin_keywords_safe()
        # Top emphasized house → Morin house keywords as a compact guidance item
        he = (metrics.get('house') or {}).get('emphasis') or {}
        if he:
            top_house = max(he.items(), key=lambda kv: int(kv[1] or 0))[0]
            hrow = (mk.get('houses') or {}).get(str(top_house), {})
            hk = hrow.get('keywords_primary') or []
            if hk:
                do = 'Lean into: ' + ', '.join(hk[:3])
                dont = 'Avoid overemphasis on contrary matters'  # generic guard
                suggestions.append({ 'category': 'Morin House', 'term': f'H{top_house}', 'do': do, 'dont': dont })
        # Sect hints
        sect = metrics.get('sect') or {}
        if sect:
            ben = sect.get('benefic_of_sect')
            mal = sect.get('malefic_of_sect')
            if ben:
                pk = (mk.get('planets') or {}).get(str(ben), {}).get('keywords_primary') or []
                do = 'Leverage: ' + ', '.join(pk[:2]) if pk else 'Leverage benefic-of-sect support'
                suggestions.append({ 'category': 'Sect', 'term': f'Benefic of sect {ben}', 'do': do, 'dont': None })
            if mal:
                sk = (mk.get('sect') or {}).get('malefic_out_of_sect') or ['harsher_effects']
                dont = 'Guard ' + ', '.join(sk[:2])
                suggestions.append({ 'category': 'Sect', 'term': f'Malefic of sect {mal}', 'do': None, 'dont': dont })
    except Exception:
        pass

    # Deduplicate by (category, term)
    seen = set()
    unique: List[Dict[str, Any]] = []
    for s in suggestions:
        key = (s.get('category'), s.get('term'))
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
    return unique[:8]


# ---------- Morin keywords helpers (non-scoring) ----------
def _load_morin_keywords_safe() -> Dict[str, Any]:
    try:
        candidates: List[str] = []
        for root in _candidate_backend_roots():
            candidates.extend(
                [
                    os.path.join(root, 'traits', 'knowledge', 'morin_keywords.json'),
                    os.path.join(root, 'traits', 'morin_keywords.json'),
                ]
            )
        seen = set()
        for p in candidates:
            norm = os.path.normcase(os.path.normpath(p))
            if norm in seen:
                continue
            seen.add(norm)
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    obj = json.load(f)
                return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    return {}


def _house_for_area(area: str) -> Optional[int]:
    m = {
        'life': 1, 'health': 6, 'wealth': 2, 'relationships': 7,
        'honors': 10, 'death': 8, 'belief': 9, 'home': 4,
        'children': 5, 'friends': 11, 'short_travel': 3,
    }
    return m.get(str(area))


def _derive_trait_keywords(evidence: List[str], metrics: Dict[str, Any], mk: Dict[str, Any]) -> List[str]:
    try:
        planets = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn']
        planet_hits: Dict[str, int] = {}
        areas: List[str] = []
        # Parse evidence strings
        for line in evidence or []:
            s = str(line)
            for p in planets:
                if p in s:
                    planet_hits[p] = planet_hits.get(p, 0) + 1
            # area[...] tokens
            if 'area[' in s:
                try:
                    seg = s.split('area[')[1]
                    inside = seg.split(']')[0]
                    for tok in inside.split(','):
                        tok = tok.strip()
                        if tok:
                            areas.append(tok)
                except Exception:
                    pass
            # sect tokens
            if s.startswith('sect '):
                # Example: 'sect benefic_of_sect=Jupiter'
                parts = s.split()
                if len(parts) >= 2 and '=' in parts[1]:
                    role, who = parts[1].split('=', 1)
                    areas.append(role.strip())

        # Fallback to strongest planet by metrics if no evidence planet found
        if not planet_hits:
            try:
                ps = metrics.get('planet_status') or {}
                for p, st in ps.items():
                    if st.get('strong'):
                        planet_hits[p] = 1
            except Exception:
                pass

        # Pick top planet and up to two areas
        top_planet = None
        if planet_hits:
            top_planet = max(planet_hits.items(), key=lambda kv: kv[1])[0]
        houses: List[int] = []
        for a in areas:
            h = _house_for_area(a)
            if h and h not in houses:
                houses.append(h)

        tags: List[str] = []
        # Add house tags from Morin dictionary
        try:
            houses = houses[:2]
            for h in houses:
                row = (mk.get('houses') or {}).get(str(h), {})
                kws = row.get('keywords_primary') or []
                for kw in kws[:2]:
                    if kw not in tags:
                        tags.append(kw)
        except Exception:
            pass
        # Add planet tags
        try:
            if top_planet:
                prow = (mk.get('planets') or {}).get(str(top_planet), {})
                pk = prow.get('keywords_primary') or []
                for kw in pk[:2]:
                    if kw not in tags:
                        tags.append(kw)
        except Exception:
            pass
        # Ensure up to 5 tags
        return tags[:5]
    except Exception:
        return []


_TRAIT_CORPUS_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "through", "their",
    "trait", "traits", "positive", "negative", "neutral", "strong", "likely", "possible",
    "source", "derived", "general", "style", "character", "pattern", "quality", "state",
    "mind", "life", "self", "other", "drive", "social", "temperament", "cognitive",
}


def _candidate_repo_roots(root: Optional[str] = None) -> List[str]:
    roots: List[str] = []
    if root:
        cur = os.path.normpath(root)
        for _ in range(3):
            roots.append(cur)
            parent = os.path.dirname(cur)
            if not parent or parent == cur:
                break
            cur = parent
    env_repo = os.environ.get("HORARY_REPO_ROOT")
    if env_repo:
        roots.append(os.path.normpath(env_repo))
    for backend_root in _candidate_backend_roots():
        roots.append(os.path.normpath(backend_root))
        parent = os.path.dirname(os.path.normpath(backend_root))
        if parent:
            roots.append(parent)

    out: List[str] = []
    seen = set()
    for item in roots:
        if not item:
            continue
        key = os.path.normcase(os.path.normpath(item))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _load_trait_corpus_support(root: Optional[str] = None) -> Dict[str, Any]:
    explicit_dir = os.environ.get("HORARY_TRAIT_CORPUS_DIR")
    explicit_index = os.environ.get("HORARY_TRAIT_CORPUS_INDEX")
    explicit_catalog = os.environ.get("HORARY_TRAIT_CORPUS_CATALOG")
    index_candidates: List[str] = []
    catalog_candidates: List[str] = []

    if explicit_index:
        index_candidates.append(os.path.normpath(explicit_index))
    if explicit_catalog:
        catalog_candidates.append(os.path.normpath(explicit_catalog))
    if explicit_dir:
        corpus_dir = os.path.normpath(explicit_dir)
        index_candidates.append(os.path.join(corpus_dir, "chunk_index.jsonl"))
        catalog_candidates.append(os.path.join(corpus_dir, "catalog.json"))

    for backend_root in _candidate_backend_roots():
        bundled_dirs = [
            os.path.join(backend_root, "traits", "corpus", "new_sources_inspection"),
            os.path.join(backend_root, "extracted_text_docs", "new_sources_inspection"),
            os.path.join(backend_root, "new_sources_inspection"),
        ]
        for corpus_dir in bundled_dirs:
            index_candidates.append(os.path.join(corpus_dir, "chunk_index.jsonl"))
            catalog_candidates.append(os.path.join(corpus_dir, "catalog.json"))

    for repo_root in _candidate_repo_roots(root):
        corpus_dir = os.path.join(repo_root, "extracted_text_docs", "new_sources_inspection")
        index_candidates.append(os.path.join(corpus_dir, "chunk_index.jsonl"))
        catalog_candidates.append(os.path.join(corpus_dir, "catalog.json"))

    def _first_existing(paths: List[str]) -> Optional[str]:
        seen = set()
        for path in paths:
            if not path:
                continue
            norm = os.path.normcase(os.path.normpath(path))
            if norm in seen:
                continue
            seen.add(norm)
            if os.path.exists(path):
                return path
        return None

    index_path = _first_existing(index_candidates)
    catalog_path = _first_existing(catalog_candidates)
    if not index_path:
        return {"index_path": None, "catalog_path": catalog_path, "chunks": [], "guide_by_title": {}}

    chunks: List[Dict[str, Any]] = []
    try:
        with open(index_path, "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or "").strip()
                source_name = str(row.get("source_name") or "").strip()
                heading = str(row.get("heading") or "").strip()
                excerpt = str(row.get("excerpt") or "").strip()
                search_blob = " ".join(part for part in (title, source_name, heading, excerpt) if part).lower()
                row["_search_blob"] = search_blob
                chunks.append(row)
    except Exception:
        chunks = []

    guide_by_title: Dict[str, str] = {}
    if catalog_path and os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as handle:
                rows = json.load(handle)
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    title = str(row.get("title") or "").strip()
                    guide_path = str(row.get("guide_path") or "").strip()
                    if title and guide_path and title not in guide_by_title:
                        guide_by_title[title] = guide_path
        except Exception:
            guide_by_title = {}

    return {
        "index_path": index_path,
        "catalog_path": catalog_path,
        "chunks": chunks,
        "guide_by_title": guide_by_title,
    }


def _trait_query_terms(trait: Dict[str, Any], morin_keywords: List[str], evidence: List[str]) -> List[Tuple[str, float]]:
    weighted: List[Tuple[str, float]] = []

    def add(term: str, weight: float) -> None:
        txt = re.sub(r"[_/]+", " ", str(term or "").strip().lower())
        txt = re.sub(r"[^a-z0-9 +.-]+", " ", txt)
        txt = re.sub(r"\s{2,}", " ", txt).strip()
        if len(txt) < 3:
            return
        if txt in _TRAIT_CORPUS_STOPWORDS:
            return
        weighted.append((txt, float(weight)))

    name = str(trait.get("name") or "").strip()
    if name:
        add(name, 7.0)
        for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", name):
            add(tok, 3.0)
    trait_id = str(trait.get("id") or "").replace("_", " ").strip()
    if trait_id:
        add(trait_id, 5.0)
        for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", trait_id):
            add(tok, 2.0)
    domain = str(trait.get("domain") or "").replace("_", " ").strip()
    if domain:
        add(domain, 4.0)
        for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", domain):
            add(tok, 2.0)
    for kw in morin_keywords[:5]:
        add(str(kw), 4.0)
    for line in evidence[:6]:
        for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{3,}", str(line)):
            add(tok, 1.25)

    dedup: Dict[str, float] = {}
    for term, weight in weighted:
        dedup[term] = max(float(weight), float(dedup.get(term, 0.0)))
    return sorted(dedup.items(), key=lambda item: (-item[1], item[0]))


def _corpus_source_info(row: Dict[str, Any]) -> Tuple[str, str]:
    blob = " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("source_name") or ""),
        ]
    ).lower()
    if "rudhyar" in blob:
        return "modern", "Dane Rudhyar"
    if "demetra george" in blob or "rubedo press" in blob:
        return "classical", "Demetra George"
    if "compendium of astrology" in blob or "lineman" in blob or "popelka" in blob:
        return "textbook", "Rose Lineman / Jan Popelka"
    return "classical", "Corpus source"


def _build_corpus_citations(
    trait: Dict[str, Any],
    morin_keywords: List[str],
    evidence: List[str],
    corpus: Dict[str, Any],
    limit: int = 3,
) -> List[Dict[str, Any]]:
    rows = corpus.get("chunks") or []
    if not rows:
        return []

    terms = _trait_query_terms(trait, morin_keywords, evidence)
    if not terms:
        return []

    ranked: List[Tuple[float, Dict[str, Any], List[str]]] = []
    for row in rows:
        text = str(row.get("_search_blob") or "")
        if not text:
            continue
        score = 0.0
        matched: List[str] = []
        for term, weight in terms:
            if term in text:
                score += float(weight)
                if term not in matched:
                    matched.append(term)
        if not matched:
            continue
        heading = str(row.get("heading") or "").lower()
        for term in matched[:3]:
            if term in heading:
                score += 0.5
        ranked.append((score, row, matched[:5]))

    ranked.sort(
        key=lambda item: (
            -float(item[0]),
            str(item[1].get("title") or ""),
            str(item[1].get("chunk_id") or ""),
        )
    )

    citations: List[Dict[str, Any]] = []
    seen_paths = set()
    guide_by_title = corpus.get("guide_by_title") or {}
    for score, row, matched in ranked:
        path = str(row.get("path") or "")
        if not path:
            continue
        if path in seen_paths:
            continue
        seen_paths.add(path)
        pages = row.get("pages") or []
        lineage, source_label = _corpus_source_info(row)
        title = str(row.get("title") or "")
        excerpt = re.sub(r"\s+", " ", str(row.get("excerpt") or "")).strip()
        if len(excerpt) > 260:
            excerpt = excerpt[:257].rstrip() + "..."
        citations.append(
            {
                "citation_id": f"{source_label.lower().replace(' ', '-')}:chunk-{str(row.get('chunk_id') or '').strip()}",
                "source_lineage": lineage,
                "source_label": source_label,
                "work_title": title,
                "author": source_label,
                "locator": {
                    "chunk_id": str(row.get("chunk_id") or ""),
                    "chunk_path": path,
                    "page_start": int(pages[0]) if isinstance(pages, list) and pages else None,
                    "page_end": int(pages[-1]) if isinstance(pages, list) and pages else None,
                    "guide_path": str(guide_by_title.get(title) or "") or None,
                },
                "excerpt": excerpt,
                "relevance": round(float(score), 2),
                "topic_tags": matched,
            }
        )
        if len(citations) >= max(1, int(limit or 3)):
            break
    return citations


def _keyword_layers_from_citations(morin_keywords: List[str], citations: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    layers: Dict[str, List[str]] = {
        "morin": list(morin_keywords[:5]),
        "classical": [],
        "modern": [],
        "textbook": [],
    }
    for citation in citations or []:
        lineage = str(citation.get("source_lineage") or "").strip().lower()
        if lineage not in layers:
            continue
        for tag in citation.get("topic_tags") or []:
            text = str(tag or "").strip()
            if not text or text in layers[lineage]:
                continue
            layers[lineage].append(text)
    return layers


def _citation_summary(citations: List[Dict[str, Any]]) -> Dict[str, Any]:
    lineages: List[str] = []
    for citation in citations or []:
        lineage = str(citation.get("source_lineage") or "").strip().lower()
        if lineage and lineage not in lineages:
            lineages.append(lineage)
    return {
        "count": len(citations or []),
        "lineages": lineages,
        "top_source": str((citations or [{}])[0].get("source_label") or "") if citations else None,
    }
