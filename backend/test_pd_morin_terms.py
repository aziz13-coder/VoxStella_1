from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent))

from pd_morin import current_bound


EGYPTIAN_BOUNDS = {
    "Aries": [("Jupiter", 6), ("Venus", 6), ("Mercury", 8), ("Mars", 5), ("Saturn", 5)],
    "Taurus": [("Venus", 8), ("Mercury", 6), ("Jupiter", 8), ("Saturn", 5), ("Mars", 3)],
    "Gemini": [("Mercury", 6), ("Jupiter", 6), ("Venus", 5), ("Mars", 7), ("Saturn", 6)],
    "Cancer": [("Mars", 7), ("Venus", 6), ("Mercury", 6), ("Jupiter", 7), ("Saturn", 4)],
    "Leo": [("Jupiter", 6), ("Venus", 5), ("Saturn", 7), ("Mercury", 6), ("Mars", 6)],
    "Virgo": [("Mercury", 7), ("Venus", 10), ("Jupiter", 4), ("Mars", 7), ("Saturn", 2)],
    "Libra": [("Saturn", 6), ("Mercury", 8), ("Jupiter", 7), ("Venus", 7), ("Mars", 2)],
    "Scorpio": [("Mars", 7), ("Venus", 4), ("Mercury", 8), ("Jupiter", 5), ("Saturn", 6)],
    "Sagittarius": [("Jupiter", 12), ("Venus", 5), ("Mercury", 4), ("Saturn", 5), ("Mars", 4)],
    "Capricorn": [("Mercury", 7), ("Jupiter", 7), ("Venus", 8), ("Saturn", 4), ("Mars", 4)],
    "Aquarius": [("Mercury", 7), ("Venus", 6), ("Jupiter", 7), ("Mars", 5), ("Saturn", 5)],
    "Pisces": [("Venus", 12), ("Jupiter", 4), ("Mercury", 3), ("Mars", 9), ("Saturn", 2)],
}


@pytest.mark.parametrize(("sign", "sequence"), EGYPTIAN_BOUNDS.items())
def test_current_bound_matches_every_egyptian_boundary(sign, sequence):
    start = 0.0
    for ruler, length in sequence:
        end = start + length
        midpoint = (start + end) / 2.0

        assert current_bound(sign, start) == {
            "lord": ruler,
            "start_deg": start,
            "end_deg": end,
        }
        assert current_bound(sign, midpoint)["lord"] == ruler
        assert current_bound(sign, end - 1e-9)["lord"] == ruler
        start = end

    assert start == 30.0


def test_current_bound_moves_to_the_next_ruler_on_an_exact_boundary():
    assert current_bound("Leo", 6.0) == {
        "lord": "Venus",
        "start_deg": 6.0,
        "end_deg": 11.0,
    }
    assert current_bound("Sagittarius", 26.0) == {
        "lord": "Mars",
        "start_deg": 26.0,
        "end_deg": 30.0,
    }
