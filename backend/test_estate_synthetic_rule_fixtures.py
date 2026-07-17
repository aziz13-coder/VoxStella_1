from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import election_models.estate as estate


def _houses(start=0.0):
    return [((start + i * 30.0) % 360.0) for i in range(12)]


def _planet(lon, *, house=None, speed=1.0):
    row = {"longitude": float(lon), "speed": float(speed)}
    if house is not None:
        row["house"] = int(house)
    return row


def _chart(*, houses=None, planets=None, fortune=None):
    return {
        "houses": houses or _houses(),
        "moon_day": {"nid": 7, "interval_tags": []},
        "planets": planets or {},
        "arabic_parts": {"fortune": fortune} if fortune else {},
    }


def _event_score(chart, *, direction="buy", latitude=45.0):
    return estate._score_event_chart(
        chart,
        {
            "estate_direction": direction,
            "event_meta": {"latitude": latitude},
        },
    )


def test_waxing_vs_waning_moon_fixture_tags_and_direction():
    waning_buy = _chart(planets={"Sun": _planet(0), "Moon": _planet(270)})
    waxing_buy = _chart(planets={"Sun": _planet(0), "Moon": _planet(60)})

    waning_score = _event_score(waning_buy, direction="buy")
    waxing_score = _event_score(waxing_buy, direction="buy")

    assert "Event buy Moon phase support: waning (+2.0)" in waning_score.tags
    assert "Event buy Moon phase mismatch: waxing (-1.0)" in waxing_score.tags
    assert waning_score.value > waxing_score.value


def test_rapid_and_slow_sign_latitude_fixture_tags_and_direction():
    rapid_buy = _chart(
        houses=_houses(300),
        planets={"Sun": _planet(0), "Moon": _planet(300)},
    )
    rapid_wrong_direction = _event_score(rapid_buy, direction="sell", latitude=45.0)
    rapid_score = _event_score(rapid_buy, direction="buy", latitude=45.0)

    assert "Event Moon rapid-sign estate support: Aquarius (+3.0)" in rapid_score.tags
    assert "Event Asc rapid-sign estate support: Aquarius (+3.0)" in rapid_score.tags
    assert rapid_score.value > rapid_wrong_direction.value

    slow_sell = _chart(
        houses=_houses(90),
        planets={"Sun": _planet(0), "Moon": _planet(90)},
    )
    slow_wrong_direction = _event_score(slow_sell, direction="buy", latitude=45.0)
    slow_score = _event_score(slow_sell, direction="sell", latitude=45.0)

    assert "Event Moon slow-sign estate support: Cancer (+2.0)" in slow_score.tags
    assert "Event Asc slow-sign estate support: Cancer (+2.0)" in slow_score.tags
    assert slow_score.value > slow_wrong_direction.value


def test_mercury_mars_friction_fixture_tags_and_direction():
    friction = _chart(planets={"Mercury": _planet(10), "Mars": _planet(10)})
    separated = _chart(planets={"Mercury": _planet(10), "Mars": _planet(150)})

    friction_score, friction_tags = estate._score_mercury_mars(estate._collect_planets(friction))
    separated_score, separated_tags = estate._score_mercury_mars(estate._collect_planets(separated))

    assert friction_tags == ["Event Mercury-Mars friction: conjunction/square (-1.5)"]
    assert separated_tags == []
    assert friction_score < separated_score


def test_second_ruler_vs_seventh_ruler_fixture_tags_and_direction():
    custom_cusps = [0, 60, 90, 120, 150, 180, 240, 270, 300, 330, 30, 60]
    tied = _chart(
        houses=custom_cusps,
        planets={"Mercury": _planet(10), "Jupiter": _planet(70)},
    )
    separated = _chart(
        houses=custom_cusps,
        planets={"Mercury": _planet(10), "Jupiter": _planet(145)},
    )

    tied_score, tied_tags = estate._score_counterparty_money_tie(
        estate._collect_planets(tied),
        estate._house_cusps(tied),
    )
    separated_score, separated_tags = estate._score_counterparty_money_tie(
        estate._collect_planets(separated),
        estate._house_cusps(separated),
    )

    assert tied_tags == ["Event counterparty tie caution: 2nd ruler sextile 7th ruler (-0.9)"]
    assert separated_tags == []
    assert tied_score < separated_score


def test_fortuna_sagittarius_pisces_fixture_tags_and_direction():
    sagittarius = _chart(fortune={"longitude": 250.0, "house": 4})
    neutral = _chart(fortune={"longitude": 10.0, "house": 4})

    sag_lon, sag_house = estate._fortune_payload(sagittarius)
    neutral_lon, neutral_house = estate._fortune_payload(neutral)
    sag_score, sag_tags = estate._score_house_topology(
        estate._collect_planets(sagittarius),
        estate._house_cusps(sagittarius),
        sag_lon,
        sag_house,
    )
    neutral_score, neutral_tags = estate._score_house_topology(
        estate._collect_planets(neutral),
        estate._house_cusps(neutral),
        neutral_lon,
        neutral_house,
    )

    assert "Event Fortuna estate sign support: Sagittarius (+1.0)" in sag_tags
    assert "Event Fortuna estate sign support: Aries (+1.0)" not in neutral_tags
    assert sag_score > neutral_score


def test_benefic_malefic_house_fixture_tags_and_direction():
    property_support = _chart(planets={"Mercury": _planet(95, house=4)})
    property_pressure = _chart(planets={"Mars": _planet(96, house=4)})

    support_score, support_tags = estate._score_house_topology(
        estate._collect_planets(property_support),
        estate._house_cusps(property_support),
        None,
        None,
    )
    pressure_score, pressure_tags = estate._score_house_topology(
        estate._collect_planets(property_pressure),
        estate._house_cusps(property_pressure),
        None,
        None,
    )

    assert support_tags == ["Event Mercury in 4th property support (+1.0)"]
    assert pressure_tags == ["Event angular property pressure: Mars in 4th (-1.1)"]
    assert support_score > pressure_score

    buy_support = _chart(planets={"Venus": _planet(45, house=2)})
    buy_pressure = _chart(planets={"Saturn": _planet(45, house=2)})
    buy_support_score, buy_support_tags = estate._score_direction_branch(
        estate._collect_planets(buy_support),
        estate._house_cusps(buy_support),
        direction="buy",
    )
    buy_pressure_score, buy_pressure_tags = estate._score_direction_branch(
        estate._collect_planets(buy_pressure),
        estate._house_cusps(buy_pressure),
        direction="buy",
    )

    assert "Event buy money set support: Venus in 2nd (+0.8)" in buy_support_tags
    assert "Event buy money set malefic caution: Saturn in 2nd (-0.8)" in buy_pressure_tags
    assert buy_support_score > buy_pressure_score

    sell_support = _chart(planets={"Jupiter": _planet(225, house=8)})
    sell_pressure = _chart(planets={"Saturn": _planet(225, house=8)})
    sell_support_score, sell_support_tags = estate._score_direction_branch(
        estate._collect_planets(sell_support),
        estate._house_cusps(sell_support),
        direction="sell",
    )
    sell_pressure_score, sell_pressure_tags = estate._score_direction_branch(
        estate._collect_planets(sell_pressure),
        estate._house_cusps(sell_pressure),
        direction="sell",
    )

    assert "Event sell transfer set support: Jupiter in 8th (+0.8)" in sell_support_tags
    assert "Event sell transfer set malefic caution: Saturn in 8th (-0.8)" in sell_pressure_tags
    assert sell_support_score > sell_pressure_score


def test_participant_fortuna_asc_and_asc_ruler_moon_fixture_tags_and_direction():
    event_chart = _chart(
        planets={"Moon": _planet(60)},
        fortune={"longitude": 0.0, "house": 1},
    )
    participant_chart = _chart(planets={"Mars": _planet(60)}, houses=_houses(0))

    precision_score, precision_tags = estate._score_participant_fit(
        "Buyer A",
        event_chart,
        participant_chart,
        event_fortuna_lon=0.0,
        precision_safe=True,
    )
    untimed_score, untimed_tags = estate._score_participant_fit(
        "Buyer A",
        event_chart,
        participant_chart,
        event_fortuna_lon=0.0,
        precision_safe=False,
    )

    assert "Buyer A: Asc ruler conjunction event Moon (+1.25)" in precision_tags
    assert "Buyer A: event Fortuna conjunction participant Asc (+1.20)" in precision_tags
    assert all("participant Asc" not in tag and "event Moon" not in tag for tag in untimed_tags)
    assert precision_score > untimed_score
