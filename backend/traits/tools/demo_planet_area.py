#!/usr/bin/env python3
# Minimal demo to exercise the new planet_area and sect conditions in TraitEngine.

from __future__ import annotations

from typing import Any, Dict

import json

try:
    from traits.engine import TraitEngine
except Exception:
    # Allow running from repo root as a script
    import sys
    sys.path.append('backend')
    from traits.engine import TraitEngine  # type: ignore


def main() -> None:
    # Fake minimal metrics just to trigger Jupiter generosity boosts
    metrics: Dict[str, Any] = {
        'planet_status': {
            'Jupiter': {'strong': True, 'dignified': True, 'afflicted': False},
            'Sun': {'strong': True, 'dignified': False, 'afflicted': False},
            'Venus': {'strong': True, 'dignified': False, 'afflicted': False},
        },
        'planet_signs': {'Jupiter': 'Pisces'},
        'sign_emphasis': {'Libra': 2.0},
        'planet_area_scores': {
            'Jupiter': {'wealth': 0.75, 'friends': 0.65},
        },
        'sect': {
            'benefic_of_sect': 'Jupiter',
            'planets': [
                {'planet': 'Jupiter', 'in_sect': True, 'hayz': False},
            ],
        },
    }
    eng = TraitEngine()
    out = eng.evaluate(metrics, limit=5, min_score=10)
    print(json.dumps({
        'top_traits': out.get('top_traits'),
    }, indent=2))


if __name__ == '__main__':
    main()

