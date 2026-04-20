from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category


FRIEND_TOKENS = (
    "my friend",
    "our friend",
    "friend of mine",
)

CONTACT_TOKENS = (
    "hear from",
    "hear back",
    "reply",
    "respond",
    "response",
    "contact",
    "call",
    "write back",
    "text back",
)

MESSAGE_TOKENS = (
    "message",
    "text",
    "sms",
    "email",
    "letter",
    "note",
    "mail",
    "dm",
    "direct message",
)

DELIVERY_TOKENS = (
    "parcel",
    "package",
    "shipment",
    "goods",
    "book",
    "books",
    "delivery",
    "delivered",
    "arrive at home",
    "arrive home",
    "arrive at my house",
    "arrive at the house",
    "at home",
    "doorstep",
    "receive the parcel",
    "receive the package",
    "receive the book",
    "receive the goods",
)

RECEIPT_TOKENS = (
    "received",
    "get my",
    "got my",
    "read my",
)


def _has_phrase(text: str, phrase: str) -> bool:
    pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
    return bool(re.search(pattern, text))


def _has_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_has_phrase(text, phrase) for phrase in phrases)


def analyze_communication_question_text(
    question: str,
    third_person_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    q = (question or "").lower().strip()
    if not q:
        return None

    if _has_any_phrase(q, DELIVERY_TOKENS):
        return {
            "family": "delivery_arrival",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 2, 4, 6, 8],
            "goods_house": 2,
            "home_house": 4,
            "courier_house": 6,
            "holder_house": 8,
            "quesited_house": 4,
            "doctrine": "Delivery-arrival questions weigh the movable goods, the place of arrival, the delivery agent, and the fact that the goods are temporarily in others' hands during transit.",
        }

    has_contact = _has_any_phrase(q, CONTACT_TOKENS)
    has_message = _has_any_phrase(q, MESSAGE_TOKENS)
    has_receipt = _has_any_phrase(q, RECEIPT_TOKENS)
    is_friend = _has_any_phrase(q, FRIEND_TOKENS)

    if not (has_contact or has_message or has_receipt):
        return None

    recipient_house = 11 if is_friend else int((third_person_analysis or {}).get("subject_house") or 7)
    category_override = Category.FRIEND_ENEMY if recipient_house == 11 else Category.GENERAL
    relevant_houses = [1, recipient_house]
    if has_message or has_receipt:
        if 3 not in relevant_houses:
            relevant_houses.append(3)
        family = "message_receipt" if has_receipt else "message_contact"
        doctrine = "Message questions judge both the recipient and the communication itself, so the 3rd house joins the primary relationship or correspondence axis."
    else:
        family = "friend_contact" if recipient_house == 11 else "contact_reply"
        doctrine = "Contact questions judge the person to be heard from, while keeping communication as a secondary witness rather than the whole matter."

    result = {
        "family": family,
        "category_override": category_override,
        "relevant_houses": relevant_houses,
        "recipient_house": recipient_house,
        "communication_house": 3,
        "quesited_house": recipient_house,
        "doctrine": doctrine,
    }

    if recipient_house == 11:
        result["friend_house"] = 11

    return result
