from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "backend" / "knowledge" / "astrocartography" / "place_goal_models.source.json"
OUTPUT_PATH = ROOT / "backend" / "knowledge" / "astrocartography" / "place_goal_models.runtime.json"
FRONTEND_OUTPUT_PATH = ROOT / "frontend" / "backend" / "knowledge" / "astrocartography" / "place_goal_models.runtime.json"
OUTPUT_PATHS = (OUTPUT_PATH, FRONTEND_OUTPUT_PATH)
REQUIRED_MODEL_IDS = {
    "education",
    "love",
    "work",
    "money",
    "home",
    "partners",
    "beliefs",
    "friends",
    "career",
    "sex",
    "personal_growth",
    "communication",
    "conflict",
    "love_commitment",
    "money_stable_income",
    "career_public_profile",
    "home_retreat",
    "gambling_luck",
    "health_risk",
    "body_presence",
    "risk_pressure",
    "protective_places",
    "accident_prone",
    "travel_fun",
    "travel_relax",
}
SCHEMA_VERSION = 2
EXPERIMENTAL_MODEL_IDS = {
    "accident_prone",
    "gambling_luck",
    "health_risk",
    "travel_fun",
    "travel_relax",
}
HIGHER_IS_WORSE_MODEL_IDS = {
    "accident_prone",
    "conflict",
    "health_risk",
    "risk_pressure",
}
SPECIALIST_COMPOSITION = {
    "love_commitment": ("love", 5.0),
    "money_stable_income": ("money", 5.0),
    "career_public_profile": ("career", 5.0),
    "home_retreat": ("home", 5.0),
    "gambling_luck": ("money", 4.0),
    "health_risk": ("risk_pressure", 5.0),
    "accident_prone": ("risk_pressure", 5.0),
    "travel_fun": ("friends", 4.0),
    "travel_relax": ("home", 4.0),
}
CANONICAL_ACG_BODIES = {
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
}
DEFAULT_EVIDENCE_POLICY = {
    "min_independent_signals": 1,
    "weak_magnitude": 2.5,
    "strong_magnitude": 8.0,
    "min_birth_time_confidence": 0.5,
    "block_caps": {
        "natal_lines": 12.0,
        "crossing_interactions": 6.0,
        "relocation": 8.0,
        "transit_overlay": 4.0,
    },
}
SPECIALIST_PARENT_WEIGHT = 0.95


def _distance(max_km: float = 300.0, falloff: str = "linear") -> Dict[str, Any]:
    return {"max_km": max_km, "falloff": falloff}


def line_component(
    planet: str,
    angles: List[str],
    weight: float,
    rationale: str,
    *,
    max_km: float = 300.0,
    falloff: str = "linear",
    polarity: str = "support",
    source_status: str = "synthesis",
    evidence_role: str = "local",
) -> Dict[str, Any]:
    return {
        "kind": "line",
        "planet": planet,
        "angles": angles,
        "distance": _distance(max_km=max_km, falloff=falloff),
        "weight": weight,
        "polarity": polarity,
        "source_status": source_status,
        "evidence_role": evidence_role,
        "rationale": rationale,
    }


def crossing_component(
    pair: List[str],
    weight: float,
    rationale: str,
    *,
    max_km: float = 300.0,
    falloff: str = "linear",
    polarity: str = "support",
    source_status: str = "synthesis",
    evidence_role: str = "local",
    interaction_scale: float = 0.5,
) -> Dict[str, Any]:
    return {
        "kind": "crossing",
        "pair": pair,
        "distance": _distance(max_km=max_km, falloff=falloff),
        "weight": weight,
        "interaction_scale": interaction_scale,
        "polarity": polarity,
        "source_status": source_status,
        "evidence_role": evidence_role,
        "rationale": rationale,
    }


def relocation_component(
    planets: List[str],
    houses: List[int],
    weight: float,
    rationale: str,
    *,
    angles: List[str] | None = None,
    source_status: str = "synthesis",
    evidence_role: str = "local",
) -> Dict[str, Any]:
    return {
        "kind": "relocation",
        "planets": planets,
        "houses": houses,
        "angles": list(angles or []),
        "weight": weight,
        "source_status": source_status,
        "evidence_role": evidence_role,
        "rationale": rationale,
    }


def modifier_component(
    metric: str,
    weight: float,
    rationale: str,
    *,
    source_status: str = "synthesis",
    evidence_role: str = "local",
) -> Dict[str, Any]:
    return {
        "kind": "modifier",
        "metric": metric,
        "weight": weight,
        "source_status": source_status,
        "evidence_role": evidence_role,
        "rationale": rationale,
    }


def constraint_component(
    metric: str,
    operator: str,
    threshold: float,
    rationale: str,
    *,
    multiplier: float | None = None,
    add: float | None = None,
    cap_score: float | None = None,
    polarity: str = "neutral",
    source_status: str = "synthesis",
) -> Dict[str, Any]:
    component: Dict[str, Any] = {
        "kind": "constraint",
        "metric": metric,
        "operator": operator,
        "threshold": threshold,
        "polarity": polarity,
        "source_status": source_status,
        "evidence_role": "local",
        "rationale": rationale,
    }
    if multiplier is not None:
        component["multiplier"] = multiplier
    if add is not None:
        component["add"] = add
    if cap_score is not None:
        component["cap_score"] = cap_score
    return component


def source_ref(source_app: str, source_file: str, kind: str, **kwargs: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "source_app": source_app,
        "source_file": source_file,
        "kind": kind,
    }
    payload.update(kwargs)
    return payload


def legacy_ref(source_file: str, kind: str, **kwargs: Any) -> Dict[str, Any]:
    return source_ref("Almagest PathFinder", source_file, kind, **kwargs)


def doc_ref(source_file: str, **kwargs: Any) -> Dict[str, Any]:
    return source_ref("Vox Stella corpus", source_file, "doc", **kwargs)


def _merge_legacy_refs(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("source_app") or "").strip(),
                str(item.get("source_file") or "").strip(),
                str(item.get("kind") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _load_source_payload() -> Dict[str, Any]:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Astrocartography goal model authoring source is missing: {SOURCE_PATH}")
    payload = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Astrocartography goal model authoring source must be a JSON object")
    models = payload.get("models") or []
    if not isinstance(models, list):
        raise ValueError("Astrocartography goal model authoring source must contain a models list")
    return payload


def _new_models() -> List[Dict[str, Any]]:
    return [
        {
            "id": "beliefs",
            "label": "Beliefs",
            "version": "1.2.0",
            "status": "active",
            "summary": "Ranks places for philosophy, pilgrimage, contemplative study, meaning, and spiritual orientation without losing coherence.",
            "description": "Reworked directly from the corpus reference layer: Jupiter for meaning and teaching, Mercury for study and doctrine, Sun for purposeful conviction, and Neptune as a limited spiritual amplifier with explicit caution control. Anchored to the recovered BELIEFS.HYP family.",
            "goal_family": "beliefs",
            "legacy_refs": [
                legacy_ref("BELIEFS.HYP", "hyp", notes=["Recovered as a second-wave PathFinder belief and worldview rule family."]),
            ],
            "score_components": [
                line_component("Jupiter", ["ASC", "MC"], 5.8, "Jupiter is the clearest meaning, philosophy, and teaching signal in the corpus."),
                line_component("Mercury", ["ASC", "MC"], 2.4, "Mercury keeps belief work connected to study, language, and coherent doctrine without making it purely academic."),
                line_component("Sun", ["ASC"], 2.2, "Sun supports conviction, purpose, and lived integrity."),
                line_component("Neptune", ["IC"], 1.8, "Neptune on the inner angle can deepen contemplative or imaginal life when the rest of the chart remains grounded."),
                line_component("Moon", ["IC"], 1.8, "Moon IC supports devotional belonging, ritual comfort, and reflective inner safety."),
                line_component("Saturn", ["MC"], -2.4, "Too much Saturn on the public axis can harden belief into heaviness, duty, or dogma.", polarity="caution"),
                line_component("Neptune", ["MC"], -1.6, "Neptune on the MC can blur guidance roles and public doctrinal clarity.", polarity="caution"),
                crossing_component(["Jupiter", "Sun"], 3.2, "Jupiter/Sun supports meaning with confidence and coherence."),
                crossing_component(["Jupiter", "Mercury"], 2.4, "Jupiter/Mercury is strong for philosophy, study, publishing, and teaching, but should not collapse into the education model."),
                crossing_component(["Jupiter", "Neptune"], 2.2, "Jupiter/Neptune can open spiritual imagination when it is not drifting."),
                crossing_component(["Mercury", "Neptune"], -2.6, "Mercury/Neptune can blur language, teaching, or doctrinal precision.", polarity="caution"),
                relocation_component(["Jupiter", "Mercury", "Sun", "Neptune", "Moon"], [9, 12], 4.4, "Relocated charts support beliefs most clearly when meaning and contemplative houses carry the relevant planets."),
                modifier_component("beliefs", 3.4, "A strong beliefs metric is the most direct relocation support layer for this goal."),
                modifier_component("mobility", 0.8, "Belief-oriented places benefit from openness and pilgrimage, but not as much as education benefits from pure mobility."),
                modifier_component("uncertainty", -2.8, "Too much uncertainty turns spiritual openness into drift."),
                constraint_component("beliefs", "gte", 0.4, "Strong meaning-and-beliefs metrics deserve a modest uplift.", multiplier=1.14, polarity="support"),
                constraint_component("uncertainty", "gte", 0.45, "Very unstable charts should be penalized so drift does not rank as spiritual depth.", add=-3.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 26},
        },
        {
            "id": "sex",
            "label": "Sex",
            "version": "1.1.0",
            "status": "active",
            "summary": "Ranks places for erotic chemistry, embodied magnetism, attraction, and intensity while downgrading chaotic or cold signatures.",
            "description": "Reworked directly from the corpus reference layer: Venus for attraction and sensual ease, Mars for heat and pursuit, Pluto for intensity, Moon for receptivity, and Saturn as cooling/inhibiting caution. Anchored to the recovered SEX.HYP family.",
            "goal_family": "sex",
            "legacy_refs": [
                legacy_ref("SEX.HYP", "hyp", notes=["Recovered as a hidden erotic and chemistry rule family in the PathFinder set."]),
            ],
            "score_components": [
                line_component("Venus", ["ASC", "DSC"], 5.4, "Venus is the clearest attraction, receptivity, and sensual ease signature."),
                line_component("Mars", ["ASC", "DSC"], 4.8, "Mars drives heat, pursuit, courage, and embodied charge."),
                line_component("Pluto", ["ASC", "DSC", "IC"], 3.3, "Pluto intensifies magnetism, depth, fixation, and erotic pressure."),
                line_component("Moon", ["DSC"], 1.6, "Moon on the partnership axis can add responsiveness and receptivity."),
                line_component("Saturn", ["DSC"], -2.7, "Saturn can cool, inhibit, or formalize chemistry too heavily.", polarity="caution"),
                line_component("Mars", ["MC"], -1.2, "Mars MC can externalize heat into conflict and performative pressure instead of embodied intimacy.", polarity="caution"),
                crossing_component(["Venus", "Mars"], 4.8, "Venus/Mars is the clearest chemistry crossing in the corpus."),
                crossing_component(["Venus", "Pluto"], 3.6, "Venus/Pluto raises intensity, obsession, and deep attraction."),
                crossing_component(["Mars", "Pluto"], 2.4, "Mars/Pluto increases force and erotic pressure, but can become harsh if overdone."),
                crossing_component(["Venus", "Moon"], 2.0, "Venus/Moon adds tenderness and receptive warmth."),
                crossing_component(["Venus", "Saturn"], -2.4, "Venus/Saturn can reduce spontaneity, warmth, and responsiveness.", polarity="caution"),
                crossing_component(["Mars", "Saturn"], -2.0, "Mars/Saturn can make the environment harsh, blocked, or frustrating.", polarity="caution"),
                relocation_component(["Venus", "Mars", "Pluto", "Moon"], [1, 5, 7, 8], 4.4, "Relocation favors chemistry when attraction planets cluster in identity, romance, and intimacy houses."),
                modifier_component("chemistry", 3.4, "Chemistry is the direct relocation metric for this family."),
                modifier_component("partnership", 0.9, "Some partnership capacity helps chemistry become interactive rather than purely solo projection."),
                modifier_component("uncertainty", -1.8, "Too much drift weakens consistency and embodied follow-through."),
                modifier_component("malefic_pressure", -1.4, "Excess pressure can turn intensity into abrasion rather than magnetism."),
                constraint_component("chemistry", "gte", 0.35, "Strong chemistry metrics deserve a modest uplift.", multiplier=1.12, polarity="support"),
                constraint_component("uncertainty", "gte", 0.45, "High instability should downgrade places that confuse intensity with actual erotic quality.", add=-2.8, polarity="caution"),
                constraint_component("malefic_pressure", "gte", 0.55, "Too much harsh pressure should cap otherwise hot-looking results.", cap_score=12.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 28},
        },
        {
            "id": "personal_growth",
            "label": "Personal Growth",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for reinvention, confidence, breakthrough change, and future-facing development.",
            "description": "Built from the corpus emphasis on Sun, Jupiter, Uranus, Pluto, and the Node for identity, growth, reinvention, and development, then aligned with the recovered PERSONAL.HYP legacy family.",
            "goal_family": "personal",
            "legacy_refs": [
                legacy_ref("PERSONAL.HYP", "hyp", notes=["Likely legacy rule family for self-development and identity-oriented relocation choices."]),
            ],
            "score_components": [
                line_component("Sun", ["ASC", "MC"], 6.0, "Sun lines foreground identity, confidence, purpose, and visible self-direction."),
                line_component("Jupiter", ["ASC", "MC"], 4.8, "Jupiter lines support growth, meaning, opportunity, and broader horizons."),
                line_component("Uranus", ["ASC", "MC"], 4.2, "Uranus lines are strong for reinvention, liberation, and breakthrough change."),
                line_component("Pluto", ["ASC", "MC"], 3.8, "Pluto lines intensify transformation, pressure, and deep rebuilding."),
                line_component("North Node", ["ASC", "MC"], 4.0, "Node lines pull toward development, future-facing contacts, and meaningful change."),
                line_component("Neptune", ["ASC", "MC"], -2.8, "Neptune can blur direction when the goal is clean personal traction.", polarity="caution"),
                crossing_component(["Sun", "Jupiter"], 3.8, "Sun/Jupiter blends identity with growth and recognition."),
                crossing_component(["Sun", "Uranus"], 3.0, "Sun/Uranus can catalyze a clean break into a new life chapter."),
                crossing_component(["Jupiter", "Pluto"], 2.5, "Jupiter/Pluto supports strategic expansion and deeper ambition."),
                relocation_component(["Sun", "Jupiter", "Uranus", "Pluto", "North Node"], [1, 8, 9, 10, 11], 4.2, "Relocated charts improve when growth planets concentrate in self-defining and future-facing houses."),
                modifier_component("personal_growth", 3.3, "Strong identity-development metrics make a place more useful for self-reinvention."),
                modifier_component("visibility", 1.2, "Some visibility helps growth become tangible rather than purely internal."),
                modifier_component("uncertainty", -1.8, "Too much uncertainty can make growth feel ungrounded rather than constructive."),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -10, "max_score": 24},
        },
        {
            "id": "body_presence",
            "label": "Body Presence",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for embodied confidence, physical presence, first impressions, and appearance-led charisma rather than deeper reinvention alone.",
            "description": "Built as a specialist personal model after reviewing the external PERSONALITY_THE BODY_APPEARANCE.HYP pack. It leans on 1st-house and ASC/body symbolism from the Morin map, then scores Sun, Venus, Moon, Mars, and Jupiter as appearance and presence amplifiers while Saturn and Neptune act as drag on vitality and clean projection.",
            "goal_family": "personal",
            "legacy_refs": [
                legacy_ref("PERSONALITY_THE BODY_APPEARANCE.HYP", "hyp", notes=["External legacy body-and-appearance rule family reviewed on 2026-04-05."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md", notes=["Sun presence, Venus attraction, Moon receptivity, Mars vitality, and Jupiter confidence all come from the core planetary reference layer."]),
                doc_ref("backend/morin_engine_knowledge_map.md", notes=["Morin explicitly maps the 1st house to self, body, vitality, appearance, constitution, and personality."]),
            ],
            "score_components": [
                line_component("Venus", ["ASC"], 6.0, "Venus ASC is the clearest ease, attractiveness, charm, and likeability signature for appearance-led presence."),
                line_component("Sun", ["ASC", "MC"], 5.2, "Sun supports vitality, confidence, visible identity, and unmistakable personal presence."),
                line_component("Moon", ["ASC"], 3.2, "Moon ASC adds softness, receptivity, and a felt human presence."),
                line_component("Mars", ["ASC"], 3.4, "Mars ASC adds athletic force, edge, and embodied confidence when not too abrasive."),
                line_component("Jupiter", ["ASC", "MC"], 3.6, "Jupiter adds generous presence, ease, and social confidence."),
                line_component("Saturn", ["ASC"], -3.2, "Saturn ASC can harden the body axis into reserve, heaviness, or self-consciousness.", polarity="caution"),
                line_component("Neptune", ["ASC"], -2.6, "Neptune ASC can blur the physical signal or weaken crisp embodied projection.", polarity="caution"),
                crossing_component(["Venus", "Sun"], 4.0, "Venus/Sun blends attractiveness with radiant confidence."),
                crossing_component(["Venus", "Moon"], 2.6, "Venus/Moon supports softness, approachability, and lived charm."),
                crossing_component(["Sun", "Mars"], 2.2, "Sun/Mars supports visible vitality and assertive physical presence."),
                crossing_component(["Venus", "Saturn"], -2.4, "Venus/Saturn can cool warmth and make beauty or charm feel constrained.", polarity="caution"),
                relocation_component(["Sun", "Venus", "Moon", "Mars", "Jupiter"], [1, 2, 5, 10], 4.4, "Relocated charts support body presence when benefics and vitality planets concentrate in bodily, expressive, and visible houses."),
                modifier_component("body_presence", 3.6, "Body presence is the direct relocation metric for this specialist personal model."),
                modifier_component("visibility", 1.8, "Some public visibility helps embodied presence register outwardly."),
                modifier_component("benefic_balance", 1.4, "A benefic-leaning chart supports ease, charm, and confidence."),
                modifier_component("uncertainty", -1.8, "Too much uncertainty weakens clean personal projection."),
                modifier_component("malefic_pressure", -1.4, "Heavy pressure can make the body signal harsher than magnetic."),
                constraint_component("body_presence", "gte", 0.35, "Strong embodied-presence signatures deserve a modest uplift.", multiplier=1.12, polarity="support"),
                constraint_component("uncertainty", "gte", 0.45, "High instability should downgrade appearance-led confidence and projection.", add=-2.4, polarity="caution"),
                constraint_component("body_presence", "lt", 0.15, "Places with almost no body-presence signal should not rank as strong appearance environments.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -10, "max_score": 28},
        },
        {
            "id": "communication",
            "label": "Communication",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for writing, teaching, messaging, networking, sales, and intellectually social work.",
            "description": "Built from the corpus' Mercury-forward communication themes and aligned with the recovered CHATTER.HYP legacy family.",
            "goal_family": "communication",
            "legacy_refs": [
                legacy_ref("CHATTER.HYP", "hyp", notes=["Likely legacy rule family for conversation, messaging, and exchange-heavy environments."]),
                legacy_ref("COMMUNICATION_BROTHER_SISTER.HYP", "hyp", notes=["External communication sibling/3rd-house variant reviewed on 2026-04-05."]),
            ],
            "score_components": [
                line_component("Mercury", ["ASC", "MC", "DSC"], 6.5, "Mercury is the clearest language, trade, writing, and exchange signature in the corpus."),
                line_component("Jupiter", ["ASC", "MC"], 3.4, "Jupiter broadens reach, teaching, publication, and meaningful exchange."),
                line_component("Venus", ["ASC", "DSC"], 2.8, "Venus smooths diplomacy, social ease, and pleasing communication."),
                line_component("Moon", ["IC", "DSC"], 2.0, "Moon adds emotional receptivity and audience feel."),
                line_component("Uranus", ["ASC", "MC"], 2.4, "Uranus sharpens originality and modern messaging."),
                line_component("Neptune", ["ASC", "MC"], -3.0, "Neptune can weaken precision and clean signal flow.", polarity="caution"),
                crossing_component(["Mercury", "Jupiter"], 4.0, "Mercury/Jupiter is strong for teaching, publishing, and big-idea communication."),
                crossing_component(["Mercury", "Venus"], 3.0, "Mercury/Venus helps language sound attractive, persuasive, and relational."),
                crossing_component(["Mercury", "Uranus"], 2.7, "Mercury/Uranus supports inventive, fast, and modern communication."),
                crossing_component(["Mercury", "Neptune"], -3.0, "Mercury/Neptune can create glamour and ambiguity instead of clarity.", polarity="caution"),
                relocation_component(["Mercury", "Venus", "Jupiter", "Moon"], [3, 7, 9, 11], 4.0, "Relocated charts are stronger when communication planets land in exchange, outreach, and audience houses."),
                modifier_component("communication", 3.2, "Communication-heavy relocated charts are the clearest support for this goal."),
                modifier_component("community", 2.0, "Community support helps messaging find listeners and collaborators."),
                modifier_component("uncertainty", -2.5, "Unclear or unstable chart signatures reduce reliability in communication work."),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -10, "max_score": 24},
        },
        {
            "id": "conflict",
            "label": "Conflict",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places where rivalry, confrontation, pressure, and hard-edge testing are most likely to surface.",
            "description": "Built from Mars/Saturn/Pluto/Uranus pressure signatures in the corpus and aligned with the recovered ENEMIES.HYP legacy family.",
            "goal_family": "conflict",
            "legacy_refs": [
                legacy_ref("ENEMIES.HYP", "hyp", notes=["Likely legacy caution/rivalry family for pressure, contention, and exposed antagonism."]),
            ],
            "score_components": [
                line_component("Mars", ["DSC", "MC"], 5.4, "Mars lines intensify open contest, exposed rivalry, and direct conflict."),
                line_component("Saturn", ["DSC"], 4.0, "Saturn on the partnership axis adds obstruction, hostility, and adversarial pressure."),
                line_component("Pluto", ["DSC", "MC"], 4.6, "Pluto amplifies power struggles, control issues, and deep confrontations."),
                line_component("Uranus", ["ASC", "DSC"], 3.0, "Uranus raises volatility, rupture, and sudden escalation when conflict is personal or relational."),
                line_component("Venus", ["DSC", "IC"], -2.0, "Venus can soften conflict and lower the intensity score.", polarity="caution"),
                crossing_component(["Mars", "Saturn"], 4.5, "Mars/Saturn crossings are classic friction, force, and obstruction signatures."),
                crossing_component(["Mars", "Pluto"], 5.0, "Mars/Pluto intensifies conflict into power struggle and compulsion."),
                crossing_component(["Mars", "Uranus"], 4.0, "Mars/Uranus can create abrupt conflict and unstable reactions."),
                crossing_component(["Venus", "Moon"], -2.8, "Venus/Moon can soften the environment and lower conflict exposure.", polarity="caution"),
                relocation_component(["Mars", "Saturn", "Pluto", "Uranus"], [1, 7, 8, 12], 4.4, "Relocated charts grow harsher when pressure planets dominate exposed conflict, confrontation, and shadow houses."),
                modifier_component("conflict_pressure", 3.5, "High conflict-pressure metrics indicate environments that test boundaries hard."),
                modifier_component("malefic_pressure", 2.6, "Malefic pressure amplifies the likelihood of confrontational dynamics."),
                modifier_component("uncertainty", 1.4, "Instability can make conflicts more sudden and less manageable."),
                constraint_component("conflict_pressure", "gte", 0.35, "Higher conflict-pressure should amplify the overall warning value of the result.", multiplier=1.15, polarity="support"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -8, "max_score": 26},
        },
        {
            "id": "accident_prone",
            "label": "Prone to Accidents",
            "version": "1.0.0",
            "status": "active",
            "summary": "Warning-oriented natal-only model for places with acute accident, collision, and crash pressure. Higher scores mean more accident-prone places.",
            "description": "Built from the subtype accident-pressure research pass rather than the generic risk lens. It emphasizes Mars, Uranus, Pluto, Saturn, and Chiron around angular lines and accident-pattern crossings, then blends in bodily-risk relocation metrics. Transit overlay is intentionally ignored because the accident benchmark got worse when transit was added.",
            "goal_family": "risk",
            "score_polarity": "higher_is_worse",
            "evaluation_strategy": "accident_pressure",
            "transit_strategy": "ignore",
            "legacy_refs": [
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md", notes=["Mars, Saturn, Uranus, Pluto, and Chiron angular risk meanings come from the core planetary reference layer."]),
                doc_ref("backend/morin_engine_knowledge_map.md", notes=["Morin-style body, crisis, and harm-house logic supports treating acute accident pressure as a narrower warning family than generic conflict or health risk."]),
                doc_ref("backend/benchmarks/astrocartography/baselines.py", notes=["This public accident warning model uses the shared accident-pressure heuristic directly so product and benchmark stay aligned."]),
                doc_ref("docs/ASTROCARTOGRAPHY_MODEL_VALIDATION_PLAN_2026-04-05.md", notes=["Subtype-matched benchmark work showed accident pressure was the only risk subtype worth further iteration, and that transit overlay hurt rather than helped."]),
            ],
            "score_components": [
                line_component("Mars", ["ASC", "DSC", "MC", "IC"], 5.2, "Mars angular pressure raises cuts, collisions, haste, and impact-prone conditions."),
                line_component("Uranus", ["ASC", "DSC", "MC", "IC"], 4.8, "Uranus angular pressure raises sudden disruption, shocks, and abrupt incident signatures."),
                line_component("Pluto", ["ASC", "DSC", "MC", "IC"], 4.4, "Pluto angular pressure raises crisis intensity and force-heavy accident environments."),
                line_component("Saturn", ["ASC", "DSC", "MC", "IC"], 3.2, "Saturn adds hard-contact, structural-friction, and bone-impact strain."),
                line_component("Chiron", ["ASC", "DSC", "MC", "IC"], 2.6, "Chiron raises exposed vulnerability and wound sensitivity."),
                line_component("Jupiter", ["ASC", "DSC", "MC", "IC"], -3.0, "Jupiter lowers acute accident pressure through protection and practical room to move.", polarity="caution"),
                line_component("Venus", ["ASC", "DSC", "MC", "IC"], -2.6, "Venus lowers acute accident pressure by softening the field and reducing abrasion.", polarity="caution"),
                line_component("Sun", ["ASC", "DSC", "MC", "IC"], -1.8, "Sun lowers acute accident pressure when vitality and coherence are strengthened.", polarity="caution"),
                line_component("Moon", ["ASC", "DSC", "MC", "IC"], -1.6, "Moon lowers acute accident pressure when the place supports responsiveness and bodily steadiness.", polarity="caution"),
                crossing_component(["Mars", "Uranus"], 4.8, "Mars/Uranus is the clearest acute accident crossing for shocks and sudden collisions."),
                crossing_component(["Mars", "Pluto"], 4.2, "Mars/Pluto intensifies force, crushing pressure, and high-severity impact conditions."),
                crossing_component(["Mars", "Saturn"], 4.0, "Mars/Saturn raises harsh friction, breaks, and hard-contact injuries."),
                crossing_component(["Uranus", "Pluto"], 3.8, "Uranus/Pluto raises violent rupture, crisis, and destabilizing impact conditions."),
                crossing_component(["Jupiter", "Venus"], -2.4, "Jupiter/Venus lowers acute accident pressure by softening the overall field.", polarity="caution"),
                modifier_component("health_risk", 3.0, "Strong bodily-risk relocation signatures raise accident pressure."),
                modifier_component("malefic_pressure", 2.0, "General malefic relocation pressure raises accident exposure."),
                modifier_component("uncertainty", 1.6, "Instability and volatility make places more accident-prone."),
                modifier_component("conflict_pressure", 0.9, "Conflict-heavy environments raise bodily-friction exposure."),
                modifier_component("benefic_balance", -2.0, "Strong benefic balance lowers accident pressure."),
                modifier_component("stability", -1.4, "Stable environments should not rank like collision hotspots."),
                constraint_component("health_risk", "gte", 0.35, "Clear bodily-risk relocation signatures deserve a stronger accident warning lift.", add=2.0, polarity="support"),
                constraint_component("malefic_pressure", "gte", 0.55, "Very strong malefic pressure should cap the ranking toward clear accident hotspots.", add=2.2, polarity="support"),
                constraint_component("benefic_balance", "gte", 0.45, "Strong benefic protection should cap otherwise harsh-looking accident zones.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 30},
        },
        {
            "id": "protective_places",
            "label": "Protective Places",
            "version": "1.0.0",
            "status": "active",
            "summary": "Public natal-only model for easier, more protected, and more supportive places. Higher scores mean stronger protection and livability.",
            "description": "Built as a broad public safety-and-support lens from the shared benefic-versus-malefic place heuristic. It rewards benefic protection, downgrades harsh angular pressure, and currently ignores transit overlay because the exploratory generic-risk benchmark got worse once transient activation was added.",
            "goal_family": "protection",
            "evaluation_strategy": "benefic_minus_malefic",
            "transit_strategy": "ignore",
            "legacy_refs": [
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md", notes=["Benefic and malefic angular pressure meanings come from the core planetary reference layer."]),
                doc_ref("backend/benchmarks/astrocartography/baselines.py", notes=["This public protective model uses the shared benefic-minus-malefic balance heuristic directly so higher score means more support and protection."]),
                doc_ref("backend/morin_engine_knowledge_map.md", notes=["Morin-style bodily strain, conflict, and instability logic supports exposing the benefic side of the same broad place field as a public protective lens."]),
            ],
            "score_components": [
                line_component("Jupiter", ["ASC", "DSC", "MC", "IC"], 3.4, "Jupiter raises protection, ease, and constructive room to move."),
                line_component("Venus", ["ASC", "DSC", "MC", "IC"], 3.0, "Venus raises softness, livability, and relational ease."),
                line_component("Sun", ["ASC", "DSC", "MC", "IC"], 2.0, "Sun raises vitality, coherence, and practical confidence."),
                line_component("Moon", ["ASC", "DSC", "MC", "IC"], 1.8, "Moon raises receptivity, comfort, and emotional steadiness."),
                line_component("Mars", ["ASC", "DSC", "MC", "IC"], -4.8, "Mars lowers the protection score through haste, conflict, and abrasive conditions.", polarity="caution"),
                line_component("Saturn", ["ASC", "DSC", "MC", "IC"], -4.4, "Saturn lowers the protection score through depletion, obstruction, and harsh conditions.", polarity="caution"),
                line_component("Uranus", ["ASC", "DSC", "MC", "IC"], -3.8, "Uranus lowers the protection score through instability and sudden disruption.", polarity="caution"),
                line_component("Pluto", ["ASC", "DSC", "MC", "IC"], -3.6, "Pluto lowers the protection score through crisis intensity and compulsion.", polarity="caution"),
                line_component("Neptune", ["ASC", "DSC", "MC", "IC"], -2.6, "Neptune lowers the protection score through confusion and weakened practical footing.", polarity="caution"),
                line_component("Chiron", ["ASC", "DSC", "MC", "IC"], -2.2, "Chiron lowers the protection score through exposed vulnerability and wound-sensitivity.", polarity="caution"),
                crossing_component(["Jupiter", "Venus"], 3.2, "Jupiter/Venus is the clearest broad protective crossing in the shared place field."),
                crossing_component(["Sun", "Moon"], 1.8, "Sun/Moon supports basic coherence and livability."),
                crossing_component(["Mars", "Saturn"], -4.2, "Mars/Saturn lowers protection through hard-pressure and harsh-friction conditions.", polarity="caution"),
                crossing_component(["Mars", "Uranus"], -3.8, "Mars/Uranus lowers protection through sudden disruption and accident-prone volatility.", polarity="caution"),
                crossing_component(["Mars", "Pluto"], -3.4, "Mars/Pluto lowers protection through force, crisis, and extreme pressure.", polarity="caution"),
                crossing_component(["Saturn", "Neptune"], -2.8, "Saturn/Neptune lowers protection through draining or structurally weakening conditions.", polarity="caution"),
                modifier_component("benefic_balance", 2.8, "Strong benefic protection should raise the protection score."),
                modifier_component("stability", 1.8, "Stable places should feel more protective and easier to live in."),
                modifier_component("malefic_pressure", -3.2, "General malefic pressure should reduce the protection score.",),
                modifier_component("conflict_pressure", -1.8, "Conflict-heavy relocated charts tend to feel less forgiving.",),
                modifier_component("uncertainty", -1.8, "Instability should reduce the sense of protection and ease.",),
                constraint_component("benefic_balance", "gte", 0.45, "Strong benefic protection deserves a modest uplift.", add=2.0, polarity="support"),
                constraint_component("stability", "gte", 0.5, "Highly stable places deserve a modest uplift.", add=1.8, polarity="support"),
                constraint_component("malefic_pressure", "gte", 0.55, "Heavy malefic pressure should cap otherwise protective-looking places.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -14, "max_score": 30},
        },
        {
            "id": "risk_pressure",
            "label": "High-Risk Places",
            "version": "1.3.0",
            "status": "deprecated",
            "summary": "Research-only natal warning model for harsh, accident-prone, destabilizing, or caution-heavy places. Kept for benchmark comparison, not public use.",
            "description": "This generic warning lens remains in the catalog for internal benchmark comparison and research replay only. It uses the broad malefic-versus-benefic place heuristic, ignores transit overlay, and is no longer intended as the public product-facing risk preset.",
            "goal_family": "risk",
            "evaluation_strategy": "malefic_minus_benefic",
            "transit_strategy": "ignore",
            "legacy_refs": [
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md", notes=["Malefic and benefic angular pressure meanings come from the core planetary reference layer."]),
                doc_ref("backend/benchmarks/astrocartography/baselines.py", notes=["This deprecated research model still uses the inverted malefic-minus-benefic form of the shared balance heuristic so higher score means more risk."]),
                doc_ref("backend/morin_engine_knowledge_map.md", notes=["Morin-style body, conflict, instability, and crisis themes justify keeping this as a broad caution research lens rather than a disease-specific one."]),
            ],
            "score_components": [
                line_component("Mars", ["ASC", "DSC", "MC", "IC"], 4.8, "Mars angular pressure raises accident, conflict, haste, and harsh-environment signatures."),
                line_component("Saturn", ["ASC", "DSC", "MC", "IC"], 4.4, "Saturn angular pressure raises heaviness, obstruction, depletion, and hard conditions."),
                line_component("Uranus", ["ASC", "DSC", "MC", "IC"], 3.8, "Uranus angular pressure raises disruption, instability, and sudden rupture."),
                line_component("Pluto", ["ASC", "DSC", "MC", "IC"], 3.6, "Pluto angular pressure raises crisis, compulsion, and extreme intensity."),
                line_component("Neptune", ["ASC", "DSC", "MC", "IC"], 2.6, "Neptune angular pressure raises confusion, diffusion, and weakened practical footing."),
                line_component("Chiron", ["ASC", "DSC", "MC", "IC"], 2.2, "Chiron angular pressure can correlate with exposed vulnerability and wound-sensitivity."),
                line_component("Jupiter", ["ASC", "DSC", "MC", "IC"], -3.4, "Jupiter lowers the score by adding protection, ease, and constructive room to move.", polarity="caution"),
                line_component("Venus", ["ASC", "DSC", "MC", "IC"], -3.0, "Venus lowers the score by softening the environment and reducing abrasiveness.", polarity="caution"),
                line_component("Sun", ["ASC", "DSC", "MC", "IC"], -2.0, "Sun lowers generic risk when the place strengthens confidence and vitality.", polarity="caution"),
                line_component("Moon", ["ASC", "DSC", "MC", "IC"], -1.8, "Moon lowers generic risk when the place supports receptivity and emotional steadiness.", polarity="caution"),
                crossing_component(["Mars", "Saturn"], 4.2, "Mars/Saturn is the clearest hard-pressure and harsh-friction crossing."),
                crossing_component(["Mars", "Uranus"], 3.8, "Mars/Uranus raises sudden disruption and accident-prone volatility."),
                crossing_component(["Mars", "Pluto"], 3.4, "Mars/Pluto intensifies force, crisis, and high-pressure environments."),
                crossing_component(["Saturn", "Neptune"], 2.8, "Saturn/Neptune supports environments that feel draining, unclear, or structurally weakening."),
                crossing_component(["Jupiter", "Venus"], -3.2, "Jupiter/Venus lowers the warning level by softening the overall field.", polarity="caution"),
                crossing_component(["Sun", "Moon"], -1.8, "Sun/Moon lowers the warning level by increasing coherence and basic livability.", polarity="caution"),
                modifier_component("malefic_pressure", 3.2, "General malefic pressure is the core relocation warning metric for this public model."),
                modifier_component("conflict_pressure", 1.8, "Conflict-heavy relocated charts tend to feel harsher and less forgiving."),
                modifier_component("uncertainty", 1.8, "Instability increases the general caution level of a place."),
                modifier_component("benefic_balance", -2.8, "Strong benefic protection should reduce the warning score."),
                modifier_component("stability", -1.8, "Stable places should not rank like harsh zones."),
                constraint_component("malefic_pressure", "gte", 0.55, "Very strong malefic pressure deserves a stronger warning lift.", add=2.8, polarity="support"),
                constraint_component("benefic_balance", "gte", 0.45, "Strong benefic protection should cap otherwise harsh-looking places.", cap_score=10.0, polarity="caution"),
                constraint_component("stability", "gte", 0.5, "High stability should further suppress generic risk warnings.", add=-2.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -14, "max_score": 30},
        },
        {
            "id": "love_commitment",
            "label": "Love Commitment",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for stable partnership, commitment, emotional continuity, and long-horizon relationship building.",
            "description": "Built as a specialist relationship model from the corpus and tied to the recovered LOVE.HYP and PARTNERS.HYP legacy families.",
            "goal_family": "love",
            "legacy_refs": [
                legacy_ref("LOVE.HYP", "hyp", notes=["Legacy love-rule family behind or adjacent to the visible Love preset."]),
                legacy_ref("PARTNERS.HYP", "hyp", notes=["Legacy partner-oriented rule family for committed bonds and serious unions."]),
            ],
            "score_components": [
                line_component("Venus", ["DSC", "IC"], 6.6, "Venus on partnership and home-root angles is the clearest harmony signature for durable love."),
                line_component("Moon", ["IC", "DSC"], 4.8, "Moon deepens care, belonging, and emotional continuity."),
                line_component("Jupiter", ["DSC", "IC"], 3.2, "Jupiter helps generosity, protection, and constructive relational growth."),
                line_component("Saturn", ["DSC", "IC"], 1.8, "Saturn can support commitment when the chart is otherwise warm enough."),
                line_component("Mars", ["DSC"], -2.6, "Mars on the partnership axis can turn intensity into conflict.", polarity="caution"),
                line_component("Uranus", ["DSC"], -3.6, "Uranus on the partnership axis can destabilize continuity and commitment.", polarity="caution"),
                crossing_component(["Venus", "Moon"], 4.2, "Venus/Moon blends affection with emotional safety."),
                crossing_component(["Venus", "Jupiter"], 3.0, "Venus/Jupiter supports generosity, goodwill, and abundance in love."),
                crossing_component(["Venus", "Saturn"], 1.8, "Venus/Saturn can support seriousness and long-term structure when not too dry."),
                crossing_component(["Venus", "Uranus"], -3.0, "Venus/Uranus is exciting but can undercut stability.", polarity="caution"),
                relocation_component(["Venus", "Moon", "Jupiter", "Saturn"], [4, 5, 7], 4.2, "Relocated charts favor commitment when relationship planets concentrate in bond-forming houses."),
                modifier_component("partnership", 3.0, "High partnership metrics support sustained relational focus."),
                modifier_component("domesticity", 2.8, "Domestic warmth helps love become lived and durable."),
                modifier_component("stability", 2.4, "Stability is a core requirement for commitment-oriented relocation choices."),
                modifier_component("uncertainty", -3.2, "High uncertainty weakens relationship continuity.",),
                constraint_component("stability", "gte", 0.35, "Stable relocated charts deserve a modest commitment bonus.", multiplier=1.15, polarity="support"),
                constraint_component("uncertainty", "gte", 0.45, "Very unstable relocated charts should lose commitment credibility.", add=-3.0, polarity="caution"),
                constraint_component("partnership", "lt", 0.2, "Places with almost no partnership signature should not rank as strong commitment zones.", cap_score=8.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 28},
        },
        {
            "id": "money_stable_income",
            "label": "Money Stable Income",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for reliable income, manageable financial flow, and durable material footing rather than speculative upside alone.",
            "description": "Built as a specialist financial model from the corpus and tied to the recovered MONEY.HYP legacy family, with extra emphasis on stability and caution control.",
            "goal_family": "money",
            "legacy_refs": [
                legacy_ref("MONEY.HYP", "hyp", notes=["Legacy money-rule family for financial opportunity and gain."]),
                legacy_ref("WORK.HYP", "hyp", notes=["Work-rule family likely overlaps when income depends on durable professional structure."]),
                legacy_ref("MONEY_GAINS_INVESTMENTS.HYP", "hyp", notes=["External money/investments variant reviewed on 2026-04-05."]),
            ],
            "score_components": [
                line_component("Jupiter", ["MC", "ASC"], 5.6, "Jupiter supports expansion, opportunity, and financial confidence."),
                line_component("Venus", ["MC", "ASC"], 4.2, "Venus helps material ease, social value, and profitable attraction."),
                line_component("Sun", ["MC"], 4.5, "Sun MC is strong for recognition that supports consistent earning power."),
                line_component("Saturn", ["MC", "IC"], 2.6, "Saturn can stabilize income when structure matters more than speed."),
                line_component("Mercury", ["MC", "ASC"], 2.8, "Mercury supports commerce, trade, and skill-based income."),
                line_component("Neptune", ["MC"], -4.0, "Neptune can blur money judgment and practical financial structure.", polarity="caution"),
                crossing_component(["Jupiter", "Venus"], 4.2, "Jupiter/Venus is the classic abundance blend."),
                crossing_component(["Jupiter", "Sun"], 3.1, "Jupiter/Sun supports confidence, visibility, and material expansion."),
                crossing_component(["Mercury", "Jupiter"], 2.4, "Mercury/Jupiter helps trade, teaching, and commercial growth."),
                crossing_component(["Jupiter", "Neptune"], -3.6, "Jupiter/Neptune can exaggerate optimism and weaken grounded money handling.", polarity="caution"),
                relocation_component(["Jupiter", "Venus", "Sun", "Saturn", "Mercury"], [2, 6, 8, 10, 11], 4.3, "Relocated charts are better for stable income when money and work planets fill material and public houses."),
                modifier_component("stability", 3.2, "Stable relocated charts are essential for reliable income outcomes."),
                modifier_component("career_status", 2.3, "Career strength supports durable earning capacity."),
                modifier_component("uncertainty", -3.2, "High uncertainty undermines stable income even when upside looks attractive."),
                modifier_component("malefic_pressure", -2.0, "Heavy pressure can disrupt consistency and increase financial strain."),
                constraint_component("stability", "gte", 0.35, "Stable charts deserve a modest confidence multiplier for income durability.", multiplier=1.15, polarity="support"),
                constraint_component("uncertainty", "gte", 0.4, "Unstable charts should be penalized for reliability-focused money searches.", add=-3.5, polarity="caution"),
                constraint_component("malefic_pressure", "gte", 0.55, "Excess pressure should cap optimistic money rankings.", add=-2.5, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 30},
        },
        {
            "id": "career_public_profile",
            "label": "Career Public Profile",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for recognition, public role, authority, and visible career ascent rather than only work throughput.",
            "description": "Built as a specialist career model from the corpus and tied to the recovered CAREER.HYP family with extra emphasis on visibility thresholds.",
            "goal_family": "career",
            "legacy_refs": [
                legacy_ref("CAREER.HYP", "hyp", notes=["Recovered as a distinct legacy rule pack with a softer, status-oriented career profile."]),
            ],
            "score_components": [
                line_component("Sun", ["MC"], 6.6, "Sun MC is the clearest visibility, leadership, and recognition line."),
                line_component("Jupiter", ["MC"], 5.0, "Jupiter MC grows reach, prestige, and professional opportunity."),
                line_component("Mercury", ["MC", "ASC"], 4.0, "Mercury helps profile-building through speech, strategy, and visible competence."),
                line_component("Saturn", ["MC"], 3.6, "Saturn MC supports authority, status, and institutional seriousness."),
                line_component("North Node", ["MC"], 4.0, "Node MC can pull public-development contacts and future-facing status opportunities."),
                line_component("Neptune", ["MC"], -3.4, "Neptune MC can weaken clean public positioning and confuse reputation.", polarity="caution"),
                crossing_component(["Sun", "Jupiter"], 4.0, "Sun/Jupiter is strong for public success, recognition, and expansion."),
                crossing_component(["Sun", "Saturn"], 2.2, "Sun/Saturn can support authority, accountability, and seniority."),
                crossing_component(["Mercury", "Jupiter"], 2.8, "Mercury/Jupiter helps teaching, media, publishing, and public thought leadership."),
                crossing_component(["Sun", "Neptune"], -3.0, "Sun/Neptune can blur public image and practical career clarity.", polarity="caution"),
                relocation_component(["Sun", "Jupiter", "Mercury", "Saturn", "North Node"], [1, 10, 11], 4.5, "Relocated charts favor public-profile growth when career planets gather in angular and audience-facing houses."),
                modifier_component("visibility", 3.5, "Visibility is a core condition for public-profile success."),
                modifier_component("career_status", 3.0, "Career-status metrics support public reach and authority."),
                modifier_component("uncertainty", -2.5, "Public-profile models need enough clarity to sustain reputation."),
                constraint_component("visibility", "gte", 0.35, "Strong visibility should lift public-profile rankings.", multiplier=1.15, polarity="support"),
                constraint_component("visibility", "lt", 0.15, "Very low visibility should cap public-profile outcomes even if other weights are decent.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -10, "max_score": 30},
        },
        {
            "id": "home_retreat",
            "label": "Home Retreat",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for sanctuary, inner rest, softer domestic life, and retreat-style home grounding.",
            "description": "Built as a specialist home model from the corpus and tied to the recovered HOME.HYP family, with extra emphasis on domestic calm and low instability.",
            "goal_family": "home",
            "legacy_refs": [
                legacy_ref("HOME.HYP", "hyp", notes=["Legacy home-rule family for roots, domestic stability, and living environment choices."]),
            ],
            "score_components": [
                line_component("Moon", ["IC"], 5.8, "Moon IC is the clearest belonging, shelter, and emotional home signature."),
                line_component("Venus", ["IC"], 3.6, "Venus IC supports beauty, softness, and livable ease in the home sphere."),
                line_component("Jupiter", ["IC"], 2.8, "Jupiter IC can enlarge comfort, generosity, and supportive domestic space."),
                line_component("Neptune", ["IC"], 3.6, "Neptune IC is more valuable here because retreat needs contemplation, imagination, and quiet interiority."),
                line_component("Mars", ["IC"], -3.0, "Mars IC can agitate the home base and weaken retreat quality.", polarity="caution"),
                crossing_component(["Moon", "Venus"], 2.4, "Moon/Venus blends care, comfort, and softness."),
                crossing_component(["Moon", "Jupiter"], 2.0, "Moon/Jupiter can enlarge emotional and domestic support."),
                crossing_component(["Moon", "Neptune"], 3.0, "Moon/Neptune better captures the contemplative and sanctuary tone of this specialist variant."),
                crossing_component(["Mars", "Moon"], -3.0, "Mars/Moon can agitate emotional peace and home calm.", polarity="caution"),
                relocation_component(["Moon", "Neptune", "Jupiter"], [4, 8, 12], 4.0, "Relocated charts support retreat when domestic and contemplative houses are warmly occupied."),
                modifier_component("domesticity", 2.0, "Domestic warmth is central to a retreat-style home goal."),
                modifier_component("home_base", 2.6, "A strong home-base signature supports lasting sanctuary."),
                modifier_component("beliefs", 2.2, "A contemplative or spiritual tone is a stronger part of retreat than of ordinary home life."),
                modifier_component("uncertainty", -2.8, "Too much instability weakens the idea of a real retreat base."),
                constraint_component("domesticity", "gte", 0.35, "High domesticity should lift retreat-style home rankings.", multiplier=1.1, polarity="support"),
                constraint_component("beliefs", "gte", 0.25, "Retreat-style homes should gain when the place also supports contemplation and inward orientation.", multiplier=1.08, polarity="support"),
                constraint_component("uncertainty", "gte", 0.45, "Strong instability should sharply reduce retreat suitability.", add=-3.0, polarity="caution"),
                constraint_component("beliefs", "lt", 0.12, "Places with no contemplative tone should not rank like retreat sanctuaries.", cap_score=11.0, polarity="caution"),
                constraint_component("home_base", "lt", 0.2, "Places with almost no home-base signal should not rank as retreat homes.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 28},
        },
        {
            "id": "travel_fun",
            "label": "Travel for Fun",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for pleasure travel, honeymoon energy, celebration, social ease, and travel that feels vivid rather than dutiful.",
            "description": "Built as a travel-specific pleasure model rather than a generic love or friends proxy. It uses Venus and Jupiter for enjoyment and ease, Mercury for movement, Sun for celebratory vitality, and the 3rd, 5th, 9th, and 11th houses for journeys, recreation, and joyful social atmosphere.",
            "goal_family": "travel",
            "legacy_refs": [
                legacy_ref("LOVE_CHILDREN_SPECULATION.HYP", "hyp", notes=["External legacy pleasure/speculation family reviewed on 2026-04-05 and used here as the closest travel-for-fun structural anchor."]),
                doc_ref("backend/morin_engine_knowledge_map.md", notes=["Morin house semantics explicitly connect the 3rd to short journeys, the 5th to pleasure and recreation, and the 9th to long journeys and foreign countries."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md", notes=["Venus pleasure, Jupiter travel opportunity, Mercury movement, and Sun vitality come from the core astrocartography reference layer."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/05_feature_notes.md", notes=["The feature notes already anticipated travel as a likely future goal family for atlas scoring."]),
            ],
            "score_components": [
                line_component("Venus", ["ASC", "DSC"], 5.2, "Venus is the clearest leisure, enjoyment, and social-pleasure signal for travel that feels fun."),
                line_component("Jupiter", ["ASC", "MC", "DSC"], 4.8, "Jupiter supports travel opportunity, generosity, luck, and a broader sense of enjoyment."),
                line_component("Sun", ["ASC", "MC"], 3.2, "Sun supports celebratory visibility, vitality, and the sense that a trip feels special."),
                line_component("Mercury", ["ASC", "DSC"], 2.8, "Mercury keeps the trip mobile, curious, and socially active rather than static."),
                line_component("Moon", ["ASC", "IC"], 1.8, "Moon adds ease, responsiveness, and emotional enjoyment."),
                line_component("Saturn", ["IC", "ASC"], -3.0, "Saturn makes trips feel dutiful, heavy, or restricted rather than genuinely fun.", polarity="caution"),
                line_component("Mars", ["IC", "DSC"], -2.4, "Mars can turn pleasure travel into friction, impatience, or avoidable irritation.", polarity="caution"),
                line_component("Neptune", ["ASC", "IC"], -1.6, "Too much Neptune can turn fun travel into confusion, drift, or impracticality.", polarity="caution"),
                crossing_component(["Venus", "Jupiter"], 4.0, "Venus/Jupiter is the clearest joy-and-ease travel crossing."),
                crossing_component(["Venus", "Mercury"], 2.6, "Venus/Mercury supports lively companionship, movement, and a light social atmosphere."),
                crossing_component(["Sun", "Jupiter"], 2.6, "Sun/Jupiter supports celebratory, optimistic travel."),
                crossing_component(["Moon", "Venus"], 2.0, "Moon/Venus adds sweetness, comfort, and easy enjoyment."),
                crossing_component(["Mars", "Saturn"], -3.0, "Mars/Saturn can make a trip feel blocked, abrasive, or overly effortful.", polarity="caution"),
                relocation_component(["Venus", "Jupiter", "Sun", "Mercury", "Moon"], [3, 5, 9, 11], 4.2, "Relocated charts support fun travel when joy, movement, and long-journey houses are populated by benefics and light planets."),
                modifier_component("travel_joy", 3.2, "Travel joy is the direct relocation metric for pleasure-oriented travel."),
                modifier_component("mobility", 1.9, "Trips should feel mobile, curious, and easy to move through."),
                modifier_component("community", 1.6, "Social warmth and a sense of welcome strengthen fun travel."),
                modifier_component("benefic_balance", 1.4, "A benefic-leaning relocated chart helps a trip feel easy rather than effortful."),
                modifier_component("beliefs", 0.8, "A small meaning-and-horizon component helps foreign travel feel expansive."),
                modifier_component("uncertainty", -1.8, "Too much drift weakens enjoyment and practical trip quality."),
                constraint_component("travel_joy", "gte", 0.35, "Clear pleasure-travel signatures deserve a modest uplift.", multiplier=1.1, polarity="support"),
                constraint_component("mobility", "gte", 0.3, "Trips that are both joyful and mobile deserve a small lift.", multiplier=1.06, polarity="support"),
                constraint_component("uncertainty", "gte", 0.5, "High instability should reduce fun-travel rankings.", add=-2.8, polarity="caution"),
                constraint_component("travel_joy", "lt", 0.15, "Places with almost no travel-joy signature should not rank like leisure destinations.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 34},
        },
        {
            "id": "travel_relax",
            "label": "Travel to Relax",
            "version": "1.0.0",
            "status": "active",
            "summary": "Ranks places for restorative travel, retreat atmosphere, decompression, and trips that feel calming rather than stimulating.",
            "description": "Built as a travel-restoration model rather than a home proxy. It keeps Moon, Venus, Jupiter, and Neptune as the core restorative planets, but shifts the emphasis toward the 4th, 9th, and 12th houses so the score reflects retreat, sanctuary, and restorative foreign travel instead of permanent domestic rooting.",
            "goal_family": "travel",
            "legacy_refs": [
                legacy_ref("HOME.HYP", "hyp", notes=["Legacy home-rule family used here as the nearest recovered anchor for sanctuary and softness, then adapted away from permanent home-base logic toward restorative travel."]),
                doc_ref("backend/morin_engine_knowledge_map.md", notes=["Morin house semantics connect the 4th to rest and shelter, the 9th to long journeys and foreign countries, and the 12th to withdrawal, contemplation, and retreat."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md", notes=["Moon comfort, Venus ease, Jupiter protection, and Neptune contemplative retreat meanings come from the core reference layer."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/05_feature_notes.md", notes=["Travel appears in the feature notes as an anticipated future goal direction; this model covers the restorative side of that request."]),
            ],
            "score_components": [
                line_component("Moon", ["IC", "ASC"], 5.6, "Moon is the clearest rest, comfort, and emotional-reset travel signal."),
                line_component("Venus", ["IC", "ASC"], 4.2, "Venus softens the field and makes the place feel easier to inhabit temporarily."),
                line_component("Jupiter", ["IC", "ASC"], 3.6, "Jupiter adds protection, breathing room, and gentle restorative ease."),
                line_component("Neptune", ["IC"], 3.2, "Neptune IC is useful here because retreat and decompression can benefit from contemplative quiet."),
                line_component("Sun", ["IC"], 1.8, "Sun IC adds warmth and simple vitality to the retreat experience."),
                line_component("Saturn", ["IC", "ASC"], -3.2, "Saturn makes a trip feel heavy, duty-bound, or emotionally dry instead of restorative.", polarity="caution"),
                line_component("Mars", ["IC", "ASC"], -3.0, "Mars agitates the nervous system and weakens the idea of genuine rest.", polarity="caution"),
                line_component("Uranus", ["ASC", "IC"], -2.6, "Uranus introduces volatility and restlessness that work against decompression.", polarity="caution"),
                crossing_component(["Moon", "Venus"], 3.2, "Moon/Venus is the clearest soft-restoration crossing."),
                crossing_component(["Moon", "Jupiter"], 2.8, "Moon/Jupiter supports generous emotional recovery and a sense of safe retreat."),
                crossing_component(["Moon", "Neptune"], 2.6, "Moon/Neptune supports contemplative retreat and inward quiet when the place is otherwise stable."),
                crossing_component(["Venus", "Jupiter"], 2.2, "Venus/Jupiter adds simple ease and restorative abundance."),
                crossing_component(["Mars", "Moon"], -3.0, "Mars/Moon agitates emotional calm and bodily rest.", polarity="caution"),
                crossing_component(["Saturn", "Neptune"], -2.2, "Saturn/Neptune can turn retreat into depletion rather than recovery.", polarity="caution"),
                relocation_component(["Moon", "Venus", "Jupiter", "Neptune", "Sun"], [4, 9, 12], 4.2, "Relocated charts support restorative travel when shelter, long-journey, and retreat houses are warmly occupied."),
                modifier_component("restoration", 3.4, "Restoration is the direct relocation metric for decompression-oriented travel."),
                modifier_component("domesticity", 1.8, "Some comfort and shelter still matter even for temporary retreat travel."),
                modifier_component("beliefs", 1.7, "Retreat travel often works better when a place also opens contemplation or meaning."),
                modifier_component("stability", 1.4, "Rest should feel steady rather than volatile."),
                modifier_component("benefic_balance", 1.2, "A benefic-leaning field helps a place feel more restorative."),
                modifier_component("uncertainty", -2.4, "Instability and nervous drift weaken decompression."),
                constraint_component("restoration", "gte", 0.35, "Strong restorative signatures deserve a modest uplift.", multiplier=1.12, polarity="support"),
                constraint_component("beliefs", "gte", 0.2, "Trips with a real contemplative or inward tone deserve a small lift.", multiplier=1.06, polarity="support"),
                constraint_component("uncertainty", "gte", 0.45, "Strong instability should sharply reduce restorative travel suitability.", add=-3.0, polarity="caution"),
                constraint_component("restoration", "lt", 0.15, "Places with almost no restoration signal should not rank as retreat destinations.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 34},
        },
        {
            "id": "gambling_luck",
            "label": "Gambling Luck",
            "version": "1.2.0",
            "status": "active",
            "summary": "Ranks places for speculative upside, lucky streaks, calculated risk-taking, and benefic 5th-house momentum rather than stable income.",
            "description": "Temporarily benchmark-aligned to the stronger parent money model. Until the specialist speculation benchmark cleanly beats the parent profile, gambling luck should inherit the top-performing base money scoring shape rather than claim extra specialist precision it has not yet earned.",
            "goal_family": "gambling",
            "legacy_refs": [
                legacy_ref("MONEY.HYP", "hyp", notes=["Primary financial parent model. Current gambling scoring is intentionally aligned to this stronger benchmark performer."]),
                legacy_ref("Gambling_Elect_Personal.hyp", "hyp", notes=["External legacy gambling model reviewed on 2026-04-05. It remains a research reference, but it does not currently outperform the money parent on the seeded benchmark."]),
                legacy_ref("MONEY_GAINS_INVESTMENTS.HYP", "hyp", notes=["External money/investments parent model reviewed alongside the gambling pack."]),
                legacy_ref("CAREER_BUSINESS_PARENT.HYP", "hyp", notes=["External career/business parent model reviewed as a contrast family."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md", notes=["Jupiter luck/opportunity, Venus ease, Mercury trade, and Sun confidence are drawn from the core planetary baseline reference."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/06_extended_goal_domains.md", notes=["Documents the speculative-use extension for astrocartography goal work."]),
                doc_ref("backend/morin_engine_knowledge_map.md", notes=["Morin house semantics explicitly map the 5th house to speculation and gambling."]),
            ],
            "score_components": [
                line_component("Jupiter", ["MC", "ASC"], 6.0, "Jupiter is the strongest corpus signal for opportunity, growth, and gain."),
                line_component("Venus", ["MC", "ASC", "IC"], 5.0, "Venus supports ease, attraction, diplomacy, and cash-friendly exchange."),
                line_component("Mercury", ["MC", "ASC"], 3.5, "Mercury supports trade, sales, writing, and transactional movement."),
                line_component("Sun", ["MC"], 3.5, "Sun MC can raise visibility and earning power through prominence."),
                line_component("Saturn", ["MC"], 1.8, "Saturn can stabilize money through discipline and structured effort."),
                line_component("Neptune", ["MC", "ASC"], -4.5, "Neptune is a caution factor for glamour, leakage, and unrealistic expectations.", polarity="caution"),
                crossing_component(["Venus", "Jupiter"], 4.0, "Venus/Jupiter crossings are the clearest ease-and-growth blend for gain."),
                crossing_component(["Sun", "Jupiter"], 3.0, "Sun/Jupiter supports recognition with expansion."),
                crossing_component(["Venus", "Neptune"], -3.0, "Venus/Neptune can look attractive while blurring practical value.", polarity="caution"),
                relocation_component(["Jupiter", "Venus", "Mercury", "Sun"], [2, 8, 10, 11], 4.5, "Benchmark-aligned relocation base inherited from the stronger base money parent."),
                modifier_component("visibility", 2.4, "Money tends to improve where the relocated chart raises profile and access."),
                modifier_component("benefic_balance", 2.0, "A benefic-leaning relocated chart helps flow, trust, and exchange."),
                modifier_component("stability", 1.6, "Stable structure improves resource retention instead of short spikes."),
                modifier_component("uncertainty", -2.8, "High uncertainty is a recurring caution for practical money outcomes."),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 30},
        },
        {
            "id": "health_risk",
            "label": "Health Risk",
            "version": "1.0.0",
            "status": "active",
            "summary": "Warning-oriented model that ranks places where injury, illness pressure, and bodily strain are more likely to surface. Higher scores mean worse places.",
            "description": "Built as an explicit caution model rather than a positive destination goal. It uses the planetary caution layer for Mars, Saturn, Uranus, Neptune, and Pluto, the ASC as the body axis, and Morin-style 6th, 8th, and 12th-house health and danger semantics. High scores are a warning signal, not a recommendation.",
            "goal_family": "risk",
            "score_polarity": "higher_is_worse",
            "legacy_refs": [
                legacy_ref("WORK__SERVICE _SICKNESS_.HYP", "hyp", notes=["External work-service-sickness hybrid family reviewed on 2026-04-05."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/02_planetary_and_angular_reference.md", notes=["Mars conflict/haste, Saturn heaviness, Uranus shock, Neptune confusion, Pluto crisis, and the ASC/body framing come from the core astrocartography reference layer."]),
                doc_ref("horary_knowledge/astrocartography_knowledge_base/reference/06_extended_goal_domains.md", notes=["Documents the risk-oriented extension for astrocartography goal work and clarifies that higher scores are negative."]),
                doc_ref("backend/morin_engine_knowledge_map.md", notes=["Morin house semantics explicitly map the 6th house to health and illness, mark malefics there as illness-prone, and use the 5th/6th/8th/12th layer for danger and bodily strain logic elsewhere in the engine."]),
                doc_ref("frontend/backend/transits_morin.py", notes=["Existing transit logic already treats 1st, 6th, 8th, and 12th-house malefic pressure as injury and illness risk signals."]),
            ],
            "score_components": [
                line_component("Mars", ["ASC"], 5.8, "Mars on the body axis raises heat, haste, cuts, inflammation, and accident exposure."),
                line_component("Saturn", ["ASC"], 5.0, "Saturn on the body axis raises depletion, heaviness, chronic strain, and lowered resilience."),
                line_component("Uranus", ["ASC"], 4.2, "Uranus on the body axis raises shock, sudden disruption, and accident-prone volatility."),
                line_component("Neptune", ["ASC"], 3.6, "Neptune on the body axis can blur vitality, immunity, and physical clarity."),
                line_component("Pluto", ["ASC"], 3.8, "Pluto on the body axis intensifies crisis, compulsion, and extreme bodily pressure."),
                line_component("Jupiter", ["ASC", "IC"], -2.8, "Jupiter can protect vitality and lower the overall risk signature.", polarity="caution"),
                line_component("Venus", ["ASC", "IC"], -2.2, "Venus can soften bodily strain and environmental abrasiveness.", polarity="caution"),
                crossing_component(["Mars", "Saturn"], 4.8, "Mars/Saturn is the clearest friction-and-injury pressure crossing."),
                crossing_component(["Mars", "Uranus"], 4.4, "Mars/Uranus raises sudden accident and shock signatures."),
                crossing_component(["Mars", "Pluto"], 4.0, "Mars/Pluto intensifies crisis, force, and high-pressure bodily situations."),
                crossing_component(["Saturn", "Neptune"], 3.0, "Saturn/Neptune supports chronic depletion and diffuse weakening patterns."),
                crossing_component(["Jupiter", "Venus"], -2.6, "Jupiter/Venus softens the environment and lowers the bodily-strain profile.", polarity="caution"),
                relocation_component(["Mars", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"], [1, 6, 8, 12], 5.0, "Relocated charts look riskier when pressure and wound planets dominate the body, illness, crisis, and hidden-burden houses."),
                modifier_component("health_risk", 3.8, "Health risk is the direct relocation metric for this warning model."),
                modifier_component("malefic_pressure", 2.8, "General malefic pressure increases bodily vulnerability."),
                modifier_component("conflict_pressure", 1.4, "Harsh environments often increase injury exposure alongside conflict."),
                modifier_component("uncertainty", 1.8, "Instability amplifies sudden or poorly managed bodily stress."),
                modifier_component("benefic_balance", -2.2, "Strong benefic protection should reduce the risk score.",),
                modifier_component("stability", -1.4, "Stable charts should not rank like hazard zones."),
                constraint_component("health_risk", "gte", 0.35, "Clear health-risk signatures deserve a stronger warning multiplier.", multiplier=1.15, polarity="support"),
                constraint_component("malefic_pressure", "gte", 0.55, "Heavy malefic pressure should sharply raise the warning score.", add=2.8, polarity="support"),
                constraint_component("benefic_balance", "gte", 0.45, "Strong benefic protection should cap otherwise harsh-looking results.", cap_score=10.0, polarity="caution"),
                constraint_component("health_risk", "lt", 0.15, "Places with almost no bodily-risk signature should not rank as health hotspots.", cap_score=8.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 32},
        },
    ]


def _patched_core_models(existing: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    education_legacy = list((existing.get("education") or {}).get("legacy_refs") or [])
    work_legacy = _merge_legacy_refs(
        list((existing.get("work") or {}).get("legacy_refs") or []),
        [
            legacy_ref("WORK__SERVICE _SICKNESS_.HYP", "hyp", notes=["External work-service-sickness hybrid family reviewed on 2026-04-05."]),
        ],
    )
    career_legacy = list((existing.get("career") or {}).get("legacy_refs") or [])
    home_legacy = list((existing.get("home") or {}).get("legacy_refs") or [])
    return [
        {
            "id": "education",
            "label": "Education",
            "version": "1.1.0",
            "status": "active",
            "summary": "Ranks places for study, teaching, research, and disciplined skill-building.",
            "description": "Reworked to stay distinct from beliefs and communication: stronger Mercury/Saturn study logic, lower dependence on spiritual meaning or public profile, and clearer emphasis on structured learning.",
            "goal_family": "education",
            "legacy_refs": education_legacy,
            "score_components": [
                line_component("Mercury", ["ASC", "MC"], 6.2, "Mercury remains the clearest study, language, and technical learning signature."),
                line_component("Jupiter", ["ASC", "MC"], 4.6, "Jupiter supports teaching, breadth, and academic expansion without defining the whole model."),
                line_component("Saturn", ["MC", "ASC"], 2.6, "Saturn adds discipline, persistence, and serious mastery."),
                line_component("Moon", ["IC"], 1.0, "Moon IC can stabilize the domestic base needed for long-form study."),
                line_component("Neptune", ["ASC", "MC"], -4.0, "Neptune is a caution factor for confusion, glamour, and scattered judgment.", polarity="caution"),
                crossing_component(["Mercury", "Jupiter"], 4.0, "Mercury/Jupiter crossings remain strong for learning, publishing, and intellectual expansion."),
                crossing_component(["Mercury", "Uranus"], 2.2, "Mercury/Uranus sharpens invention, breakthrough thinking, and modern research."),
                crossing_component(["Mercury", "Neptune"], -3.0, "Mercury/Neptune can blur precision and make study less grounded.", polarity="caution"),
                relocation_component(["Mercury", "Jupiter", "Saturn"], [3, 9, 10], 4.2, "Relocated charts are favorable when learning planets land in study, doctrine, and disciplined public-development houses."),
                modifier_component("mobility", 2.4, "Education improves when the relocated chart stays mentally active, exploratory, and curious."),
                modifier_component("stability", 1.6, "Sustained study benefits from enough structure to keep progress coherent."),
                modifier_component("visibility", 0.8, "Some public visibility helps education turn into teaching or publication, but it is secondary."),
                modifier_component("uncertainty", -2.6, "High uncertainty weakens focus, retention, and coherent educational progress."),
                constraint_component("stability", "gte", 0.2, "Structured environments deserve a modest study bonus.", multiplier=1.05, polarity="support"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -10, "max_score": 24},
        },
        {
            "id": "work",
            "label": "Work",
            "version": "1.1.0",
            "status": "active",
            "summary": "Ranks places for reliable output, usable skill, structured effort, and sustainable day-to-day professional traction.",
            "description": "Reworked to stay distinct from status-oriented career models: stronger Mercury, Saturn, Mars, and 6th-house emphasis, with less dependence on pure visibility.",
            "goal_family": "work",
            "legacy_refs": work_legacy,
            "score_components": [
                line_component("Saturn", ["MC", "ASC"], 5.0, "Saturn supports structure, endurance, and repeatable work habits."),
                line_component("Mercury", ["MC", "ASC"], 4.8, "Mercury supports craft, coordination, communication, and practical output."),
                line_component("Mars", ["MC", "ASC"], 2.8, "Mars helps energy, pace, and execution when not overheated."),
                line_component("Sun", ["MC"], 2.4, "Sun can support visible effort, but work is broader than recognition alone."),
                line_component("Jupiter", ["MC"], 2.0, "Jupiter can expand work opportunity without defining the model."),
                line_component("Neptune", ["MC"], -3.8, "Neptune can blur role clarity, incentives, and reliable execution.", polarity="caution"),
                crossing_component(["Mercury", "Saturn"], 4.0, "Mercury/Saturn is strong for focus, process, and disciplined craft."),
                crossing_component(["Mercury", "Mars"], 2.4, "Mercury/Mars supports pace, responsiveness, and execution."),
                crossing_component(["Sun", "Neptune"], -2.8, "Sun/Neptune can weaken practical role framing.", polarity="caution"),
                relocation_component(["Mercury", "Saturn", "Mars", "Sun"], [3, 6, 10], 4.8, "Work improves when skill and effort planets land in communication, labor, and public-output houses."),
                modifier_component("stability", 3.4, "Reliable work wants steady structure more than pure prestige."),
                modifier_component("career_status", 1.4, "Some career support helps, but it is not the main driver here."),
                modifier_component("uncertainty", -2.6, "Unclear or unstable environments weaken sustainable work output."),
                constraint_component("stability", "lt", 0.15, "Places with almost no structural stability should not rank as strong work environments.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 26},
        },
        {
            "id": "career",
            "label": "Career",
            "version": "1.1.0",
            "status": "active",
            "summary": "Ranks places for advancement, authority, institutional credibility, and steady career elevation over time.",
            "description": "Reworked to stay distinct from daily work and the public-profile specialist model: stronger Saturn/Jupiter authority and status logic, with lower dependence on pure visibility.",
            "goal_family": "career",
            "legacy_refs": career_legacy,
            "score_components": [
                line_component("Saturn", ["MC"], 5.0, "Saturn MC supports authority, seriousness, and durable position."),
                line_component("Jupiter", ["MC", "ASC"], 4.8, "Jupiter supports promotion, room to grow, and institutional lift."),
                line_component("Sun", ["MC"], 4.0, "Sun helps advancement, but this model is not only about public glare."),
                line_component("Pluto", ["MC"], 2.4, "Pluto can deepen influence and strategic command."),
                line_component("Mercury", ["MC"], 1.8, "Mercury supports status through strategy and competence."),
                line_component("Neptune", ["MC"], -4.0, "Neptune on the public axis can blur standing and role definition.", polarity="caution"),
                crossing_component(["Sun", "Saturn"], 3.2, "Sun/Saturn supports authority, responsibility, and earned stature."),
                crossing_component(["Jupiter", "Saturn"], 3.0, "Jupiter/Saturn balances expansion with institutional durability."),
                crossing_component(["Sun", "Jupiter"], 2.8, "Sun/Jupiter remains useful for upward career movement."),
                crossing_component(["Sun", "Neptune"], -3.2, "Sun/Neptune weakens status clarity and trust in the role.", polarity="caution"),
                relocation_component(["Saturn", "Jupiter", "Sun", "Pluto"], [1, 10, 11], 4.8, "Career improves when advancement planets gather in identity, public, and network houses."),
                modifier_component("career_status", 3.2, "Career status is the clearest relocation support metric for this family."),
                modifier_component("stability", 2.8, "Authority compounds best in stable systems."),
                modifier_component("visibility", 1.2, "Visibility matters, but it is secondary to actual authority here."),
                modifier_component("uncertainty", -2.6, "Role ambiguity weakens advancement."),
                constraint_component("career_status", "lt", 0.2, "Places with almost no career-status signature should not rank as strong career zones.", cap_score=12.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -12, "max_score": 28},
        },
        {
            "id": "home",
            "label": "Home",
            "version": "1.1.0",
            "status": "active",
            "summary": "Ranks places for livable home-base support, family continuity, emotional steadiness, and everyday belonging.",
            "description": "Reworked to stay distinct from the retreat-oriented home variant: stronger general belonging, community, and livability, with less contemplative emphasis.",
            "goal_family": "home",
            "legacy_refs": home_legacy,
            "score_components": [
                line_component("Moon", ["IC", "ASC"], 5.8, "Moon through IC and ASC is the clearest rootedness and belonging signature."),
                line_component("Venus", ["IC", "ASC"], 4.8, "Venus supports comfort, harmony, and a place that feels pleasant to inhabit."),
                line_component("Jupiter", ["IC"], 2.8, "Jupiter on the home base broadens support and generosity."),
                line_component("Mars", ["IC"], -3.4, "Mars on the home base can make settlement feel restless or abrasive.", polarity="caution"),
                line_component("Pluto", ["IC"], -3.0, "Pluto on the home base can intensify domestic life beyond what feels easy.", polarity="caution"),
                crossing_component(["Moon", "Venus"], 4.2, "Moon/Venus is the clearest heart-and-home blend."),
                crossing_component(["Moon", "Jupiter"], 2.6, "Moon/Jupiter broadens care and domestic support."),
                crossing_component(["Venus", "Jupiter"], 2.0, "Venus/Jupiter supports social and material livability."),
                crossing_component(["Mars", "Moon"], -2.5, "Mars/Moon can agitate the emotional base.", polarity="caution"),
                relocation_component(["Moon", "Venus", "Jupiter"], [2, 4, 5, 11], 4.4, "Home improves when belonging planets land in family, value, comfort, and community houses."),
                modifier_component("home_base", 3.0, "A strong home-base metric helps a city feel inhabitable rather than merely interesting."),
                modifier_component("domesticity", 2.1, "Domestic softness directly supports settling."),
                modifier_component("community", 1.8, "General home life improves when the surrounding social field is supportive."),
                modifier_component("stability", 2.0, "Stable structure helps a place stay sustainable over time."),
                modifier_component("uncertainty", -2.0, "High uncertainty weakens rootedness and ease."),
                constraint_component("home_base", "lt", 0.15, "Places with almost no home-base signature should not rank as strong home candidates.", cap_score=10.0, polarity="caution"),
            ],
            "normalization": {"method": "bounded_linear", "min_score": -10, "max_score": 24},
        },
    ]


def _standalone_overhaul_components() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "protective_places": [
            line_component("Jupiter", ["ASC", "MC", "IC"], 3.4, "Jupiter can broaden practical support when its natal condition is constructive."),
            line_component("Venus", ["ASC", "DSC", "IC"], 3.0, "Venus can support relational ease and livability when its natal condition is constructive."),
            line_component("Sun", ["ASC"], 2.0, "Sun ASC can support vitality and coherent self-direction."),
            line_component("Moon", ["IC"], 1.8, "Moon IC can support emotional grounding and familiarity."),
            line_component("Mars", ["DSC", "IC"], -2.6, "Mars on relationship or home axes can add abrasion that reduces livability.", polarity="caution"),
            line_component("Saturn", ["ASC", "IC"], -2.4, "Saturn on body or home axes can add burden that reduces ease.", polarity="caution"),
            crossing_component(["Jupiter", "Venus"], 2.4, "Jupiter/Venus is retained as a modest interaction theme, not a safety guarantee."),
            modifier_component("stability", 1.6, "Relocated stability can corroborate a more sustainable environment."),
            modifier_component("uncertainty", -1.8, "Relocated uncertainty lowers practical support.",),
            constraint_component("malefic_pressure", "gte", 0.55, "Heavy relocated pressure caps a protective interpretation.", cap_score=8.0, polarity="caution"),
        ],
        "risk_pressure": [
            line_component("Mars", ["ASC", "DSC"], 3.8, "Mars on body and relationship axes can describe sharper conflict or haste themes."),
            line_component("Saturn", ["ASC", "DSC"], 3.4, "Saturn on body and relationship axes can describe heavier obstruction themes."),
            line_component("Uranus", ["ASC", "DSC"], 3.2, "Uranus on personal axes can describe abrupt instability."),
            line_component("Pluto", ["ASC", "DSC"], 3.0, "Pluto on personal axes can describe intensified pressure and power struggle."),
            line_component("Neptune", ["ASC", "MC"], 2.4, "Neptune on body or public axes can describe reduced clarity."),
            crossing_component(["Mars", "Saturn"], 2.6, "Mars/Saturn is retained as a bounded hard-pressure interaction."),
            crossing_component(["Saturn", "Neptune"], 2.0, "Saturn/Neptune is retained as a bounded depletion-and-ambiguity interaction."),
            modifier_component("uncertainty", 1.4, "Relocated instability can corroborate a caution-heavy interpretation."),
            constraint_component("malefic_pressure", "gte", 0.55, "Multiple pressure placements warrant a modest additional caution.", add=1.5, polarity="support"),
        ],
    }


def _specialist_residual_components() -> Dict[str, List[Dict[str, Any]]]:
    experimental = {"source_status": "experimental"}
    return {
        "love_commitment": [
            modifier_component("stability", 2.0, "Commitment adds durable structure only beyond the parent love signal."),
            modifier_component("uncertainty", -2.8, "Instability is a specialist caution for long-horizon partnership."),
            crossing_component(["Venus", "Saturn"], 1.0, "Venus/Saturn is a modest conditional structure theme, not universally positive."),
            constraint_component("partnership", "lt", 0.15, "Without partnership corroboration, the commitment residual is capped.", cap_score=2.0, polarity="caution"),
        ],
        "money_stable_income": [
            relocation_component(["Mercury", "Saturn"], [2, 6, 10], 2.4, "Stable income emphasizes earned-resource, work, and vocation houses rather than shared 8th-house resources."),
            modifier_component("stability", 2.2, "Stability is the principal residual over the broader money parent."),
            modifier_component("uncertainty", -3.0, "Uncertainty weakens dependable income even when opportunity exists."),
            constraint_component("stability", "lt", 0.15, "Low stability caps the stable-income residual.", cap_score=2.0, polarity="caution"),
        ],
        "career_public_profile": [
            relocation_component(["Mercury", "Sun"], [10], 1.8, "Public-profile specialization requires direct 10th-house corroboration."),
            line_component(
                "North Node",
                ["MC"],
                3.0,
                "North Node MC is retained as an experimental public-direction theme that distinguishes the specialist from general career support.",
                source_status="experimental",
            ),
            modifier_component("visibility", 2.6, "Visibility is the specialist residual beyond the broader career parent."),
            modifier_component("uncertainty", -2.2, "Role ambiguity weakens public-profile reliability."),
            constraint_component("visibility", "lt", 0.2, "Low visibility caps the public-profile residual.", cap_score=2.0, polarity="caution"),
        ],
        "home_retreat": [
            relocation_component(["Moon", "Venus"], [4, 12], 2.0, "Retreat specialization emphasizes shelter and withdrawal without equating all home signatures with retreat."),
            modifier_component("restoration", 2.2, "Restoration is the bounded residual beyond the general home parent."),
            line_component("Neptune", ["IC"], -2.0, "Neptune IC remains a caution for unreliable foundations rather than an automatic retreat benefit.", polarity="caution"),
            modifier_component("uncertainty", -2.6, "Instability weakens a sanctuary interpretation."),
        ],
        "travel_fun": [
            relocation_component(["Mercury", "Jupiter"], [3, 9], 1.6, "Pleasure travel needs journey-specific corroboration beyond the social parent."),
            modifier_component("travel_joy", 2.2, "Travel joy is the experimental specialist residual."),
            modifier_component("mobility", 1.6, "Mobility distinguishes travel from ordinary friendship support."),
            modifier_component("uncertainty", -2.0, "High instability reduces practical trip quality."),
        ],
        "travel_relax": [
            relocation_component(["Moon", "Venus"], [9, 12], 1.8, "Restorative travel requires journey or retreat-house corroboration beyond the home parent."),
            modifier_component("restoration", 2.4, "Restoration is the experimental travel residual."),
            line_component("Neptune", ["IC"], -2.0, "Neptune IC is treated as uncertain foundations, not an automatic restorative benefit.", polarity="caution"),
            modifier_component("uncertainty", -2.4, "Instability works against decompression."),
        ],
        "gambling_luck": [
            relocation_component(["Jupiter", "Venus", "Mercury", "Moon"], [5], 2.4, "The experimental residual is limited to local 5th-house speculation symbolism.", **experimental),
            modifier_component("speculation", 2.0, "Local speculation placements may corroborate the money parent without implying outcomes.", **experimental),
            modifier_component("speculation_drag", -2.4, "Local speculation cautions reduce the experimental residual.", **experimental),
            modifier_component("pattern_support", 1.0, "Natal pattern geometry is recorded only as a global prior and cannot differentiate cities.", evidence_role="global_prior", **experimental),
            modifier_component("pattern_pressure", -1.0, "Natal pattern pressure is recorded only as a global prior and cannot differentiate cities.", evidence_role="global_prior", **experimental),
        ],
        "health_risk": [
            relocation_component(["Mars", "Saturn", "Uranus", "Neptune", "Pluto"], [6, 8, 12], 2.4, "The experimental health residual requires local illness, crisis, or burden-house corroboration.", **experimental),
            modifier_component("health_risk", 2.0, "Health-risk metrics are interpretive caution themes, not medical prediction.", **experimental),
            constraint_component("health_risk", "gte", 0.5, "Several local caution placements warrant a modest research-only lift.", add=1.2, polarity="support", **experimental),
        ],
        "accident_prone": [
            crossing_component(["Mars", "Uranus"], 3.0, "Mars/Uranus is retained as an experimental acute-disruption interaction, not an accident probability.", **experimental),
            crossing_component(["Mars", "Pluto"], 2.2, "Mars/Pluto is retained as an experimental force-pressure interaction.", **experimental),
            modifier_component("health_risk", 1.4, "Local bodily-pressure themes provide limited corroboration only.", **experimental),
            constraint_component("conflict_pressure", "gte", 0.5, "Multiple local pressure themes warrant a modest research-only lift.", add=1.0, polarity="support", **experimental),
        ],
    }


def _model_bodies(model: Dict[str, Any]) -> set[str]:
    bodies: set[str] = set()
    for component in model.get("score_components") or []:
        planet = str(component.get("planet") or "").strip()
        if planet:
            bodies.add(planet)
        bodies.update(str(item).strip() for item in (component.get("pair") or []) if str(item).strip())
        bodies.update(str(item).strip() for item in (component.get("planets") or []) if str(item).strip())
    return bodies


def _apply_model_overhaul(models_by_id: Dict[str, Dict[str, Any]]) -> None:
    standalone_components = _standalone_overhaul_components()
    specialist_components = _specialist_residual_components()
    for model_id, components in standalone_components.items():
        models_by_id[model_id]["score_components"] = components
    for model_id, components in specialist_components.items():
        models_by_id[model_id]["score_components"] = components

    money = models_by_id.get("money") or {}
    money["score_components"] = [
        component
        for component in (money.get("score_components") or [])
        if not (
            component.get("kind") == "modifier"
            and component.get("metric") == "benefic_balance"
        )
    ]

    for model_id, model in models_by_id.items():
        model.pop("evaluation_strategy", None)
        model["version"] = "2.0.0"
        model["scoring_engine"] = "declarative_components_v2"
        model["score_polarity"] = "higher_is_worse" if model_id in HIGHER_IS_WORSE_MODEL_IDS else "higher_is_better"
        model["status"] = "experimental" if model_id in EXPERIMENTAL_MODEL_IDS else str(model.get("status") or "active")
        if model_id == "risk_pressure":
            model["status"] = "deprecated"
        model["source_status"] = "experimental" if model["status"] == "experimental" else "synthesis"
        if model_id in SPECIALIST_COMPOSITION:
            parent_id, max_abs_residual = SPECIALIST_COMPOSITION[model_id]
            model["composition"] = {
                "mode": "specialist_residual",
                "parent_id": parent_id,
                "parent_weight": SPECIALIST_PARENT_WEIGHT,
                "max_abs_residual": max_abs_residual,
            }
        else:
            model["composition"] = {"mode": "standalone"}

        evidence_policy = json.loads(json.dumps(DEFAULT_EVIDENCE_POLICY))
        if model_id in {"risk_pressure", "health_risk", "accident_prone"}:
            evidence_policy["min_independent_signals"] = 2
        model["evidence_policy"] = evidence_policy
        model["distance_policy"] = {
            "primary_profile": "standard",
            "sensitivity_profiles": ["conservative", "standard", "wide"],
            "note": "Scores expose conservative, standard, and wide distance sensitivity; the standard profile is not a probability claim.",
        }
        normalization = dict(model.get("normalization") or {})
        normalization["method"] = "bounded_linear"
        normalization["neutral_score"] = 50
        model["normalization"] = normalization

        seen_component_ids: set[str] = set()
        for index, component in enumerate(model.get("score_components") or [], start=1):
            component_id = f"{model_id}.{str(component.get('kind') or 'component')}.{index:02d}"
            if component_id in seen_component_ids:
                raise RuntimeError(f"Duplicate generated component id: {component_id}")
            seen_component_ids.add(component_id)
            component["component_id"] = component_id
            component["source_status"] = (
                "experimental"
                if model["status"] == "experimental"
                else str(component.get("source_status") or "synthesis")
            )
            component["evidence_role"] = str(component.get("evidence_role") or "local")
            component.setdefault("evidence_refs", [])
            if component.get("kind") == "crossing":
                component.setdefault("interaction_scale", 0.5)

        extended_bodies = sorted(_model_bodies(model) - CANONICAL_ACG_BODIES)
        model["body_scope"] = "extended" if extended_bodies else "canonical_ten"
        if extended_bodies:
            not_scored = ["South Node"] if "North Node" in extended_bodies and "South Node" not in extended_bodies else []
            model["extended_body_policy"] = {
                "status": "experimental",
                "supported": extended_bodies,
                "not_scored": not_scored,
                "note": "The ten classical planetary lines are canonical. Nodes and Chiron are explicitly experimental extensions; an unlisted counterpart is not silently inferred.",
            }
        else:
            model.pop("extended_body_policy", None)

    for specialist_id, (parent_id, _max_abs_residual) in SPECIALIST_COMPOSITION.items():
        models_by_id[specialist_id]["normalization"] = json.loads(
            json.dumps(models_by_id[parent_id]["normalization"])
        )

    speculation = models_by_id.get("gambling_luck") or {}
    speculation["label"] = "Speculation Themes"
    speculation["summary"] = "Research-only interpretation of speculative-place themes; it does not predict wins, payouts, or financial outcomes."
    speculation["description"] = "Experimental residual over the broader money model. Only local 5th-house symbolism differentiates places; natal pattern geometry is exposed as a non-ranking global prior."

    for model_id, label, summary in (
        ("health_risk", "Health Caution Themes", "Research-only interpretive bodily-pressure themes; not medical advice or prediction."),
        ("accident_prone", "Acute Disruption Themes", "Research-only acute-disruption themes; not a safety forecast or accident probability."),
        ("travel_fun", "Travel Enjoyment Themes", "Experimental pleasure-travel interpretation pending independent destination validation."),
        ("travel_relax", "Restorative Travel Themes", "Experimental restorative-travel interpretation pending independent destination validation."),
    ):
        models_by_id[model_id]["label"] = label
        models_by_id[model_id]["summary"] = summary


def build_payload() -> Dict[str, Any]:
    payload = _load_source_payload()
    models_by_id = {
        str(model.get("id") or "").strip().lower(): model
        for model in payload.get("models") or []
        if isinstance(model, dict) and str(model.get("id") or "").strip()
    }
    for model in _patched_core_models(models_by_id):
        models_by_id[str(model["id"]).strip().lower()] = model
    for model in _new_models():
        model_id = str(model["id"]).strip().lower()
        models_by_id[model_id] = model
    _apply_model_overhaul(models_by_id)
    payload["schema_version"] = SCHEMA_VERSION
    payload["generated_on"] = str(date.today())
    payload["generator"] = "scripts/build_astrocartography_goal_models.py"
    payload["models"] = list(models_by_id.values())
    _validate_payload(payload)
    return payload


def _validate_payload(payload: Dict[str, Any]) -> None:
    models = {
        str(model.get("id") or "").strip().lower(): model
        for model in payload.get("models") or []
        if isinstance(model, dict) and str(model.get("id") or "").strip()
    }
    missing = sorted(REQUIRED_MODEL_IDS - set(models))
    if missing:
        raise RuntimeError(f"Refusing to write incomplete astrocartography goal payload; missing models: {', '.join(missing)}")
    unexpected = sorted(set(models) - REQUIRED_MODEL_IDS)
    if unexpected:
        raise RuntimeError(f"Refusing to write unknown astrocartography goal models: {', '.join(unexpected)}")

    for model_id in HIGHER_IS_WORSE_MODEL_IDS:
        model = models.get(model_id) or {}
        if str(model.get("score_polarity") or "").strip().lower() != "higher_is_worse":
            raise RuntimeError(f"Refusing to write {model_id} without higher_is_worse score polarity")

    import sys

    backend_path = str(ROOT / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from astrocartography_goal_models import validate_goal_model_payload

    schema = json.loads(
        (ROOT / "backend" / "knowledge" / "astrocartography" / "place_goal_model.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate_goal_model_payload(payload, schema=schema)


def main() -> None:
    payload = build_payload()
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    for path in OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"Wrote {len(payload.get('models') or [])} astrocartography goal models to {', '.join(str(path) for path in OUTPUT_PATHS)}")


if __name__ == "__main__":
    main()
