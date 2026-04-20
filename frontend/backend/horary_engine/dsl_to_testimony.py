"""Dispatch DSL primitives to testimony tokens with metadata."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .dsl import (
    AccidentalDignity,
    Aspect,
    Collection,
    EssentialDignity,
    L10,
    LQ,
    Moon,
    Reception,
    Role,
    Translation,
)
try:  # pragma: no cover - allow package/script execution
    from ..models import Aspect as AspectType
    from ..models import Planet
except ImportError:  # pragma: no cover
    from models import Aspect as AspectType
    from models import Planet

from .polarity_weights import TestimonyKey

Dispatch = Dict[str, Any]


def _resolve_role(role: Role, contract: Dict[str, Planet]) -> Optional[Planet]:
    mapping = {"l1": "querent", "lq": "quesited"}
    key = mapping.get(role.name.lower(), role.name.lower())
    return contract.get(key)


def _role_tag(role: Role, contract: Dict[str, Planet]) -> str:
    if role is LQ:
        house = contract.get("quesited_house", 7)
        return f"L{house}"
    return role.name.upper()


def _collect_roles(obj: Any, contract: Dict[str, Planet]) -> Dict[str, Planet]:
    roles: Dict[str, Planet] = {}
    for attr in (
        "actor",
        "receiver",
        "received",
        "translator",
        "from_actor",
        "to_actor",
        "actor1",
        "actor2",
        "collector",
    ):
        value = getattr(obj, attr, None)
        if isinstance(value, Role):
            tag = _role_tag(value, contract).lower()
            planet = _resolve_role(value, contract)
            if planet is not None:
                roles[tag] = planet
    return roles


def _dispatch_aspect(asp: Aspect, contract: Dict[str, Planet]) -> List[Dispatch]:
    results: List[Dispatch] = []
    actor1_planet = _resolve_role(asp.actor1, contract) if isinstance(asp.actor1, Role) else asp.actor1
    actor2_planet = _resolve_role(asp.actor2, contract) if isinstance(asp.actor2, Role) else asp.actor2
    if (
        asp.actor1 == Moon
        and actor2_planet == Planet.SUN
        and asp.aspect == AspectType.TRINE
        and asp.applying
    ):
        results.append(
            {
                "key": TestimonyKey.MOON_APPLYING_TRINE_EXAMINER_SUN,
                "house": None,
                "factor": 1.0,
                "roles": list(_collect_roles(asp, contract).keys()),
            }
        )

    role_map = _collect_roles(asp, contract)
    if role_map:
        tag1 = _role_tag(asp.actor1, contract) if isinstance(asp.actor1, Role) else asp.actor1.name
        tag2 = _role_tag(asp.actor2, contract) if isinstance(asp.actor2, Role) else asp.actor2.name
        p1 = _resolve_role(asp.actor1, contract) if isinstance(asp.actor1, Role) else asp.actor1
        p2 = _resolve_role(asp.actor2, contract) if isinstance(asp.actor2, Role) else asp.actor2
        results.append(
            {
                "key": f"ASPECT_{tag1}_{asp.aspect.name}_{tag2}",
                "house": None,
                "factor": 1.0,
                "roles": list(role_map.keys()),
                "planets": [p1, p2],
            }
        )
    return results


def dispatch(obj: Any, contract: Optional[Dict[str, Planet]] = None) -> List[Dispatch]:
    """Return testimony mappings for a DSL primitive."""
    contract = contract or {}
    if isinstance(obj, Aspect):
        return _dispatch_aspect(obj, contract)
    if isinstance(obj, Translation):
        role_map = _collect_roles(obj, contract)
        aspect_name = getattr(obj.aspect, "name", "CONJUNCTION")
        reception_tag = "WITH_RECEPTION" if getattr(obj, "reception", False) else "WITHOUT_RECEPTION"
        token_name = f"TRANSLATION_{aspect_name}_{reception_tag}"
        key = getattr(TestimonyKey, token_name, TestimonyKey.PERFECTION_TRANSLATION_OF_LIGHT)
        return [{
            "key": key,
            "house": None,
            "factor": 1.0,
            "roles": list(role_map.keys()),
            "planets": list(role_map.values()),
            "applying": obj.applying,
        }]
    if isinstance(obj, Collection):
        role_map = _collect_roles(obj, contract)
        aspect_name = getattr(obj.aspect, "name", "CONJUNCTION")
        reception_tag = "WITH_RECEPTION" if getattr(obj, "reception", False) else "WITHOUT_RECEPTION"
        token_name = f"COLLECTION_{aspect_name}_{reception_tag}"
        key = getattr(TestimonyKey, token_name, TestimonyKey.PERFECTION_COLLECTION_OF_LIGHT)
        return [{
            "key": key,
            "house": None,
            "factor": 1.0,
            "roles": list(role_map.keys()),
            "planets": list(role_map.values()),
            "applying": obj.applying,
        }]
    if isinstance(obj, Reception):
        if obj.receiver == L10:
            role_map = _collect_roles(obj, contract)
            return [{
                "key": TestimonyKey.L10_FORTUNATE,
                "house": 10,
                "factor": 1.0,
                "roles": list(role_map.keys()),
                "planets": list(role_map.values()),
            }]
    if isinstance(obj, EssentialDignity):
        if isinstance(obj.score, str) and obj.score.lower() == "detriment":
            role_map = _collect_roles(obj, contract)
            return [{
                "key": TestimonyKey.ESSENTIAL_DETRIMENT,
                "house": None,
                "factor": 1.0,
                "roles": list(role_map.keys()),
                "planets": list(role_map.values()),
            }]
    if isinstance(obj, AccidentalDignity):
        if isinstance(obj.score, str):
            score = obj.score.lower()
            token = None
            if score == "retro":
                token = TestimonyKey.ACCIDENTAL_RETROGRADE
            elif score == "sign_change":
                actor = _resolve_role(obj.actor, contract) if isinstance(obj.actor, Role) else obj.actor
                if actor is not None:
                    token_name = f"SIGN_CHANGE_{actor.name}"
                    token = getattr(TestimonyKey, token_name, None)
            if token is not None:
                role_map = _collect_roles(obj, contract)
                planets = list(role_map.values()) or [
                    _resolve_role(obj.actor, contract) if isinstance(obj.actor, Role) else obj.actor
                ]
                return [{
                    "key": token,
                    "house": None,
                    "factor": 1.0,
                    "roles": list(role_map.keys()),
                    "planets": planets,
                }]
    return []


__all__ = ["dispatch"]
