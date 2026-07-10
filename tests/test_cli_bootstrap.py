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
