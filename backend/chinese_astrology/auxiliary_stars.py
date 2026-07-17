from __future__ import annotations

from typing import Any, Dict, List, Optional

from .curation import confidence_tags
from .relationships import PILLAR_DOMAIN_LABELS
from .tables import BRANCH_INDEX, BRANCHES, STEM_INDEX


PEACH_BLOSSOM_BRANCHES = ("Zi", "Wu", "Mao", "You")
PEACH_BLOSSOM_BY_DAY_BRANCH = {
    "Yin": "Mao",
    "Wu": "Mao",
    "Xu": "Mao",
    "Si": "Wu",
    "You": "Wu",
    "Chou": "Wu",
    "Shen": "You",
    "Zi": "You",
    "Chen": "You",
    "Hai": "Zi",
    "Mao": "Zi",
    "Wei": "Zi",
}

TRAVELING_HORSE_BY_BRANCH = {
    "Shen": "Yin",
    "Zi": "Yin",
    "Chen": "Yin",
    "Yin": "Shen",
    "Wu": "Shen",
    "Xu": "Shen",
    "Si": "Hai",
    "You": "Hai",
    "Chou": "Hai",
    "Hai": "Si",
    "Mao": "Si",
    "Wei": "Si",
}

GENERAL_STAR_BY_BRANCH = {
    "Shen": "Zi",
    "Zi": "Zi",
    "Chen": "Zi",
    "Yin": "Wu",
    "Wu": "Wu",
    "Xu": "Wu",
    "Si": "You",
    "You": "You",
    "Chou": "You",
    "Hai": "Mao",
    "Mao": "Mao",
    "Wei": "Mao",
}

WEN_CHANG_BY_STEM = {
    "Jia": "Si",
    "Yi": "Wu",
    "Bing": "Shen",
    "Ding": "You",
    "Wu": "Shen",
    "Ji": "You",
    "Geng": "Hai",
    "Xin": "Zi",
    "Ren": "Yin",
    "Gui": "Mao",
}

TIAN_YI_BY_STEM = {
    "Jia": ("Chou", "Wei"),
    "Wu": ("Chou", "Wei"),
    "Geng": ("Chou", "Wei"),
    "Yi": ("Zi", "Shen"),
    "Ji": ("Zi", "Shen"),
    "Bing": ("Hai", "You"),
    "Ding": ("Hai", "You"),
    "Ren": ("Mao", "Si"),
    "Gui": ("Mao", "Si"),
    "Xin": ("Yin", "Wu"),
}

TIAN_DE_BY_MONTH_BRANCH = {
    "Yin": ("stem", "Ding"),
    "Mao": ("branch", "Shen"),
    "Chen": ("stem", "Ren"),
    "Si": ("stem", "Xin"),
    "Wu": ("branch", "Hai"),
    "Wei": ("stem", "Jia"),
    "Shen": ("stem", "Gui"),
    "You": ("branch", "Yin"),
    "Xu": ("stem", "Bing"),
    "Hai": ("stem", "Yi"),
    "Zi": ("branch", "Si"),
    "Chou": ("stem", "Geng"),
}

YUE_DE_BY_MONTH_BRANCH = {
    "Yin": "Bing",
    "Wu": "Bing",
    "Xu": "Bing",
    "Shen": "Ren",
    "Zi": "Ren",
    "Chen": "Ren",
    "Hai": "Jia",
    "Mao": "Jia",
    "Wei": "Jia",
    "Si": "Geng",
    "You": "Geng",
    "Chou": "Geng",
}

HUA_GAI_BY_BRANCH = {
    "Yin": "Xu", "Wu": "Xu", "Xu": "Xu",
    "Si": "Chou", "You": "Chou", "Chou": "Chou",
    "Shen": "Chen", "Zi": "Chen", "Chen": "Chen",
    "Hai": "Wei", "Mao": "Wei", "Wei": "Wei",
}

YANG_REN_BY_STEM = {
    "Jia": "Mao", "Yi": "Chen", "Bing": "Wu", "Ding": "Wei", "Wu": "Wu",
    "Ji": "Wei", "Geng": "You", "Xin": "Xu", "Ren": "Zi", "Gui": "Chou",
}

GAN_LU_BY_STEM = {
    "Jia": "Yin", "Yi": "Mao", "Bing": "Si", "Ding": "Wu", "Wu": "Si",
    "Ji": "Wu", "Geng": "Shen", "Xin": "You", "Ren": "Hai", "Gui": "Zi",
}

HONG_YAN_BY_STEM = {
    "Jia": "Wu", "Yi": "Wu", "Bing": "Yin", "Ding": "Wei", "Wu": "Chen",
    "Ji": "Chen", "Geng": "Xu", "Xin": "You", "Ren": "Zi", "Gui": "Shen",
}

JIE_SHA_BY_BRANCH = {
    "Shen": "Si", "Zi": "Si", "Chen": "Si",
    "Hai": "Shen", "Mao": "Shen", "Wei": "Shen",
    "Yin": "Hai", "Wu": "Hai", "Xu": "Hai",
    "Si": "Yin", "You": "Yin", "Chou": "Yin",
}

WANG_SHEN_BY_BRANCH = {
    "Shen": "Hai", "Zi": "Hai", "Chen": "Hai",
    "Hai": "Yin", "Mao": "Yin", "Wei": "Yin",
    "Yin": "Si", "Wu": "Si", "Xu": "Si",
    "Si": "Shen", "You": "Shen", "Chou": "Shen",
}

GU_CHEN_BY_YEAR_BRANCH = {
    "Hai": "Yin", "Zi": "Yin", "Chou": "Yin",
    "Yin": "Si", "Mao": "Si", "Chen": "Si",
    "Si": "Shen", "Wu": "Shen", "Wei": "Shen",
    "Shen": "Hai", "You": "Hai", "Xu": "Hai",
}

GUA_SU_BY_YEAR_BRANCH = {
    "Hai": "Xu", "Zi": "Xu", "Chou": "Xu",
    "Yin": "Chou", "Mao": "Chou", "Chen": "Chou",
    "Si": "Chen", "Wu": "Chen", "Wei": "Chen",
    "Shen": "Wei", "You": "Wei", "Xu": "Wei",
}

KUI_GANG_DAY_PILLARS = {("Geng", "Chen"), ("Geng", "Xu"), ("Ren", "Chen"), ("Wu", "Xu")}
SAN_QI_SETS = (
    ("Jia", "Wu", "Geng"),
    ("Yi", "Bing", "Ding"),
    ("Ren", "Gui", "Xin"),
)

SHEN_SHA_SOURCE_PAGE_REFS = {
    "tian_yi": ["lu_zhiji_fate_search:p133"],
    "wen_chang": ["lu_zhiji_fate_search:p133"],
    "gan_lu": ["lu_zhiji_fate_search:p133"],
    "yang_ren": ["lu_zhiji_fate_search:p133"],
    "hong_yan": ["lu_zhiji_fate_search:p133"],
    "traveling_horse": ["lu_zhiji_fate_search:p134"],
    "general_star": ["lu_zhiji_fate_search:p134"],
    "peach_blossom": ["lu_zhiji_fate_search:p134"],
    "hua_gai": ["lu_zhiji_fate_search:p134"],
    "jie_sha": ["lu_zhiji_fate_search:p134"],
    "wang_shen": ["lu_zhiji_fate_search:p134"],
    "gu_chen": ["lu_zhiji_fate_search:p134"],
    "gua_su": ["lu_zhiji_fate_search:p134"],
    "tian_de": ["lu_zhiji_fate_search:p135"],
    "yue_de": ["lu_zhiji_fate_search:p135"],
    "kong_wang": ["lu_zhiji_fate_search:p135", "sanming_tonghui_part3:p272"],
    "san_qi": ["lu_zhiji_fate_search:pp135-136"],
    "kui_gang": ["lu_zhiji_fate_search:p136"],
}


def _shen_sha_source_page_refs(marker_id: str) -> List[str]:
    return list(SHEN_SHA_SOURCE_PAGE_REFS.get(marker_id, ()))

MARKER_META = {
    "peach_blossom": {
        "label": "Peach Blossom",
        "chinese": "桃花",
        "pinyin": "tao hua",
        "theme": "Attraction, social visibility, charisma, and relationship timing.",
        "formula": "Day Branch triad target: Yin/Wu/Xu -> Mao; Si/You/Chou -> Wu; Shen/Zi/Chen -> You; Hai/Mao/Wei -> Zi.",
        "variant": "day_branch_personal",
        "keywords": ["attraction", "visibility", "charisma", "relationship timing"],
    },
    "traveling_horse": {
        "label": "Traveling Horse",
        "chinese": "驿马",
        "pinyin": "yi ma",
        "theme": "Movement, travel, relocation, transition, and change-of-role themes.",
        "formula": "Day Branch triad target: Shen/Zi/Chen -> Yin; Yin/Wu/Xu -> Shen; Si/You/Chou -> Hai; Hai/Mao/Wei -> Si.",
        "variant": "day_branch_triad",
        "keywords": ["movement", "travel", "relocation", "transition"],
    },
    "general_star": {
        "label": "General Star",
        "chinese": "将星",
        "pinyin": "jiang xing",
        "theme": "Command, decisiveness, focus, and visible responsibility themes.",
        "formula": "Day Branch triad center: Shen/Zi/Chen -> Zi; Yin/Wu/Xu -> Wu; Si/You/Chou -> You; Hai/Mao/Wei -> Mao.",
        "variant": "day_branch_triad_center",
        "keywords": ["command", "focus", "responsibility", "presence"],
    },
    "wen_chang": {
        "label": "Wen Chang",
        "chinese": "文昌",
        "pinyin": "wen chang",
        "theme": "Study, writing, documents, craft, exams, and cultivated skill themes.",
        "formula": "Day Stem target: Jia->Si, Yi->Wu, Bing/Wu->Shen, Ding/Ji->You, Geng->Hai, Xin->Zi, Ren->Yin, Gui->Mao.",
        "variant": "day_stem_main",
        "keywords": ["study", "writing", "documents", "skill"],
    },
    "tian_yi": {
        "label": "Tian Yi Nobleman",
        "chinese": "天乙贵人",
        "pinyin": "tian yi gui ren",
        "theme": "Help, guidance, support, and timely assistance themes.",
        "formula": "Day Stem paired-branch variant: Jia/Wu/Geng->Chou/Wei; Yi/Ji->Zi/Shen; Bing/Ding->Hai/You; Ren/Gui->Mao/Si; Xin->Yin/Wu.",
        "variant": "day_stem_paired_branches",
        "keywords": ["support", "guidance", "help", "assistance"],
    },
    "tian_de": {
        "label": "Heavenly Virtue",
        "chinese": "天德",
        "pinyin": "tian de",
        "theme": "Softening, virtue, repair, and support-through-conduct themes.",
        "formula": "Month Branch table with stem or branch target; match visible stems or branches according to the table cell.",
        "variant": "month_branch_mixed_target",
        "keywords": ["virtue", "softening", "repair", "support"],
    },
    "yue_de": {
        "label": "Moon Virtue",
        "chinese": "月德",
        "pinyin": "yue de",
        "theme": "Supportive conduct, social ease, and softening of difficult texture.",
        "formula": "Month Branch triad stem target: Yin/Wu/Xu->Bing; Shen/Zi/Chen->Ren; Hai/Mao/Wei->Jia; Si/You/Chou->Geng.",
        "variant": "month_branch_triad_stem",
        "keywords": ["support", "conduct", "ease", "softening"],
    },
    "hua_gai": {
        "label": "Hua Gai",
        "chinese": "hua gai",
        "pinyin": "hua gai",
        "theme": "Solitude, specialist study, art, metaphysics, and inward distinction.",
        "formula": "Day Branch triad storage target: Yin/Wu/Xu->Xu; Si/You/Chou->Chou; Shen/Zi/Chen->Chen; Hai/Mao/Wei->Wei.",
        "variant": "day_branch_triad_storage",
        "keywords": ["study", "art", "solitude", "metaphysics"],
    },
    "yang_ren": {
        "label": "Yang Ren",
        "chinese": "yang ren",
        "pinyin": "yang ren",
        "theme": "Sharp force, competitiveness, courage, and risk that needs structure.",
        "formula": "Day Stem blade branch table: Jia->Mao, Yi->Chen, Bing/Wu->Wu, Ding/Ji->Wei, Geng->You, Xin->Xu, Ren->Zi, Gui->Chou.",
        "variant": "day_stem_blade_branch",
        "keywords": ["force", "competition", "risk", "decisiveness"],
    },
    "gan_lu": {
        "label": "Gan Lu",
        "chinese": "gan lu",
        "pinyin": "gan lu",
        "theme": "Stem-root prosperity, capacity, support, and practical footing.",
        "formula": "Day Stem Lu branch: Jia->Yin, Yi->Mao, Bing/Wu->Si, Ding/Ji->Wu, Geng->Shen, Xin->You, Ren->Hai, Gui->Zi.",
        "variant": "day_stem_lu_branch",
        "keywords": ["root", "capacity", "support", "standing"],
    },
    "hong_yan": {
        "label": "Hong Yan",
        "chinese": "hong yan",
        "pinyin": "hong yan",
        "theme": "Personal charm, sensual visibility, attraction, and social magnetism.",
        "formula": "Day Stem red-beauty table: Jia/Yi->Wu, Bing->Yin, Ding->Wei, Wu/Ji->Chen, Geng->Xu, Xin->You, Ren->Zi, Gui->Shen.",
        "variant": "day_stem_red_beauty",
        "keywords": ["attraction", "charm", "visibility", "social"],
    },
    "jie_sha": {
        "label": "Jie Sha",
        "chinese": "jie sha",
        "pinyin": "jie sha",
        "theme": "Robbery-killing pressure, sudden contests, and risky loss channels.",
        "formula": "Day Branch triad target: Shen/Zi/Chen->Si; Hai/Mao/Wei->Shen; Yin/Wu/Xu->Hai; Si/You/Chou->Yin.",
        "variant": "day_branch_triad_pressure",
        "keywords": ["pressure", "loss", "risk", "contest"],
    },
    "wang_shen": {
        "label": "Wang Shen",
        "chinese": "wang shen",
        "pinyin": "wang shen",
        "theme": "Concealed pressure, wandering attention, memory, and unsettled attachment.",
        "formula": "Day Branch triad target: Shen/Zi/Chen->Hai; Hai/Mao/Wei->Yin; Yin/Wu/Xu->Si; Si/You/Chou->Shen.",
        "variant": "day_branch_triad_pressure",
        "keywords": ["pressure", "wandering", "memory", "hidden"],
    },
    "gu_chen": {
        "label": "Gu Chen",
        "chinese": "gu chen",
        "pinyin": "gu chen",
        "theme": "Independence, isolation, delayed intimacy, and self-contained temperament.",
        "formula": "Year Branch seasonal group: Hai/Zi/Chou->Yin; Yin/Mao/Chen->Si; Si/Wu/Wei->Shen; Shen/You/Xu->Hai.",
        "variant": "year_branch_seasonal_group",
        "keywords": ["independence", "isolation", "reserve", "distance"],
    },
    "gua_su": {
        "label": "Gua Su",
        "chinese": "gua su",
        "pinyin": "gua su",
        "theme": "Solitary partnership tone, emotional reserve, and separation motifs.",
        "formula": "Year Branch seasonal group: Hai/Zi/Chou->Xu; Yin/Mao/Chen->Chou; Si/Wu/Wei->Chen; Shen/You/Xu->Wei.",
        "variant": "year_branch_seasonal_group",
        "keywords": ["solitude", "reserve", "partnership", "separation"],
    },
    "kong_wang": {
        "label": "Kong Wang",
        "chinese": "kong wang",
        "pinyin": "kong wang",
        "theme": "Void/emptiness, missing function, delayed manifestation, or ungrounded branch topics.",
        "formula": "Day pillar xun void branches: JiaZi->Xu/Hai; JiaXu->Shen/You; JiaShen->Wu/Wei; JiaWu->Chen/Si; JiaChen->Yin/Mao; JiaYin->Zi/Chou.",
        "variant": "day_pillar_xun_void",
        "keywords": ["void", "delay", "absence", "ungrounded"],
    },
    "kui_gang": {
        "label": "Kui Gang",
        "chinese": "kui gang",
        "pinyin": "kui gang",
        "theme": "Strong-willed command, pressure-bearing temperament, and uncompromising force.",
        "formula": "Exact Day Pillar: Geng-Chen, Geng-Xu, Ren-Chen, Wu-Xu.",
        "variant": "exact_day_pillar",
        "keywords": ["command", "force", "will", "pressure"],
    },
    "san_qi": {
        "label": "San Qi",
        "chinese": "san qi",
        "pinyin": "san qi",
        "theme": "Three-wonders pattern: unusual talent, coherence, and visible ordered support.",
        "formula": "Visible stems include Jia-Wu-Geng, Yi-Bing-Ding, or Ren-Gui-Xin, ideally in order.",
        "variant": "visible_stem_sequence",
        "keywords": ["talent", "coherence", "support", "unusual"],
    },
}

MARKER_CHINESE = {
    "peach_blossom": "\u6843\u82b1",
    "traveling_horse": "\u9a7f\u9a6c",
    "general_star": "\u5c06\u661f",
    "wen_chang": "\u6587\u660c",
    "tian_yi": "\u5929\u4e59\u8d35\u4eba",
    "tian_de": "\u5929\u5fb7",
    "yue_de": "\u6708\u5fb7",
    "hua_gai": "\u534e\u76d6",
    "yang_ren": "\u7f8a\u5203",
    "gan_lu": "\u5e72\u7984",
    "hong_yan": "\u7ea2\u8273",
    "jie_sha": "\u52ab\u715e",
    "wang_shen": "\u4ea1\u795e",
    "gu_chen": "\u5b64\u8fb0",
    "gua_su": "\u5be1\u5bbf",
    "kong_wang": "\u7a7a\u4ea1",
    "kui_gang": "\u9b41\u7f61",
    "san_qi": "\u4e09\u5947",
}

SOURCE_BASIS = [
    {
        "id": "local.destiny_code_peach_blossom",
        "label": "BaZi - The Destiny Code",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-your-guide-to-the-four-pillar-of-destin.md",
        "basis": "Personal Peach Blossom is derived from the Day Branch and may appear in natal, Luck Pillar, or annual branches as attraction/popularity potential.",
    },
    {
        "id": "local.destiny_code_revealed_peach_blossom",
        "label": "BaZi - The Destiny Code Revealed",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-revealed-a-deeper-journey-into-the-four-pillars-of-destiny.md",
        "basis": "Peach Blossom must be read with placement, affected palace, element quality, and relationship-contact pressure rather than as an automatic promise.",
    },
    {
        "id": "web.bazitalk_shen_sha_formula_table",
        "label": "说八字 - 八字神煞概要总结",
        "url": "https://bazitalk.com/category/shensha/11429.html",
        "basis": "Chinese formula cross-check for common Shen Sha tables including Tian Yi, Yi Ma, Wen Chang, Jiang Xing, Tian De, Yue De, and Tao Hua.",
    },
    {
        "id": "web.fatemaster_yi_ma",
        "label": "FateMaster - Yi Ma",
        "url": "https://www.fatemaster.ai/en/guides/shensha/yi-ma",
        "basis": "English cross-check for Traveling Horse / Yi Ma as a branch-triad auxiliary marker.",
    },
    {
        "id": "local.chinese_books_shen_sha",
        "label": "Chinese BaZi Shen Sha tables",
        "path": "output/chinese_books_private_corpus/ocr",
        "basis": "Local Chinese sources list expanded auxiliary markers including Hua Gai, Yang Ren, Gan Lu, Hong Yan, Jie Sha, Wang Shen, Gu Chen, Gua Su, Kong Wang, Kui Gang, and San Qi.",
    },
]


def build_auxiliary_stars(
    *,
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Optional[Dict[str, Any]] = None,
    relationships: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    peach = build_peach_blossom_profile(
        pillars=pillars,
        timing=timing,
        relationships=relationships,
    )
    markers = _build_auxiliary_markers(
        pillars=pillars,
        timing=timing or {},
        relationships=relationships or {},
        peach=peach,
    )
    return {
        "status": "source_anchored_markers",
        "method": "auxiliary_stars_v1",
        "markers": markers,
        "active_markers": [marker for marker in markers if marker.get("marker_state") != "quiet"],
        "peach_blossom": peach,
        "notes": [
            "Auxiliary stars refine placement, movement, visibility, study, support, and virtue themes after the main BaZi structure is read.",
        ],
        "source_basis": SOURCE_BASIS,
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }


def build_peach_blossom_profile(
    *,
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Optional[Dict[str, Any]] = None,
    relationships: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    day = pillars.get("day") if isinstance(pillars, dict) else {}
    day_branch = str((day or {}).get("branch") or "")
    target_branch = PEACH_BLOSSOM_BY_DAY_BRANCH.get(day_branch)
    if not target_branch:
        return {
            "status": "unavailable",
            "method": "day_branch_personal_peach_blossom_v1",
            "summary": "Personal Peach Blossom cannot be calculated without the Day Branch.",
            "source_basis": SOURCE_BASIS,
            "source_confidence": confidence_tags("local_source", "provisional_model"),
        }

    natal = _matching_placements(pillars, target_branch, "natal")
    timing_hits = _timing_placements(timing or {}, target_branch)
    activations = natal + timing_hits
    pressure = _branch_pressure(target_branch, relationships or {})
    branch_family = _peach_blossom_branch_presence(pillars, timing or {})
    summary_bits = [f"{target_branch} is the personal Peach Blossom branch for Day Branch {day_branch}."]
    if natal:
        summary_bits.append(f"It appears in {len(natal)} natal placement(s).")
    if timing_hits:
        summary_bits.append(f"It is activated by {len(timing_hits)} timing layer(s).")
    if pressure.get("status") != "clear":
        summary_bits.append(f"Relationship-code pressure is {pressure['status']}.")

    return {
        "status": "source_based_preview",
        "method": "day_branch_personal_peach_blossom_v1",
        "day_branch": day_branch,
        "target_branch": target_branch,
        "target_animal": _branch_animal(target_branch),
        "natal_count": len(natal),
        "timing_count": len(timing_hits),
        "activations": activations,
        "pressure": pressure,
        "branch_family": branch_family,
        "keywords": MARKER_META["peach_blossom"]["keywords"],
        "summary": " ".join(summary_bits),
        "source_basis": SOURCE_BASIS,
        "source_confidence": confidence_tags("local_source", "computed_rule"),
    }


def _build_auxiliary_markers(
    *,
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Dict[str, Any],
    relationships: Dict[str, Any],
    peach: Dict[str, Any],
) -> List[Dict[str, Any]]:
    markers: List[Dict[str, Any]] = []
    if peach.get("status") == "source_based_preview":
        markers.append(_marker_from_targets(
            marker_id="peach_blossom",
            reference_type="day_branch",
            reference_value=str(peach.get("day_branch") or ""),
            targets=[{"type": "branch", "value": str(peach.get("target_branch") or "")}],
            pillars=pillars,
            timing=timing,
            relationships=relationships,
            known_activations=peach.get("activations"),
            known_pressure=peach.get("pressure"),
            summary=peach.get("summary"),
        ))

    day_branch = str(((pillars.get("day") or {}) if isinstance(pillars, dict) else {}).get("branch") or "")
    year_branch = str(((pillars.get("year") or {}) if isinstance(pillars, dict) else {}).get("branch") or "")
    day_stem = str(((pillars.get("day") or {}) if isinstance(pillars, dict) else {}).get("stem") or "")
    month_branch = str(((pillars.get("month") or {}) if isinstance(pillars, dict) else {}).get("branch") or "")

    for marker_id, mapping in (
        ("traveling_horse", TRAVELING_HORSE_BY_BRANCH),
        ("general_star", GENERAL_STAR_BY_BRANCH),
    ):
        target = mapping.get(day_branch)
        if target:
            markers.append(_marker_from_targets(
                marker_id=marker_id,
                reference_type="day_branch",
                reference_value=day_branch,
                targets=[{"type": "branch", "value": target}],
                pillars=pillars,
                timing=timing,
                relationships=relationships,
            ))

    wen_chang = WEN_CHANG_BY_STEM.get(day_stem)
    if wen_chang:
        markers.append(_marker_from_targets(
            marker_id="wen_chang",
            reference_type="day_stem",
            reference_value=day_stem,
            targets=[{"type": "branch", "value": wen_chang}],
            pillars=pillars,
            timing=timing,
            relationships=relationships,
        ))

    tian_yi = TIAN_YI_BY_STEM.get(day_stem)
    if tian_yi:
        markers.append(_marker_from_targets(
            marker_id="tian_yi",
            reference_type="day_stem",
            reference_value=day_stem,
            targets=[{"type": "branch", "value": branch} for branch in tian_yi],
            pillars=pillars,
            timing=timing,
            relationships=relationships,
        ))

    tian_de = TIAN_DE_BY_MONTH_BRANCH.get(month_branch)
    if tian_de:
        target_type, value = tian_de
        markers.append(_marker_from_targets(
            marker_id="tian_de",
            reference_type="month_branch",
            reference_value=month_branch,
            targets=[{"type": target_type, "value": value}],
            pillars=pillars,
            timing=timing,
            relationships=relationships,
        ))

    yue_de = YUE_DE_BY_MONTH_BRANCH.get(month_branch)
    if yue_de:
        markers.append(_marker_from_targets(
            marker_id="yue_de",
            reference_type="month_branch",
            reference_value=month_branch,
            targets=[{"type": "stem", "value": yue_de}],
            pillars=pillars,
            timing=timing,
            relationships=relationships,
        ))

    for marker_id, mapping, reference_type, reference_value in (
        ("hua_gai", HUA_GAI_BY_BRANCH, "day_branch", day_branch),
        ("jie_sha", JIE_SHA_BY_BRANCH, "day_branch", day_branch),
        ("wang_shen", WANG_SHEN_BY_BRANCH, "day_branch", day_branch),
        ("gu_chen", GU_CHEN_BY_YEAR_BRANCH, "year_branch", year_branch),
        ("gua_su", GUA_SU_BY_YEAR_BRANCH, "year_branch", year_branch),
    ):
        target = mapping.get(reference_value)
        if target:
            markers.append(_marker_from_targets(
                marker_id=marker_id,
                reference_type=reference_type,
                reference_value=reference_value,
                targets=[{"type": "branch", "value": target}],
                pillars=pillars,
                timing=timing,
                relationships=relationships,
            ))

    for marker_id, mapping in (
        ("yang_ren", YANG_REN_BY_STEM),
        ("gan_lu", GAN_LU_BY_STEM),
        ("hong_yan", HONG_YAN_BY_STEM),
    ):
        target = mapping.get(day_stem)
        if target:
            markers.append(_marker_from_targets(
                marker_id=marker_id,
                reference_type="day_stem",
                reference_value=day_stem,
                targets=[{"type": "branch", "value": target}],
                pillars=pillars,
                timing=timing,
                relationships=relationships,
            ))

    kong_wang = _kong_wang_targets(day_stem, day_branch)
    if kong_wang:
        markers.append(_marker_from_targets(
            marker_id="kong_wang",
            reference_type="day_pillar",
            reference_value=f"{day_stem}-{day_branch}",
            targets=[{"type": "branch", "value": branch} for branch in kong_wang],
            pillars=pillars,
            timing=timing,
            relationships=relationships,
        ))

    markers.append(_kui_gang_marker(pillars, timing))
    markers.append(_san_qi_marker(pillars, timing))

    # Year-branch variants are included only when they add a different target.
    for marker_id, mapping in (
        ("traveling_horse", TRAVELING_HORSE_BY_BRANCH),
        ("general_star", GENERAL_STAR_BY_BRANCH),
    ):
        target = mapping.get(year_branch)
        if target and not any(
            marker.get("id") == marker_id and marker.get("target_summary") == target
            for marker in markers
        ):
            year_marker = _marker_from_targets(
                marker_id=marker_id,
                reference_type="year_branch",
                reference_value=year_branch,
                targets=[{"type": "branch", "value": target}],
                pillars=pillars,
                timing=timing,
                relationships=relationships,
            )
            year_marker["id"] = f"{marker_id}_year"
            year_marker["secondary_reference"] = True
            markers.append(year_marker)

    order = {
        "peach_blossom": 0,
        "traveling_horse": 1,
        "general_star": 2,
        "wen_chang": 3,
        "tian_yi": 4,
        "tian_de": 5,
        "yue_de": 6,
        "hua_gai": 7,
        "yang_ren": 8,
        "gan_lu": 9,
        "hong_yan": 10,
        "jie_sha": 11,
        "wang_shen": 12,
        "gu_chen": 13,
        "gua_su": 14,
        "kong_wang": 15,
        "kui_gang": 16,
        "san_qi": 17,
        "traveling_horse_year": 18,
        "general_star_year": 19,
    }
    return sorted(markers, key=lambda marker: (order.get(str(marker.get("id")), 99), marker.get("secondary_reference") is True))


def _kong_wang_targets(day_stem: str, day_branch: str) -> List[str]:
    stem_index = STEM_INDEX.get(str(day_stem or ""))
    branch_index = BRANCH_INDEX.get(str(day_branch or ""))
    if stem_index is None or branch_index is None:
        return []
    for cycle_index in range(60):
        if cycle_index % 10 == stem_index and cycle_index % 12 == branch_index:
            xun_start = (cycle_index // 10) * 10
            present_branches = {(xun_start + offset) % 12 for offset in range(10)}
            missing = [BRANCHES[index]["key"] for index in range(12) if index not in present_branches]
            return missing
    return []


def _kui_gang_marker(
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Dict[str, Any],
) -> Dict[str, Any]:
    day = (pillars.get("day") or {}) if isinstance(pillars, dict) else {}
    activations: List[Dict[str, Any]] = []
    if (day.get("stem"), day.get("branch")) in KUI_GANG_DAY_PILLARS:
        activations.append(_placement_payload(day, "day", "natal"))
    return _custom_marker(
        marker_id="kui_gang",
        reference_type="day_pillar",
        reference_value=f"{day.get('stem') or '-'}-{day.get('branch') or '-'}",
        target_summary="Geng-Chen / Geng-Xu / Ren-Chen / Wu-Xu",
        activations=activations,
        extra={
            "timing_activation_status": "unsupported_with_current_sources",
            "timing_activation_note": (
                "The checked source defines Kui Gang by the natal Day Pillar; "
                "matching timing pillars are not promoted as fresh activations."
            ),
        },
    )


def _san_qi_marker(
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Dict[str, Any],
) -> Dict[str, Any]:
    visible = [
        str((pillars.get(name) or {}).get("stem") or "")
        for name in ("year", "month", "day", "hour")
        if isinstance(pillars, dict) and isinstance(pillars.get(name), dict)
    ]
    activations: List[Dict[str, Any]] = []
    matched_set: Optional[tuple[str, str, str]] = None
    order_state = "missing"
    for target in SAN_QI_SETS:
        if set(target).issubset(set(visible)):
            matched_set = target
            positions = [visible.index(stem) for stem in target]
            order_state = "ordered" if positions == sorted(positions) else "unordered"
            for pillar_name in ("year", "month", "day", "hour"):
                pillar = pillars.get(pillar_name) if isinstance(pillars, dict) else None
                if isinstance(pillar, dict) and pillar.get("stem") in target:
                    row = _placement_payload(pillar, pillar_name, "natal")
                    row["target_type"] = "stem"
                    activations.append(row)
            break
    return _custom_marker(
        marker_id="san_qi",
        reference_type="visible_stems",
        reference_value="-".join(stem for stem in visible if stem),
        target_summary="Jia-Wu-Geng / Yi-Bing-Ding / Ren-Gui-Xin",
        activations=activations,
        extra={"matched_set": list(matched_set or []), "order_state": order_state},
    )


def _custom_marker(
    *,
    marker_id: str,
    reference_type: str,
    reference_value: str,
    target_summary: str,
    activations: List[Dict[str, Any]],
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    meta = MARKER_META[marker_id]
    state = "active" if activations else "quiet"
    payload = {
        "id": marker_id,
        "label": meta["label"],
        "chinese": MARKER_CHINESE.get(marker_id, meta["chinese"]),
        "pinyin": meta["pinyin"],
        "status": "source_anchored_marker",
        "marker_state": state,
        "state_label": _marker_state_label(state),
        "formula_variant": meta["variant"],
        "formula": meta["formula"],
        "reference": {
            "type": reference_type,
            "label": _reference_label(reference_type),
            "value": reference_value,
        },
        "targets": [{"type": "exact", "value": target_summary, "label": target_summary}],
        "target_summary": target_summary,
        "natal_count": sum(1 for row in activations if row.get("layer") == "natal"),
        "timing_count": sum(1 for row in activations if row.get("layer") != "natal"),
        "flowing_activations": [row for row in activations if str(row.get("layer") or "").startswith("flowing_")],
        "activations": activations,
        "pressure": {"status": "clear", "event_impacts": []},
        "placement_interpretation": _placement_interpretation(activations),
        "timing_interpretation": _timing_interpretation(activations),
        "summary": _generic_marker_summary(
            label=str(meta["label"]),
            target_summary=target_summary,
            reference_type=reference_type,
            reference_value=reference_value,
            activations=activations,
        ),
        "theme": meta["theme"],
        "keywords": meta["keywords"],
        "source_page_refs": _shen_sha_source_page_refs(marker_id),
        "source_basis": SOURCE_BASIS,
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }
    payload.update(extra)
    return payload


def _marker_from_targets(
    *,
    marker_id: str,
    reference_type: str,
    reference_value: str,
    targets: List[Dict[str, str]],
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Dict[str, Any],
    relationships: Dict[str, Any],
    known_activations: Optional[Any] = None,
    known_pressure: Optional[Any] = None,
    summary: Optional[Any] = None,
) -> Dict[str, Any]:
    meta = MARKER_META[marker_id]
    activations = (
        [row for row in known_activations if isinstance(row, dict)]
        if isinstance(known_activations, list)
        else _target_placements(pillars, timing, targets)
    )
    pressure = (
        known_pressure
        if isinstance(known_pressure, dict)
        else _combined_branch_pressure([target["value"] for target in targets if target.get("type") == "branch"], relationships)
    )
    state = _marker_state(activations, pressure)
    target_summary = " / ".join(_target_label(target) for target in targets)
    marker_summary = str(summary) if summary else _generic_marker_summary(
        label=str(meta["label"]),
        target_summary=target_summary,
        reference_type=reference_type,
        reference_value=reference_value,
        activations=activations,
    )
    return {
        "id": marker_id,
        "label": meta["label"],
        "chinese": MARKER_CHINESE.get(marker_id, meta["chinese"]),
        "pinyin": meta["pinyin"],
        "status": "source_anchored_marker",
        "marker_state": state,
        "state_label": _marker_state_label(state),
        "formula_variant": meta["variant"],
        "formula": meta["formula"],
        "reference": {
            "type": reference_type,
            "label": _reference_label(reference_type),
            "value": reference_value,
        },
        "targets": [_target_payload(target) for target in targets],
        "target_summary": target_summary,
        "natal_count": sum(1 for row in activations if row.get("layer") == "natal"),
        "timing_count": sum(1 for row in activations if row.get("layer") != "natal"),
        "flowing_activations": [row for row in activations if str(row.get("layer") or "").startswith("flowing_")],
        "activations": activations,
        "pressure": pressure,
        "placement_interpretation": _placement_interpretation(activations),
        "timing_interpretation": _timing_interpretation(activations),
        "summary": marker_summary,
        "theme": meta["theme"],
        "keywords": meta["keywords"],
        "source_page_refs": _shen_sha_source_page_refs(marker_id),
        "source_basis": SOURCE_BASIS,
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }


def _target_placements(
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Dict[str, Any],
    targets: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for target in targets:
        if target.get("type") == "branch":
            rows.extend(_matching_placements(pillars, str(target.get("value") or ""), "natal"))
            rows.extend(_timing_placements(timing, str(target.get("value") or "")))
        elif target.get("type") == "stem":
            rows.extend(_matching_stem_placements(pillars, str(target.get("value") or ""), "natal"))
            rows.extend(_timing_stem_placements(timing, str(target.get("value") or "")))
    return rows


def _matching_stem_placements(
    pillars: Dict[str, Optional[Dict[str, Any]]],
    stem: str,
    layer: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for pillar_name in ("year", "month", "day", "hour"):
        pillar = pillars.get(pillar_name) if isinstance(pillars, dict) else None
        if isinstance(pillar, dict) and pillar.get("stem") == stem:
            row = _placement_payload(pillar, pillar_name, layer)
            row["target_type"] = "stem"
            rows.append(row)
    return rows


def _timing_stem_placements(timing: Dict[str, Any], stem: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key, layer in (
        ("active_luck_pillar", "luck"),
        ("annual_pillar", "annual"),
        ("flowing_month_pillar", "flowing_month"),
        ("flowing_day_pillar", "flowing_day"),
        ("flowing_hour_pillar", "flowing_hour"),
    ):
        pillar = timing.get(key)
        if isinstance(pillar, dict) and pillar.get("stem") == stem:
            row = _placement_payload(pillar, layer, layer)
            row["target_type"] = "stem"
            rows.append(row)
    return rows


def _combined_branch_pressure(branches: List[str], relationships: Dict[str, Any]) -> Dict[str, Any]:
    impacts: List[Dict[str, Any]] = []
    for branch in branches:
        impacts.extend(_branch_pressure(branch, relationships).get("event_impacts") or [])
    tones = {impact.get("tone") for impact in impacts}
    if "challenging" in tones and "supportive" in tones:
        status = "mixed"
    elif "challenging" in tones:
        status = "pressured"
    elif "supportive" in tones:
        status = "supported"
    else:
        status = "clear"
    return {"status": status, "event_impacts": impacts[:6]}


def _marker_state(activations: List[Dict[str, Any]], pressure: Dict[str, Any]) -> str:
    pressure_status = str((pressure or {}).get("status") or "clear")
    if pressure_status in {"pressured", "mixed", "supported"} and activations:
        return pressure_status
    if activations:
        return "active"
    return "quiet"


def _marker_state_label(state: str) -> str:
    return {
        "active": "Active",
        "quiet": "Quiet",
        "pressured": "Pressured",
        "supported": "Supported",
        "mixed": "Mixed",
    }.get(state, str(state or "Open").title())


def _generic_marker_summary(
    *,
    label: str,
    target_summary: str,
    reference_type: str,
    reference_value: str,
    activations: List[Dict[str, Any]],
) -> str:
    opening = f"{label} target {target_summary} is calculated from {_reference_label(reference_type)} {reference_value}."
    if not activations:
        return f"{opening} It is not active in the checked natal, Luck, or annual placements."
    layers = sorted({str(row.get("pillar_label") or row.get("layer") or "") for row in activations if row.get("pillar_label") or row.get("layer")})
    return f"{opening} It appears in {', '.join(layers[:4])}."


def _placement_interpretation(activations: List[Dict[str, Any]]) -> Dict[str, Any]:
    natal = [row for row in activations if row.get("layer") == "natal"]
    palaces = sorted({str(row.get("pillar_label") or row.get("pillar") or "") for row in natal if row.get("pillar_label") or row.get("pillar")})
    return {
        "status": "natal_present" if natal else "not_natal",
        "palaces": palaces,
        "summary": (
            f"Natal placement appears in {', '.join(palaces)}."
            if palaces else
            "No natal placement; timing hits are treated as activation rather than birth-chart promise."
        ),
    }


def _timing_interpretation(activations: List[Dict[str, Any]]) -> Dict[str, Any]:
    timing_rows = [row for row in activations if row.get("layer") != "natal"]
    flow_rows = [row for row in timing_rows if str(row.get("layer") or "").startswith("flowing_")]
    layers = sorted({str(row.get("layer") or "") for row in timing_rows if row.get("layer")})
    return {
        "status": "flowing_active" if flow_rows else ("timing_active" if timing_rows else "quiet"),
        "layers": layers,
        "flowing_count": len(flow_rows),
        "summary": (
            f"Timing activates this marker through {', '.join(layers)}."
            if layers else
            "No current timing layer activates this marker."
        ),
    }


def _target_payload(target: Dict[str, str]) -> Dict[str, Any]:
    value = str(target.get("value") or "")
    target_type = str(target.get("type") or "")
    payload = {"type": target_type, "value": value, "label": _target_label(target)}
    if target_type == "branch":
        payload["animal"] = _branch_animal(value)
    return payload


def _target_label(target: Dict[str, str]) -> str:
    target_type = str(target.get("type") or "")
    value = str(target.get("value") or "")
    if target_type == "branch":
        animal = _branch_animal(value)
        return f"{value} {animal}" if animal else value
    return value


def _reference_label(reference_type: str) -> str:
    return {
        "day_branch": "Day Branch",
        "year_branch": "Year Branch",
        "day_stem": "Day Stem",
        "month_branch": "Month Branch",
        "day_pillar": "Day Pillar",
        "visible_stems": "Visible Stems",
    }.get(str(reference_type or ""), str(reference_type or "").replace("_", " ").title())


def _matching_placements(
    pillars: Dict[str, Optional[Dict[str, Any]]],
    branch: str,
    layer: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for pillar_name in ("year", "month", "day", "hour"):
        pillar = pillars.get(pillar_name) if isinstance(pillars, dict) else None
        if isinstance(pillar, dict) and pillar.get("branch") == branch:
            rows.append(_placement_payload(pillar, pillar_name, layer))
    return rows


def _timing_placements(timing: Dict[str, Any], branch: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key, layer in (
        ("active_luck_pillar", "luck"),
        ("annual_pillar", "annual"),
        ("flowing_month_pillar", "flowing_month"),
        ("flowing_day_pillar", "flowing_day"),
        ("flowing_hour_pillar", "flowing_hour"),
    ):
        pillar = timing.get(key)
        if isinstance(pillar, dict) and pillar.get("branch") == branch:
            rows.append(_placement_payload(pillar, layer, layer))
    return rows


def _placement_payload(pillar: Dict[str, Any], pillar_name: str, layer: str) -> Dict[str, Any]:
    branch = pillar.get("branch")
    return {
        "layer": layer,
        "pillar": pillar_name,
        "pillar_label": _pillar_label(pillar_name),
        "branch": branch,
        "animal": pillar.get("animal") or _branch_animal(branch),
        "stem": pillar.get("stem"),
        "element": pillar.get("branch_element"),
        "ten_god": pillar.get("ten_god"),
        "five_factor": pillar.get("five_factor"),
        "domain": PILLAR_DOMAIN_LABELS.get(pillar_name, _timing_domain(layer)),
    }


def _branch_pressure(branch: str, relationships: Dict[str, Any]) -> Dict[str, Any]:
    impacts: List[Dict[str, Any]] = []
    for event in relationships.get("events") or []:
        if not isinstance(event, dict):
            continue
        symbols = {str(symbol) for symbol in event.get("symbols") or []}
        point_branches = {
            str(point.get("branch"))
            for point in event.get("points") or []
            if isinstance(point, dict) and point.get("branch")
        }
        if branch not in symbols and branch not in point_branches:
            continue
        tone = _event_tone(event.get("type"))
        impacts.append({
            "label": event.get("label") or event.get("type") or "relationship code",
            "type": event.get("type"),
            "scope": event.get("scope"),
            "scope_label": event.get("scope_label"),
            "tone": tone,
            "intensity": event.get("intensity"),
            "affected_palaces": event.get("affected_palaces") if isinstance(event.get("affected_palaces"), list) else [],
        })
    tones = {impact["tone"] for impact in impacts}
    if "challenging" in tones and "supportive" in tones:
        status = "mixed"
    elif "challenging" in tones:
        status = "pressured"
    elif "supportive" in tones:
        status = "supported"
    else:
        status = "clear"
    return {"status": status, "event_impacts": impacts}


def _peach_blossom_branch_presence(
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Dict[str, Any],
) -> Dict[str, Any]:
    placements: List[Dict[str, Any]] = []
    for branch in PEACH_BLOSSOM_BRANCHES:
        placements.extend(_matching_placements(pillars, branch, "natal"))
        placements.extend(_timing_placements(timing, branch))
    present_set = {str(row.get("branch")) for row in placements if row.get("branch")}
    present = [branch for branch in PEACH_BLOSSOM_BRANCHES if branch in present_set]
    return {
        "branches": list(PEACH_BLOSSOM_BRANCHES),
        "present": present,
        "present_count": len(present),
        "placement_count": len(placements),
        "all_four_present": set(PEACH_BLOSSOM_BRANCHES).issubset(set(present)),
        "placements": placements[:8],
    }


def _event_tone(event_type: Any) -> str:
    key = str(event_type or "")
    if key in {"branch_clash", "branch_harm", "branch_destruction", "branch_punishment", "self_punishment"}:
        return "challenging"
    if key in {"stem_combination", "branch_combination", "three_harmony_combination", "seasonal_combination", "branch_cross"}:
        return "supportive"
    return "mixed"


def _branch_animal(branch: Any) -> Optional[str]:
    key = str(branch or "")
    index = BRANCH_INDEX.get(key)
    return BRANCHES[index]["animal"] if index is not None else None


def _pillar_label(pillar: str) -> str:
    return {
        "year": "Year",
        "month": "Month",
        "day": "Day",
        "hour": "Hour",
        "luck": "Current Luck",
        "annual": "Current Year",
        "flowing_month": "Flowing Month",
        "flowing_day": "Flowing Day",
        "flowing_hour": "Flowing Hour",
    }.get(str(pillar or ""), str(pillar or "").title())


def _timing_domain(layer: str) -> str:
    if layer == "luck":
        return "Current 10-year luck pillar"
    if layer == "annual":
        return "Current BaZi year"
    if layer == "flowing_month":
        return "Current flowing month"
    if layer == "flowing_day":
        return "Current flowing day"
    if layer == "flowing_hour":
        return "Current flowing hour"
    return ""
