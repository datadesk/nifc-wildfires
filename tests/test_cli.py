"""Test the command-line interface."""

import json

import pytest
from click.testing import CliRunner

from nifc_wildfires import QueryOptions, cli

FAKE_DATA = {"type": "FeatureCollection", "features": []}


@pytest.fixture
def runner(monkeypatch):
    """Return a command-line runner that never touches the network."""
    calls = {}

    def fake(name):
        def get(*args, **kwargs):
            calls[name] = (args, kwargs)
            return {"from": name}

        return get

    monkeypatch.setattr(cli, "get_active_perimeters", fake("perimeters"))
    monkeypatch.setattr(cli, "get_incidents", fake("incidents"))
    runner = CliRunner()
    runner.calls = calls
    return runner


@pytest.mark.unit
def test_active_perimeters(runner):
    """Test that the active-perimeters command prints the data as valid JSON."""
    result = runner.invoke(cli.cmd, ["active-perimeters"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"from": "perimeters"}


@pytest.mark.unit
def test_incidents(runner):
    """Test that the incidents command prints the data as valid JSON."""
    result = runner.invoke(cli.cmd, ["incidents"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"from": "incidents"}


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


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command", "name"),
    [("active-perimeters", "perimeters"), ("incidents", "incidents")],
)
def test_defaults_ask_for_everything(runner, command, name):
    """Test that the commands download everything unless told otherwise."""
    runner.invoke(cli.cmd, [command])
    assert runner.calls[name] == ((QueryOptions(),), {"strict": True})


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command", "name"),
    [("active-perimeters", "perimeters"), ("incidents", "incidents")],
)
def test_options_are_passed_along(runner, command, name):
    """Test that the filter, field and precision options reach the download."""
    result = runner.invoke(
        cli.cmd,
        [
            command,
            "--where",
            "a=1",
            "--out-fields",
            "OBJECTID",
            "--geometry-precision",
            "5",
        ],
    )
    assert result.exit_code == 0
    options = QueryOptions(where="a=1", out_fields="OBJECTID", geometry_precision=5)
    assert runner.calls[name] == ((options,), {"strict": True})


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad",
    [["--where", ""], ["--out-fields", ""], ["--geometry-precision", "-1"]],
)
def test_invalid_options_are_a_usage_error(runner, bad):
    """Test that a nonsense option is reported plainly and nothing downloads."""
    result = runner.invoke(cli.cmd, ["incidents", *bad])
    assert result.exit_code == 2
    assert "Error" in result.output
    assert runner.calls == {}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command", "name"),
    [("active-perimeters", "perimeters"), ("incidents", "incidents")],
)
def test_no_strict_is_passed_along(runner, command, name):
    """Test that --no-strict reaches the download, and --strict is the default."""
    runner.invoke(cli.cmd, [command, "--no-strict"])
    assert runner.calls[name][1] == {"strict": False}
    runner.invoke(cli.cmd, [command, "--strict"])
    assert runner.calls[name][1] == {"strict": True}
