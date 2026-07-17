from __future__ import annotations

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "AGENTS.md").exists() and (candidate / "backend").is_dir():
            return candidate
    return Path(__file__).resolve().parents[1]


REPO_ROOT = _repo_root()


def _backend_tokens() -> set[str]:
    src = (BACKEND_DIR / "transits_morin.py").read_text(encoding="utf-8")
    return set(re.findall(r"_add\('([a-z0-9_]+)'\)", src))


def _dictionary_tokens() -> set[str]:
    path = REPO_ROOT / "event_keywords_dictionary(2).md"
    text = path.read_text(encoding="utf-8")
    tokens: set[str] = set()
    # event keys
    for name in re.findall(r"^([a-z0-9_]+):", text, flags=re.MULTILINE):
        tokens.add(name.lower())
    # list elements inside square brackets
    for block in re.findall(r"\[([^\]]+)\]", text):
        for raw in block.split(","):
            tok = raw.strip().strip("'\"").lower()
            if re.fullmatch(r"[a-z0-9_]+", tok):
                tokens.add(tok)
    return tokens


def _ui_tokens() -> set[str]:
    jsx = (REPO_ROOT / "frontend" / "src" / "features" / "astroclock" / "TransitsModal.jsx").read_text(encoding="utf-8")
    block = re.search(r"const\s+CanonicalLabels\s*=\s*\{(.*?)\}\s*;", jsx, flags=re.DOTALL)
    if not block:
        return set()
    tokens: set[str] = set()
    for line in block.group(1).splitlines():
        m = re.match(r"\s*([a-z0-9_]+)\s*:", line)
        if m:
            tokens.add(m.group(1))
    return tokens


def test_transit_keywords_align_with_dictionary_and_ui():
    backend = _backend_tokens()
    dictionary = _dictionary_tokens()
    ui = _ui_tokens()

    # Backend contains many internal/research tags that are not end-user labels.
    # Sync checks focus on canonical user-facing event tokens.
    canonical_tokens = {
        "birth_self",
        "birth_of_child",
        "death_natural",
        "death_violent",
        "death_of_family",
        "pregnancy",
        "marriage",
        "illness_acute",
        "illness_chronic",
        "financial_gain",
        "financial_loss",
        "injury_risk",
        "public_recognition",
        "lawsuit",
        "inheritance",
    }
    required = sorted(tok for tok in canonical_tokens if tok in backend)

    missing_in_dict = sorted(tok for tok in required if tok not in dictionary)
    missing_in_ui = sorted(tok for tok in required if tok not in ui)

    assert not missing_in_dict, f"Backend transit keywords missing from dictionary: {missing_in_dict}"
    assert not missing_in_ui, f"Backend transit keywords missing from UI labels: {missing_in_ui}"
