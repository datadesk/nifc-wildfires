"""Test the command-line interface, faking only the web request."""

import json
from datetime import UTC, datetime

import pytest
import requests
from click.testing import CliRunner

import nifc_wildfires
from nifc_wildfires import cli


class Reply:
    """A stand-in for a response from the NIFC service."""

    def __init__(self, data, status_code=200):
        """Store the data and status code to hand back."""
        self.data = data
        self.status_code = status_code

    def json(self):
        """Return the fake data."""
        return self.data


def feature(object_id, geometry="Point"):
    """Build a fake feature."""
    return {
        "type": "Feature",
        "geometry": {"type": geometry, "coordinates": [[0, 0]]},
        "properties": {"OBJECTID": object_id},
    }


def collection(*features):
    """Wrap features in a fake reply."""
    return Reply({"type": "FeatureCollection", "features": list(features)})


class Web:
    """A fake web that records requests and hands back prepared replies."""

    def __init__(self):
        """Start with one good point feature to hand back."""
        self.reply = collection(feature(1))
        self.error = None
        self.calls = []

    def __call__(self, url, *, params, timeout):
        """Record the request, then fail or reply."""
        self.calls.append((url, params, timeout))
        if self.error:
            raise self.error
        return self.reply


@pytest.fixture
def web(monkeypatch):
    """Replace the network with a fake that records what is asked of it."""
    fake = Web()
    monkeypatch.setattr(nifc_wildfires.requests, "get", fake)
    return fake


@pytest.fixture
def run():
    """Return a function that runs a command and captures both output streams."""
    runner = CliRunner()

    def invoke(*args):
        return runner.invoke(cli.cmd, list(args))

    return invoke


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command", "layer", "geometry"),
    [
        ("active-perimeters", "WFIGS_Interagency_Perimeters_Current", "Polygon"),
        ("incidents", "WFIGS_Incident_Locations_Current", "Point"),
    ],
)
def test_download_prints_valid_json(web, run, command, layer, geometry):
    """Test that each download command prints its layer's data as valid JSON."""
    web.reply = collection(feature(7, geometry))
    result = run(command)
    assert result.exit_code == 0
    assert json.loads(result.stdout)["features"][0]["properties"]["OBJECTID"] == 7
    assert layer in web.calls[0][0]


@pytest.mark.unit
def test_help_lists_every_command(run):
    """Test that the help text lists all three commands."""
    result = run("--help")
    assert result.exit_code == 0
    for name in ("active-perimeters", "incidents", "last-edited"):
        assert name in result.output


@pytest.mark.unit
@pytest.mark.parametrize("command", ["active-perimeters", "incidents"])
def test_defaults_ask_for_everything(web, run, command):
    """Test that nothing is filtered, and the default timeout applies."""
    web.reply = collection()
    run(command)
    _, params, timeout = web.calls[0]
    assert params["where"] == "1=1"
    assert params["outFields"] == "*"
    assert "geometryPrecision" not in params
    assert timeout == nifc_wildfires.TIMEOUT


@pytest.mark.unit
@pytest.mark.parametrize("command", ["active-perimeters", "incidents"])
def test_query_options_reach_the_request(web, run, command):
    """Test that the filter, field and precision options reach the request."""
    web.reply = collection()
    result = run(
        command,
        "--where",
        "a=1",
        "--out-fields",
        "OBJECTID",
        "--geometry-precision",
        "5",
    )
    assert result.exit_code == 0
    params = web.calls[0][1]
    assert (params["where"], params["outFields"], params["geometryPrecision"]) == (
        "a=1",
        "OBJECTID",
        5,
    )


@pytest.mark.unit
@pytest.mark.parametrize("command", ["active-perimeters", "incidents", "last-edited"])
def test_timeout_reaches_the_request(web, run, command):
    """Test that --timeout sets how long each request may take."""
    web.reply = collection()
    args = [command, "incidents"] if command == "last-edited" else [command]
    if command == "last-edited":
        web.reply = Reply({"editingInfo": {"lastEditDate": 0}})
    run(*args, "--timeout", "12.5")
    assert web.calls[0][2] == 12.5


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["0", "-3", "soon"])
def test_bad_timeout_is_a_usage_error(web, run, bad):
    """Test that a timeout that makes no sense is rejected before any request."""
    result = run("incidents", "--timeout", bad)
    assert result.exit_code == 2
    assert web.calls == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad",
    [["--where", ""], ["--out-fields", ""], ["--geometry-precision", "-1"]],
)
def test_invalid_options_are_a_usage_error(web, run, bad):
    """Test that a nonsense option is reported plainly and nothing downloads."""
    result = run("incidents", *bad)
    assert result.exit_code == 2
    assert "Error" in result.output
    assert web.calls == []


def bad_reply(count=1):
    """Build a reply of features with no shape, which fail the checks."""
    return Reply(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"OBJECTID": i}} for i in range(count)
            ],
        }
    )


@pytest.mark.unit
def test_strict_failure_is_a_short_error_with_a_hint(web, run):
    """Test that bad data is one clear message and a failing exit code."""
    web.reply = bad_reply()
    result = run("incidents")
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Error: NIFC reply is not in the expected shape" in result.stderr
    assert "--verbose" in result.stderr
    assert "--no-strict" in result.stderr
    assert "Traceback" not in result.output


@pytest.mark.unit
def test_verbose_lists_every_problem(web, run):
    """Test that --verbose lists each problem and says how many there were."""
    web.reply = bad_reply(count=5)
    result = run("incidents", "--verbose")
    assert result.exit_code == 1
    assert "5 problem(s) in all, 5 shown" in result.stderr
    for i in range(5):
        assert f"features.{i}.geometry: Field required" in result.stderr
    assert "--verbose" not in result.stderr


@pytest.mark.unit
def test_no_strict_prints_the_data_anyway(web, run):
    """Test that --no-strict prints data that fails the checks."""
    web.reply = bad_reply(count=2)
    result = run("incidents", "--no-strict")
    assert result.exit_code == 0
    assert len(json.loads(result.stdout)["features"]) == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    ("setup", "message"),
    [
        (lambda w: setattr(w, "reply", Reply({}, status_code=503)), "503"),
        (lambda w: setattr(w, "reply", Reply({"error": {"code": 400}})), "API error"),
        (
            lambda w: setattr(w, "error", requests.Timeout("slow")),
            "did not answer in time",
        ),
        (
            lambda w: setattr(w, "error", requests.ConnectionError("down")),
            "Could not reach NIFC",
        ),
    ],
)
@pytest.mark.parametrize(
    "command", [["active-perimeters"], ["incidents"], ["last-edited", "incidents"]]
)
def test_other_failures_are_short_errors_too(web, run, setup, message, command):
    """Test that failed requests and NIFC errors never print a traceback."""
    setup(web)
    result = run(*command)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert message in result.stderr
    assert "Traceback" not in result.output


@pytest.mark.unit
@pytest.mark.parametrize(
    ("layer", "service"),
    [
        ("active-perimeters", "WFIGS_Interagency_Perimeters_Current"),
        ("incidents", "WFIGS_Incident_Locations_Current"),
    ],
)
def test_last_edited_prints_the_time(web, run, layer, service):
    """Test that last-edited prints an ISO time in UTC for the chosen layer."""
    web.reply = Reply({"editingInfo": {"lastEditDate": 1794865327701}})
    result = run("last-edited", layer)
    assert result.exit_code == 0
    printed = datetime.fromisoformat(result.stdout.strip())
    assert printed == datetime(2026, 11, 16, 21, 42, 7, 701000, tzinfo=UTC)
    assert service in web.calls[0][0]


@pytest.mark.unit
def test_last_edited_needs_a_known_layer(web, run):
    """Test that last-edited rejects a missing or unknown layer."""
    assert run("last-edited").exit_code == 2
    assert run("last-edited", "nope").exit_code == 2
    assert web.calls == []


@pytest.mark.unit
def test_last_edited_bad_metadata_is_a_clear_error(web, run):
    """Test that an unusable edit time is a short error, not a traceback."""
    web.reply = Reply({"editingInfo": {}})
    result = run("last-edited", "incidents")
    assert result.exit_code == 1
    assert "layer metadata" in result.stderr


@pytest.mark.unit
def test_connection_errors_are_short_unless_verbose(web, run):
    """Test that the long technical detail of a connection failure needs --verbose."""
    web.error = requests.ConnectionError("pool exhausted: very long details")
    short = run("incidents")
    assert "Could not reach NIFC (ConnectionError)" in short.stderr
    assert "very long details" not in short.stderr
    detailed = run("incidents", "--verbose")
    assert "very long details" in detailed.stderr


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command", "field"),
    [
        ("active-perimeters", "attr_IncidentTypeCategory"),
        ("incidents", "IncidentTypeCategory"),
    ],
)
def test_incident_type_flags_build_the_filter(web, run, command, field):
    """Test that the type flags reach the request, in any letter case."""
    web.reply = collection()
    run(command, "--incident-type", "wf", "--incident-type", "CX")
    assert web.calls[0][1]["where"] == f"{field} IN ('CX', 'WF')"
    run(command, "--exclude-incident-type", "rx")
    assert web.calls[1][1]["where"] == f"({field} IS NULL OR {field} NOT IN ('RX'))"


@pytest.mark.unit
def test_incident_type_flags_join_where(web, run):
    """Test that --where and a type flag are both applied."""
    web.reply = collection()
    run("incidents", "--where", "OBJECTID > 5", "--exclude-incident-type", "RX")
    assert web.calls[0][1]["where"].startswith("(OBJECTID > 5) AND ")


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad",
    [
        ["--incident-type", "ZZ"],
        ["--exclude-incident-type", "ZZ"],
        ["--incident-type", "WF", "--exclude-incident-type", "RX"],
    ],
)
def test_bad_incident_type_flags_are_a_usage_error(web, run, bad):
    """Test that unknown codes, or keeping and excluding together, are rejected."""
    result = run("incidents", *bad)
    assert result.exit_code == 2
    assert "Error" in result.output
    assert web.calls == []


@pytest.mark.unit
def test_keep_and_exclude_error_says_why(web, run):
    """Test that the clash message is not blank."""
    result = run("incidents", "--incident-type", "WF", "--exclude-incident-type", "RX")
    assert "not both" in result.output


@pytest.mark.unit
def test_incidents_help_says_prescribed_burns_are_included(run):
    """Test that the command help makes clear that prescribed burns are in there."""
    assert "prescribed burns" in " ".join(run("incidents", "--help").output.split())


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "service", "geometry"),
    [
        ("current-perimeters", "WFIGS_Interagency_Perimeters_Current", "Polygon"),
        ("current-incidents", "WFIGS_Incident_Locations_Current", "Point"),
        ("incidents-last-24-hours", "WFIGS_Incident_Locations_Last24h", "Point"),
        ("incidents-year-to-date", "WFIGS_Incident_Locations_YearToDate", "Point"),
        (
            "perimeters-year-to-date",
            "WFIGS_Interagency_Perimeters_YearToDate",
            "MultiPolygon",
        ),
    ],
)
def test_download_command_reaches_every_layer(web, run, name, service, geometry):
    """Test that the download command asks the right service for each layer."""
    web.reply = collection(feature(3, geometry))
    result = run("download", name)
    assert result.exit_code == 0
    assert service in web.calls[0][0]
    assert json.loads(result.stdout)["features"][0]["properties"]["OBJECTID"] == 3


@pytest.mark.unit
def test_download_command_takes_the_same_options(web, run):
    """Test that download accepts the filters, precision, timeout and strict flags."""
    web.reply = collection()
    result = run(
        "download",
        "incidents-year-to-date",
        "--exclude-incident-type",
        "RX",
        "--out-fields",
        "OBJECTID",
        "--geometry-precision",
        "3",
        "--timeout",
        "90",
        "--no-strict",
    )
    assert result.exit_code == 0
    _, params, timeout = web.calls[0]
    assert "IncidentTypeCategory" in params["where"]
    assert (params["outFields"], params["geometryPrecision"], timeout) == (
        "OBJECTID",
        3,
        90,
    )


@pytest.mark.unit
def test_download_command_needs_a_known_layer(web, run):
    """Test that download rejects a missing or unknown layer."""
    assert run("download").exit_code == 2
    assert run("download", "everything").exit_code == 2
    assert web.calls == []


@pytest.mark.unit
def test_the_named_commands_still_use_the_current_layers(web, run):
    """Test that active-perimeters and incidents keep downloading the current layers."""
    web.reply = collection()
    run("active-perimeters")
    run("incidents")
    assert web.calls[0][0].endswith(
        "WFIGS_Interagency_Perimeters_Current/FeatureServer/0/query"
    )
    assert web.calls[1][0].endswith(
        "WFIGS_Incident_Locations_Current/FeatureServer/0/query"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "service"),
    [
        ("active-perimeters", "WFIGS_Interagency_Perimeters_Current"),
        ("incidents", "WFIGS_Incident_Locations_Current"),
        ("current-incidents", "WFIGS_Incident_Locations_Current"),
        ("incidents-last-24-hours", "WFIGS_Incident_Locations_Last24h"),
        ("incidents-year-to-date", "WFIGS_Incident_Locations_YearToDate"),
        ("perimeters-year-to-date", "WFIGS_Interagency_Perimeters_YearToDate"),
    ],
)
def test_last_edited_accepts_every_layer(web, run, name, service):
    """Test that last-edited works for the old names and for every layer."""
    web.reply = Reply({"editingInfo": {"lastEditDate": 0}})
    result = run("last-edited", name)
    assert result.exit_code == 0
    assert service in web.calls[0][0]


@pytest.mark.unit
def test_help_does_not_claim_the_current_incidents_are_the_whole_year(run):
    """Test that the incidents help says it is not the whole year."""
    text = " ".join(run("incidents", "--help").output.split())
    assert "Not the whole year" in text
    assert "YTD" not in text
    assert "YTD" not in run("--help").output
