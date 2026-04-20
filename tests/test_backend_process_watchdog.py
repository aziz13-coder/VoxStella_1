import pytest

from backend.process_watchdog import (
    parse_parent_pid,
    parent_state_file_fresh,
    watchdog_should_exit,
    _watch_parent_loop,
)


def test_parse_parent_pid_accepts_positive_ints():
    assert parse_parent_pid("1234") == 1234
    assert parse_parent_pid(" 42 ") == 42


def test_parse_parent_pid_rejects_blank_zero_and_invalid_values():
    assert parse_parent_pid(None) is None
    assert parse_parent_pid("") is None
    assert parse_parent_pid("0") is None
    assert parse_parent_pid("-1") is None
    assert parse_parent_pid("abc") is None


def test_watchdog_should_exit_when_parent_is_missing():
    assert watchdog_should_exit(321, alive_check=lambda _pid: False) is True
    assert watchdog_should_exit(321, alive_check=lambda _pid: True) is False


def test_parent_state_file_fresh_detects_recent_heartbeat(tmp_path):
    state_file = tmp_path / "parent-state.json"
    state_file.write_text('{"updated_at_ms": 100000}', encoding="utf-8")

    assert parent_state_file_fresh(
        str(state_file),
        stale_after_seconds=10,
        time_fn=lambda: 105.0,
    ) is True


def test_watchdog_should_exit_when_state_file_goes_stale(tmp_path):
    state_file = tmp_path / "parent-state.json"
    state_file.write_text('{"updated_at_ms": 1000}', encoding="utf-8")

    assert watchdog_should_exit(
        321,
        parent_state_file=str(state_file),
        alive_check=lambda _pid: True,
        state_file_fresh=parent_state_file_fresh,
        stale_after_seconds=0.1,
    ) is True


def test_watch_parent_loop_calls_exit_when_parent_disappears():
    exits = []

    def fake_exit(code):
        exits.append(code)
        raise RuntimeError("exit")

    with pytest.raises(RuntimeError, match="exit"):
        _watch_parent_loop(
            123,
            poll_interval=0,
            exit_func=fake_exit,
            alive_check=lambda _pid: False,
            sleep_fn=lambda _seconds: None,
        )

    assert exits == [0]


def test_watch_parent_loop_calls_exit_when_parent_state_file_stops_updating(tmp_path):
    state_file = tmp_path / "parent-state.json"
    state_file.write_text('{"updated_at_ms": 0}', encoding="utf-8")
    exits = []

    def fake_exit(code):
        exits.append(code)
        raise RuntimeError("exit")

    with pytest.raises(RuntimeError, match="exit"):
        _watch_parent_loop(
            123,
            parent_state_file=str(state_file),
            poll_interval=0,
            exit_func=fake_exit,
            stale_after_seconds=0.1,
            alive_check=lambda _pid: True,
            state_file_fresh=lambda *_args, **_kwargs: False,
            sleep_fn=lambda _seconds: None,
        )

    assert exits == [0]
