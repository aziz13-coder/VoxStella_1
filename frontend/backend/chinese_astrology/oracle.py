from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


LineBits = Tuple[int, int, int]


ORACLE_SOURCE_EVIDENCE: List[Dict[str, str]] = [
    {
        "source_id": "local.iching_huang",
        "title": "I Ching, Kerson Huang and Rosemary Huang",
        "path": "docs/iching_feature/source_manifest.yml",
        "claim": "Local corpus anchor for I Ching casting terminology and hexagram reading structure.",
    },
    {
        "source_id": "local.iching_source_audit_2026_05_11",
        "title": "Chinese Astrology Source Audit",
        "path": "docs/iching_feature/CHINESE_ASTROLOGY_SOURCE_AUDIT_2026-05-11.md",
        "claim": "Product decision: standalone Oracle, manual or coin casting, six lines stored bottom-to-top, primary/changing/resulting hexagrams derived.",
    },
    {
        "source_id": "public.iching_divination_method",
        "title": "I Ching divination method reference",
        "url": "https://en.wikipedia.org/wiki/I_Ching_divination",
        "claim": "Line numbers 6, 7, 8, and 9 correspond to old yin, young yang, young yin, and old yang; old lines change to produce a second hexagram.",
    },
    {
        "source_id": "public.king_wen_hexagram_list",
        "title": "King Wen order hexagram list",
        "url": "https://en.wikipedia.org/wiki/List_of_hexagrams_of_the_I_Ching",
        "claim": "Public cross-check for King Wen sequence numbers, English titles, and upper/lower trigram identities.",
    },
    {
        "source_id": "classic.received_zhouyi_sequence",
        "title": "Book of Changes received hexagram sequence",
        "url": "https://ctext.org/book-of-changes",
        "claim": "Classical received Zhouyi / King Wen sequence anchor for the sixty-four hexagrams.",
    },
    {
        "source_id": "classic.xici_yarrow_procedure",
        "title": "Great Appendix yarrow procedure",
        "url": "https://www.eee-learning.com/book/1742",
        "claim": "Classical yarrow basis: fifty stalks, forty-nine used, four operations make a change, eighteen changes make a hexagram.",
    },
    {
        "source_id": "public.yarrow_stalk_probability_model",
        "title": "Yarrow stalk probability model",
        "url": "https://www.cosmictao.com/library/terms/iching/yarrow-stalk-method",
        "claim": "Yarrow-style software casting uses the 1/16, 5/16, 7/16, and 3/16 probability model for lines 6, 7, 8, and 9.",
    },
    {
        "source_id": "public.nuclear_hexagram_structure",
        "title": "Nuclear hexagram structure",
        "url": "https://www.ichi-ng.com/basics/hexagram-structures/",
        "claim": "The lower nuclear trigram uses lines 2, 3, and 4; the upper nuclear trigram uses lines 3, 4, and 5.",
    },
    {
        "source_id": "classic.zhu_xi_seven_rule_line_policy",
        "title": "Zhu Xi seven-rule changing-line policy",
        "url": "https://www.shidianguji.com/book/SK0104/chapter/1lxfusbsfh4i2",
        "claim": "Named interpretation policy for reading none, one, several, or all six changing lines; exposed as a selectable source policy rather than the only school.",
    },
]


TRIGRAMS: Dict[LineBits, Dict[str, str]] = {
    (1, 1, 1): {"key": "qian", "name": "Qian", "image": "Heaven", "polarity": "pure yang"},
    (1, 1, 0): {"key": "dui", "name": "Dui", "image": "Lake", "polarity": "open yin above"},
    (1, 0, 1): {"key": "li", "name": "Li", "image": "Fire", "polarity": "yang enclosing yin"},
    (1, 0, 0): {"key": "zhen", "name": "Zhen", "image": "Thunder", "polarity": "yang rising below"},
    (0, 1, 1): {"key": "xun", "name": "Xun", "image": "Wind", "polarity": "yin entering below"},
    (0, 1, 0): {"key": "kan", "name": "Kan", "image": "Water", "polarity": "yang held within yin"},
    (0, 0, 1): {"key": "gen", "name": "Gen", "image": "Mountain", "polarity": "yang resting above"},
    (0, 0, 0): {"key": "kun", "name": "Kun", "image": "Earth", "polarity": "pure yin"},
}


KING_WEN_BY_TRIGRAMS: Dict[Tuple[str, str], int] = {
    ("qian", "qian"): 1,
    ("qian", "dui"): 43,
    ("qian", "li"): 14,
    ("qian", "zhen"): 34,
    ("qian", "xun"): 9,
    ("qian", "kan"): 5,
    ("qian", "gen"): 26,
    ("qian", "kun"): 11,
    ("dui", "qian"): 10,
    ("dui", "dui"): 58,
    ("dui", "li"): 38,
    ("dui", "zhen"): 54,
    ("dui", "xun"): 61,
    ("dui", "kan"): 60,
    ("dui", "gen"): 41,
    ("dui", "kun"): 19,
    ("li", "qian"): 13,
    ("li", "dui"): 49,
    ("li", "li"): 30,
    ("li", "zhen"): 55,
    ("li", "xun"): 37,
    ("li", "kan"): 63,
    ("li", "gen"): 22,
    ("li", "kun"): 36,
    ("zhen", "qian"): 25,
    ("zhen", "dui"): 17,
    ("zhen", "li"): 21,
    ("zhen", "zhen"): 51,
    ("zhen", "xun"): 42,
    ("zhen", "kan"): 3,
    ("zhen", "gen"): 27,
    ("zhen", "kun"): 24,
    ("xun", "qian"): 44,
    ("xun", "dui"): 28,
    ("xun", "li"): 50,
    ("xun", "zhen"): 32,
    ("xun", "xun"): 57,
    ("xun", "kan"): 48,
    ("xun", "gen"): 18,
    ("xun", "kun"): 46,
    ("kan", "qian"): 6,
    ("kan", "dui"): 47,
    ("kan", "li"): 64,
    ("kan", "zhen"): 40,
    ("kan", "xun"): 59,
    ("kan", "kan"): 29,
    ("kan", "gen"): 4,
    ("kan", "kun"): 7,
    ("gen", "qian"): 33,
    ("gen", "dui"): 31,
    ("gen", "li"): 56,
    ("gen", "zhen"): 62,
    ("gen", "xun"): 53,
    ("gen", "kan"): 39,
    ("gen", "gen"): 52,
    ("gen", "kun"): 15,
    ("kun", "qian"): 12,
    ("kun", "dui"): 45,
    ("kun", "li"): 35,
    ("kun", "zhen"): 16,
    ("kun", "xun"): 20,
    ("kun", "kan"): 8,
    ("kun", "gen"): 23,
    ("kun", "kun"): 2,
}


HEXAGRAMS: Dict[int, Dict[str, Any]] = {
    1: {"pinyin": "Qian", "title": "The Creative", "keywords": ["initiative", "force", "leadership"], "theme": "Strong initiating power is available, but it must be directed with discipline.", "counsel": "Act from principle, take responsibility, and avoid forcing what needs timing."},
    2: {"pinyin": "Kun", "title": "The Receptive", "keywords": ["receptivity", "support", "yielding"], "theme": "The answer favors receptivity, steadiness, and a willingness to carry what is real.", "counsel": "Support the process, simplify the field, and let form emerge before pressing."},
    3: {"pinyin": "Zhun", "title": "Difficulty at the Beginning", "keywords": ["beginnings", "disorder", "germination"], "theme": "A new situation is forming through confusion and pressure.", "counsel": "Organize the first step, seek grounded help, and do not mistake early friction for failure."},
    4: {"pinyin": "Meng", "title": "Youthful Folly", "keywords": ["learning", "inexperience", "instruction"], "theme": "The matter asks for instruction before judgment.", "counsel": "Ask a precise question, accept limits, and learn the pattern before trying to master it."},
    5: {"pinyin": "Xu", "title": "Waiting", "keywords": ["patience", "timing", "nourishment"], "theme": "The timing is not empty; preparation is the active work.", "counsel": "Wait with purpose, keep resources available, and do not move from anxiety."},
    6: {"pinyin": "Song", "title": "Conflict", "keywords": ["dispute", "boundaries", "claims"], "theme": "Contrary aims or facts need resolution before progress can hold.", "counsel": "Clarify the claim, lower escalation, and use a fair standard outside the argument."},
    7: {"pinyin": "Shi", "title": "The Army", "keywords": ["discipline", "organization", "collective effort"], "theme": "The situation needs structure, leadership, and disciplined coordination.", "counsel": "Define command, purpose, and limits; avoid letting force outrun legitimacy."},
    8: {"pinyin": "Bi", "title": "Holding Together", "keywords": ["alliance", "belonging", "selection"], "theme": "The answer centers on union, trust, and choosing the right bonds.", "counsel": "Join with what is sincere and durable; do not overextend loyalty where it is not mutual."},
    9: {"pinyin": "Xiao Chu", "title": "Small Taming", "keywords": ["restraint", "small gains", "refinement"], "theme": "Small influences can restrain larger force while conditions mature.", "counsel": "Refine the details, conserve leverage, and let modest corrections accumulate."},
    10: {"pinyin": "Lu", "title": "Treading", "keywords": ["conduct", "risk", "manners"], "theme": "Progress depends on careful conduct around a stronger force.", "counsel": "Step precisely, keep etiquette and boundaries clean, and avoid provocation."},
    11: {"pinyin": "Tai", "title": "Peace", "keywords": ["flow", "accord", "opening"], "theme": "Heaven and earth communicate; growth is possible through open exchange.", "counsel": "Use the opening well, include others, and maintain the conditions that allow flow."},
    12: {"pinyin": "Pi", "title": "Standstill", "keywords": ["stagnation", "separation", "closure"], "theme": "The channels are blocked and good intent may not penetrate.", "counsel": "Do not spend strength on a closed field; preserve integrity and wait for a real opening."},
    13: {"pinyin": "Tong Ren", "title": "Fellowship", "keywords": ["community", "shared purpose", "public trust"], "theme": "The matter benefits from open fellowship and a purpose larger than private gain.", "counsel": "Align with people through shared principles, not convenience alone."},
    14: {"pinyin": "Da You", "title": "Great Possession", "keywords": ["abundance", "capacity", "stewardship"], "theme": "Resources or influence are present and require responsible use.", "counsel": "Be generous without losing discernment; possession becomes useful through stewardship."},
    15: {"pinyin": "Qian", "title": "Modesty", "keywords": ["humility", "balance", "proportion"], "theme": "The strongest position is the one that remains proportionate.", "counsel": "Reduce excess, credit others, and let substance speak quietly."},
    16: {"pinyin": "Yu", "title": "Enthusiasm", "keywords": ["mobilization", "inspiration", "readiness"], "theme": "Energy can be gathered when rhythm and purpose are clear.", "counsel": "Prepare before celebrating; enthusiasm should move the work, not replace it."},
    17: {"pinyin": "Sui", "title": "Following", "keywords": ["adaptation", "response", "leadership by listening"], "theme": "The right move follows the living current rather than a fixed idea.", "counsel": "Respond to what has authority in the moment, and do not follow what weakens judgment."},
    18: {"pinyin": "Gu", "title": "Work on the Decayed", "keywords": ["repair", "inheritance", "correction"], "theme": "Old damage or neglect is asking to be repaired.", "counsel": "Name the pattern, correct causes rather than symptoms, and continue after the first fix."},
    19: {"pinyin": "Lin", "title": "Approach", "keywords": ["arrival", "supervision", "encouragement"], "theme": "Something comes near and can be guided by attentive presence.", "counsel": "Approach with care and consistency; do not waste the moment through complacency."},
    20: {"pinyin": "Guan", "title": "Contemplation", "keywords": ["view", "observation", "example"], "theme": "The answer asks for a higher vantage point and cleaner example.", "counsel": "Look before acting, and let your conduct become evidence others can trust."},
    21: {"pinyin": "Shi He", "title": "Biting Through", "keywords": ["decision", "justice", "obstruction"], "theme": "An obstacle must be bitten through by clear action.", "counsel": "Make the decision explicit, apply the rule evenly, and remove what prevents union."},
    22: {"pinyin": "Bi", "title": "Grace", "keywords": ["form", "beauty", "presentation"], "theme": "Outer form matters, but it must serve inner substance.", "counsel": "Polish the presentation without mistaking ornament for truth."},
    23: {"pinyin": "Bo", "title": "Splitting Apart", "keywords": ["erosion", "stripping", "collapse"], "theme": "The structure is being stripped down and cannot be propped by appearances.", "counsel": "Stop feeding what is falling apart; protect the seed that can survive."},
    24: {"pinyin": "Fu", "title": "Return", "keywords": ["turning point", "renewal", "recurrence"], "theme": "A return to the source or right path is possible.", "counsel": "Restart simply, honor the first returning sign, and avoid rushing the cycle."},
    25: {"pinyin": "Wu Wang", "title": "Innocence", "keywords": ["spontaneity", "truth", "no false motive"], "theme": "The strongest path is simple, uncontrived, and free of hidden agenda.", "counsel": "Act cleanly from what is true; do not add manipulation to a natural process."},
    26: {"pinyin": "Da Chu", "title": "Great Taming", "keywords": ["accumulated power", "restraint", "study"], "theme": "Large force is held back so it can become useful and mature.", "counsel": "Train capacity, gather knowledge, and release strength only when it has form."},
    27: {"pinyin": "Yi", "title": "Nourishment", "keywords": ["feeding", "speech", "sustenance"], "theme": "The matter turns on what is taken in and what is given out.", "counsel": "Examine inputs, words, and habits; feed what supports life and clarity."},
    28: {"pinyin": "Da Guo", "title": "Great Exceeding", "keywords": ["overload", "critical mass", "transition"], "theme": "The structure carries unusual weight and cannot remain as it is.", "counsel": "Act decisively, redistribute pressure, and do not pretend the load is ordinary."},
    29: {"pinyin": "Kan", "title": "The Abysmal", "keywords": ["danger", "depth", "repetition"], "theme": "Repeated difficulty asks for steadiness rather than panic.", "counsel": "Keep inner truth, move by small reliable steps, and avoid adding fear to danger."},
    30: {"pinyin": "Li", "title": "The Clinging", "keywords": ["clarity", "dependence", "illumination"], "theme": "Clarity depends on what it attaches to.", "counsel": "Choose the right support, keep perception bright, and do not burn through the vessel."},
    31: {"pinyin": "Xian", "title": "Influence", "keywords": ["attraction", "sensitivity", "mutual effect"], "theme": "Subtle influence is moving between people or conditions.", "counsel": "Influence through sincerity and responsiveness rather than pressure."},
    32: {"pinyin": "Heng", "title": "Duration", "keywords": ["continuity", "commitment", "rhythm"], "theme": "The situation asks what can endure through changing conditions.", "counsel": "Keep the steady rhythm, adapt without abandoning the commitment."},
    33: {"pinyin": "Dun", "title": "Retreat", "keywords": ["withdrawal", "strategy", "distance"], "theme": "Strategic withdrawal preserves strength and dignity.", "counsel": "Step back cleanly, avoid resentment, and keep the retreat purposeful."},
    34: {"pinyin": "Da Zhuang", "title": "Great Power", "keywords": ["strength", "momentum", "restraint"], "theme": "Power is present and must be governed by correctness.", "counsel": "Use strength only where it is right; unchecked force weakens the position."},
    35: {"pinyin": "Jin", "title": "Progress", "keywords": ["advance", "recognition", "illumination"], "theme": "The path opens through visible progress and useful contribution.", "counsel": "Advance steadily, accept recognition, and keep the purpose clear."},
    36: {"pinyin": "Ming Yi", "title": "Darkening of the Light", "keywords": ["concealment", "injury", "survival"], "theme": "Brightness is under pressure and should be protected.", "counsel": "Keep insight inward, avoid needless exposure, and preserve the light for later."},
    37: {"pinyin": "Jia Ren", "title": "Family", "keywords": ["roles", "household", "ordered relations"], "theme": "The issue depends on clear roles and trustworthy conduct in the close circle.", "counsel": "Put the household order right: responsibilities, speech, and example matter."},
    38: {"pinyin": "Kui", "title": "Opposition", "keywords": ["difference", "divergence", "small accord"], "theme": "Differences are real, but limited cooperation may still work.", "counsel": "Do not force sameness; find the small shared point and act from there."},
    39: {"pinyin": "Jian", "title": "Obstruction", "keywords": ["difficulty", "detour", "help"], "theme": "An obstruction requires a changed route and wise assistance.", "counsel": "Do not ram the barrier; turn toward counsel, support, and a safer path."},
    40: {"pinyin": "Xie", "title": "Deliverance", "keywords": ["release", "untying", "relief"], "theme": "Tension can be released after pressure or entanglement.", "counsel": "Untie what can be untied, forgive what is finished, and move before the knot reforms."},
    41: {"pinyin": "Sun", "title": "Decrease", "keywords": ["reduction", "sacrifice", "simplicity"], "theme": "Less becomes stronger when reduction is sincere and well aimed.", "counsel": "Cut excess, offer what is appropriate, and let simplicity restore balance."},
    42: {"pinyin": "Yi", "title": "Increase", "keywords": ["growth", "benefit", "generosity"], "theme": "Increase is available when benefit flows outward.", "counsel": "Act generously and promptly; growth is strengthened by useful service."},
    43: {"pinyin": "Guai", "title": "Breakthrough", "keywords": ["resolution", "declaration", "removal"], "theme": "A decisive declaration is needed to remove what has become untenable.", "counsel": "State the truth clearly without aggression, and do not compromise with corruption."},
    44: {"pinyin": "Gou", "title": "Coming to Meet", "keywords": ["encounter", "temptation", "influence"], "theme": "A powerful encounter arrives and should not be underestimated.", "counsel": "Recognize the attraction, set boundaries early, and avoid letting a small opening rule the field."},
    45: {"pinyin": "Cui", "title": "Gathering Together", "keywords": ["assembly", "shared center", "resources"], "theme": "People or resources gather around a center.", "counsel": "Make the center worthy, name the purpose, and prepare for the responsibility of gathering."},
    46: {"pinyin": "Sheng", "title": "Pushing Upward", "keywords": ["ascent", "growth", "patient work"], "theme": "Gradual ascent is possible through modest, persistent effort.", "counsel": "Climb step by step, seek support above, and do not despise small progress."},
    47: {"pinyin": "Kun", "title": "Oppression", "keywords": ["exhaustion", "constraint", "inner truth"], "theme": "Outer resources are constrained; inner steadiness becomes decisive.", "counsel": "Reduce speech, conserve strength, and keep faith with what cannot be taken."},
    48: {"pinyin": "Jing", "title": "The Well", "keywords": ["source", "shared resource", "renewal"], "theme": "The source remains valuable if it is maintained and reached properly.", "counsel": "Repair access to the source; do not abandon what can nourish many."},
    49: {"pinyin": "Ge", "title": "Revolution", "keywords": ["change", "renewal", "legitimacy"], "theme": "Change is justified only when its timing and grounds are clear.", "counsel": "Make reform legitimate, visible, and necessary; avoid change for display."},
    50: {"pinyin": "Ding", "title": "The Cauldron", "keywords": ["transformation", "culture", "vessel"], "theme": "Raw material can be transformed into nourishment or culture.", "counsel": "Tend the vessel, refine the ingredients, and make the work worthy of sharing."},
    51: {"pinyin": "Zhen", "title": "The Arousing", "keywords": ["shock", "awakening", "movement"], "theme": "Shock wakes the field and reveals what is steady.", "counsel": "Stay centered through the jolt; use the awakening without scattering."},
    52: {"pinyin": "Gen", "title": "Keeping Still", "keywords": ["stillness", "boundaries", "meditation"], "theme": "Stillness is the correct action when motion would obscure the point.", "counsel": "Stop at the right place, quiet the impulse, and let boundaries do their work."},
    53: {"pinyin": "Jian", "title": "Development", "keywords": ["gradual progress", "maturity", "proper sequence"], "theme": "Progress develops by correct sequence rather than sudden demand.", "counsel": "Let each step mature; do not demand fruit before roots are established."},
    54: {"pinyin": "Gui Mei", "title": "The Marrying Maiden", "keywords": ["secondary role", "imperfect position", "adaptation"], "theme": "The position is constrained and cannot command the whole arrangement.", "counsel": "Know the limits of the role, avoid overclaiming, and protect dignity through correct conduct."},
    55: {"pinyin": "Feng", "title": "Abundance", "keywords": ["fullness", "peak", "clarity"], "theme": "Abundance reaches a bright peak, but fullness is temporary.", "counsel": "Use the fullness while it is present, make clear decisions, and do not cling to the peak."},
    56: {"pinyin": "Lu", "title": "The Wanderer", "keywords": ["travel", "transience", "careful conduct"], "theme": "The matter is temporary or foreign; security comes from good conduct.", "counsel": "Travel lightly, respect local rules, and avoid creating obligations you cannot keep."},
    57: {"pinyin": "Xun", "title": "The Gentle", "keywords": ["penetration", "influence", "persistence"], "theme": "Gentle penetration works through repeated, precise influence.", "counsel": "Enter gradually, be consistent, and let subtle force do its work."},
    58: {"pinyin": "Dui", "title": "The Joyous", "keywords": ["exchange", "pleasure", "communication"], "theme": "Joy and exchange can open the situation when they remain sincere.", "counsel": "Communicate openly, enjoy what is shared, and avoid pleasing at the expense of truth."},
    59: {"pinyin": "Huan", "title": "Dispersion", "keywords": ["dissolving", "release", "reunion"], "theme": "Rigid separation can be dispersed so a wider unity can return.", "counsel": "Dissolve fear and isolation, gather around shared meaning, and move through the blockage."},
    60: {"pinyin": "Jie", "title": "Limitation", "keywords": ["bounds", "measure", "discipline"], "theme": "Good limits make action sustainable.", "counsel": "Set limits that serve life; avoid both looseness and bitter restriction."},
    61: {"pinyin": "Zhong Fu", "title": "Inner Truth", "keywords": ["sincerity", "trust", "inner alignment"], "theme": "Sincere inner alignment can create trust across distance.", "counsel": "Speak from the center, listen carefully, and let trust arise from consistency."},
    62: {"pinyin": "Xiao Guo", "title": "Small Exceeding", "keywords": ["small matters", "caution", "humility"], "theme": "Small acts may exceed the normal measure, but large ambitions should wait.", "counsel": "Attend to details, keep low, and succeed through careful modest action."},
    63: {"pinyin": "Ji Ji", "title": "After Completion", "keywords": ["completion", "order", "maintenance"], "theme": "A cycle is complete, but completion requires vigilance.", "counsel": "Maintain the order, watch the small signs, and do not relax into decline."},
    64: {"pinyin": "Wei Ji", "title": "Before Completion", "keywords": ["unfinished", "transition", "care"], "theme": "The work is close but not yet complete.", "counsel": "Cross carefully, sequence the last steps, and do not call the matter finished too soon."},
}


LINE_DEFINITIONS: Dict[int, Dict[str, Any]] = {
    6: {"label": "old yin", "yin_yang": "yin", "solid": False, "moving": True, "changes_to": 7},
    7: {"label": "young yang", "yin_yang": "yang", "solid": True, "moving": False, "changes_to": 7},
    8: {"label": "young yin", "yin_yang": "yin", "solid": False, "moving": False, "changes_to": 8},
    9: {"label": "old yang", "yin_yang": "yang", "solid": True, "moving": True, "changes_to": 8},
}


LINE_POSITION_FOCUS: Dict[int, str] = {
    1: "foundation and first impulse",
    2: "inner alignment and practical support",
    3: "threshold where pressure and choice become visible",
    4: "approach to the outer field and counsel",
    5: "governing center and mature expression",
    6: "completion, excess, and transition beyond the current pattern",
}


COIN_VALUE_SCHEMES: Dict[str, Dict[str, int]] = {
    "heads_2_tails_3": {"heads": 2, "tails": 3},
    "heads_3_tails_2": {"heads": 3, "tails": 2},
}


YARROW_LINE_WEIGHTS: Tuple[Tuple[int, int], ...] = (
    (6, 1),
    (7, 5),
    (8, 7),
    (9, 3),
)


LINE_VALUE_ALIASES = {
    "6": 6,
    "old_yin": 6,
    "moving_yin": 6,
    "yin_moving": 6,
    "changing_yin": 6,
    "7": 7,
    "young_yang": 7,
    "stable_yang": 7,
    "yang": 7,
    "8": 8,
    "young_yin": 8,
    "stable_yin": 8,
    "yin": 8,
    "9": 9,
    "old_yang": 9,
    "moving_yang": 9,
    "yang_moving": 9,
    "changing_yang": 9,
}


def _source_ids() -> List[str]:
    return [row["source_id"] for row in ORACLE_SOURCE_EVIDENCE]


def _clean_question(question: Any) -> str:
    text = str(question or "").strip()
    if len(text) > 500:
        return text[:500].rstrip()
    return text


def _normalize_line_value(value: Any) -> int:
    if isinstance(value, dict):
        for key in ("value", "number", "line", "code"):
            if key in value:
                return _normalize_line_value(value[key])
    if isinstance(value, bool):
        raise ValueError("Oracle line values must be 6, 7, 8, or 9; boolean values are ambiguous.")
    if isinstance(value, int):
        if value in LINE_DEFINITIONS:
            return value
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in LINE_VALUE_ALIASES:
        return LINE_VALUE_ALIASES[text]
    raise ValueError("Oracle line values must be 6 old yin, 7 young yang, 8 young yin, or 9 old yang.")


def _line_payload(position: int, value: int, *, coins: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    definition = LINE_DEFINITIONS[value]
    changed_value = int(definition["changes_to"])
    changed = LINE_DEFINITIONS[changed_value]
    return {
        "position": position,
        "order": "bottom_to_top",
        "value": value,
        "label": definition["label"],
        "yin_yang": definition["yin_yang"],
        "solid": bool(definition["solid"]),
        "moving": bool(definition["moving"]),
        "changes_to": changed_value,
        "resulting_label": changed["label"],
        "resulting_solid": bool(changed["solid"]),
        "visual": "solid" if definition["solid"] else "broken",
        "resulting_visual": "solid" if changed["solid"] else "broken",
        "position_focus": LINE_POSITION_FOCUS[position],
        "coins": list(coins or []),
        "source_ids": ["public.iching_divination_method", "local.iching_source_audit_2026_05_11"],
    }


def _coin_face(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("face", "side", "value"):
            if key in value:
                return _coin_face(value[key])
    if isinstance(value, int):
        if value == 2:
            return "heads"
        if value == 3:
            return "tails"
    text = str(value or "").strip().lower()
    if text in {"h", "head", "heads", "obverse"}:
        return "heads"
    if text in {"t", "tail", "tails", "reverse"}:
        return "tails"
    raise ValueError("Coin throws must contain heads/tails labels or numeric 2/3 values.")


def _line_from_coin_throw(throw: Any, *, scheme: str) -> Tuple[int, List[str]]:
    if not isinstance(throw, (list, tuple)) or len(throw) != 3:
        raise ValueError("Each Oracle coin throw must contain exactly three coins.")
    mapping = COIN_VALUE_SCHEMES.get(scheme)
    if not mapping:
        raise ValueError("Unknown Oracle coin value scheme.")
    faces = [_coin_face(item) for item in throw]
    total = sum(mapping[face] for face in faces)
    if total not in LINE_DEFINITIONS:
        raise ValueError("Coin throw did not resolve to a valid I Ching line value.")
    return total, faces


def _generate_coin_lines(seed: Optional[Any], *, scheme: str) -> Tuple[List[int], List[List[str]]]:
    rng = random.Random(str(seed)) if seed is not None else random.SystemRandom()
    throws: List[List[str]] = []
    values: List[int] = []
    mapping = COIN_VALUE_SCHEMES.get(scheme)
    if not mapping:
        raise ValueError("Unknown Oracle coin value scheme.")
    for _ in range(6):
        faces = [rng.choice(("heads", "tails")) for _ in range(3)]
        values.append(sum(mapping[face] for face in faces))
        throws.append(faces)
    return values, throws


def _weighted_yarrow_line(rng: random.Random) -> int:
    total = sum(weight for _, weight in YARROW_LINE_WEIGHTS)
    mark = rng.randrange(total)
    cumulative = 0
    for value, weight in YARROW_LINE_WEIGHTS:
        cumulative += weight
        if mark < cumulative:
            return value
    return YARROW_LINE_WEIGHTS[-1][0]


def _generate_yarrow_lines(seed: Optional[Any]) -> List[int]:
    rng = random.Random(str(seed)) if seed is not None else random.SystemRandom()
    return [_weighted_yarrow_line(rng) for _ in range(6)]


def _manual_line_values(lines: Any) -> List[int]:
    if not isinstance(lines, list):
        raise ValueError("Manual Oracle casting requires a six-item lines list ordered bottom-to-top.")
    values = [_normalize_line_value(item) for item in lines]
    if len(values) != 6:
        raise ValueError("Manual Oracle casting requires exactly six lines ordered bottom-to-top.")
    return values


def _bits_from_line_values(values: Sequence[int], *, resulting: bool = False) -> Tuple[int, ...]:
    bits = []
    for value in values:
        definition = LINE_DEFINITIONS[value]
        if resulting:
            definition = LINE_DEFINITIONS[int(definition["changes_to"])]
        bits.append(1 if definition["solid"] else 0)
    return tuple(bits)


def _trigram_payload(bits: LineBits) -> Dict[str, Any]:
    trigram = TRIGRAMS.get(bits)
    if not trigram:
        raise ValueError("Oracle trigram pattern is invalid.")
    return {
        "key": trigram["key"],
        "name": trigram["name"],
        "image": trigram["image"],
        "polarity": trigram["polarity"],
        "bits_bottom_to_top": list(bits),
    }


def _hexagram_payload_from_bits(bits: Sequence[int], *, source_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    bits = tuple(int(bit) for bit in bits)
    if len(bits) != 6:
        raise ValueError("A hexagram requires six lines.")
    lower = _trigram_payload((bits[0], bits[1], bits[2]))
    upper = _trigram_payload((bits[3], bits[4], bits[5]))
    number = KING_WEN_BY_TRIGRAMS.get((upper["key"], lower["key"]))
    if not number:
        raise ValueError("Hexagram pattern could not be resolved against the King Wen trigram table.")
    metadata = HEXAGRAMS[number]
    return {
        "number": number,
        "pinyin": metadata["pinyin"],
        "title": metadata["title"],
        "label": f"{number}. {metadata['title']}",
        "keywords": list(metadata["keywords"]),
        "theme": metadata["theme"],
        "counsel": metadata["counsel"],
        "upper_trigram": upper,
        "lower_trigram": lower,
        "line_bits_bottom_to_top": list(bits),
        "line_visuals_bottom_to_top": ["solid" if bit else "broken" for bit in bits],
        "source_ids": list(source_ids or ["local.iching_huang", "classic.received_zhouyi_sequence", "public.king_wen_hexagram_list"]),
    }


def _hexagram_payload(values: Sequence[int], *, resulting: bool = False) -> Dict[str, Any]:
    return _hexagram_payload_from_bits(_bits_from_line_values(values, resulting=resulting))


def _nuclear_hexagram_payload(values: Sequence[int]) -> Dict[str, Any]:
    bits = _bits_from_line_values(values)
    nuclear_bits = (bits[1], bits[2], bits[3], bits[2], bits[3], bits[4])
    payload = _hexagram_payload_from_bits(
        nuclear_bits,
        source_ids=["public.nuclear_hexagram_structure", "classic.received_zhouyi_sequence", "public.king_wen_hexagram_list"],
    )
    payload["derivation"] = {
        "method": "nuclear_hexagram",
        "line_order": "bottom_to_top",
        "lower_nuclear_lines": [2, 3, 4],
        "upper_nuclear_lines": [3, 4, 5],
        "source_ids": ["public.nuclear_hexagram_structure"],
    }
    return payload


def _moving_line_focus(lines: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    focus = []
    for line in lines:
        if not line.get("moving"):
            continue
        direction = "opens from yin into yang" if line.get("value") == 6 else "settles from yang into yin"
        focus.append({
            "position": line["position"],
            "line_value": line["value"],
            "label": line["label"],
            "focus": line["position_focus"],
            "transition": direction,
            "counsel": f"Line {line['position']} changes at the {line['position_focus']}; adjust that layer before treating the relating hexagram as settled.",
            "source_ids": ["public.iching_divination_method"],
        })
    return focus


def _zhu_xi_line_policy(
    primary: Dict[str, Any],
    relating: Optional[Dict[str, Any]],
    lines: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    moving_positions = [int(line["position"]) for line in lines if line.get("moving")]
    stable_positions = [int(line["position"]) for line in lines if not line.get("moving")]
    moving_count = len(moving_positions)
    base: Dict[str, Any] = {
        "id": "zhu_xi_seven_rule_line_policy",
        "label": "Zhu Xi seven-rule line focus",
        "moving_line_count": moving_count,
        "moving_lines": moving_positions,
        "source_ids": ["classic.zhu_xi_seven_rule_line_policy"],
    }
    if moving_count == 0:
        base.update({
            "focus": "primary_hexagram_judgment",
            "selected_hexagram": primary["label"],
            "selected_lines": [],
            "summary": "No lines change, so the primary hexagram gives the reading focus.",
        })
    elif moving_count == 1:
        base.update({
            "focus": "single_moving_line",
            "selected_hexagram": primary["label"],
            "selected_lines": moving_positions,
            "summary": f"One line changes, so line {moving_positions[0]} of the primary hexagram carries the reading focus.",
        })
    elif moving_count == 2:
        base.update({
            "focus": "two_moving_lines_upper_primary",
            "selected_hexagram": primary["label"],
            "selected_lines": moving_positions,
            "primary_line": max(moving_positions),
            "summary": f"Two lines change, so both primary moving lines are read, with line {max(moving_positions)} carrying the stronger focus.",
        })
    elif moving_count == 3:
        base.update({
            "focus": "primary_and_relating_judgments",
            "selected_hexagram": primary["label"],
            "relating_hexagram": relating["label"] if relating else "",
            "selected_lines": [],
            "summary": "Three lines change, so the primary judgment frames the present pattern and the relating judgment frames the direction of change.",
        })
    elif moving_count == 4:
        selected = stable_positions
        base.update({
            "focus": "relating_non_moving_lines_lower_primary",
            "selected_hexagram": relating["label"] if relating else primary["label"],
            "selected_lines": selected,
            "primary_line": min(selected) if selected else None,
            "summary": f"Four lines change, so the two non-changing line positions in the relating hexagram are emphasized, with line {min(selected) if selected else '-'} carrying the first focus.",
        })
    elif moving_count == 5:
        base.update({
            "focus": "relating_single_non_moving_line",
            "selected_hexagram": relating["label"] if relating else primary["label"],
            "selected_lines": stable_positions,
            "primary_line": stable_positions[0] if stable_positions else None,
            "summary": f"Five lines change, so the one non-changing line position {stable_positions[0] if stable_positions else '-'} in the relating hexagram carries the focus.",
        })
    else:
        all_values = [int(line["value"]) for line in lines]
        if primary.get("number") == 1 and all(value == 9 for value in all_values):
            focus = "qian_all_nines_dynamic_line"
            summary = "All six lines are old yang in Qian, so the special all-nines dynamic line is the focus."
        elif primary.get("number") == 2 and all(value == 6 for value in all_values):
            focus = "kun_all_sixes_dynamic_line"
            summary = "All six lines are old yin in Kun, so the special all-sixes dynamic line is the focus."
        else:
            focus = "relating_hexagram_judgment"
            summary = "All six lines change; outside the Qian/Kun special cases, the relating hexagram gives the reading focus."
        base.update({
            "focus": focus,
            "selected_hexagram": relating["label"] if relating else primary["label"],
            "selected_lines": moving_positions,
            "summary": summary,
        })
    return base


def _reading(
    primary: Dict[str, Any],
    relating: Optional[Dict[str, Any]],
    nuclear: Dict[str, Any],
    lines: Sequence[Dict[str, Any]],
    moving_focus: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    moving_count = len(moving_focus)
    policy = _zhu_xi_line_policy(primary, relating, lines)
    focus = [
        f"Primary: {primary['label']} / {primary['theme']}",
        f"Lower trigram {primary['lower_trigram']['name']} ({primary['lower_trigram']['image']}) under upper trigram {primary['upper_trigram']['name']} ({primary['upper_trigram']['image']}).",
        f"Nuclear: {nuclear['label']} as the inner structure derived from lines 2-4 and 3-5.",
        f"Reading policy: {policy['summary']}",
    ]
    if relating:
        focus.append(f"Relating: {relating['label']} after {moving_count} changing line{'s' if moving_count != 1 else ''}.")
    else:
        focus.append("No changing lines: the primary hexagram is treated as the complete structural answer.")
    focus.extend(item["counsel"] for item in moving_focus[:6])
    return {
        "status": "source_backed_structural_oracle",
        "summary": primary["theme"] if not relating else f"{primary['theme']} The changing lines move the matter toward {relating['label']}.",
        "primary_counsel": primary["counsel"],
        "relating_counsel": relating["counsel"] if relating else "",
        "nuclear_counsel": nuclear["counsel"],
        "policy": policy,
        "focus": focus,
        "limits": [
            "The engine computes structure, line movement, and concise original guidance; it does not copy long translated hexagram text.",
            "Use the source evidence panel when auditing why the Oracle reached this structure.",
        ],
        "source_ids": _source_ids(),
    }


def cast_iching_oracle(
    *,
    question: Any = "",
    method: str = "coins",
    lines: Any = None,
    coins: Any = None,
    seed: Optional[Any] = None,
    coin_value_scheme: str = "heads_2_tails_3",
) -> Dict[str, Any]:
    """Cast or read a standalone I Ching Oracle query.

    Lines are always stored and returned bottom-to-top. This function is
    deliberately independent from BaZi and Yong Shen logic.
    """
    method_key = str(method or "coins").strip().lower().replace("-", "_")
    scheme = str(coin_value_scheme or "heads_2_tails_3").strip().lower()
    if scheme not in COIN_VALUE_SCHEMES:
        raise ValueError("coin_value_scheme must be heads_2_tails_3 or heads_3_tails_2.")

    coin_throws: List[List[str]] = []
    cast_source = "generated_system_random"
    random_model = ""
    if method_key in {"manual", "line_entry", "lines"}:
        values = _manual_line_values(lines)
        resolved_method = "manual_lines"
        cast_source = "provided_manual_lines"
        random_model = "none"
    elif method_key in {"coins", "coin", "three_coins", "three_coin"}:
        if coins is not None:
            if not isinstance(coins, list) or len(coins) != 6:
                raise ValueError("Coin Oracle casting requires six throws ordered bottom-to-top.")
            values = []
            for throw in coins:
                value, faces = _line_from_coin_throw(throw, scheme=scheme)
                values.append(value)
                coin_throws.append(faces)
            cast_source = "provided_coin_throws"
        else:
            values, coin_throws = _generate_coin_lines(seed, scheme=scheme)
            cast_source = "seeded_three_coin_generator" if seed is not None else "system_three_coin_generator"
        resolved_method = "three_coin"
        random_model = "three_coin_equal_coin_faces"
    elif method_key in {"yarrow", "yarrow_stalk", "yarrow_stalks", "stalks"}:
        values = _generate_yarrow_lines(seed)
        resolved_method = "yarrow_probability"
        cast_source = "seeded_yarrow_probability_generator" if seed is not None else "system_yarrow_probability_generator"
        random_model = "yarrow_stalk_probability_1_5_7_3"
    else:
        raise ValueError("Oracle method must be coins, yarrow, or manual.")

    line_rows = [
        _line_payload(index + 1, value, coins=coin_throws[index] if index < len(coin_throws) else None)
        for index, value in enumerate(values)
    ]
    primary = _hexagram_payload(values)
    changing_lines = [line["position"] for line in line_rows if line["moving"]]
    relating = _hexagram_payload(values, resulting=True) if changing_lines else None
    nuclear = _nuclear_hexagram_payload(values)
    moving_focus = _moving_line_focus(line_rows)

    return {
        "method": "iching_oracle_v1",
        "question": _clean_question(question),
        "casting_method": resolved_method,
        "cast_source": cast_source,
        "random_model": random_model,
        "line_order": "bottom_to_top",
        "coin_value_scheme": scheme,
        "seeded": seed is not None,
        "lines": line_rows,
        "changing_lines": changing_lines,
        "moving_line_focus": moving_focus,
        "primary": primary,
        "relating": relating,
        "nuclear": nuclear,
        "reading": _reading(primary, relating, nuclear, line_rows, moving_focus),
        "source_confidence": [
            {
                "key": "source_backed_structural_oracle",
                "label": "Structure source-backed",
                "description": "Line order, changing-line behavior, and King Wen resolution are source-anchored.",
            },
            {
                "key": "original_summary",
                "label": "Original summaries",
                "description": "Short guidance is original app text, not copied canonical translation.",
            },
        ],
        "source_evidence": ORACLE_SOURCE_EVIDENCE,
        "validation": {
            "status": "fixture_backed",
            "fixture_ids": [
                "iching.oracle.manual_all_yang_qian",
                "iching.oracle.manual_all_yin_kun",
                "iching.oracle.moving_lines_resulting_hexagram",
                "iching.oracle.coin_throw_values",
                "iching.oracle.yarrow_probability_model",
                "iching.oracle.nuclear_hexagram_structure",
                "iching.oracle.zhu_xi_line_policy",
            ],
            "source_reference_status": "local_and_public_method_anchored",
        },
        "debug": {
            "primary_trigram_key": f"{primary['upper_trigram']['key']}/{primary['lower_trigram']['key']}",
            "relating_trigram_key": f"{relating['upper_trigram']['key']}/{relating['lower_trigram']['key']}" if relating else "",
            "nuclear_trigram_key": f"{nuclear['upper_trigram']['key']}/{nuclear['lower_trigram']['key']}",
        },
    }


__all__ = [
    "COIN_VALUE_SCHEMES",
    "HEXAGRAMS",
    "KING_WEN_BY_TRIGRAMS",
    "LINE_DEFINITIONS",
    "ORACLE_SOURCE_EVIDENCE",
    "TRIGRAMS",
    "YARROW_LINE_WEIGHTS",
    "cast_iching_oracle",
]
