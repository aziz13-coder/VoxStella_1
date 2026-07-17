from __future__ import annotations

from typing import Any, Dict, List, Tuple


# UTC instants are derived from the cited local birth records.  Using UTC here
# keeps the benchmark deterministic and avoids historic timezone database drift.
TRAIT_LOGIC_BENCHMARK_CASES: List[Dict[str, Any]] = [
    {
        "case_id": "albert_einstein",
        "label": "Albert Einstein",
        "birth": {
            "datetime": "1879-03-14T10:50:02+00:00",
            "source_local_time": "1879-03-14 11:30 LMT, Ulm",
            "location": "Ulm, Germany",
            "timezone": "Etc/GMT+0",
            "latitude": 48.3984,
            "longitude": 9.9916,
            "house_system_code": "R",
            "source_url": "https://www.astro.com/astro-databank/Einstein%2C_Albert",
            "source_quality": "Astro-Databank indexed Rodden AA",
        },
        "biography_sources": [
            "https://www.nobelprize.org/prizes/physics/1921/einstein/facts/",
            "https://www.nobelprize.org/prizes/physics/1921/einstein/biographical/",
        ],
        "expected_clusters": [
            {
                "cluster_id": "scientific_originality",
                "label": "scientific originality and discovery",
                "trait_ids": ["invention_discovery", "genius_inventive_scientific"],
                "min_score": 35.0,
                "max_summary_rank": 4,
                "rationale": "Nobel biography/facts emphasize theoretical physics, relativity, and photoelectric-effect work.",
            }
        ],
    },
    {
        "case_id": "marie_curie",
        "label": "Marie Curie",
        "birth": {
            "datetime": "1867-11-07T10:36:00+00:00",
            "source_local_time": "1867-11-07 12:00 LMT, Warsaw",
            "location": "Warsaw, Poland",
            "timezone": "Etc/GMT+0",
            "latitude": 52.2297,
            "longitude": 21.0122,
            "house_system_code": "R",
            "source_url": "https://www.astro.com/astro-databank/Curie%2C_Marie",
            "source_quality": "Astro-Databank indexed Rodden AA",
        },
        "biography_sources": [
            "https://www.nobelprize.org/prizes/chemistry/1911/marie-curie/facts/",
            "https://www.nobelprize.org/prizes/chemistry/1911/marie-curie/biographical/",
        ],
        "expected_clusters": [
            {
                "cluster_id": "scientific_research",
                "label": "scientific research and discovery",
                "trait_ids": ["genius_inventive_scientific", "invention_discovery"],
                "min_score": 35.0,
                "max_summary_rank": 6,
                "rationale": "Nobel records emphasize radioactivity research, radium/polonium discovery, and two Nobel prizes.",
            },
            {
                "cluster_id": "discipline_resilience",
                "label": "discipline, work, and resilience",
                "trait_ids": ["industriousness", "perseverance", "endurance"],
                "min_score": 40.0,
                "max_summary_rank": 12,
                "rationale": "Biography notes difficult laboratory conditions, teaching load, continued research, and institution-building.",
            },
        ],
    },
    {
        "case_id": "frida_kahlo",
        "label": "Frida Kahlo",
        "birth": {
            "datetime": "1907-07-06T15:06:39+00:00",
            "source_local_time": "1907-07-06 08:30 LMT, Coyoacan",
            "location": "Coyoacan, Mexico",
            "timezone": "Etc/GMT+0",
            "latitude": 19.3467,
            "longitude": -99.1617,
            "house_system_code": "R",
            "source_url": "https://www.astro.com/astro-databank/Kahlo%2C_Frida",
            "source_quality": "Astro-Databank indexed Rodden AA",
        },
        "biography_sources": [
            "https://www.museofridakahlo.org.mx/wp/wp-content/uploads/2022/08/Biografias-Frida-Kahlo-ingles.pdf",
        ],
        "expected_clusters": [
            {
                "cluster_id": "artistic_imagination",
                "label": "artistic imagination and self-expression",
                "trait_ids": ["imagination", "grace_artistic", "creativity"],
                "min_score": 50.0,
                "max_summary_rank": 10,
                "rationale": "Museum biography emphasizes self-portraiture, folk-art identity, and painting from lived reality.",
            }
        ],
    },
    {
        "case_id": "muhammad_ali",
        "label": "Muhammad Ali",
        "birth": {
            "datetime": "1942-01-18T00:35:00+00:00",
            "source_local_time": "1942-01-17 18:35 CST, Louisville",
            "location": "Louisville, Kentucky",
            "timezone": "Etc/GMT+0",
            "latitude": 38.2527,
            "longitude": -85.7585,
            "house_system_code": "R",
            "source_url": "https://www.astro.com/astro-databank/Ali%2C_Muhammad",
            "source_quality": "Astro-Databank indexed Rodden AA",
        },
        "biography_sources": [
            "https://www.archives.gov/research/african-americans/individuals/muhammad-ali",
            "https://nmaahc.si.edu/explore/stories/float-butterfly",
        ],
        "expected_clusters": [
            {
                "cluster_id": "combative_public_assertion",
                "label": "combative public assertion",
                "trait_ids": ["pugnacity", "warlike", "self_assertion", "frankness"],
                "min_score": 30.0,
                "max_summary_rank": 20,
                "rationale": "Archives/Smithsonian sources emphasize boxing, outspoken public stance, activism, and principled refusal.",
            }
        ],
    },
    {
        "case_id": "eleanor_roosevelt",
        "label": "Eleanor Roosevelt",
        "birth": {
            "datetime": "1884-10-11T16:00:00+00:00",
            "source_local_time": "1884-10-11 11:00 EST, New York",
            "location": "New York, New York",
            "timezone": "Etc/GMT+0",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "house_system_code": "R",
            "source_url": "https://www.astro.com/astro-databank/Roosevelt%2C_Eleanor",
            "source_quality": "Astro-Databank indexed Rodden AA",
        },
        "biography_sources": [
            "https://www.nps.gov/elro/learn/historyculture/udhr.htm",
            "https://home.nps.gov/wori/learn/historyculture/eleanor-roosevelt.htm",
        ],
        "expected_clusters": [
            {
                "cluster_id": "humanitarian_advocacy",
                "label": "humanitarian and justice advocacy",
                "trait_ids": ["humanitarianism", "justice_advocacy"],
                "min_score": 35.0,
                "max_summary_rank": 40,
                "rationale": "NPS sources emphasize human-rights commission leadership and the Universal Declaration of Human Rights.",
            }
        ],
    },
    {
        "case_id": "amelia_earhart",
        "label": "Amelia Earhart",
        "birth": {
            "datetime": "1897-07-25T05:30:00+00:00",
            "source_local_time": "1897-07-24 23:30 CST, Atchison",
            "location": "Atchison, Kansas",
            "timezone": "Etc/GMT+0",
            "latitude": 39.5631,
            "longitude": -95.1216,
            "house_system_code": "R",
            "source_url": "https://www.astro.com/astro-databank/Earhart%2C_Amelia",
            "source_quality": "Astro-Databank indexed Rodden AA",
        },
        "biography_sources": [
            "https://www.nps.gov/articles/amelia-earhart-birthplace.htm",
            "https://sova.si.edu/record/nasm.1991.0003",
        ],
        "expected_clusters": [
            {
                "cluster_id": "pioneering_exploration",
                "label": "pioneering exploration and risk",
                "trait_ids": ["venturesomeness", "travel_inclination", "yearning_for_travel", "recklessness"],
                "min_score": 40.0,
                "max_summary_rank": 70,
                "rationale": "NPS/Smithsonian sources emphasize aviation records, solo Atlantic flight, and around-the-world attempt.",
            }
        ],
    },
]


TRAIT_HOUSE_DETERMINATION_BENCHMARK_CASES: List[Dict[str, Any]] = [
    {
        "case_id": "morin_h1_mars_temperament",
        "label": "Morin H1 Mars temperament determination",
        "case_type": "house_determination",
        "source_basis": [
            "docs/moren_summary.md: planets require location/rulership/aspect determination by house",
            "backend/traits/knowledge/morin_keywords.json: H1 life/temperament; Mars conflict/heat/boldness",
        ],
        "metrics": {
            "sign_emphasis": {"Aries": 2.0},
            "element_balance": {"Fire": 0.5, "Earth": 0.2, "Air": 0.2, "Water": 0.1},
            "modality_balance": {"Cardinal": 0.5, "Fixed": 0.25, "Mutable": 0.25},
            "planet_status": {"Mars": {"strong": True}},
            "house": {"emphasis": {"1": 1.0}, "afflicted": {}},
            "planet_area_scores": {"Mars": {"life": 0.82}},
            "planetary_aspects": [],
        },
        "expected_clusters": [
            {
                "cluster_id": "martial_temperament",
                "label": "Mars determined to H1 self/temperament",
                "trait_ids": ["self_assertion", "pugnacity", "warlike"],
                "min_score": 35.0,
                "required_evidence": ["Mars area[life]"],
                "rationale": "This case should not pass on Aries/Fire alone; it must show Mars specifically determined to H1 life/temperament.",
            }
        ],
    },
    {
        "case_id": "morin_h3_h9_learning_journey_axis",
        "label": "Morin H3/H9 learning and journeys determination",
        "case_type": "house_determination",
        "source_basis": [
            "docs/moren_summary.md: Jupiter multiplied by H9 gives religious devotion or long journeys",
            "backend/traits/knowledge/morin_keywords.json: H3 messages/local movement; H9 religion/journeys/doctrine; Mercury learning/trade; Jupiter faith/increase",
        ],
        "metrics": {
            "sign_emphasis": {"Gemini": 1.6, "Sagittarius": 1.6},
            "element_balance": {"Fire": 0.3, "Earth": 0.1, "Air": 0.45, "Water": 0.15},
            "modality_balance": {"Cardinal": 0.2, "Fixed": 0.2, "Mutable": 0.6},
            "planet_status": {"Mercury": {"strong": True}, "Jupiter": {"strong": True}},
            "house": {"emphasis": {"3": 1.0, "9": 1.0}, "afflicted": {}},
            "planet_area_scores": {
                "Mercury": {"short_travel": 0.76, "belief": 0.5},
                "Jupiter": {"belief": 0.8},
            },
            "planetary_aspects": [],
        },
        "expected_clusters": [
            {
                "cluster_id": "learning_journey_axis",
                "label": "Mercury/Jupiter determined to H3/H9",
                "trait_ids": ["travel_inclination", "yearning_for_travel", "scholarship", "venturesomeness"],
                "min_score": 40.0,
                "required_evidence": ["Mercury area[short_travel]", "Jupiter area[belief]"],
                "rationale": "H3/H9 traits must show the actual Mercury/Jupiter house-topic route, not just a broad mutable or Sagittarius signature.",
            }
        ],
    },
    {
        "case_id": "morin_h4_h5_domestic_children_topics",
        "label": "Morin H4/H5 domestic and children determinations",
        "case_type": "house_determination",
        "source_basis": [
            "backend/traits/knowledge/morin_keywords.json: H4 parents/home/inheritance; H5 children/pleasure/fertility; Moon body/common needs; Venus affection/pleasure",
            "backend/knowledge/basic_analysis_rules.json: Moon/Venus natural support for domestic and fecund topics",
        ],
        "metrics": {
            "sign_emphasis": {"Cancer": 2.0, "Taurus": 1.6},
            "element_balance": {"Fire": 0.1, "Earth": 0.25, "Air": 0.15, "Water": 0.5},
            "modality_balance": {"Cardinal": 0.45, "Fixed": 0.35, "Mutable": 0.2},
            "planet_status": {"Moon": {"strong": True}, "Venus": {"strong": True}, "Jupiter": {"strong": True}},
            "planet_signs": {"Moon": "Cancer", "Venus": "Taurus"},
            "house": {"emphasis": {"4": 1.0, "5": 1.0}, "afflicted": {}},
            "planet_area_scores": {
                "Moon": {"home": 0.86, "children": 0.72},
                "Venus": {"children": 0.78, "home": 0.55},
                "Jupiter": {"children": 0.52, "home": 0.5},
            },
            "planetary_aspects": [],
        },
        "expected_clusters": [
            {
                "cluster_id": "domestic_home_topic",
                "label": "Moon determined to H4 home",
                "trait_ids": ["home_domesticity", "hospitality"],
                "min_score": 45.0,
                "required_evidence": ["Moon area[home]"],
                "rationale": "The home topic must be carried by an H4 determination, not by Cancer/Water alone.",
            },
            {
                "cluster_id": "children_fertility_topic",
                "label": "Moon/Venus determined to H5 children",
                "trait_ids": ["fertility", "hospitality"],
                "min_score": 40.0,
                "required_evidence": ["Moon area[children]", "Venus area[children]"],
                "rationale": "H5 children/fertility needs explicit Moon/Venus area evidence.",
            },
        ],
    },
    {
        "case_id": "morin_h6_h10_service_profession",
        "label": "Morin H6/H10 service and profession determinations",
        "case_type": "house_determination",
        "source_basis": [
            "backend/traits/knowledge/morin_keywords.json: H6 service/labor/illness; H10 action/profession/dignity; Mercury craft/calculation; Saturn endurance/severity",
            "docs/moren_summary.md: planet nature must be particularized by house domain",
        ],
        "metrics": {
            "sign_emphasis": {"Virgo": 1.8, "Capricorn": 1.7},
            "element_balance": {"Fire": 0.1, "Earth": 0.55, "Air": 0.2, "Water": 0.15},
            "modality_balance": {"Cardinal": 0.35, "Fixed": 0.25, "Mutable": 0.4},
            "planet_status": {"Mercury": {"strong": True}, "Saturn": {"strong": True}},
            "house": {"emphasis": {"6": 1.0, "10": 1.0}, "afflicted": {}},
            "planet_area_scores": {
                "Mercury": {"health": 0.75, "honors": 0.54},
                "Saturn": {"health": 0.68, "honors": 0.7},
            },
            "planetary_aspects": [],
        },
        "expected_clusters": [
            {
                "cluster_id": "service_profession_work_topic",
                "label": "Mercury/Saturn determined to H6/H10",
                "trait_ids": ["industriousness", "craftsmanship", "zeal_for_service"],
                "min_score": 35.0,
                "required_evidence": ["Mercury area[health]", "Saturn area[health]"],
                "rationale": "Work traits must show the H6 service/labor route and not only Virgo/Earth/Saturn status.",
            }
        ],
    },
    {
        "case_id": "morin_h2_h11_resources_support",
        "label": "Morin H2/H11 resources and support determinations",
        "case_type": "house_determination",
        "source_basis": [
            "backend/traits/knowledge/morin_keywords.json: H2 wealth/resources; H11 friends/allies/support; Jupiter increase/beneficence; Venus concord/sociability",
            "docs/moren_summary.md: a planet's general nature becomes a specific topic by house multiplication",
        ],
        "metrics": {
            "sign_emphasis": {"Aquarius": 1.7},
            "element_balance": {"Fire": 0.15, "Earth": 0.25, "Air": 0.45, "Water": 0.15},
            "modality_balance": {"Cardinal": 0.25, "Fixed": 0.45, "Mutable": 0.3},
            "planet_status": {"Jupiter": {"strong": True}, "Venus": {"strong": True}},
            "house": {"emphasis": {"2": 1.0, "11": 1.0}, "afflicted": {}},
            "planet_area_scores": {
                "Jupiter": {"wealth": 0.73, "friends": 0.84},
                "Venus": {"friends": 0.62},
            },
            "planetary_aspects": [],
        },
        "expected_clusters": [
            {
                "cluster_id": "benefic_support_resources",
                "label": "Jupiter/Venus determined to H2/H11",
                "trait_ids": ["charity", "friendship_allies"],
                "min_score": 35.0,
                "required_evidence": ["Jupiter area[friends,wealth]", "Venus area[friends]"],
                "rationale": "Benefic social support should show H11/H2 determination evidence instead of only generic Jupiter/Venus strength.",
            }
        ],
    },
    {
        "case_id": "morin_h7_h9_h10_legal_social_office",
        "label": "Morin H7/H9/H10 legal and public office determinations",
        "case_type": "house_determination",
        "source_basis": [
            "backend/traits/knowledge/morin_keywords.json: H7 contracts/lawsuits; H9 doctrine; H10 office/dignity; Jupiter justice/faith/honor; Venus concord",
            "docs/moren_summary.md: specific affairs use the house factors relevant to that affair",
        ],
        "metrics": {
            "sign_emphasis": {"Libra": 1.8, "Aquarius": 1.5},
            "element_balance": {"Fire": 0.15, "Earth": 0.2, "Air": 0.5, "Water": 0.15},
            "modality_balance": {"Cardinal": 0.45, "Fixed": 0.35, "Mutable": 0.2},
            "planet_status": {"Jupiter": {"strong": True}, "Venus": {"strong": True}},
            "house": {"emphasis": {"7": 1.0, "9": 1.0, "10": 1.0, "11": 1.0}, "afflicted": {}},
            "planet_area_scores": {
                "Jupiter": {"belief": 0.8, "relationships": 0.64, "honors": 0.62, "friends": 0.58},
                "Venus": {"relationships": 0.78, "friends": 0.63},
            },
            "planetary_aspects": [],
        },
        "expected_clusters": [
            {
                "cluster_id": "legal_social_office_topic",
                "label": "Jupiter/Venus determined to H7/H9/H10/H11",
                "trait_ids": ["legal_mind", "justice_advocacy", "mediation", "tact"],
                "min_score": 35.0,
                "required_evidence": ["Jupiter area[belief,relationships,honors]", "Venus area[relationships]"],
                "rationale": "Legal and advocacy traits should expose doctrine/contract/alliance determinations, not just Libra/Jupiter ornaments.",
            }
        ],
    },
]


def get_trait_logic_benchmark_cases() -> List[Dict[str, Any]]:
    return [dict(case) for case in TRAIT_LOGIC_BENCHMARK_CASES]


def get_trait_house_determination_benchmark_cases() -> List[Dict[str, Any]]:
    return [dict(case) for case in TRAIT_HOUSE_DETERMINATION_BENCHMARK_CASES]


TRAIT_PUBLIC_FIGURE_BASELINE_ROWS: List[Tuple[str, str, str, str, str, str, str, str, float, float, float, str]] = [
    (
        "gabriel_attal",
        "Gabriel Attal",
        "political_cabinet",
        "France PM / minister, rapid public ascent",
        "AA",
        "1989-03-16T12:35:00+00:00",
        "16/03/1989 13:35",
        "Clamart, France",
        1.0,
        48.80038,
        2.26302,
        "https://arcadia-astrology.com/en/astrodb/attal-gabriel",
    ),
    (
        "elisabeth_borne",
        "Elisabeth Borne",
        "political_cabinet",
        "France PM / technocratic executive",
        "AA",
        "1961-04-18T08:00:00+00:00",
        "18/04/1961 09:00",
        "Paris Arrondissement 15, France",
        1.0,
        48.84120,
        2.30030,
        "https://arcadia-astrology.com/en/astrodb/borne-elisabeth",
    ),
    (
        "emmanuel_macron",
        "Emmanuel Macron",
        "political_cabinet",
        "France president, executive charisma / reform politics",
        "AA",
        "1977-12-21T09:40:00+00:00",
        "21/12/1977 10:40",
        "Amiens, France",
        1.0,
        49.89417,
        2.29570,
        "https://arcadia-astrology.com/en/astrodb/macron-emmanuel",
    ),
    (
        "francois_hollande",
        "Francois Hollande",
        "political_cabinet",
        "France president, institutional party leadership",
        "AA",
        "1954-08-11T23:10:00+00:00",
        "12/08/1954 00:10",
        "Rouen, France",
        1.0,
        49.44046,
        1.09397,
        "https://arcadia-astrology.com/en/astrodb/hollande-francois",
    ),
    (
        "nicolas_sarkozy",
        "Nicolas Sarkozy",
        "political_cabinet",
        "France president / cabinet, confrontational leadership",
        "AA",
        "1955-01-28T21:00:00+00:00",
        "28/01/1955 22:00",
        "Paris, France",
        1.0,
        48.85350,
        2.34839,
        "https://arcadia-astrology.com/en/astrodb/sarkozy-nicolas",
    ),
    (
        "christine_lagarde",
        "Christine Lagarde",
        "political_cabinet",
        "France finance minister / IMF / ECB, institutional finance",
        "AA",
        "1956-01-01T12:40:00+00:00",
        "01/01/1956 13:40",
        "Paris, France",
        1.0,
        48.85350,
        2.34839,
        "https://arcadia-astrology.com/en/astrodb/lagarde-christine",
    ),
    (
        "giorgia_meloni",
        "Giorgia Meloni",
        "political_cabinet",
        "Italy PM, nationalist party leadership",
        "AA",
        "1977-01-15T17:30:00+00:00",
        "15/01/1977 18:30",
        "Rome, Italy",
        1.0,
        41.89332,
        12.48293,
        "https://arcadia-astrology.com/en/astrodb/meloni-giorgia",
    ),
    (
        "silvio_berlusconi",
        "Silvio Berlusconi",
        "political_cabinet",
        "Italy PM, media-business politics",
        "AA",
        "1936-09-29T05:30:00+00:00",
        "29/09/1936 06:30",
        "Milan, Italy",
        1.0,
        45.46419,
        9.18963,
        "https://arcadia-astrology.com/en/astrodb/berlusconi-silvio",
    ),
    (
        "pedro_sanchez",
        "Pedro Sanchez",
        "political_cabinet",
        "Spain PM, party resilience / coalition politics",
        "AA",
        "1972-02-29T09:25:00+00:00",
        "29/02/1972 10:25",
        "Madrid, Spain",
        1.0,
        40.41678,
        -3.70351,
        "https://arcadia-astrology.com/en/astrodb/sanchez-pedro",
    ),
    (
        "jose_maria_aznar",
        "Jose Maria Aznar",
        "political_cabinet",
        "Spain PM, conservative executive leadership",
        "AA",
        "1953-02-25T06:00:00+00:00",
        "25/02/1953 07:00",
        "Madrid, Spain",
        1.0,
        40.41678,
        -3.70351,
        "https://arcadia-astrology.com/en/astrodb/aznar-jose-maria",
    ),
    (
        "tony_blair",
        "Tony Blair",
        "political_cabinet",
        "UK PM, persuasive public modernization",
        "AA",
        "1953-05-06T05:10:00+00:00",
        "06/05/1953 06:10",
        "Edinburgh, Scotland",
        1.0,
        55.95335,
        -3.18837,
        "https://arcadia-astrology.com/en/astrodb/blair-tony",
    ),
    (
        "gordon_brown",
        "Gordon Brown",
        "political_cabinet",
        "UK PM / chancellor, fiscal governance",
        "AA",
        "1951-02-20T08:40:00+00:00",
        "20/02/1951 08:40",
        "Giffnock, Scotland",
        0.0,
        55.80394,
        -4.29296,
        "https://arcadia-astrology.com/en/astrodb/brown-gordon",
    ),
    (
        "winston_churchill",
        "Winston Churchill",
        "political_cabinet",
        "UK PM, wartime rhetoric / endurance",
        "A",
        "1874-11-30T01:30:00+00:00",
        "30/11/1874 01:30",
        "Woodstock, England",
        0.0,
        51.84749,
        -1.35453,
        "https://arcadia-astrology.com/en/astrodb/churchill-winston",
    ),
    (
        "margaret_thatcher",
        "Margaret Thatcher",
        "political_cabinet",
        "UK PM, ideological firmness / executive discipline",
        "A",
        "1925-10-13T09:00:00+00:00",
        "13/10/1925 09:00",
        "Grantham, England",
        0.0,
        52.91319,
        -0.64390,
        "https://arcadia-astrology.com/en/astrodb/thatcher-margaret",
    ),
    (
        "boris_johnson",
        "Boris Johnson",
        "political_cabinet",
        "UK PM, populist communication / controversy",
        "A",
        "1964-06-19T18:00:00+00:00",
        "19/06/1964 14:00",
        "New York, New York",
        -4.0,
        40.71273,
        -74.00602,
        "https://arcadia-astrology.com/en/astrodb/johnson-boris",
    ),
    (
        "mark_rutte",
        "Mark Rutte",
        "political_cabinet",
        "Netherlands PM, pragmatic coalition endurance",
        "A",
        "1967-02-14T17:53:00+00:00",
        "14/02/1967 18:53",
        "The Hague, Netherlands",
        1.0,
        52.07998,
        4.31135,
        "https://arcadia-astrology.com/en/astrodb/rutte-mark",
    ),
    (
        "viktor_orban",
        "Viktor Orban",
        "political_cabinet",
        "Hungary PM, centralized nationalist power",
        "A",
        "1963-05-31T13:00:00+00:00",
        "31/05/1963 14:00",
        "Szekesfehervar, Hungary",
        1.0,
        47.19102,
        18.41081,
        "https://arcadia-astrology.com/en/astrodb/orban-viktor",
    ),
    (
        "justin_trudeau",
        "Justin Trudeau",
        "political_cabinet",
        "Canada PM, dynastic public leadership",
        "A",
        "1971-12-26T02:27:00+00:00",
        "25/12/1971 21:27",
        "Ottawa, Ontario, Canada",
        -5.0,
        45.42088,
        -75.69011,
        "https://arcadia-astrology.com/en/astrodb/trudeau-justin",
    ),
    (
        "brian_mulroney",
        "Brian Mulroney",
        "political_cabinet",
        "Canada PM, negotiation / trade politics",
        "AA",
        "1939-03-21T03:17:00+00:00",
        "20/03/1939 22:17",
        "Baie-Comeau, Quebec, Canada",
        -5.0,
        49.21184,
        -68.18014,
        "https://arcadia-astrology.com/en/astrodb/mulroney-brian",
    ),
    (
        "jean_chretien",
        "Jean Chretien",
        "political_cabinet",
        "Canada PM, retail politics / resilience",
        "A",
        "1934-01-11T07:45:00+00:00",
        "11/01/1934 02:45",
        "Shawinigan, Quebec, Canada",
        -5.0,
        46.53966,
        -72.75186,
        "https://arcadia-astrology.com/en/astrodb/chretien-jean",
    ),
    (
        "kim_campbell",
        "Kim Campbell",
        "political_cabinet",
        "Canada PM / cabinet, short high-office tenure",
        "A",
        "1947-03-10T19:00:00+00:00",
        "10/03/1947 11:00",
        "Port Alberni, British Columbia, Canada",
        -8.0,
        49.23437,
        -124.80565,
        "https://arcadia-astrology.com/en/astrodb/campbell-kim",
    ),
    (
        "tony_abbott",
        "Tony Abbott",
        "political_cabinet",
        "Australia PM, combative conservative politics",
        "A",
        "1957-11-04T04:00:00+00:00",
        "04/11/1957 04:00",
        "London, England",
        0.0,
        51.50745,
        -0.12777,
        "https://arcadia-astrology.com/en/astrodb/abbott-tony",
    ),
    (
        "helen_clark",
        "Helen Clark",
        "political_cabinet",
        "New Zealand PM, administrative endurance",
        "A",
        "1950-02-26T07:30:00+00:00",
        "26/02/1950 19:30",
        "Hamilton, New Zealand",
        12.0,
        -37.78788,
        175.28179,
        "https://arcadia-astrology.com/en/astrodb/clark-helen",
    ),
    (
        "john_howard",
        "John Howard",
        "political_cabinet",
        "Australia PM, long conservative tenure",
        "A",
        "1939-07-25T16:00:00+00:00",
        "26/07/1939 02:00",
        "Sydney, Australia",
        10.0,
        -33.86984,
        151.20828,
        "https://arcadia-astrology.com/en/astrodb/howard-john",
    ),
    (
        "indira_gandhi",
        "Indira Gandhi",
        "political_cabinet",
        "India PM, central authority / crisis leadership",
        "A",
        "1917-11-19T17:41:00+00:00",
        "19/11/1917 23:11",
        "Allahabad, India",
        5.5,
        25.43813,
        81.83380,
        "https://arcadia-astrology.com/en/astrodb/gandhi-indira",
    ),
    (
        "jawaharlal_nehru",
        "Jawaharlal Nehru",
        "political_cabinet",
        "India PM, founding statesmanship / intellectual politics",
        "A",
        "1889-11-14T18:09:00+00:00",
        "14/11/1889 23:30",
        "Allahabad, India",
        5.35,
        25.43813,
        81.83380,
        "https://arcadia-astrology.com/en/astrodb/nehru-jawaharlal",
    ),
    (
        "rajiv_gandhi",
        "Rajiv Gandhi",
        "political_cabinet",
        "India PM, dynastic modernization politics",
        "AA",
        "1944-08-20T01:42:40+00:00",
        "20/08/1944 06:34",
        "Mumbai, India",
        4.85555555555556,
        19.05500,
        72.86920,
        "https://arcadia-astrology.com/en/astrodb/gandhi-rajiv",
    ),
    (
        "corazon_aquino",
        "Corazon Aquino",
        "political_cabinet",
        "Philippines president, democratic restoration",
        "AA",
        "1933-01-25T13:45:00+00:00",
        "25/01/1933 21:45",
        "Manila, Philippines",
        8.0,
        14.59045,
        120.98036,
        "https://arcadia-astrology.com/en/astrodb/aquino-corazon",
    ),
    (
        "benigno_aquino_iii",
        "Benigno Aquino III",
        "political_cabinet",
        "Philippines president, reformist dynastic leadership",
        "AA",
        "1960-02-08T02:28:00+00:00",
        "08/02/1960 10:28",
        "Manila, Philippines",
        8.0,
        14.59045,
        120.98036,
        "https://arcadia-astrology.com/en/astrodb/aquino-benigno-iii",
    ),
    (
        "michelle_bachelet",
        "Michelle Bachelet",
        "political_cabinet",
        "Chile president / health and defense minister",
        "AA",
        "1951-09-29T04:10:00+00:00",
        "29/09/1951 00:10",
        "Santiago, Chile",
        -4.0,
        -33.43770,
        -70.65107,
        "https://arcadia-astrology.com/en/astrodb/bachelet-michelle",
    ),
    (
        "salvador_allende",
        "Salvador Allende",
        "political_cabinet",
        "Chile president, ideological reform / crisis",
        "AA",
        "1908-06-26T06:12:40+00:00",
        "26/06/1908 01:30",
        "Santiago, Chile",
        -4.71111111111111,
        -33.43770,
        -70.65107,
        "https://arcadia-astrology.com/en/astrodb/allende-salvador",
    ),
    (
        "gabriel_boric",
        "Gabriel Boric",
        "political_cabinet",
        "Chile president, youth-left coalition politics",
        "AA",
        "1986-02-11T16:07:00+00:00",
        "11/02/1986 13:07",
        "Punta Arenas, Chile",
        -3.0,
        -53.16257,
        -70.90782,
        "https://arcadia-astrology.com/en/astrodb/boric-gabriel",
    ),
    (
        "andres_manuel_lopez_obrador",
        "Andres Manuel Lopez Obrador",
        "political_cabinet",
        "Mexico president, populist anti-establishment politics",
        "AA",
        "1953-11-13T08:00:00+00:00",
        "13/11/1953 02:00",
        "Macuspana, Mexico",
        -6.0,
        17.85568,
        -92.42239,
        "https://arcadia-astrology.com/en/astrodb/lopez-obrador-andres-manuel",
    ),
    (
        "hugo_chavez",
        "Hugo Chavez",
        "political_cabinet",
        "Venezuela president, charismatic revolutionary politics",
        "AA",
        "1954-07-28T06:30:00+00:00",
        "28/07/1954 02:00",
        "Sabaneta, Venezuela",
        -4.5,
        8.75293,
        -69.93454,
        "https://arcadia-astrology.com/en/astrodb/chavez-hugo",
    ),
    (
        "javier_milei",
        "Javier Milei",
        "political_cabinet",
        "Argentina president, anti-establishment disruption",
        "AA",
        "1970-10-23T02:59:00+00:00",
        "22/10/1970 23:59",
        "Buenos Aires, Argentina",
        -3.0,
        -34.60956,
        -58.38879,
        "https://arcadia-astrology.com/en/astrodb/milei-javier",
    ),
    (
        "alberto_fujimori",
        "Alberto Fujimori",
        "political_cabinet",
        "Peru president, technocratic authoritarian crisis",
        "AA",
        "1938-07-28T06:20:00+00:00",
        "28/07/1938 01:20",
        "Lima, Peru",
        -5.0,
        -12.04598,
        -77.03059,
        "https://arcadia-astrology.com/en/astrodb/fujimori-alberto",
    ),
    (
        "jair_bolsonaro",
        "Jair Bolsonaro",
        "political_cabinet",
        "Brazil president, military-populist confrontation",
        "AA",
        "1955-03-21T17:45:00+00:00",
        "21/03/1955 14:45",
        "Glicerio, Sao Paulo, Brazil",
        -3.0,
        -21.38120,
        -50.21230,
        "https://arcadia-astrology.com/en/astrodb/bolsonaro-jair",
    ),
    (
        "volodymyr_zelenskyy",
        "Volodymyr Zelenskyy",
        "political_cabinet",
        "Ukraine president, performer-to-wartime leadership",
        "A",
        "1978-01-25T11:00:00+00:00",
        "25/01/1978 14:00",
        "Kryvyi Rih, Ukraine",
        3.0,
        47.91027,
        33.39177,
        "https://arcadia-astrology.com/en/astrodb/zelensky-volodymyr",
    ),
    (
        "donald_trump",
        "Donald Trump",
        "political_cabinet",
        "US president, celebrity-populist executive style",
        "AA",
        "1946-06-14T14:54:00+00:00",
        "14/06/1946 10:54",
        "Jamaica Hospital Queens, New York",
        -4.0,
        40.70037,
        -73.81650,
        "https://arcadia-astrology.com/en/astrodb/trump-donald",
    ),
    (
        "barack_obama",
        "Barack Obama",
        "political_cabinet",
        "US president, rhetorical coalition leadership",
        "AA",
        "1961-08-05T05:24:00+00:00",
        "04/08/1961 19:24",
        "Honolulu, Hawaii",
        -10.0,
        21.30455,
        -157.85568,
        "https://arcadia-astrology.com/en/astrodb/obama-barack",
    ),
    (
        "joe_biden",
        "Joe Biden",
        "political_cabinet",
        "US president, institutional persistence",
        "A",
        "1942-11-20T12:30:00+00:00",
        "20/11/1942 08:30",
        "Scranton, Pennsylvania",
        -4.0,
        41.40869,
        -75.66213,
        "https://arcadia-astrology.com/en/astrodb/biden-joe",
    ),
    (
        "bill_clinton",
        "Bill Clinton",
        "political_cabinet",
        "US president, interpersonal persuasion",
        "A",
        "1946-08-19T14:51:00+00:00",
        "19/08/1946 08:51",
        "Hope, Arkansas",
        -6.0,
        33.66706,
        -93.59157,
        "https://arcadia-astrology.com/en/astrodb/clinton-bill",
    ),
    (
        "kamala_harris",
        "Kamala Harris",
        "political_cabinet",
        "US vice president, prosecutor-to-executive path",
        "AA",
        "1964-10-21T04:28:00+00:00",
        "20/10/1964 21:28",
        "Oakland, California",
        -7.0,
        37.80446,
        -122.27136,
        "https://arcadia-astrology.com/en/astrodb/harris-kamala",
    ),
    (
        "george_w_bush",
        "George W. Bush",
        "political_cabinet",
        "US president, executive decisiveness / crisis",
        "AA",
        "1946-07-06T11:26:00+00:00",
        "06/07/1946 07:26",
        "New Haven, Connecticut",
        -4.0,
        41.30821,
        -72.92505,
        "https://arcadia-astrology.com/en/astrodb/bush-george-w",
    ),
    (
        "franklin_d_roosevelt",
        "Franklin D. Roosevelt",
        "political_cabinet",
        "US president, crisis governance / endurance",
        "AA",
        "1882-01-31T01:40:44+00:00",
        "30/01/1882 20:45",
        "Hyde Park, New York",
        -4.92888888888889,
        41.78420,
        -73.93739,
        "https://arcadia-astrology.com/en/astrodb/roosevelt-franklin-d",
    ),
    (
        "john_f_kennedy",
        "John F. Kennedy",
        "political_cabinet",
        "US president, charisma / crisis symbolism",
        "A",
        "1917-05-29T20:00:00+00:00",
        "29/05/1917 15:00",
        "Brookline, Massachusetts",
        -5.0,
        42.33292,
        -71.11878,
        "https://arcadia-astrology.com/en/astrodb/kennedy-john-f",
    ),
    (
        "dick_cheney",
        "Dick Cheney",
        "political_cabinet",
        "US vice president / defense secretary, hard-power executive",
        "AA",
        "1941-01-31T01:30:00+00:00",
        "30/01/1941 19:30",
        "Lincoln, Nebraska",
        -6.0,
        40.80889,
        -96.70778,
        "https://arcadia-astrology.com/en/astrodb/cheney-dick",
    ),
    (
        "henry_kissinger",
        "Henry Kissinger",
        "political_cabinet",
        "US secretary of state, strategic diplomacy",
        "AA",
        "1923-05-27T04:30:00+00:00",
        "27/05/1923 05:30",
        "Furth, Germany",
        1.0,
        49.48857,
        10.95872,
        "https://arcadia-astrology.com/en/astrodb/kissinger-henry",
    ),
    (
        "donald_rumsfeld",
        "Donald Rumsfeld",
        "political_cabinet",
        "US defense secretary, bureaucratic hard power",
        "AA",
        "1932-07-09T23:40:00+00:00",
        "09/07/1932 17:40",
        "Chicago, Illinois",
        -6.0,
        41.87556,
        -87.62442,
        "https://arcadia-astrology.com/en/astrodb/rumsfeld-donald",
    ),
    (
        "albert_einstein",
        "Albert Einstein",
        "famous_control",
        "scientific originality / discovery",
        "AA",
        "1879-03-14T10:50:00+00:00",
        "14/03/1879 11:30",
        "Ulm, Germany",
        0.666666666666667,
        48.39850,
        9.99125,
        "https://arcadia-astrology.com/en/astrodb/einstein-albert",
    ),
    (
        "marie_curie",
        "Marie Curie",
        "famous_control",
        "scientific discipline / research endurance",
        "AA",
        "1867-11-07T10:36:00+00:00",
        "07/11/1867 12:00",
        "Warsaw, Poland",
        1.4,
        52.22970,
        21.01220,
        "https://arcadia-astrology.com/en/astrodb/curie-marie",
    ),
    (
        "muhammad_ali",
        "Muhammad Ali",
        "famous_control",
        "combative public assertion / performance",
        "AA",
        "1942-01-18T00:35:00+00:00",
        "17/01/1942 18:35",
        "Louisville, Kentucky",
        -6.0,
        38.25424,
        -85.75941,
        "https://arcadia-astrology.com/en/astrodb/ali-muhammad",
    ),
    (
        "eleanor_roosevelt",
        "Eleanor Roosevelt",
        "famous_control",
        "humanitarian advocacy / public service",
        "AA",
        "1884-10-11T16:00:00+00:00",
        "11/10/1884 11:00",
        "New York, New York",
        -5.0,
        40.71273,
        -74.00602,
        "https://arcadia-astrology.com/en/astrodb/roosevelt-eleanor",
    ),
    (
        "amelia_earhart",
        "Amelia Earhart",
        "famous_control",
        "exploration / risk / public pioneering",
        "AA",
        "1897-07-25T05:30:00+00:00",
        "24/07/1897 23:30",
        "Atchison, Kansas",
        -6.0,
        39.54582,
        -95.33261,
        "https://arcadia-astrology.com/en/astrodb/earhart-amelia",
    ),
    (
        "frida_kahlo",
        "Frida Kahlo",
        "famous_control",
        "artistic imagination / bodily hardship themes",
        "AA",
        "1907-07-06T15:06:40+00:00",
        "06/07/1907 08:30",
        "Coyoacan, Mexico",
        -6.61111111111111,
        19.34670,
        -99.16174,
        "https://arcadia-astrology.com/en/astrodb/kahlo-frida",
    ),
    (
        "oprah_winfrey",
        "Oprah Winfrey",
        "famous_control",
        "media influence / public empathy / wealth creation",
        "A",
        "1954-01-29T10:30:00+00:00",
        "29/01/1954 04:30",
        "Kosciusko, Mississippi",
        -6.0,
        33.05763,
        -89.58758,
        "https://arcadia-astrology.com/en/astrodb/winfrey-oprah",
    ),
    (
        "steve_jobs",
        "Steve Jobs",
        "famous_control",
        "product vision / design control / entrepreneurship",
        "AA",
        "1955-02-25T03:15:00+00:00",
        "24/02/1955 19:15",
        "San Francisco, California",
        -8.0,
        37.78794,
        -122.40752,
        "https://arcadia-astrology.com/en/astrodb/jobs-steve",
    ),
    (
        "bill_gates",
        "Bill Gates",
        "famous_control",
        "software entrepreneurship / philanthropy",
        "A",
        "1955-10-29T06:00:00+00:00",
        "28/10/1955 22:00",
        "Seattle, Washington",
        -8.0,
        47.60383,
        -122.33006,
        "https://arcadia-astrology.com/en/astrodb/gates-bill",
    ),
    (
        "pope_francis",
        "Pope Francis",
        "famous_control",
        "religious leadership / institutional reform",
        "AA",
        "1936-12-18T00:00:00+00:00",
        "17/12/1936 21:00",
        "Buenos Aires, Argentina",
        -3.0,
        -34.60956,
        -58.38879,
        "https://arcadia-astrology.com/en/astrodb/pope-francis",
    ),
    (
        "lionel_messi",
        "Lionel Messi",
        "famous_control",
        "elite athletic mastery / quiet public dominance",
        "AA",
        "1987-06-24T23:30:00+00:00",
        "24/06/1987 20:30",
        "Rosario, Santa Fe, Argentina",
        -3.0,
        -32.92617,
        -60.73907,
        "https://arcadia-astrology.com/en/astrodb/messi-lionel",
    ),
    (
        "lebron_james",
        "LeBron James",
        "famous_control",
        "elite athletic leadership / business expansion",
        "AA",
        "1984-12-30T21:04:00+00:00",
        "30/12/1984 16:04",
        "Akron, Ohio",
        -5.0,
        41.08306,
        -81.51848,
        "https://arcadia-astrology.com/en/astrodb/james-lebron",
    ),
    (
        "serena_williams",
        "Serena Williams",
        "famous_control",
        "competitive dominance / athletic resilience",
        "AA",
        "1981-09-27T00:28:00+00:00",
        "26/09/1981 20:28",
        "Saginaw, Michigan",
        -4.0,
        43.42004,
        -83.94904,
        "https://arcadia-astrology.com/en/astrodb/williams-serena",
    ),
    (
        "roger_federer",
        "Roger Federer",
        "famous_control",
        "elite athletic grace / sustained excellence",
        "A",
        "1981-08-08T06:40:00+00:00",
        "08/08/1981 08:40",
        "Basel, Switzerland",
        2.0,
        47.55811,
        7.58783,
        "https://arcadia-astrology.com/en/astrodb/federer-roger",
    ),
    (
        "david_bowie",
        "David Bowie",
        "famous_control",
        "artistic reinvention / persona fluidity",
        "A",
        "1947-01-08T09:00:00+00:00",
        "08/01/1947 09:00",
        "Brixton, London, England",
        0.0,
        51.46339,
        -0.11480,
        "https://arcadia-astrology.com/en/astrodb/bowie-david",
    ),
    (
        "elvis_presley",
        "Elvis Presley",
        "famous_control",
        "mass celebrity / musical performance",
        "AA",
        "1935-01-08T10:35:00+00:00",
        "08/01/1935 04:35",
        "Tupelo, Mississippi",
        -6.0,
        34.25761,
        -88.70339,
        "https://arcadia-astrology.com/en/astrodb/presley-elvis",
    ),
    (
        "angelina_jolie",
        "Angelina Jolie",
        "famous_control",
        "film celebrity / humanitarian public role",
        "AA",
        "1975-06-04T16:09:00+00:00",
        "04/06/1975 09:09",
        "Los Angeles Cedars of Lebanon, California",
        -7.0,
        34.07516,
        -118.38109,
        "https://arcadia-astrology.com/en/astrodb/jolie-angelina",
    ),
    (
        "robin_williams",
        "Robin Williams",
        "famous_control",
        "comic imagination / emotional expressiveness",
        "AA",
        "1951-07-21T19:34:00+00:00",
        "21/07/1951 13:34",
        "Chicago, Illinois",
        -6.0,
        41.87556,
        -87.62442,
        "https://arcadia-astrology.com/en/astrodb/williams-robin",
    ),
    (
        "tom_hanks",
        "Tom Hanks",
        "famous_control",
        "popular trust / acting range / public steadiness",
        "AA",
        "1956-07-09T18:17:00+00:00",
        "09/07/1956 11:17",
        "Concord, California",
        -7.0,
        37.97685,
        -122.03356,
        "https://arcadia-astrology.com/en/astrodb/hanks-tom",
    ),
]


def _wiki_bio(label: str) -> str:
    return "https://en.wikipedia.org/wiki/" + str(label).strip().replace(" ", "_")


def _bio_cluster(
    cluster_id: str,
    label: str,
    trait_ids: List[str],
    rationale: str,
    *,
    min_score: float = 30.0,
    max_summary_rank: int = 12,
) -> Dict[str, Any]:
    return {
        "cluster_id": cluster_id,
        "label": label,
        "trait_ids": trait_ids,
        "min_score": min_score,
        "max_summary_rank": max_summary_rank,
        "rationale": rationale,
    }


TRAIT_PUBLIC_FIGURE_BIOGRAPHY_EXPECTATIONS: Dict[str, Dict[str, Any]] = {
    "gabriel_attal": {
        "biography_sources": [_wiki_bio("Gabriel Attal")],
        "expected_clusters": [
            _bio_cluster(
                "rapid_executive_ascent",
                "prime-ministerial and ministerial rapid ascent",
                ["leadership_executive", "government_authority", "enterprise_initiative", "capricorn_ambition"],
                "Public biography centers on rapid ascent through ministerial office to prime ministerial leadership.",
            )
        ],
    },
    "elisabeth_borne": {
        "biography_sources": [_wiki_bio("Elisabeth Borne")],
        "expected_clusters": [
            _bio_cluster(
                "technocratic_governance",
                "technocratic executive governance",
                ["responsibility", "precision", "rationality", "organization_capricorn", "government_authority"],
                "Public biography emphasizes engineering, transport, labor, and prime-ministerial administrative roles.",
            )
        ],
    },
    "emmanuel_macron": {
        "biography_sources": [_wiki_bio("Emmanuel Macron")],
        "expected_clusters": [
            _bio_cluster(
                "reform_executive",
                "reformist executive leadership and public persuasion",
                ["leadership_executive", "enterprise_initiative", "zeal_for_reform", "eloquence", "government_authority"],
                "Public biography emphasizes presidential executive power, reform politics, and public persuasion.",
            )
        ],
    },
    "francois_hollande": {
        "biography_sources": [_wiki_bio("Francois Hollande")],
        "expected_clusters": [
            _bio_cluster(
                "institutional_party_leadership",
                "institutional party leadership and mediation",
                ["mediation", "tact", "cooperation", "government_authority", "judgment_sound"],
                "Public biography centers on party leadership, institutional politics, and presidential governance.",
            )
        ],
    },
    "nicolas_sarkozy": {
        "biography_sources": [_wiki_bio("Nicolas Sarkozy")],
        "expected_clusters": [
            _bio_cluster(
                "assertive_executive",
                "assertive and confrontational executive leadership",
                ["self_assertion", "frankness", "pugnacity", "leadership_executive", "government_authority"],
                "Public biography emphasizes high-conflict presidential politics and assertive executive style.",
            )
        ],
    },
    "christine_lagarde": {
        "biography_sources": [_wiki_bio("Christine Lagarde")],
        "expected_clusters": [
            _bio_cluster(
                "institutional_finance",
                "institutional financial judgment",
                ["calculation", "judgment_sound", "rationality", "responsibility", "leadership_executive"],
                "Public biography emphasizes finance ministry, IMF, ECB, and institutional economic leadership.",
            )
        ],
    },
    "giorgia_meloni": {
        "biography_sources": [_wiki_bio("Giorgia Meloni")],
        "expected_clusters": [
            _bio_cluster(
                "conservative_national_leadership",
                "conservative nationalist party leadership",
                ["leadership_executive", "government_authority", "conservatism", "self_assertion", "willfulness"],
                "Public biography emphasizes conservative-national political leadership and prime ministerial office.",
            )
        ],
    },
    "silvio_berlusconi": {
        "biography_sources": [_wiki_bio("Silvio Berlusconi")],
        "expected_clusters": [
            _bio_cluster(
                "media_business_politics",
                "media-business entrepreneurship and political display",
                ["enterprise_initiative", "worldliness", "leadership_executive", "sociability", "kingship_leadership_display"],
                "Public biography centers on media entrepreneurship, wealth, celebrity, and prime-ministerial politics.",
            )
        ],
    },
    "pedro_sanchez": {
        "biography_sources": [_wiki_bio("Pedro Sanchez")],
        "expected_clusters": [
            _bio_cluster(
                "coalition_resilience",
                "coalition politics and resilience",
                ["mediation", "tact", "cooperation", "perseverance", "leadership_executive"],
                "Public biography emphasizes party leadership, coalition governance, and political resilience.",
            )
        ],
    },
    "jose_maria_aznar": {
        "biography_sources": [_wiki_bio("Jose Maria Aznar")],
        "expected_clusters": [
            _bio_cluster(
                "conservative_executive",
                "conservative executive governance",
                ["conservatism", "leadership_executive", "responsibility", "government_authority", "steadiness"],
                "Public biography centers on conservative party leadership and prime-ministerial governance.",
            )
        ],
    },
    "tony_blair": {
        "biography_sources": [_wiki_bio("Tony Blair")],
        "expected_clusters": [
            _bio_cluster(
                "persuasive_modernization",
                "persuasive reform and modernization politics",
                ["eloquence", "zeal_for_reform", "leadership_executive", "sociability", "enterprise_initiative"],
                "Public biography emphasizes New Labour modernization, public persuasion, and executive leadership.",
            )
        ],
    },
    "gordon_brown": {
        "biography_sources": [_wiki_bio("Gordon Brown")],
        "expected_clusters": [
            _bio_cluster(
                "fiscal_governance",
                "fiscal governance and responsibility",
                ["calculation", "responsibility", "rationality", "government_authority", "judgment_sound"],
                "Public biography emphasizes chancellorship, fiscal policy, and prime-ministerial governance.",
            )
        ],
    },
    "winston_churchill": {
        "biography_sources": [_wiki_bio("Winston Churchill")],
        "expected_clusters": [
            _bio_cluster(
                "wartime_leadership",
                "wartime leadership, courage, and rhetoric",
                ["courage_aries", "valor", "fortitude", "leadership_executive", "eloquence"],
                "Public biography emphasizes wartime premiership, public rhetoric, courage, and endurance.",
            )
        ],
    },
    "margaret_thatcher": {
        "biography_sources": [_wiki_bio("Margaret Thatcher")],
        "expected_clusters": [
            _bio_cluster(
                "ideological_firmness",
                "ideological firmness and executive will",
                ["willfulness", "tenacity", "conservatism", "leadership_executive", "self_assertion"],
                "Public biography emphasizes ideological firmness, conservative leadership, and strong executive style.",
            )
        ],
    },
    "boris_johnson": {
        "biography_sources": [_wiki_bio("Boris Johnson")],
        "expected_clusters": [
            _bio_cluster(
                "populist_communication",
                "populist communication and wit",
                ["eloquence", "wit", "humour", "sociability", "self_assertion"],
                "Public biography emphasizes journalism, public communication, populism, and performative politics.",
            )
        ],
    },
    "mark_rutte": {
        "biography_sources": [_wiki_bio("Mark Rutte")],
        "expected_clusters": [
            _bio_cluster(
                "pragmatic_coalition",
                "pragmatic coalition leadership",
                ["mediation", "tact", "cooperation", "responsibility", "perseverance"],
                "Public biography emphasizes long coalition governance and pragmatic prime-ministerial leadership.",
            )
        ],
    },
    "viktor_orban": {
        "biography_sources": [_wiki_bio("Viktor Orban")],
        "expected_clusters": [
            _bio_cluster(
                "centralized_national_power",
                "centralized nationalist power",
                ["government_authority", "domination_capricorn", "conservatism", "leadership_executive", "willfulness"],
                "Public biography emphasizes centralized power, nationalism, and long executive control.",
            )
        ],
    },
    "justin_trudeau": {
        "biography_sources": [_wiki_bio("Justin Trudeau")],
        "expected_clusters": [
            _bio_cluster(
                "public_progressive_leadership",
                "public-facing progressive leadership",
                ["leadership_executive", "sociability", "justice_advocacy", "eloquence", "cooperation"],
                "Public biography emphasizes prime-ministerial leadership, public communication, and liberal-progressive politics.",
            )
        ],
    },
    "brian_mulroney": {
        "biography_sources": [_wiki_bio("Brian Mulroney")],
        "expected_clusters": [
            _bio_cluster(
                "trade_negotiation",
                "negotiation and trade politics",
                [
                    "mediation",
                    "tact",
                    "cooperation",
                    "legal_mind",
                    "leadership_executive",
                    "government_authority",
                    "eloquence",
                    "enterprise_initiative",
                ],
                "Public biography emphasizes trade agreements, party leadership, public persuasion, and prime-ministerial governance.",
            )
        ],
    },
    "jean_chretien": {
        "biography_sources": [_wiki_bio("Jean Chretien")],
        "expected_clusters": [
            _bio_cluster(
                "retail_resilience",
                "retail politics and resilience",
                ["resilience", "perseverance", "sociability", "leadership_executive", "steadiness"],
                "Public biography emphasizes long political survival, retail politics, and prime-ministerial leadership.",
            )
        ],
    },
    "kim_campbell": {
        "biography_sources": [_wiki_bio("Kim Campbell")],
        "expected_clusters": [
            _bio_cluster(
                "cabinet_executive",
                "cabinet and prime-ministerial executive service",
                ["leadership_executive", "government_authority", "enterprise_initiative", "legal_mind", "responsibility"],
                "Public biography emphasizes cabinet office, justice and defense portfolios, and prime-ministerial leadership.",
            )
        ],
    },
    "tony_abbott": {
        "biography_sources": [_wiki_bio("Tony Abbott")],
        "expected_clusters": [
            _bio_cluster(
                "combative_conservatism",
                "combative conservative politics",
                ["pugnacity", "conservatism", "self_assertion", "frankness", "willfulness"],
                "Public biography emphasizes combative conservative party politics and prime-ministerial office.",
            )
        ],
    },
    "helen_clark": {
        "biography_sources": [_wiki_bio("Helen Clark")],
        "expected_clusters": [
            _bio_cluster(
                "administrative_endurance",
                "administrative endurance and responsibility",
                ["responsibility", "organization_capricorn", "perseverance", "leadership_executive", "steadiness"],
                "Public biography emphasizes long prime-ministerial service, administration, and international leadership.",
            )
        ],
    },
    "john_howard": {
        "biography_sources": [_wiki_bio("John Howard")],
        "expected_clusters": [
            _bio_cluster(
                "long_conservative_tenure",
                "long conservative tenure",
                ["conservatism", "perseverance", "steadiness", "leadership_executive", "government_authority"],
                "Public biography emphasizes long conservative prime-ministerial tenure and political steadiness.",
            )
        ],
    },
    "indira_gandhi": {
        "biography_sources": [_wiki_bio("Indira Gandhi")],
        "expected_clusters": [
            _bio_cluster(
                "central_crisis_authority",
                "central authority and crisis leadership",
                ["government_authority", "leadership_executive", "willfulness", "courage_aries", "self_assertion"],
                "Public biography emphasizes centralized authority, crisis politics, and prime-ministerial leadership.",
            )
        ],
    },
    "jawaharlal_nehru": {
        "biography_sources": [_wiki_bio("Jawaharlal Nehru")],
        "expected_clusters": [
            _bio_cluster(
                "founding_intellectual_statesman",
                "founding intellectual statesmanship",
                ["scholarship", "intelligence_general", "vision_big_picture", "leadership_executive", "government_authority"],
                "Public biography emphasizes intellectual statesmanship and founding prime-ministerial leadership.",
            )
        ],
    },
    "rajiv_gandhi": {
        "biography_sources": [_wiki_bio("Rajiv Gandhi")],
        "expected_clusters": [
            _bio_cluster(
                "modernization_leadership",
                "modernization and dynastic leadership",
                ["zeal_for_reform", "enterprise_initiative", "leadership_executive", "invention_discovery", "government_authority"],
                "Public biography emphasizes modernizing politics, technology orientation, and dynastic prime-ministerial leadership.",
            )
        ],
    },
    "corazon_aquino": {
        "biography_sources": [_wiki_bio("Corazon Aquino")],
        "expected_clusters": [
            _bio_cluster(
                "democratic_restoration",
                "democratic restoration and reform",
                ["justice_advocacy", "zeal_for_reform", "courage_aries", "leadership_executive", "responsibility"],
                "Public biography emphasizes democratic restoration after authoritarian rule and presidential leadership.",
            )
        ],
    },
    "benigno_aquino_iii": {
        "biography_sources": [_wiki_bio("Benigno Aquino III")],
        "expected_clusters": [
            _bio_cluster(
                "reformist_presidency",
                "reformist presidential governance",
                ["justice_advocacy", "zeal_for_reform", "leadership_executive", "responsibility", "government_authority"],
                "Public biography emphasizes anti-corruption reform themes and presidential governance.",
            )
        ],
    },
    "michelle_bachelet": {
        "biography_sources": [_wiki_bio("Michelle Bachelet")],
        "expected_clusters": [
            _bio_cluster(
                "service_and_governance",
                "public service, health, defense, and governance",
                ["zeal_for_service", "humanitarianism", "leadership_executive", "responsibility", "government_authority"],
                "Public biography emphasizes health, defense, presidency, and human-rights public service.",
            )
        ],
    },
    "salvador_allende": {
        "biography_sources": [_wiki_bio("Salvador Allende")],
        "expected_clusters": [
            _bio_cluster(
                "ideological_reform",
                "ideological reform and justice politics",
                ["zeal_for_reform", "justice_advocacy", "leadership_executive", "utopianism", "government_authority"],
                "Public biography emphasizes socialist reform agenda and presidential crisis leadership.",
            )
        ],
    },
    "gabriel_boric": {
        "biography_sources": [_wiki_bio("Gabriel Boric")],
        "expected_clusters": [
            _bio_cluster(
                "youth_left_reform",
                "youth-left reform and social justice",
                ["zeal_for_reform", "justice_advocacy", "humanitarianism", "leadership_executive", "rebellion"],
                "Public biography emphasizes student politics, left coalition leadership, and social reform themes.",
            )
        ],
    },
    "andres_manuel_lopez_obrador": {
        "biography_sources": [_wiki_bio("Andres Manuel Lopez Obrador")],
        "expected_clusters": [
            _bio_cluster(
                "populist_reform",
                "populist anti-establishment reform",
                ["rebellion", "zeal_for_reform", "self_assertion", "leadership_executive", "justice_advocacy"],
                "Public biography emphasizes populist anti-establishment politics and reformist presidential agenda.",
            )
        ],
    },
    "hugo_chavez": {
        "biography_sources": [_wiki_bio("Hugo Chavez")],
        "expected_clusters": [
            _bio_cluster(
                "revolutionary_charisma",
                "revolutionary charisma and centralized rule",
                ["rebellion", "self_assertion", "leadership_executive", "eloquence", "government_authority"],
                "Public biography emphasizes revolutionary politics, charismatic communication, and presidential authority.",
            )
        ],
    },
    "javier_milei": {
        "biography_sources": [_wiki_bio("Javier Milei")],
        "expected_clusters": [
            _bio_cluster(
                "anti_establishment_disruption",
                "anti-establishment disruption and blunt assertion",
                ["rebellion", "disruptiveness", "frankness", "self_assertion", "unconventionality"],
                "Public biography emphasizes libertarian anti-establishment politics, disruption, and blunt public style.",
            )
        ],
    },
    "alberto_fujimori": {
        "biography_sources": [_wiki_bio("Alberto Fujimori")],
        "expected_clusters": [
            _bio_cluster(
                "technocratic_authority",
                "technocratic authority and crisis governance",
                ["calculation", "government_authority", "leadership_executive", "ruthlessness", "responsibility"],
                "Public biography emphasizes technocratic politics, presidential authority, and crisis governance.",
            )
        ],
    },
    "jair_bolsonaro": {
        "biography_sources": [_wiki_bio("Jair Bolsonaro")],
        "expected_clusters": [
            _bio_cluster(
                "military_populist_confrontation",
                "military-populist confrontation",
                ["pugnacity", "self_assertion", "frankness", "courage_aries", "government_authority"],
                "Public biography emphasizes military background, populist politics, and confrontational public style.",
            )
        ],
    },
    "volodymyr_zelenskyy": {
        "biography_sources": [_wiki_bio("Volodymyr Zelenskyy")],
        "expected_clusters": [
            _bio_cluster(
                "performer_wartime_leadership",
                "performer-to-wartime leadership",
                ["courage_aries", "valor", "leadership_executive", "humour", "eloquence"],
                "Public biography emphasizes entertainment career, wartime presidency, courage, and public address.",
            )
        ],
    },
    "donald_trump": {
        "biography_sources": [_wiki_bio("Donald Trump")],
        "expected_clusters": [
            _bio_cluster(
                "celebrity_populist_executive",
                "celebrity-populist executive style",
                ["self_assertion", "leadership_executive", "kingship_leadership_display", "worldliness", "enterprise_initiative"],
                "Public biography emphasizes business celebrity, populist politics, and presidential executive style.",
            )
        ],
    },
    "barack_obama": {
        "biography_sources": [_wiki_bio("Barack Obama")],
        "expected_clusters": [
            _bio_cluster(
                "rhetorical_coalition_leadership",
                "rhetorical coalition leadership and justice themes",
                ["eloquence", "mediation", "cooperation", "justice_advocacy", "leadership_executive"],
                "Public biography emphasizes oratory, coalition politics, legal background, and presidential leadership.",
            )
        ],
    },
    "joe_biden": {
        "biography_sources": [_wiki_bio("Joe Biden")],
        "expected_clusters": [
            _bio_cluster(
                "institutional_persistence",
                "institutional persistence and responsibility",
                ["perseverance", "responsibility", "cooperation", "leadership_executive", "government_authority"],
                "Public biography emphasizes long Senate career, vice presidency, presidency, and persistence through losses.",
            )
        ],
    },
    "bill_clinton": {
        "biography_sources": [_wiki_bio("Bill Clinton")],
        "expected_clusters": [
            _bio_cluster(
                "interpersonal_persuasion",
                "interpersonal persuasion and political communication",
                ["eloquence", "sociability", "tact", "leadership_executive", "quick_wittedness"],
                "Public biography emphasizes charismatic retail politics, public speaking, and presidential leadership.",
            )
        ],
    },
    "kamala_harris": {
        "biography_sources": [_wiki_bio("Kamala Harris")],
        "expected_clusters": [
            _bio_cluster(
                "legal_executive_path",
                "prosecutor-to-executive legal leadership",
                ["legal_mind", "justice_advocacy", "leadership_executive", "self_assertion", "government_authority"],
                "Public biography emphasizes prosecutor, attorney general, senator, and vice-presidential executive path.",
            )
        ],
    },
    "george_w_bush": {
        "biography_sources": [_wiki_bio("George W. Bush")],
        "expected_clusters": [
            _bio_cluster(
                "crisis_executive_decisiveness",
                "crisis executive decisiveness",
                [
                    "leadership_executive",
                    "government_authority",
                    "self_assertion",
                    "courage_aries",
                    "responsibility",
                    "enterprise_initiative",
                ],
                "Public biography emphasizes governorship, presidency, and crisis executive decision-making.",
            )
        ],
    },
    "franklin_d_roosevelt": {
        "biography_sources": [_wiki_bio("Franklin D. Roosevelt")],
        "expected_clusters": [
            _bio_cluster(
                "crisis_endurance_governance",
                "crisis governance and endurance",
                ["leadership_executive", "endurance", "resilience", "government_authority", "zeal_for_reform"],
                "Public biography emphasizes New Deal reform, wartime presidency, disability, and long crisis leadership.",
            )
        ],
    },
    "john_f_kennedy": {
        "biography_sources": [_wiki_bio("John F. Kennedy")],
        "expected_clusters": [
            _bio_cluster(
                "charismatic_crisis_leadership",
                "charismatic crisis leadership",
                [
                    "leadership_executive",
                    "courage_aries",
                    "eloquence",
                    "kingship_leadership_display",
                    "valor",
                    "government_authority",
                ],
                "Public biography emphasizes charismatic presidency, war service, public address, and crisis symbolism.",
            )
        ],
    },
    "dick_cheney": {
        "biography_sources": [_wiki_bio("Dick Cheney")],
        "expected_clusters": [
            _bio_cluster(
                "hard_power_executive",
                "hard-power executive authority",
                [
                    "government_authority",
                    "leadership_executive",
                    "severity",
                    "ruthlessness",
                    "responsibility",
                    "steadiness",
                    "craftsmanship",
                ],
                "Public biography emphasizes defense secretary, vice presidency, hard-power national security influence, and long institutional operating style.",
            )
        ],
    },
    "henry_kissinger": {
        "biography_sources": [_wiki_bio("Henry Kissinger")],
        "expected_clusters": [
            _bio_cluster(
                "strategic_diplomacy",
                "strategic diplomacy and judgment",
                ["mediation", "tact", "legal_mind", "judgment_sound", "scholarship"],
                "Public biography emphasizes diplomacy, national security strategy, scholarship, and secretary-of-state service.",
            )
        ],
    },
    "donald_rumsfeld": {
        "biography_sources": [_wiki_bio("Donald Rumsfeld")],
        "expected_clusters": [
            _bio_cluster(
                "defense_bureaucratic_power",
                "defense bureaucracy and hard power",
                [
                    "government_authority",
                    "severity",
                    "leadership_executive",
                    "responsibility",
                    "self_assertion",
                    "legal_mind",
                    "steadiness",
                ],
                "Public biography emphasizes defense secretary roles, bureaucracy, legal-political office, and hard-power executive decisions.",
            )
        ],
    },
    "albert_einstein": {
        "biography_sources": [_wiki_bio("Albert Einstein")],
        "expected_clusters": [
            _bio_cluster(
                "scientific_originality",
                "scientific originality and discovery",
                ["invention_discovery", "genius_inventive_scientific", "intelligence_general", "curiosity"],
                "Public biography emphasizes theoretical physics, relativity, and scientific discovery.",
            )
        ],
    },
    "marie_curie": {
        "biography_sources": [_wiki_bio("Marie Curie")],
        "expected_clusters": [
            _bio_cluster(
                "scientific_research_endurance",
                "scientific research discipline and endurance",
                ["genius_inventive_scientific", "invention_discovery", "industriousness", "perseverance", "endurance"],
                "Public biography emphasizes radioactivity research, Nobel prizes, and sustained scientific labor.",
            )
        ],
    },
    "muhammad_ali": {
        "biography_sources": [_wiki_bio("Muhammad Ali")],
        "expected_clusters": [
            _bio_cluster(
                "combative_public_assertion",
                "combative public assertion",
                ["pugnacity", "self_assertion", "warlike", "frankness", "courage_aries"],
                "Public biography emphasizes boxing, public assertion, activism, and principled confrontation.",
            )
        ],
    },
    "eleanor_roosevelt": {
        "biography_sources": [_wiki_bio("Eleanor Roosevelt")],
        "expected_clusters": [
            _bio_cluster(
                "humanitarian_advocacy",
                "humanitarian and justice advocacy",
                ["humanitarianism", "justice_advocacy", "charity", "unselfishness", "zeal_for_service"],
                "Public biography emphasizes human rights, the UN, social reform, and public service.",
            )
        ],
    },
    "amelia_earhart": {
        "biography_sources": [_wiki_bio("Amelia Earhart")],
        "expected_clusters": [
            _bio_cluster(
                "pioneering_exploration",
                "pioneering exploration and risk",
                ["venturesomeness", "travel_inclination", "courage_aries", "recklessness", "yearning_for_travel"],
                "Public biography emphasizes aviation records, pioneering exploration, and high-risk travel.",
            )
        ],
    },
    "frida_kahlo": {
        "biography_sources": [_wiki_bio("Frida Kahlo")],
        "expected_clusters": [
            _bio_cluster(
                "artistic_resilience",
                "artistic imagination and resilience",
                ["imagination", "creativity", "grace_artistic", "resilience", "transformation"],
                "Public biography emphasizes painting, self-expression, bodily hardship, and resilient artistic identity.",
            )
        ],
    },
    "oprah_winfrey": {
        "biography_sources": [_wiki_bio("Oprah Winfrey")],
        "expected_clusters": [
            _bio_cluster(
                "media_empathy_enterprise",
                "media empathy and enterprise",
                ["empathy", "sociability", "humanitarianism", "enterprise_initiative", "eloquence"],
                "Public biography emphasizes media communication, personal interviews, philanthropy, and entrepreneurship.",
            )
        ],
    },
    "steve_jobs": {
        "biography_sources": [_wiki_bio("Steve Jobs")],
        "expected_clusters": [
            _bio_cluster(
                "product_invention_design",
                "product invention, design, and enterprise",
                ["invention_discovery", "creativity", "craftsmanship", "enterprise_initiative", "leadership_executive"],
                "Public biography emphasizes Apple, product vision, design control, and entrepreneurship.",
            )
        ],
    },
    "bill_gates": {
        "biography_sources": [_wiki_bio("Bill Gates")],
        "expected_clusters": [
            _bio_cluster(
                "software_enterprise_philanthropy",
                "software enterprise and philanthropy",
                ["invention_discovery", "scholarship", "philanthropy", "enterprise_initiative", "leadership_executive"],
                "Public biography emphasizes Microsoft, software entrepreneurship, and philanthropy.",
            )
        ],
    },
    "pope_francis": {
        "biography_sources": [_wiki_bio("Pope Francis")],
        "expected_clusters": [
            _bio_cluster(
                "religious_humanitarian_reform",
                "religious humanitarian reform",
                ["piety", "compassion_universalism", "humanitarianism", "charity", "zeal_for_reform"],
                "Public biography emphasizes papal leadership, religious vocation, reform, and concern for the poor.",
            )
        ],
    },
    "lionel_messi": {
        "biography_sources": [_wiki_bio("Lionel Messi")],
        "expected_clusters": [
            _bio_cluster(
                "elite_athletic_mastery",
                "elite athletic mastery",
                ["ability", "precision", "grace_artistic", "perseverance", "steadiness"],
                "Public biography emphasizes elite football mastery, sustained performance, and technical excellence.",
            )
        ],
    },
    "lebron_james": {
        "biography_sources": [_wiki_bio("LeBron James")],
        "expected_clusters": [
            _bio_cluster(
                "athletic_leadership_enterprise",
                "athletic leadership and enterprise",
                ["ability", "leadership_executive", "enterprise_initiative", "perseverance", "self_assertion"],
                "Public biography emphasizes elite basketball, leadership, business expansion, and sustained excellence.",
            )
        ],
    },
    "serena_williams": {
        "biography_sources": [_wiki_bio("Serena Williams")],
        "expected_clusters": [
            _bio_cluster(
                "competitive_dominance",
                "competitive dominance and resilience",
                ["ability", "pugnacity", "perseverance", "self_assertion", "fortitude"],
                "Public biography emphasizes tennis dominance, competitive force, and resilience.",
            )
        ],
    },
    "roger_federer": {
        "biography_sources": [_wiki_bio("Roger Federer")],
        "expected_clusters": [
            _bio_cluster(
                "athletic_grace",
                "athletic grace and sustained excellence",
                ["ability", "grace_artistic", "precision", "steadiness", "temperance"],
                "Public biography emphasizes elite tennis, technical grace, sportsmanship, and sustained excellence.",
            )
        ],
    },
    "david_bowie": {
        "biography_sources": [_wiki_bio("David Bowie")],
        "expected_clusters": [
            _bio_cluster(
                "artistic_reinvention",
                "artistic reinvention and persona fluidity",
                ["creativity", "grace_artistic", "unconventionality", "imagination", "transformation"],
                "Public biography emphasizes music, performance personas, artistic reinvention, and experimental style.",
            )
        ],
    },
    "elvis_presley": {
        "biography_sources": [_wiki_bio("Elvis Presley")],
        "expected_clusters": [
            _bio_cluster(
                "mass_musical_performance",
                "mass musical celebrity and performance",
                ["grace_artistic", "creativity", "kingship_leadership_display", "vivacity", "sociability"],
                "Public biography emphasizes music, performance, mass celebrity, and cultural display.",
            )
        ],
    },
    "angelina_jolie": {
        "biography_sources": [_wiki_bio("Angelina Jolie")],
        "expected_clusters": [
            _bio_cluster(
                "film_humanitarian",
                "film celebrity and humanitarian work",
                ["grace_artistic", "humanitarianism", "charity", "empathy", "creativity"],
                "Public biography emphasizes acting, celebrity, humanitarian work, and refugee advocacy.",
            )
        ],
    },
    "robin_williams": {
        "biography_sources": [_wiki_bio("Robin Williams")],
        "expected_clusters": [
            _bio_cluster(
                "comic_imagination",
                "comic imagination and emotional expression",
                ["humour", "wit", "imagination", "creativity", "empathy"],
                "Public biography emphasizes comedy, improvisation, acting imagination, and emotional expressiveness.",
            )
        ],
    },
    "tom_hanks": {
        "biography_sources": [_wiki_bio("Tom Hanks")],
        "expected_clusters": [
            _bio_cluster(
                "trusted_actor_public_steadiness",
                "trusted acting range and public steadiness",
                ["sociability", "sincerity", "reliability", "empathy", "creativity"],
                "Public biography emphasizes acting range, trusted public image, and steady popular appeal.",
            )
        ],
    },
}


def _build_trait_public_figure_case(
    row: Tuple[str, str, str, str, str, str, str, str, float, float, float, str]
) -> Dict[str, Any]:
    (
        case_id,
        label,
        benchmark_group,
        role_target,
        rating,
        utc_datetime,
        source_local_time,
        location,
        gmt_offset_hours,
        latitude,
        longitude,
        source_url,
    ) = row
    case = {
        "case_id": case_id,
        "label": label,
        "benchmark_group": benchmark_group,
        "role_target": role_target,
        "summary_context": "public_figure_biography",
        "birth": {
            "datetime": utc_datetime,
            "source_local_time": (
                f"{source_local_time} at {location}, source displayed GMT offset "
                f"{gmt_offset_hours:+g}"
            ),
            "source_gmt_offset_hours": gmt_offset_hours,
            "location": location,
            "timezone": "Etc/GMT+0",
            "latitude": latitude,
            "longitude": longitude,
            "house_system_code": "R",
            "source_url": source_url,
            "source_quality": f"Arcadia AstroDB citing Astro-Databank Rodden {rating}",
            "source_rating": rating,
        },
    }
    expectation = TRAIT_PUBLIC_FIGURE_BIOGRAPHY_EXPECTATIONS.get(case_id)
    if expectation:
        case["biography_sources"] = list(expectation.get("biography_sources") or [])
        case["expected_clusters"] = [dict(cluster) for cluster in expectation.get("expected_clusters") or []]
    return case


def get_trait_public_figure_baseline_cases() -> List[Dict[str, Any]]:
    return [_build_trait_public_figure_case(row) for row in TRAIT_PUBLIC_FIGURE_BASELINE_ROWS]


TRAIT_CRIMINAL_FIGURE_BASELINE_ROWS: List[Tuple[str, str, str, str, str, str, str, str, float, float, float, str]] = [
    (
        "ted_bundy",
        "Ted Bundy",
        "violent_offender",
        "serial murder and violent predation",
        "AA",
        "1946-11-25T03:35:00+00:00",
        "24/11/1946 22:35",
        "Burlington, Vermont",
        -5.0,
        44.4759,
        -73.2121,
        "https://arcadia-astrology.com/en/astrodb/bundy-ted",
    ),
    (
        "jeffrey_dahmer",
        "Jeffrey Dahmer",
        "violent_offender",
        "serial murder, violence, and extreme secrecy",
        "AA",
        "1960-05-21T21:34:00+00:00",
        "21/05/1960 16:34",
        "Milwaukee, Wisconsin",
        -5.0,
        43.0389,
        -87.9065,
        "https://arcadia-astrology.com/en/astrodb/dahmer-jeffrey",
    ),
    (
        "john_wayne_gacy",
        "John Wayne Gacy",
        "violent_offender",
        "serial murder and public-mask duplicity",
        "AA",
        "1942-03-17T05:29:00+00:00",
        "17/03/1942 00:29",
        "Chicago, Illinois",
        -5.0,
        41.8781,
        -87.6298,
        "https://arcadia-astrology.com/en/astrodb/gacy-john-wayne",
    ),
    (
        "charles_manson",
        "Charles Manson",
        "cult_crime",
        "cult leadership, manipulation, and violence",
        "AA",
        "1934-11-12T21:40:00+00:00",
        "12/11/1934 16:40",
        "Cincinnati, Ohio",
        -5.0,
        39.1031,
        -84.512,
        "https://arcadia-astrology.com/en/astrodb/manson-charles",
    ),
    (
        "david_berkowitz",
        "David Berkowitz",
        "violent_offender",
        "serial shootings and destabilizing violence",
        "AA",
        "1953-06-01T20:52:00+00:00",
        "01/06/1953 16:52",
        "Brooklyn (Kings County), New York",
        -4.0,
        40.6782,
        -73.9442,
        "https://arcadia-astrology.com/en/astrodb/berkowitz-david",
    ),
    (
        "mark_david_chapman",
        "Mark David Chapman",
        "assassination",
        "assassination and obsessive public violence",
        "AA",
        "1955-05-11T01:30:00+00:00",
        "10/05/1955 19:30",
        "Fort Worth, Texas",
        -6.0,
        32.7555,
        -97.3308,
        "https://arcadia-astrology.com/en/astrodb/chapman-mark-david",
    ),
    (
        "gary_gilmore",
        "Gary Gilmore",
        "violent_offender",
        "murder, defiance, and death-penalty notoriety",
        "AA",
        "1940-12-04T12:30:00+00:00",
        "04/12/1940 06:30",
        "McCamey, USA",
        -6.0,
        31.1357,
        -102.2243,
        "https://arcadia-astrology.com/en/astrodb/gilmore-gary",
    ),
    (
        "john_hinckley_jr",
        "John Hinckley Jr.",
        "assassination",
        "attempted assassination and obsessive public fixation",
        "AA",
        "1955-05-30T05:42:00+00:00",
        "29/05/1955 23:42",
        "Ardmore, Oklahoma",
        -6.0,
        34.1743,
        -97.1436,
        "https://arcadia-astrology.com/en/astrodb/hinckley-john-jr",
    ),
    (
        "squeaky_fromme",
        "Squeaky Fromme",
        "cult_crime",
        "cult allegiance and attempted assassination",
        "AA",
        "1948-10-22T12:37:00+00:00",
        "22/10/1948 05:37",
        "Santa Monica, California",
        -7.0,
        34.0195,
        -118.4912,
        "https://arcadia-astrology.com/en/astrodb/fromme-squeaky",
    ),
    (
        "robert_hansen",
        "Robert Hansen",
        "violent_offender",
        "serial murder and predatory violence",
        "AA",
        "1939-02-15T11:56:00+00:00",
        "15/02/1939 05:56",
        "Estherville, Iowa",
        -6.0,
        43.4016,
        -94.8339,
        "https://arcadia-astrology.com/en/astrodb/hansen-robert",
    ),
    (
        "clifford_olson",
        "Clifford Olson",
        "violent_offender",
        "serial murder and predatory violence",
        "A",
        "1940-01-02T06:10:00+00:00",
        "01/01/1940 22:10",
        "Vancouver, British Columbia (CAN)",
        -8.0,
        49.2827,
        -123.1207,
        "https://arcadia-astrology.com/en/astrodb/olson-clifford",
    ),
    (
        "nathan_leopold",
        "Nathan Leopold",
        "violent_offender",
        "planned murder and intellectualized transgression",
        "AA",
        "1904-11-19T21:55:00+00:00",
        "19/11/1904 15:55",
        "Chicago, Illinois",
        -6.0,
        41.8781,
        -87.6298,
        "https://arcadia-astrology.com/en/astrodb/leopold-nathan",
    ),
    (
        "reggie_kray",
        "Reggie Kray",
        "organized_crime",
        "organized crime leadership and violence",
        "AA",
        "1933-10-24T20:00:00+00:00",
        "24/10/1933 20:00",
        "London, England",
        0.0,
        51.5074,
        -0.1278,
        "https://arcadia-astrology.com/en/astrodb/kray-reggie",
    ),
    (
        "ronnie_kray",
        "Ronnie Kray",
        "organized_crime",
        "organized crime leadership and violence",
        "AA",
        "1933-10-24T20:10:00+00:00",
        "24/10/1933 20:10",
        "London, England",
        0.0,
        51.5074,
        -0.1278,
        "https://arcadia-astrology.com/en/astrodb/kray-ronnie",
    ),
    (
        "lucky_luciano",
        "Lucky Luciano",
        "organized_crime",
        "organized crime enterprise and syndicate leadership",
        "AA",
        "1897-11-24T11:00:00+00:00",
        "24/11/1897 12:00",
        "Lercara Friddi, Italy",
        1.0,
        37.7465,
        13.6042,
        "https://arcadia-astrology.com/en/astrodb/luciano-lucky",
    ),
    (
        "frank_coppola",
        "Frank Coppola",
        "organized_crime",
        "organized crime violence and underworld leadership",
        "AA",
        "1899-10-06T05:00:00+00:00",
        "06/10/1899 06:00",
        "Partinico, Italy",
        1.0,
        38.0464,
        13.1207,
        "https://arcadia-astrology.com/en/astrodb/coppola-frank",
    ),
    (
        "david_carpenter",
        "David Carpenter",
        "violent_offender",
        "serial murder and predatory violence",
        "AA",
        "1930-05-07T05:16:00+00:00",
        "06/05/1930 21:16",
        "San Francisco, California",
        -8.0,
        37.7749,
        -122.4194,
        "https://arcadia-astrology.com/en/astrodb/carpenter-david",
    ),
    (
        "caryl_chessman",
        "Caryl Chessman",
        "violent_offender",
        "kidnapping, sexual assault, and legal notoriety",
        "AA",
        "1921-05-27T17:10:00+00:00",
        "27/05/1921 12:10",
        "St.Joseph, USA",
        -5.0,
        39.7675,
        -94.8467,
        "https://arcadia-astrology.com/en/astrodb/chessman-caryl",
    ),
    (
        "kenneth_kimes_jr",
        "Kenneth Kimes Jr.",
        "fraud_murder",
        "fraud, murder, and criminal family enterprise",
        "AA",
        "1975-03-24T15:19:00+00:00",
        "24/03/1975 08:19",
        "Los Angeles, California",
        -7.0,
        34.0522,
        -118.2437,
        "https://arcadia-astrology.com/en/astrodb/kimes-kenneth-jr",
    ),
    (
        "giovanni_brusca",
        "Giovanni Brusca",
        "organized_crime",
        "mafia violence, assassination, and command activity",
        "AA",
        "1957-02-20T21:00:00+00:00",
        "20/02/1957 22:00",
        "San Giuseppe, Italy",
        1.0,
        37.9739,
        13.1883,
        "https://arcadia-astrology.com/en/astrodb/brusca-giovanni",
    ),
    (
        "salvatore_riina",
        "Salvatore Riina",
        "organized_crime",
        "mafia leadership, violence, and domination",
        "AA",
        "1930-11-16T15:00:00+00:00",
        "16/11/1930 16:00",
        "Palermo, Italy",
        1.0,
        38.1157,
        13.3615,
        "https://arcadia-astrology.com/en/astrodb/riina-salvatore",
    ),
]


TRAIT_CRIMINAL_FIGURE_BIOGRAPHY_EXPECTATIONS: Dict[str, Dict[str, Any]] = {
    "ted_bundy": {
        "biography_sources": [_wiki_bio("Ted Bundy")],
        "expected_clusters": [
            _bio_cluster(
                "serial_predation_deception",
                "serial predation and deceptive violence",
                ["destructiveness", "cunning", "ruthlessness", "lying_falsehood", "recklessness"],
                "Biography centers on serial murder, abduction, deceptive presentation, and violent predation.",
            )
        ],
    },
    "jeffrey_dahmer": {
        "biography_sources": [_wiki_bio("Jeffrey Dahmer")],
        "expected_clusters": [
            _bio_cluster(
                "serial_violence_concealment",
                "serial violence and concealment",
                ["cunning", "severity", "pugnacity", "domination_capricorn", "calculation", "reticence"],
                "Biography centers on serial murder, concealment, domination of victims, and extreme violence.",
            )
        ],
    },
    "john_wayne_gacy": {
        "biography_sources": [_wiki_bio("John Wayne Gacy")],
        "expected_clusters": [
            _bio_cluster(
                "public_mask_serial_violence",
                "public-mask duplicity and serial violence",
                ["disruptiveness", "calculation", "knavery_trickery_deceit", "lying_falsehood", "violence"],
                "Biography emphasizes civic/public masking alongside serial murder and deception.",
            )
        ],
    },
    "charles_manson": {
        "biography_sources": [_wiki_bio("Charles Manson")],
        "expected_clusters": [
            _bio_cluster(
                "cult_control_violence",
                "cult control, manipulation, and violence",
                ["cunning", "ruthlessness", "tyranny", "calculation", "reticence", "willfulness"],
                "Biography centers on cult control, manipulation, criminal command, and violent ideology.",
            )
        ],
    },
    "david_berkowitz": {
        "biography_sources": [_wiki_bio("David Berkowitz")],
        "expected_clusters": [
            _bio_cluster(
                "serial_shooting_disruption",
                "serial shootings and destabilizing violence",
                ["severity", "destructiveness", "recklessness", "calculation", "zeal_for_status"],
                "Biography centers on serial shootings, public fear, and destabilizing violence.",
            )
        ],
    },
    "mark_david_chapman": {
        "biography_sources": [_wiki_bio("Mark David Chapman")],
        "expected_clusters": [
            _bio_cluster(
                "assassination_obsession",
                "assassination and obsessive public violence",
                ["destructiveness", "ruthlessness", "tyranny", "recklessness", "rebellion"],
                "Biography centers on John Lennon's assassination and obsessive public violence.",
            )
        ],
    },
    "gary_gilmore": {
        "biography_sources": [_wiki_bio("Gary Gilmore")],
        "expected_clusters": [
            _bio_cluster(
                "murder_defiance",
                "murder, defiance, and notoriety",
                ["cunning", "ruthlessness", "tyranny", "pugnacity", "self_assertion"],
                "Biography centers on murder convictions, defiance, and death-penalty notoriety.",
            )
        ],
    },
    "john_hinckley_jr": {
        "biography_sources": [_wiki_bio("John Hinckley Jr.")],
        "expected_clusters": [
            _bio_cluster(
                "attempted_assassination_fixation",
                "attempted assassination and fixation",
                ["ruthlessness", "recklessness", "subtlety", "rebellion", "watchfulness"],
                "Biography centers on attempted assassination, fixation, and institutional confinement after a not-guilty-by-insanity verdict.",
            )
        ],
    },
    "squeaky_fromme": {
        "biography_sources": [_wiki_bio("Squeaky Fromme")],
        "expected_clusters": [
            _bio_cluster(
                "cult_allegiance_attempted_assassination",
                "cult allegiance and attempted assassination",
                ["destructiveness", "restlessness", "greed_covetousness", "enterprise_initiative", "reticence"],
                "Biography centers on Manson-family allegiance and attempted assassination of President Gerald Ford.",
            )
        ],
    },
    "robert_hansen": {
        "biography_sources": [_wiki_bio("Robert Hansen")],
        "expected_clusters": [
            _bio_cluster(
                "predatory_serial_murder",
                "predatory serial murder",
                ["destructiveness", "disruptiveness", "lying_falsehood", "recklessness", "rebellion"],
                "Biography centers on serial murder, abduction, deception, and predatory violence.",
            )
        ],
    },
    "clifford_olson": {
        "biography_sources": [_wiki_bio("Clifford Olson")],
        "expected_clusters": [
            _bio_cluster(
                "serial_predatory_violence",
                "serial predatory violence",
                ["destructiveness", "pugnacity", "recklessness", "lying_falsehood", "violence"],
                "Biography centers on serial child murders, deception, and predatory violence.",
            )
        ],
    },
    "nathan_leopold": {
        "biography_sources": [_wiki_bio("Leopold and Loeb")],
        "expected_clusters": [
            _bio_cluster(
                "planned_intellectualized_murder",
                "planned and intellectualized murder",
                ["severity", "ruthlessness", "calculation", "cunning", "reticence"],
                "Biography centers on the planned Leopold and Loeb murder and intellectualized transgression.",
            )
        ],
    },
    "reggie_kray": {
        "biography_sources": [_wiki_bio("Kray twins")],
        "expected_clusters": [
            _bio_cluster(
                "gangland_control_violence",
                "gangland control and violence",
                ["cunning", "destructiveness", "severity", "calculation", "enterprise_initiative"],
                "Biography centers on organized crime, gangland violence, and underworld leadership.",
            )
        ],
    },
    "ronnie_kray": {
        "biography_sources": [_wiki_bio("Kray twins")],
        "expected_clusters": [
            _bio_cluster(
                "gangland_control_violence",
                "gangland control and violence",
                ["cunning", "destructiveness", "severity", "calculation", "enterprise_initiative"],
                "Biography centers on organized crime, gangland violence, and underworld leadership.",
            )
        ],
    },
    "lucky_luciano": {
        "biography_sources": [_wiki_bio("Lucky Luciano")],
        "expected_clusters": [
            _bio_cluster(
                "organized_crime_enterprise",
                "organized crime enterprise and syndicate power",
                ["destructiveness", "ruthlessness", "cunning", "disruptiveness", "self_assertion", "turbulence"],
                "Biography centers on organized-crime syndicate formation, coercive enterprise, and underworld power.",
            )
        ],
    },
    "frank_coppola": {
        "biography_sources": [_wiki_bio("Frank Coppola (mobster)")],
        "expected_clusters": [
            _bio_cluster(
                "mafia_underworld_leadership",
                "mafia underworld leadership",
                ["cunning", "destructiveness", "recklessness", "enterprise_initiative", "greed_covetousness"],
                "Biography centers on Mafia leadership, underworld enterprise, and criminal violence.",
            )
        ],
    },
    "david_carpenter": {
        "biography_sources": [_wiki_bio("David Carpenter")],
        "expected_clusters": [
            _bio_cluster(
                "serial_predatory_violence",
                "serial predatory violence",
                ["severity", "ruthlessness", "pugnacity", "calculation", "reticence", "watchfulness"],
                "Biography centers on serial murder, predation, and repeated violent attacks.",
            )
        ],
    },
    "caryl_chessman": {
        "biography_sources": [_wiki_bio("Caryl Chessman")],
        "expected_clusters": [
            _bio_cluster(
                "kidnapping_legal_notoriety",
                "kidnapping, violence, and legal notoriety",
                ["severity", "ruthlessness", "calculation", "recklessness", "watchfulness"],
                "Biography centers on kidnapping, sexual assault conviction, death-row writing, and legal notoriety.",
            )
        ],
    },
    "kenneth_kimes_jr": {
        "biography_sources": [_wiki_bio("Sante Kimes")],
        "expected_clusters": [
            _bio_cluster(
                "fraud_murder_family_enterprise",
                "fraud, murder, and criminal family enterprise",
                ["destructiveness", "cunning", "recklessness", "lying_falsehood", "calculation"],
                "Biography centers on fraud schemes, murder, deception, and criminal activity with Sante Kimes.",
            )
        ],
    },
    "giovanni_brusca": {
        "biography_sources": [_wiki_bio("Giovanni Brusca")],
        "expected_clusters": [
            _bio_cluster(
                "mafia_assassination_command",
                "mafia assassination and command violence",
                ["ruthlessness", "tyranny", "recklessness", "lying_falsehood", "severity"],
                "Biography centers on Mafia command violence, assassination activity, and organized-crime enforcement.",
            )
        ],
    },
    "salvatore_riina": {
        "biography_sources": [_wiki_bio("Salvatore Riina")],
        "expected_clusters": [
            _bio_cluster(
                "mafia_domination_leadership",
                "mafia domination and leadership",
                ["cunning", "ruthlessness", "severity", "reticence", "leadership_executive"],
                "Biography centers on Cosa Nostra leadership, domination, violence, and underworld command.",
            )
        ],
    },
}


def _build_trait_criminal_figure_case(
    row: Tuple[str, str, str, str, str, str, str, str, float, float, float, str]
) -> Dict[str, Any]:
    (
        case_id,
        label,
        benchmark_group,
        role_target,
        rating,
        utc_datetime,
        source_local_time,
        location,
        gmt_offset_hours,
        latitude,
        longitude,
        source_url,
    ) = row
    case = {
        "case_id": case_id,
        "label": label,
        "benchmark_group": benchmark_group,
        "role_target": role_target,
        "summary_context": "criminal_biography",
        "birth": {
            "datetime": utc_datetime,
            "source_local_time": (
                f"{source_local_time} at {location}, source displayed GMT offset "
                f"{gmt_offset_hours:+g}"
            ),
            "source_gmt_offset_hours": gmt_offset_hours,
            "location": location,
            "timezone": "Etc/GMT+0",
            "latitude": latitude,
            "longitude": longitude,
            "house_system_code": "R",
            "source_url": source_url,
            "source_quality": f"Arcadia AstroDB citing Astro-Databank Rodden {rating}",
            "source_rating": rating,
        },
    }
    expectation = TRAIT_CRIMINAL_FIGURE_BIOGRAPHY_EXPECTATIONS.get(case_id)
    if expectation:
        case["biography_sources"] = list(expectation.get("biography_sources") or [])
        case["expected_clusters"] = [dict(cluster) for cluster in expectation.get("expected_clusters") or []]
    return case


def get_trait_criminal_figure_baseline_cases() -> List[Dict[str, Any]]:
    return [_build_trait_criminal_figure_case(row) for row in TRAIT_CRIMINAL_FIGURE_BASELINE_ROWS]
