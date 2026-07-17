from pathlib import Path
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
    assert len(add_data_values) == len(build_backend.RUNTIME_DATA_ENTRIES) + 1
