"""
Build a compact Astrocartography city catalog from GeoNames.

Output:
- backend/knowledge/astrocartography/city_catalog.runtime.json

The catalog is intended for atlas-style Astrocartography candidate search.
It keeps a medium-size world city corpus in-repo so the app can score cities
without calling the geocoder for every candidate.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(r"C:\Users\sabaa\Downloads\codexhorary")
OUTPUT_PATH = ROOT / "backend" / "knowledge" / "astrocartography" / "city_catalog.runtime.json"

GEONAMES_CITIES_URL = "https://download.geonames.org/export/dump/cities15000.zip"
GEONAMES_COUNTRIES_URL = "https://download.geonames.org/export/dump/countryInfo.txt"

INCLUDED_ADMIN_CODES = {"PPLC", "PPLA"}
INCLUDED_PLACE_CODES = INCLUDED_ADMIN_CODES | {"PPL"}
DEFAULT_MIN_POPULATION = 15000
CONTINENT_NAMES = {
    "AF": "Africa",
    "AN": "Antarctica",
    "AS": "Asia",
    "EU": "Europe",
    "NA": "North America",
    "OC": "Oceania",
    "SA": "South America",
}


def _download_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def _load_country_meta(country_info_text: str) -> Dict[str, Dict[str, str]]:
    countries: Dict[str, Dict[str, str]] = {}
    for raw_line in country_info_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 9:
            continue
        iso = str(parts[0] or "").strip().upper()
        name = str(parts[4] or "").strip()
        continent_code = str(parts[8] or "").strip().upper()
        if iso and name:
            countries[iso] = {
                "country_name": name,
                "continent_code": continent_code,
                "continent_name": CONTINENT_NAMES.get(continent_code, continent_code or "Unknown"),
            }
    return countries


def _load_city_rows_from_zip(payload: bytes) -> Iterable[List[str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        member = next((name for name in archive.namelist() if name.endswith(".txt")), None)
        if not member:
            raise ValueError("GeoNames archive did not contain a .txt member")
        with archive.open(member, "r") as fh:
            stream = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
            reader = csv.reader(stream, delimiter="\t")
            for row in reader:
                if row:
                    yield row


def _priority(feature_code: str) -> int:
    if feature_code == "PPLC":
        return 0
    if feature_code.startswith("PPLA"):
        return 1
    return 2


def _build_label(name: str, country_name: str, admin1_code: str) -> str:
    if admin1_code and admin1_code.isalpha() and len(admin1_code) <= 3:
        return f"{name}, {admin1_code}, {country_name}"
    return f"{name}, {country_name}"


def build_catalog(min_population: int = DEFAULT_MIN_POPULATION) -> Dict[str, Any]:
    cities_zip = _download_bytes(GEONAMES_CITIES_URL)
    country_text = _download_bytes(GEONAMES_COUNTRIES_URL).decode("utf-8", errors="replace")
    country_meta = _load_country_meta(country_text)

    seen: set[Tuple[str, str, str]] = set()
    cities: List[Dict[str, Any]] = []

    for row in _load_city_rows_from_zip(cities_zip):
        if len(row) < 19:
            continue

        feature_class = str(row[6] or "").strip()
        feature_code = str(row[7] or "").strip().upper()
        country_code = str(row[8] or "").strip().upper()

        if feature_class != "P" or feature_code not in INCLUDED_PLACE_CODES:
            continue

        try:
            population = int(float(row[14] or 0))
        except Exception:
            population = 0

        include = feature_code in INCLUDED_ADMIN_CODES or (feature_code == "PPL" and population >= int(min_population))
        if not include:
            continue

        name = str(row[1] or "").strip()
        ascii_name = str(row[2] or "").strip() or name
        admin1_code = str(row[10] or "").strip()
        timezone_name = str(row[17] or "").strip()
        meta = country_meta.get(country_code, {})
        country_name = str(meta.get("country_name") or country_code or "Unknown")
        continent_code = str(meta.get("continent_code") or "")
        continent_name = str(meta.get("continent_name") or continent_code or "Unknown")

        if not name or not country_code:
            continue

        dedupe_key = (ascii_name.lower(), country_code, admin1_code.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        try:
            latitude = round(float(row[4]), 6)
            longitude = round(float(row[5]), 6)
        except Exception:
            continue

        label = _build_label(ascii_name, country_name, admin1_code)
        cities.append(
            {
                "geonameid": int(row[0]),
                "name": name,
                "ascii_name": ascii_name,
                "country_code": country_code,
                "country_name": country_name,
                "continent_code": continent_code,
                "continent_name": continent_name,
                "admin1_code": admin1_code,
                "latitude": latitude,
                "longitude": longitude,
                "population": population,
                "timezone": timezone_name,
                "feature_code": feature_code,
                "label": label,
                "query": f"{ascii_name}, {country_name}",
            }
        )

    cities.sort(
        key=lambda item: (
            _priority(str(item.get("feature_code") or "")),
            -int(item.get("population") or 0),
            str(item.get("ascii_name") or ""),
            str(item.get("country_code") or ""),
        )
    )

    return {
        "generated_on": date.today().isoformat(),
        "generator": "scripts/build_astrocartography_city_catalog.py",
        "source": {
            "provider": "GeoNames",
            "dataset": "cities15000",
            "cities_url": GEONAMES_CITIES_URL,
            "countries_url": GEONAMES_COUNTRIES_URL,
        },
        "thresholds": {
            "min_population": int(min_population),
            "included_feature_codes": sorted(INCLUDED_PLACE_CODES),
        },
        "city_count": len(cities),
        "continents": [
            {"code": code, "label": label}
            for code, label in sorted(CONTINENT_NAMES.items())
            if any(str(city.get("continent_code") or "") == code for city in cities)
        ],
        "cities": cities,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Astrocartography atlas city catalog.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Output JSON path")
    parser.add_argument("--min-population", type=int, default=DEFAULT_MIN_POPULATION, help="Population threshold for non-admin cities")
    args = parser.parse_args()

    payload = build_catalog(min_population=args.min_population)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({payload['city_count']} cities)")


if __name__ == "__main__":
    main()
