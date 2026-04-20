"""Aggregate testimonies into a score with a contribution ledger."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .polarity import Polarity
from .polarity_weights import (
    FAMILY_TABLE,
    KIND_TABLE,
    POLARITY_TABLE,
    WEIGHT_TABLE,
    TestimonyKey,
)


def _get_testimony_hierarchy_weight(token: TestimonyKey, contract: Dict[str, Any] | None = None) -> float:
    """Return category-aware weight with traditional hierarchy emphasis."""
    contract = contract or {}
    category_rules = contract.get("category_rules", {}) if isinstance(contract, dict) else {}
    base_weight = WEIGHT_TABLE.get(token, 1.0)
    token_name = token.value

    # Major testimonies dominate.
    if (
        token_name.startswith("perfection_")
        or token_name.startswith("translation_")
        or token_name.startswith("collection_")
        or "mutual_reception" in token_name
    ):
        return base_weight * 25.0

    # Secondary testimonies: significators and Moon applications.
    if (
        token_name.startswith("moon_applying_")
        or "significator" in token_name
        or token_name in {"l1_fortunate", "l1_malific_debility", "l7_fortunate", "l7_malific_debility"}
    ):
        primary_sigs = category_rules.get("primary_significators", [])
        if any(str(sig).lower() in token_name for sig in primary_sigs):
            return base_weight * 10.0
        return base_weight * 5.0

    # House-condition testimonies.
    if token_name.startswith("l") and ("fortunate" in token_name or "debility" in token_name):
        try:
            house_num = int(token_name[1:token_name.index("_")])
        except Exception:
            return base_weight
        irrelevant = category_rules.get("irrelevant_houses", [])
        outcomes = category_rules.get("outcome_houses", [])
        if house_num in irrelevant:
            return 0.0
        if house_num in outcomes:
            return base_weight * 2.0
        return base_weight * 0.5

    # Context indicators.
    if token_name in {"essential_detriment", "accidental_retrograde"} or "sign_change" in token_name:
        return base_weight

    return base_weight


def _is_testimony_relevant(token: TestimonyKey, contract: Dict[str, Any] | None = None) -> bool:
    """Return whether a testimony is relevant for the given category contract."""
    contract = contract or {}
    category_rules = contract.get("category_rules", {}) if isinstance(contract, dict) else {}
    irrelevant_houses = category_rules.get("irrelevant_houses", [])
    token_name = token.value

    # Always include major perfection testimonies.
    if (
        token_name.startswith("perfection_")
        or token_name.startswith("translation_")
        or token_name.startswith("collection_")
    ):
        return True

    if token_name.startswith("l") and ("fortunate" in token_name or "debility" in token_name):
        try:
            house_num = int(token_name[1:token_name.index("_")])
            return house_num not in irrelevant_houses
        except Exception:
            return True
    return True


def _coerce_tokens(testimonies: Iterable[TestimonyKey | str]) -> Sequence[TestimonyKey]:
    """Convert mixed testimony values to canonical ``TestimonyKey`` values."""
    result: List[TestimonyKey] = []
    for raw in testimonies:
        if isinstance(raw, TestimonyKey):
            result.append(raw)
            continue
        try:
            result.append(TestimonyKey(raw))
        except Exception:
            continue
    return result


def aggregate(
    testimonies: Iterable[TestimonyKey | str],
    contract: Dict[str, Any] | None = None,
) -> Tuple[float, List[Dict[str, float | TestimonyKey | Polarity | str | bool]]]:
    """Aggregate testimony tokens into a weighted score and ledger."""
    total_yes = 0.0
    total_no = 0.0
    ledger: List[Dict[str, float | TestimonyKey | Polarity | str | bool]] = []
    seen: set[TestimonyKey] = set()
    families_seen: set[str] = set()

    tokens = _coerce_tokens(testimonies)
    if contract:
        tokens = [token for token in tokens if _is_testimony_relevant(token, contract)]

    for token in sorted(tokens, key=lambda t: t.value):
        if token in seen:
            continue
        seen.add(token)
        polarity = POLARITY_TABLE.get(token, Polarity.NEUTRAL)
        if polarity is Polarity.NEUTRAL:
            continue

        family = FAMILY_TABLE.get(token)
        kind = KIND_TABLE.get(token)
        context_only = family is not None and family in families_seen
        if family is not None and not context_only:
            families_seen.add(family)

        weight = (
            _get_testimony_hierarchy_weight(token, contract)
            if contract
            else 1.0
        )
        if weight < 0:
            raise ValueError("Weights must be non-negative for monotonicity")

        delta_yes = weight if (not context_only and polarity is Polarity.POSITIVE) else 0.0
        delta_no = weight if (not context_only and polarity is Polarity.NEGATIVE) else 0.0
        total_yes += delta_yes
        total_no += delta_no
        ledger.append(
            {
                "key": token,
                "polarity": polarity,
                "weight": weight,
                "delta_yes": delta_yes,
                "delta_no": delta_no,
                "family": family,
                "kind": kind,
                "context": context_only,
            }
        )

    return total_yes - total_no, ledger


__all__ = [
    "aggregate",
    "_get_testimony_hierarchy_weight",
    "_is_testimony_relevant",
]
