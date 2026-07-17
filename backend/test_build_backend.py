from pathlib import Path, PureWindowsPath
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_backend


def test_runtime_data_args_include_benchmark_tree():
    backend_dir = Path(__file__).resolve().parent
    build_metadata_path = backend_dir / "build" / "build_metadata.json"

    args = build_backend.build_runtime_data_args(backend_dir, build_metadata_path)
    add_data_values = [args[index + 1] for index, value in enumerate(args) if value == "--add-data"]

    assert f"{backend_dir / 'benchmarks'};benchmarks" in add_data_values
    assert f"{backend_dir / 'ephemeris' / 'sweph'};ephemeris/sweph" in add_data_values
    assert f"{backend_dir / 'knowledge' / 'weather'};knowledge/weather" in add_data_values
    assert any(value.endswith(";tc") for value in add_data_values)
    assert len(add_data_values) == (
        len(build_backend.RUNTIME_DATA_ENTRIES)
        + len(build_backend.OPTIONAL_RUNTIME_DATA_ENTRIES)
        + 1
    )


def test_bundled_corpus_paths_fit_conservative_default_windows_install_root():
    backend_dir = Path(__file__).resolve().parent
    corpus_source = (backend_dir / "../extracted_text_docs/new_sources_inspection").resolve()
    install_root = PureWindowsPath(
        r"C:\Users\VoxStellaReleaseUser\AppData\Local\Programs\Vox Stella"
    )
    runtime_root = PureWindowsPath(
        "resources", "backend", "runtime", "horary_backend", "_internal"
    )
    corpus_destination = next(
        destination
        for source, destination in build_backend.OPTIONAL_RUNTIME_DATA_ENTRIES
        if source.endswith("new_sources_inspection")
    )

    projected = [
        install_root.joinpath(
            runtime_root,
            corpus_destination,
            *source_path.relative_to(corpus_source).parts,
        )
        for source_path in corpus_source.rglob("*")
        if source_path.is_file()
    ]

    assert projected
    # The release gate is intentionally 12 characters below legacy MAX_PATH.
    assert max(len(str(path)) for path in projected) <= 247


def test_pyinstaller_spec_is_generated_below_ignored_build_directory():
    source = Path(build_backend.__file__).read_text(encoding="utf-8")

    assert 'spec_dir = build_dir / "spec"' in source
    assert '"--specpath",\n            str(spec_dir)' in source


def test_required_pyinstaller_version_matches_release_requirements():
    requirements = (Path(__file__).resolve().parent / "requirements.txt").read_text(
        encoding="utf-8"
    )
    match = re.search(r"^pyinstaller==([^\s]+)$", requirements, flags=re.MULTILINE)

    assert match is not None
    assert build_backend.REQUIRED_PYINSTALLER == match.group(1)
