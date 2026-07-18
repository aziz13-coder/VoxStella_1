from pathlib import Path
import sys

import pytest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.reception import TraditionalReceptionCalculator
from backend.models import Planet, Sign


TRIPLICITY_CASES = (
    (
        (Sign.ARIES, Sign.LEO, Sign.SAGITTARIUS),
        Planet.SUN,
        Planet.JUPITER,
    ),
    (
        (Sign.TAURUS, Sign.VIRGO, Sign.CAPRICORN),
        Planet.VENUS,
        Planet.MOON,
    ),
    (
        (Sign.GEMINI, Sign.LIBRA, Sign.AQUARIUS),
        Planet.SATURN,
        Planet.MERCURY,
    ),
    (
        (Sign.CANCER, Sign.SCORPIO, Sign.PISCES),
        Planet.VENUS,
        Planet.MARS,
    ),
)


@pytest.mark.parametrize(("signs", "day_ruler", "night_ruler"), TRIPLICITY_CASES)
def test_triplicity_rulers_follow_sect_for_every_element(
    signs: tuple[Sign, ...],
    day_ruler: Planet,
    night_ruler: Planet,
) -> None:
    calculator = TraditionalReceptionCalculator()

    for sign in signs:
        assert calculator._has_triplicity_dignity(day_ruler, sign, is_day=True)
        assert not calculator._has_triplicity_dignity(
            night_ruler, sign, is_day=True
        )
        assert calculator._has_triplicity_dignity(
            night_ruler, sign, is_day=False
        )
        assert not calculator._has_triplicity_dignity(
            day_ruler, sign, is_day=False
        )
