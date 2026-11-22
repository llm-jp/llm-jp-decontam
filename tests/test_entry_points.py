"""The installed commands start and print their usage."""

import subprocess
import sysconfig
from pathlib import Path

import pytest


@pytest.mark.parametrize("command", ["decontam-stats", "decontam-filter"])
def test_command_prints_usage(command):
    executable = Path(sysconfig.get_path("scripts")) / command
    assert executable.exists(), f"{command} is not installed in this environment"
    result = subprocess.run([executable, "--help"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert result.stdout.startswith(f"usage: {command}")
