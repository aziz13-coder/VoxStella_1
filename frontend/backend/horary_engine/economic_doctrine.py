from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..taxonomy import Category
    from ..models import Planet
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category
    from models import Planet


def _turn(base: int, offset: int) -> int:
    return ((base + offset - 2) % 12) + 1


def analyze_economic_question_text(question: str, question_type: Category | None) -> Dict[str, Any] | None:
    """Classify money/work questions into doctrine-level families.

    These families exist to keep routing stable before the scoring layer runs.
    They intentionally encode house logic only; they do not force verdicts.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    def has_any(*tokens: str) -> bool:
        return any(token in q for token in tokens)

    def regex(*patterns: str) -> bool:
        return any(re.search(pattern, q, re.IGNORECASE) for pattern in patterns)

    repayment_patterns = (
        r"\bpay me back\b",
        r"\bpay back\b",
        r"\bget (?:my|the) money back\b",
        r"\bget back\b.*\bmoney\b",
        r"\bmoney back\b",
        r"\brepay\b",
        r"\brepayment\b",
        r"\brefund\b",
        r"\breimburse(?:ment)?\b",
        r"\breturn the deposit\b",
        r"\binsurance claim\b",
    )

    if regex(*repayment_patterns):
        if has_any("friend of mine", "my friend", "our friend", "ally"):
            return {
                "family": "friend_repayment",
                "category_override": Category.MONEY,
                "relevant_houses": [1, 11, 2],
                "quesited_house": 2,
                "counterparty_house": 11,
                "counterparty_money_house": _turn(11, 2),
                "receipt_house": 2,
                "doctrine": "Money owed back by a friend keeps the friend on the 11th while the querent's money to be recovered remains on the 2nd.",
            }

        if has_any("college", "university", "school", "faculty", "campus"):
            institution_house = 9
            institution_money_house = _turn(institution_house, 2)
            return {
                "family": "institutional_refund",
                "category_override": Category.MONEY,
                "relevant_houses": [1, institution_house, institution_money_house],
                "quesited_house": institution_money_house,
                "counterparty_house": institution_house,
                "counterparty_money_house": institution_money_house,
                "receipt_house": 2,
                "doctrine": "A refund from a college or university is judged from the institution in the 9th and its money in the turned 2nd from that house.",
            }

        if has_any("tax", "irs", "hmrc", "revenue service", "government refund"):
            institution_house = 10
            institution_money_house = _turn(institution_house, 2)
            return {
                "family": "government_refund",
                "category_override": Category.MONEY,
                "relevant_houses": [1, institution_house, institution_money_house],
                "quesited_house": institution_money_house,
                "counterparty_house": institution_house,
                "counterparty_money_house": institution_money_house,
                "receipt_house": 2,
                "doctrine": "A tax refund is judged from the government in the 10th and the government's money in the turned 2nd from that house.",
            }

        if has_any("insurance", "insurer", "insurance company", "company", "merchant", "seller", "vendor", "landlord"):
            counterparty_house = 7
            counterparty_money_house = _turn(counterparty_house, 2)
            return {
                "family": "counterparty_refund",
                "category_override": Category.MONEY,
                "relevant_houses": [1, counterparty_house, counterparty_money_house],
                "quesited_house": counterparty_money_house,
                "counterparty_house": counterparty_house,
                "counterparty_money_house": counterparty_money_house,
                "receipt_house": 2,
                "doctrine": "Refunds from a company or other contracting party are judged from the 7th and that party's money in the turned 2nd from the 7th.",
            }

    if has_any("yearly review", "annual review", "performance review") or (
        "review" in q and has_any("my work", "my job", "boss", "manager", "employment", "promotion")
    ):
        return {
            "family": "career_review",
            "category_override": Category.CAREER,
            "relevant_houses": [1, 10],
            "quesited_house": 10,
            "reviewer_house": 10,
            "doctrine": "Career review questions belong to the superior or judge in the 10th, not generic 6th-house work.",
        }

    if has_any("tenant", "landlord") and has_any("payment", "pay", "full payment", "arrears", "rent due"):
        return {
            "family": "tenant_payment",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 7, 8],
            "quesited_house": 8,
            "tenant_house": 7,
            "tenant_money_house": 8,
            "receipt_house": 2,
            "doctrine": "Tenant is the 7th house; the tenant's money is the turned 2nd from the 7th, or radical 8th.",
        }

    if has_any("bet", "betting", "bookmaker", "wager") and has_any("profit", "win", "winnings", "gain"):
        return {
            "family": "bet_profit",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 2, 8],
            "quesited_house": 8,
            "stake_house": 2,
            "bookmaker_house": 7,
            "winnings_house": 8,
            "doctrine": "Profit from a bet is money coming from the other party, so winnings are judged from the 8th.",
        }

    hostile_bank_words = (
        "foreclose",
        "foreclosure",
        "repo",
        "repossession",
        "seize",
        "seizure",
        "call the loan",
        "call in the loan",
    )
    if has_any("bank") and has_any(*hostile_bank_words):
        return {
            "family": "bank_counterparty",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 7],
            "quesited_house": 7,
            "counterparty_house": 7,
            "property_house": 4,
            "doctrine": "The bank is the contracting counterparty in the 7th; the house itself remains a secondary 4th-house witness.",
        }

    named_lender_words = (
        "bank",
        "lender",
        "credit union",
        "finance company",
        "loan company",
        "mortgage company",
        "mortgage lender",
        "creditor",
    )
    named_lender_loan_words = (
        "loan",
        "mortgage",
        "borrow",
        "borrowing",
        "credit",
        "financing",
        "refinancing",
    )
    named_lender_process_patterns = (
        r"\b(approve|approved|approval|qualify|qualified|qualifying|get|getting|receive|receiving|grant|granted|lend|lending|borrow|borrowing|take|taking|apply|applied|application|obtain|obtaining|secure|securing)\b",
    )
    if (
        has_any(*named_lender_words)
        and has_any(*named_lender_loan_words)
        and regex(*named_lender_process_patterns)
        and not has_any(*hostile_bank_words)
    ):
        counterparty_house = 7
        counterparty_money_house = _turn(counterparty_house, 2)
        return {
            "family": "named_lender_loan",
            "category_override": Category.MONEY,
            "relevant_houses": [1, counterparty_house, counterparty_money_house],
            "quesited_house": counterparty_money_house,
            "counterparty_house": counterparty_house,
            "counterparty_money_house": counterparty_money_house,
            "lender_house": counterparty_house,
            "loan_house": counterparty_money_house,
            "receipt_house": 2,
            "doctrine": "A named bank or lender is the 7th-house counterparty, and the loan itself is the lender's money in the turned 2nd from that house, or radical 8th.",
        }

    if "business" in q and regex(r"\b(start|open|launch|begin)\b"):
        return {
            "family": "business_start",
            "category_override": Category.CAREER,
            "relevant_houses": [1, 10],
            "quesited_house": 10,
            "business_house": 10,
            "profit_house": 11,
            "partner_house": 7,
            "doctrine": "A business undertaking is judged from the 10th, with profit in the 11th and partners/clients secondary in the 7th.",
        }

    if "business" in q and has_any("profit", "profitable", "invest", "investing", "investment", "returns"):
        return {
            "family": "business_profit",
            "category_override": Category.MONEY,
            "relevant_houses": [1, 10, 11],
            "quesited_house": 11,
            "business_house": 10,
            "profit_house": 11,
            "partner_house": 7,
            "doctrine": "The business itself is the 10th, while profit from that business belongs to the 11th.",
        }

    return None


def build_bank_counterparty_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    economic_analysis: Dict[str, Any] | None,
    perfection: Dict[str, Any] | None,
    reception_info: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    """Build a narrow snapshot for hostile bank/counterparty questions."""

    analysis = economic_analysis or {}
    if analysis.get("family") != "bank_counterparty":
        return None

    querent_pos = chart.planets.get(querent_planet)
    quesited_pos = chart.planets.get(quesited_planet)
    if not querent_pos or not quesited_pos:
        return None

    property_house = analysis.get("property_house", 4)
    property_ruler = chart.house_rulers.get(property_house)
    return {
        "family": "bank_counterparty",
        "querent_name": querent_planet.value,
        "quesited_name": quesited_planet.value,
        "quesited_dignity": getattr(quesited_pos, "dignity_score", 0),
        "quesited_house": getattr(quesited_pos, "house", None),
        "perfection_type": (perfection or {}).get("type"),
        "perfection_reason": (perfection or {}).get("reason"),
        "reception_type": (reception_info or {}).get("type", "none"),
        "traditional_strength": int((reception_info or {}).get("traditional_strength", 0) or 0),
        "mutual": (reception_info or {}).get("mutual", "none"),
        "display_text": (reception_info or {}).get("display_text", "no reception"),
        "one_way": list((reception_info or {}).get("one_way", []) or []),
        "property_ruler_is_querent": property_ruler == querent_planet,
    }


def evaluate_bank_counterparty_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    """Interpret agreement/reception in foreclosure-style questions.

    For hostile counterparty questions, strong reception plus a weak/cadent
    counterparty is evidence of accommodation or settlement rather than the
    feared hostile act.
    """

    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = []
    score = 0

    if snapshot.get("traditional_strength", 0) >= 3:
        score -= 6
        reasoning.append(
            {
                "stage": "Economic Doctrine",
                "rule": "Strong reception between querent and bank points to accommodation rather than foreclosure",
                "weight": -6,
            }
        )

    if snapshot.get("perfection_type") in {"collection", "translation"} and snapshot.get("traditional_strength", 0) >= 3:
        score -= 4
        reasoning.append(
            {
                "stage": "Economic Doctrine",
                "rule": "Indirect perfection with strong reception is read as settlement/contact, not hostile seizure",
                "weight": -4,
            }
        )

    if snapshot.get("quesited_dignity", 0) <= -5 or snapshot.get("quesited_house") in {6, 8, 12}:
        score -= 3
        reasoning.append(
            {
                "stage": "Economic Doctrine",
                "rule": "The bank significator is too weak or cadent to carry out the hostile action cleanly",
                "weight": -3,
            }
        )

    if snapshot.get("property_ruler_is_querent"):
        score -= 2
        reasoning.append(
            {
                "stage": "Economic Doctrine",
                "rule": "The querent also rules the house itself, supporting continued possession",
                "weight": -2,
            }
        )

    if score <= -8:
        return {
            "applies": True,
            "result": "NO",
            "confidence": 78,
            "reasoning": reasoning,
            "score": score,
        }

    return {"applies": False, "reasoning": reasoning, "result": None, "score": score}
