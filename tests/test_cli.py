"""Test the command-line interface."""

import pytest
from click.testing import CliRunner

from nifc_wildfires import cli

FAKE_DATA = {"type": "FeatureCollection", "features": []}


@pytest.fixture
def runner(monkeypatch):
    """Return a command-line runner that never touches the network."""
    monkeypatch.setattr(cli, "get_active_perimeters", lambda: {"from": "perimeters"})
    monkeypatch.setattr(cli, "get_incidents", lambda: {"from": "incidents"})
    return CliRunner()


@pytest.mark.unit
def test_active_perimeters(runner):
    """Test that the active-perimeters command prints the perimeters data."""
    result = runner.invoke(cli.cmd, ["active-perimeters"])
    assert result.exit_code == 0
    assert "perimeters" in result.output


@pytest.mark.unit
def test_incidents(runner):
    """Test that the incidents command prints the incidents data."""
    result = runner.invoke(cli.cmd, ["incidents"])
    assert result.exit_code == 0
    assert "incidents" in result.output


@pytest.mark.unit
def test_help_lists_both_commands(runner):
    """Test that the help text lists both commands."""
    result = runner.invoke(cli.cmd, ["--help"])
    assert result.exit_code == 0
    assert "active-perimeters" in result.output
    assert "incidents" in result.output


@pytest.mark.unit
def test_unknown_command_fails(runner):
    """Test that an unknown command exits with an error."""
    assert runner.invoke(cli.cmd, ["nope"]).exit_code != 0
