from pathlib import Path
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
    assert any(
        value.endswith(";traits/corpus/new_sources_inspection")
        for value in add_data_values
    )
    assert len(add_data_values) == (
        len(build_backend.RUNTIME_DATA_ENTRIES)
        + len(build_backend.OPTIONAL_RUNTIME_DATA_ENTRIES)
        + 1
    )


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
