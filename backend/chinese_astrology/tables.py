ELEMENTS = ("Wood", "Fire", "Earth", "Metal", "Water")

STEMS = (
    {"key": "Jia", "element": "Wood", "polarity": "yang"},
    {"key": "Yi", "element": "Wood", "polarity": "yin"},
    {"key": "Bing", "element": "Fire", "polarity": "yang"},
    {"key": "Ding", "element": "Fire", "polarity": "yin"},
    {"key": "Wu", "element": "Earth", "polarity": "yang"},
    {"key": "Ji", "element": "Earth", "polarity": "yin"},
    {"key": "Geng", "element": "Metal", "polarity": "yang"},
    {"key": "Xin", "element": "Metal", "polarity": "yin"},
    {"key": "Ren", "element": "Water", "polarity": "yang"},
    {"key": "Gui", "element": "Water", "polarity": "yin"},
)

BRANCHES = (
    {"key": "Zi", "animal": "Rat", "element": "Water", "polarity": "yang", "hidden_stems": ("Gui",)},
    {"key": "Chou", "animal": "Ox", "element": "Earth", "polarity": "yin", "hidden_stems": ("Ji", "Gui", "Xin")},
    {"key": "Yin", "animal": "Tiger", "element": "Wood", "polarity": "yang", "hidden_stems": ("Jia", "Bing", "Wu")},
    {"key": "Mao", "animal": "Rabbit", "element": "Wood", "polarity": "yin", "hidden_stems": ("Yi",)},
    {"key": "Chen", "animal": "Dragon", "element": "Earth", "polarity": "yang", "hidden_stems": ("Wu", "Yi", "Gui")},
    {"key": "Si", "animal": "Snake", "element": "Fire", "polarity": "yin", "hidden_stems": ("Bing", "Wu", "Geng")},
    {"key": "Wu", "animal": "Horse", "element": "Fire", "polarity": "yang", "hidden_stems": ("Ding", "Ji")},
    {"key": "Wei", "animal": "Goat", "element": "Earth", "polarity": "yin", "hidden_stems": ("Ji", "Ding", "Yi")},
    {"key": "Shen", "animal": "Monkey", "element": "Metal", "polarity": "yang", "hidden_stems": ("Geng", "Ren", "Wu")},
    {"key": "You", "animal": "Rooster", "element": "Metal", "polarity": "yin", "hidden_stems": ("Xin",)},
    {"key": "Xu", "animal": "Dog", "element": "Earth", "polarity": "yang", "hidden_stems": ("Wu", "Xin", "Ding")},
    {"key": "Hai", "animal": "Pig", "element": "Water", "polarity": "yin", "hidden_stems": ("Ren", "Jia")},
)

STEM_INDEX = {stem["key"]: idx for idx, stem in enumerate(STEMS)}
BRANCH_INDEX = {branch["key"]: idx for idx, branch in enumerate(BRANCHES)}

PRODUCES = {
    "Wood": "Fire",
    "Fire": "Earth",
    "Earth": "Metal",
    "Metal": "Water",
    "Water": "Wood",
}

CONTROLS = {
    "Wood": "Earth",
    "Earth": "Water",
    "Water": "Fire",
    "Fire": "Metal",
    "Metal": "Wood",
}

MONTH_BRANCH_INDICES = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1)

FACTOR_META = {
    "Companion": {
        "chinese": "比劫",
        "pinyin": "bi jie",
        "relation_chinese": "同我",
        "relation_label": "same element as the Day Master",
    },
    "Output": {
        "chinese": "食傷",
        "pinyin": "shi shang",
        "relation_chinese": "我生",
        "relation_label": "the Day Master produces this element",
    },
    "Wealth": {
        "chinese": "財星",
        "pinyin": "cai xing",
        "relation_chinese": "我克",
        "relation_label": "the Day Master controls this element",
    },
    "Influence": {
        "chinese": "官殺",
        "pinyin": "guan sha",
        "relation_chinese": "克我",
        "relation_label": "this element controls the Day Master",
    },
    "Resource": {
        "chinese": "印梟",
        "pinyin": "yin xiao",
        "relation_chinese": "生我",
        "relation_label": "this element produces the Day Master",
    },
}

TEN_GOD_META = {
    "Friend": {"chinese": "比肩", "pinyin": "bi jian"},
    "Rob Wealth": {"chinese": "劫財", "pinyin": "jie cai"},
    "Eating God": {"chinese": "食神", "pinyin": "shi shen"},
    "Hurting Officer": {"chinese": "傷官", "pinyin": "shang guan"},
    "Indirect Wealth": {"chinese": "偏財", "pinyin": "pian cai"},
    "Direct Wealth": {"chinese": "正財", "pinyin": "zheng cai"},
    "Seven Killings": {"chinese": "七殺", "pinyin": "qi sha"},
    "Direct Officer": {"chinese": "正官", "pinyin": "zheng guan"},
    "Indirect Resource": {"chinese": "偏印", "pinyin": "pian yin"},
    "Direct Resource": {"chinese": "正印", "pinyin": "zheng yin"},
}

FIRST_MONTH_STEM_BY_YEAR_STEM = {
    0: 2,
    5: 2,
    1: 4,
    6: 4,
    2: 6,
    7: 6,
    3: 8,
    8: 8,
    4: 0,
    9: 0,
}

FIRST_HOUR_STEM_BY_DAY_STEM = {
    0: 0,
    5: 0,
    1: 2,
    6: 2,
    2: 4,
    7: 4,
    3: 6,
    8: 6,
    4: 8,
    9: 8,
}


def sexagenary_name(index: int) -> str:
    idx = int(index) % 60
    return f"{STEMS[idx % 10]['key']} {BRANCHES[idx % 12]['key']}"


def _ten_god_payload(factor: str, god: str, same_polarity: bool) -> dict:
    factor_meta = FACTOR_META.get(factor, {})
    god_meta = TEN_GOD_META.get(god, {})
    return {
        "factor": factor,
        "factor_chinese": factor_meta.get("chinese"),
        "factor_pinyin": factor_meta.get("pinyin"),
        "relation_chinese": factor_meta.get("relation_chinese"),
        "relation_label": factor_meta.get("relation_label"),
        "god": god,
        "god_chinese": god_meta.get("chinese"),
        "god_pinyin": god_meta.get("pinyin"),
        "polarity_relation": "same" if same_polarity else "opposite",
    }


def ten_god(day_stem_index: int, target_stem_index: int) -> dict:
    day = STEMS[int(day_stem_index) % 10]
    target = STEMS[int(target_stem_index) % 10]
    day_element = day["element"]
    target_element = target["element"]
    same_polarity = day["polarity"] == target["polarity"]

    if target_element == day_element:
        return _ten_god_payload("Companion", "Friend" if same_polarity else "Rob Wealth", same_polarity)
    if PRODUCES[day_element] == target_element:
        return _ten_god_payload("Output", "Eating God" if same_polarity else "Hurting Officer", same_polarity)
    if CONTROLS[day_element] == target_element:
        return _ten_god_payload("Wealth", "Indirect Wealth" if same_polarity else "Direct Wealth", same_polarity)
    if CONTROLS[target_element] == day_element:
        return _ten_god_payload("Influence", "Seven Killings" if same_polarity else "Direct Officer", same_polarity)
    if PRODUCES[target_element] == day_element:
        return _ten_god_payload("Resource", "Indirect Resource" if same_polarity else "Direct Resource", same_polarity)
    return {"factor": "Unknown", "god": "Unknown"}
