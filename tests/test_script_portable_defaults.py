from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_REPO_PATH = r"C:\Users\sabaa\Downloads\codexhorary"

SCRIPT_DEFAULTS = (
    (
        "scripts.build_astrocartography_city_catalog",
        {
            "ROOT": REPO_ROOT,
            "OUTPUT_PATH": REPO_ROOT
            / "backend"
            / "knowledge"
            / "astrocartography"
            / "city_catalog.runtime.json",
        },
    ),
    (
        "scripts.build_astrocartography_knowledge_base",
        {
            "REPO_ROOT": REPO_ROOT,
            "RAW_DIR": REPO_ROOT / "horary_knowledge" / "astrocartography_books_text",
            "OUT_DIR": REPO_ROOT / "horary_knowledge" / "astrocartography_knowledge_base",
        },
    ),
    (
        "scripts.build_astrocartography_runtime_assets",
        {
            "ROOT": REPO_ROOT,
            "REFERENCE_DIR": REPO_ROOT
            / "horary_knowledge"
            / "astrocartography_knowledge_base"
            / "reference",
            "OUTPUT_PATH": REPO_ROOT
            / "backend"
            / "knowledge"
            / "astrocartography"
            / "interpretation_runtime.json",
        },
    ),
    (
        "scripts.build_synastry_knowledge_base",
        {
            "REPO_ROOT": REPO_ROOT,
            "RAW_DIR": REPO_ROOT / "horary_knowledge" / "synastry_books_text",
            "OUT_DIR": REPO_ROOT / "horary_knowledge" / "synastry_knowledge_base",
        },
    ),
    (
        "scripts.build_synastry_source_corpus",
        {
            "REPO_ROOT": REPO_ROOT,
            "DEFAULT_RAW_DEST": REPO_ROOT / "horary_knowledge" / "synastry_books_text",
            "DEFAULT_KB_DEST": REPO_ROOT / "horary_knowledge" / "synastry_knowledge_base",
        },
    ),
    (
        "scripts.build_text_inspection_corpus",
        {
            "REPO_ROOT": REPO_ROOT,
            "DEFAULT_RAW": REPO_ROOT / "extracted_text_docs" / "new_sources_text",
            "DEFAULT_OUT": REPO_ROOT / "extracted_text_docs" / "new_sources_inspection",
        },
    ),
    (
        "scripts.convert_desktop_books_to_text",
        {
            "REPO_ROOT": REPO_ROOT,
            "DEFAULT_DEST": REPO_ROOT / "horary_knowledge" / "desktop_books_text",
        },
    ),
    (
        "scripts.extract_horary_book_corpus",
        {
            "REPO_ROOT": REPO_ROOT,
            "OUTPUT_PATH": REPO_ROOT / "tests" / "fixtures" / "horary_book_examples_corpus.json",
        },
    ),
    (
        "scripts.search_text_inspection_corpus",
        {
            "REPO_ROOT": REPO_ROOT,
            "DEFAULT_INDEX": REPO_ROOT
            / "extracted_text_docs"
            / "new_sources_inspection"
            / "chunk_index.jsonl",
        },
    ),
)


@pytest.mark.parametrize(("module_name", "expected_defaults"), SCRIPT_DEFAULTS)
def test_repo_local_script_defaults_follow_checkout(
    module_name: str,
    expected_defaults: dict[str, Path],
) -> None:
    script_path = REPO_ROOT.joinpath(*module_name.split(".")).with_suffix(".py")
    module = _load_script(script_path)

    for constant_name, expected_path in expected_defaults.items():
        assert getattr(module, constant_name) == expected_path

    assert LEGACY_REPO_PATH not in script_path.read_text(encoding="utf-8")


def _load_script(script_path: Path) -> ModuleType:
    module_name = f"_portable_defaults_{script_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None

    injected_modules: list[str] = []
    if (
        script_path.name == "convert_desktop_books_to_text.py"
        and importlib.util.find_spec("pypdf") is None
    ):
        pypdf_stub = ModuleType("pypdf")
        pypdf_stub.PdfReader = object
        sys.modules["pypdf"] = pypdf_stub
        injected_modules.append("pypdf")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
        for injected_module in injected_modules:
            sys.modules.pop(injected_module, None)
    return module
