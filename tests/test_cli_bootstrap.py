import pytest
import subprocess
import sys


def test_module_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "safeloop", "--help"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "SafeLoop Coding Agent Harness" in result.stdout
    assert "demo" in result.stdout
    assert "web" in result.stdout


def test_version_flag_prints_version():
    result = subprocess.run(
        [sys.executable, "-m", "safeloop", "--version"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip().startswith("safeloop ")


@pytest.mark.parametrize("command", ["web"])
def test_placeholder_commands_exit_one_and_report_not_yet_implemented(command):
    result = subprocess.run(
        [sys.executable, "-m", "safeloop", command],
        text=True,
        capture_output=True,
        check=False,
    )

    combined_output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 1
    assert "not yet implemented" in combined_output
