# -*- coding: utf-8 -*-
"""
NLG templates for Morin Transit Engine predictions

Based on the knowledge map (backend/morin_engine_knowledge_map.md), this module
provides human-friendly labels and sentences for life areas and event types,
and composes a concise description for a transit hit using:
- transiting planet, aspect, target
- prediction.lifeArea / prediction.eventType
- concordance (PD/SR/LR) cues
- enriched keywords (optional)
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List


LIFE_AREA_LABELS = {
    'life': 'life and physical vitality',
    'wealth': 'wealth and acquired goods',
    'money': 'wealth and acquired goods',
    'short_travel': 'brothers, relations, and short journeys',
    'short_journeys': 'brothers, relations, and short journeys',
    'home': 'parents, home, and inheritances',
    'children': 'children and bodily pleasures',
    'health': 'illness, service, and subordinates',
    'relationships': 'marriage, contracts, lawsuits, and open enemies',
    'marriage': 'marriage and binding unions',
    'death': 'death and mortality',
    'belief': 'religion and journeys',
    'honors': 'action, profession, dignity, and fame',
    'career': 'action, profession, dignity, and fame',
    'friends': 'friends',
    'shared_resources': 'inheritance, debts, and shared burdens',
    'secrets': 'seclusion, exile, or hidden adversity',
}


EVENT_TEMPLATES = {
    'promotion': 'advancement or elevation in office',
    'recognition': 'fame, recognition, or public notice',
    'public_recognition': 'public fame or distinction',
    'business_deal': 'a business or contract agreement',
    'contract_signing': 'a contract or agreement',
    'communication_breakthrough': 'a communication breakthrough',
    'romantic_connection': 'a courtship or affectionate attachment',
    'reconciliation': 'reconciliation or renewed accord',
    'financial_gain': 'gain in wealth or income',
    'financial_loss': 'loss of wealth or expense',
    'injury_risk': 'a heightened risk of accidents or injuries',
    'accident_risk': 'a heightened risk of accidents',
    'parties_celebrations': 'celebrations or social events',
    'opportunity_received': 'an opportunity or favor received',
    'protection_granted': 'protection and support',
    'delay_obstruction': 'delays or obstructions',
    'illness_chronic': 'chronic health concerns',
    'fall_from_power': 'a setback or loss of standing',
    'authority_problems': 'conflicts with authority',
    'domestic_happiness': 'domestic happiness',
    'family_joy': 'family joy',
    'domestic_disruption': 'domestic disruption',
    'family_problems': 'family problems',
    'illness_acute': 'an acute illness episode',
    'miscommunication': 'miscommunication or crossed wires',
    'excess_problems': 'excess or overextension problems',
    'structure_established': 'structure established and stability gained',
    'discipline_rewarded': 'discipline rewarded',
    'authority_earned': 'authority earned through perseverance',
    'new_job': 'a new office, role, or appointment',
    'job_loss': 'loss of office or employment',
    'demotion': 'a demotion or loss of standing',
    'degree_completion': 'completion of studies or degree',
    'exam_success': 'success in examination or trial',
    'exam_failure': 'failure or setback in examination',
    'enrollment_admission': 'admission or entrance into study',
    'accident_major': 'a major accident or catastrophe',
    'near_death_experience': 'a near-death experience or brush with mortality',
    'attack_violence': 'a violent attack, assault, or conflict',
    'fire_burn': 'injury from fire or severe burns',
    'drowning_submersion': 'a drowning or submersion danger',
    'fall_from_height': 'a dangerous fall from height',
    'spiritual_awakening': 'a religious or spiritual awakening',
    'religious_conversion': 'a change of religion or faith',
    'pilgrimage': 'a pilgrimage or religious journey',
    'mystical_experience': 'a visionary or mystical experience',
    'publication': 'a publication or issued work',
    'artistic_success': 'artistic distinction or success',
    'discovery_breakthrough': 'a breakthrough discovery or innovation',
    'loss_of_possessions': 'loss of personal possessions or resources',
    'reputation_damage': 'damage to reputation or public standing',
    'war_declaration_offensive': 'offensive war or open-enemy conflict',
    'war_response_defensive': 'defensive war or open-enemy conflict',
    'internal_conflict_war': 'internal conflict or civil discord',
    'property_value_increase': 'an increase in property value or real estate gains',
    'property_value_decrease': 'a decline in property value or real estate losses',
    'speculation_gain': 'gain through speculation or hazard',
    'speculation_loss': 'loss through speculation or hazard',
    'inheritance_windfall': 'inheritance or succession gain',
    'shared_resource_loss': 'loss through debts or shared burdens',
    'business_success': 'business success or expansion',
    'business_failure': 'business failure or setbacks',
    'retirement': 'retirement or stepping down from duties',
    'marriage': 'a marriage or binding union',
    'engagement': 'an engagement or betrothal',
    'divorce': 'a divorce or dissolution of union',
    'separation': 'a separation or estrangement',
    'relationship_conflict': 'partnership conflict or open dispute',
    'betrayal': 'a breach of trust or faith',
    'pregnancy': 'pregnancy or expectancy',
    'family_celebration': 'a family or domestic celebration',
    'family_conflict': 'family conflict or household strife',
    'moving_home': 'a change of home or residence',
    'purchase_property': 'purchase of land, home, or property',
    'lawsuit': 'a lawsuit, legal contest, or open dispute',
    'legal_victory': 'a legal victory or favorable judgment',
    'legal_defeat': 'a legal defeat or adverse ruling',
    'legal_resolution': 'a legal resolution or agreement',
    'settlement': 'a settlement or negotiated agreement',
    'arrest_imprisonment': 'imprisonment or exile',
    'short_journey': 'a short journey or local movement',
    'long_journey': 'a long journey or distant travel',
    'relocation_permanent': 'a permanent change of residence',
    'travel_accident': 'a travel accident or mishap',
    'injury_accident': 'an injury or accident',
    'surgery': 'a surgical procedure or operation',
    'hospitalization': 'a hospital stay or medical confinement',
    'recovery_health': 'recovery from illness',
    'fever': 'a fever or spike in temperature',
}


PLANET_ROLES = {
    'Sun': 'visibility, authority, and creative drive',
    'Moon': 'emotions, the public, and daily life',
    'Mercury': 'information, commerce, and agreements',
    'Venus': 'affection, harmony, and value',
    'Mars': 'action, competition, and heat',
    'Jupiter': 'opportunity, growth, and protection',
    'Saturn': 'structure, limits, and responsibility',
}


ASPECT_TONE = {
    'Conjunction': 'focuses',
    'Trine': 'supports',
    'Sextile': 'assists',
    'Square': 'pressures',
    'Opposition': 'polarizes',
}


_SEVENTH_HOUSE_CONFLICT_EVENTS = {
    'attack_violence',
    'war_declaration_offensive',
    'war_response_defensive',
    'internal_conflict_war',
    'warfare_involvement',
    'enemy_attack',
    'violent_confrontation',
    'lawsuit',
    'legal_victory',
    'legal_defeat',
    'legal_resolution',
    'settlement',
    'relationship_conflict',
}


def _label_area(token: Optional[str], event_token: Optional[str] = None) -> Optional[str]:
    if not token:
        return None
    s = str(token)
    event = str(event_token or '')
    if s in {'relationships', 'marriage'} and event in _SEVENTH_HOUSE_CONFLICT_EVENTS:
        return 'partnerships, contracts, or open enemies'
    return LIFE_AREA_LABELS.get(s, s.replace('_',' '))


def _label_event(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    s = str(token)
    return EVENT_TEMPLATES.get(s, s.replace('_',' '))


def render_prediction(hit: Dict[str, Any]) -> str:
    """Return a human-friendly prediction sentence for a single transit hit."""
    A = str(hit.get('transiting') or '')
    asp = str(hit.get('aspect') or '')
    tgt = str(hit.get('target_label') or hit.get('natal') or '')
    pred = hit.get('prediction') or {}
    area_tok = pred.get('lifeArea')
    event_tok = pred.get('eventType')
    area = _label_area(area_tok, event_tok)
    event = _label_event(event_tok)
    try:
        det_strength = abs(float(hit.get('determination_strength') or 0.0))
    except Exception:
        det_strength = 0.0
    conc = hit.get('concordance') or {}
    try:
        dir_score = float(conc.get('direction_concordance') or 0.0)
    except Exception:
        dir_score = 0.0
    try:
        overall_score = float(conc.get('overall_concordance') or 0.0)
    except Exception:
        overall_score = 0.0
    try:
        solar_score = float(conc.get('solar_score') or 0.0)
    except Exception:
        solar_score = 0.0
    try:
        lunar_score = float(conc.get('lunar_score') or 0.0)
    except Exception:
        lunar_score = 0.0
    strong_prediction = det_strength >= 0.55 and dir_score >= 0.3 and overall_score >= 0.55
    moderate_prediction = det_strength >= 0.35 and overall_score >= 0.4 and (
        dir_score >= 0.15 or solar_score >= 0.35 or lunar_score >= 0.35
    )
    # Tone
    verb = ASPECT_TONE.get(asp, 'touches')
    role = PLANET_ROLES.get(A, '')
    # Drivers
    drivers: List[str] = []
    try:
        c = hit.get('concordance') or {}
        if float(c.get('direction_concordance') or 0.0) > 0:
            for m in (c.get('pd_matches') or []):
                t = str(m.get('type') or '')
                if t:
                    drivers.append(f"PD aligns with {t}")
                    break
        if float(c.get('solar_match') or 0.0) > 0:
            drivers.append('SR theme active')
        if float(c.get('lunar_match') or 0.0) > 0:
            drivers.append('LR theme active')
    except Exception:
        pass
    drv = f" (drivers: {', '.join(drivers)})" if drivers else ''
    # Compose
    if event and area:
        connector = 'indicates' if strong_prediction else ('points to' if moderate_prediction else 'can coincide with')
        return f"{A} {asp} {tgt} {verb} {role}; {connector} {event} in {area}.{drv}"
    if area:
        return f"{A} {asp} {tgt} {verb} {role}; activates {area}.{drv}"
    if event:
        connector = 'suggests' if strong_prediction else ('points toward' if moderate_prediction else 'can point to')
        return f"{A} {asp} {tgt} {verb} {role}; {connector} {event}.{drv}"
    return f"{A} {asp} {tgt} {verb} {role}.{drv}"


__all__ = ['render_prediction']
