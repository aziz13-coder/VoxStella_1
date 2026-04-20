"""Election scoring facade.

This module re-exports isolated election model scorers from
`backend/election_models`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from election_models.common import Score  # stable dataclass

# New isolated implementations
from election_models.contract import score_contract_election
from election_models.surgery import score_surgery_election
from election_models.marriage import score_marriage_election
from election_models.marriage_beta import score_marriage_beta_election
from election_models.business import score_business_election
from election_models.business_beta import score_business_beta_election
from election_models.journey import score_journey_election
from election_models.haircut import score_haircut_election
from election_models.viral_content import score_viral_content_election
from election_models.legal import score_legal_election
from election_models.battle import score_battle_election
from election_models.conception import score_conception_election
from election_models.beautification import score_beautification_election

__all__ = [
    'Score',
    'score_marriage_election',
    'score_marriage_beta_election',
    'score_surgery_election',
    'score_contract_election',
    'score_business_election',
    'score_business_beta_election',
    'score_journey_election',
    'score_haircut_election',
    'score_viral_content_election',
    'score_legal_election',
    'score_battle_election',
    'score_conception_election',
    'score_beautification_election',
]
