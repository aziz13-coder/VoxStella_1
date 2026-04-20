from __future__ import annotations

from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


VEHICLE_TOKENS = (
    "car",
    "vehicle",
    "automobile",
    "truck",
    "van",
    "motorcycle",
    "bike",
)

BUY_TOKENS = (
    "buy",
    "purchase",
    "get",
    "acquire",
    "obtain",
)

SELL_TOKENS = (
    "sell",
    "sale",
    "selling",
    "dispose of",
)

SPECIFIC_COUNTERPARTY_TOKENS = (
    "the car",
    "this car",
    "that car",
    "dealer",
    "dealership",
    "seller",
)

DELIVERY_OR_LOST_TOKENS = (
    "deliver",
    "delivery",
    "arrive",
    "arrival",
    "lost",
    "missing",
    "stolen",
    "where is",
)


def _vehicle_natural_significators(item_name: str = "car") -> Dict[str, Any]:
    return {
        item_name: "sun",
        "category": Category.VEHICLE,
        "traditional_source": "Based on classical horary significator assignments",
    }


def analyze_vehicle_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Classify vehicle acquisition and sale questions into shared families."""

    q = (question or "").lower().strip()
    if not q:
        return None

    def has_any(*tokens: str) -> bool:
        return any(token in q for token in tokens)

    if not has_any(*VEHICLE_TOKENS):
        return None
    if has_any(*DELIVERY_OR_LOST_TOKENS):
        return None

    has_buy = has_any(*BUY_TOKENS)
    has_sell = has_any(*SELL_TOKENS)

    if third_person_analysis and third_person_analysis.get("is_third_person") and has_buy:
        subject_house = int(third_person_analysis.get("subject_house") or 7)
        possession_house = _turn(subject_house, 2)
        vehicle_house = _turn(subject_house, 3)
        return {
            "family": "turned_vehicle_acquisition",
            "category_override": Category.MONEY,
            "relevant_houses": [subject_house, possession_house, vehicle_house],
            "subject_house": subject_house,
            "possession_house": possession_house,
            "vehicle_house": vehicle_house,
            "quesited_house": possession_house,
            "special_significators": _vehicle_natural_significators(),
            "doctrine": "When the question is about a relative or partner buying a vehicle, that person becomes the operative subject, with the turned 2nd for the acquisition or possession side and the turned 3rd for the vehicle itself.",
        }

    if has_sell and (" my " in f" {q} " or q.startswith("my ") or q.startswith("will i")):
        return {
            "family": "owned_vehicle_sale",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 3, 7],
            "subject_house": 1,
            "seller_house": 1,
            "vehicle_house": 3,
            "buyer_house": 7,
            "quesited_house": 7,
            "transaction_type": True,
            "special_significators": _vehicle_natural_significators(),
            "doctrine": "Selling one's own car keeps the querent as seller, the buyer on the 7th, and the vehicle itself visible on the 3rd.",
        }

    if has_buy and has_any(*SPECIFIC_COUNTERPARTY_TOKENS):
        return {
            "family": "specific_vehicle_purchase",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 7, 8],
            "subject_house": 1,
            "seller_house": 7,
            "buyer_house": 1,
            "vehicle_house": 8,
            "quesited_house": 8,
            "transaction_type": True,
            "special_significators": _vehicle_natural_significators(),
            "doctrine": "A specific car still owned by someone else is judged from the seller in the 7th and the seller's possession in the turned 2nd from that house, or radical 8th.",
        }

    if has_buy:
        return {
            "family": "general_vehicle_acquisition",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 2, 3],
            "subject_house": 1,
            "buyer_money_house": 2,
            "vehicle_house": 3,
            "quesited_house": 3,
            "special_significators": _vehicle_natural_significators(),
            "doctrine": "A general question about getting a vehicle keeps the querent's money on the 2nd and the vehicle itself on the 3rd.",
        }

    return None
