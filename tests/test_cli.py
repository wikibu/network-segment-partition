"""End-to-end tests using `python -m nsp.cli` to verify exit codes, stdout, stderr."""

import json
import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "nsp.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_success_exits_zero_and_writes_stdout():
    r = run_cli("-c", "10.10.0.0/16", "-m", "/19", "/20")
    assert r.returncode == 0
    assert r.stdout
    assert "Parent: 10.10.0.0/16" in r.stdout
    assert r.stderr == ""


def test_json_output_parses():
    r = run_cli("-c", "10.10.0.0/16", "-m", "web=/19", "db=/20", "-f", "json")
    assert r.returncode == 0
    parsed = json.loads(r.stdout)
    assert parsed["parent"]["cidr"] == "10.10.0.0/16"
    assert parsed["allocated"][0]["label"] == "web"


def test_business_error_exits_one_and_writes_stderr():
    r = run_cli("-c", "10.10.0.0/24", "-m", "/23")
    assert r.returncode == 1
    assert r.stdout == ""
    assert "error:" in r.stderr
    assert "/23 is larger than parent" in r.stderr


def test_capacity_exceeded_alignment_hints_sort():
    r = run_cli("-c", "10.10.0.0/23", "-m", "/25", "/24", "/25")
    assert r.returncode == 1
    assert "--sort" in r.stderr


def test_capacity_exceeded_alignment_succeeds_with_sort():
    r = run_cli("-c", "10.10.0.0/23", "-m", "/25", "/24", "/25", "--sort")
    assert r.returncode == 0


def test_invalid_cidr_exits_one():
    r = run_cli("-c", "not-a-cidr", "-m", "/19")
    assert r.returncode == 1
    assert "invalid CIDR" in r.stderr


def test_missing_required_arg_exits_two():
    r = run_cli("-c", "10.10.0.0/16")
    assert r.returncode == 2
    assert "the following arguments are required" in r.stderr


def test_invalid_format_choice_exits_two():
    r = run_cli("-c", "10.10.0.0/16", "-m", "/19", "-f", "xml")
    assert r.returncode == 2


def test_version_flag():
    r = run_cli("--version")
    assert r.returncode == 0
    assert "nsp 0.1.0" in r.stdout
