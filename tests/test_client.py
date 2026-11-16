"""Test the NIFC client class."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

import nifc_wildfires
from nifc_wildfires import (
    Layer,
    NIFCClient,
    NIFCError,
    NIFCValidationError,
    QueryOptions,
)


class Reply:
    """A stand-in for a response from the NIFC service."""

    status_code = 200

    def __init__(self, data):
        """Store the data to hand back."""
        self.data = data

    def json(self):
        """Return the fake data."""
        return self.data


def good_page(more=None, start=1, count=1):
    """Build a fake page of point features with IDs from ``start``."""
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "properties": {"OBJECTID": start + i},
            }
            for i in range(count)
        ],
    }
    if more is not None:
        data["properties"] = {"exceededTransferLimit": more}
    return Reply(data)


class Recorder:
    """A fetch function that records its calls and replays prepared replies."""

    def __init__(self, *replies):
        """Store the replies to hand back, in order."""
        self.replies = list(replies)
        self.calls = []

    def __call__(self, url, *, params, timeout):
        """Record the request and return the next reply."""
        self.calls.append((url, params, timeout))
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


@pytest.mark.unit
def test_defaults_match_the_module_settings():
    """Test that a bare client starts with the package's default settings."""
    client = NIFCClient()
    assert client.get is None
    assert client.strict is True
    assert client.timeout == nifc_wildfires.TIMEOUT
    assert client.page_size == nifc_wildfires.PAGE_SIZE
    assert client.max_pages == nifc_wildfires.MAX_PAGES
    assert client.max_attempts == nifc_wildfires.MAX_ATTEMPTS
    assert client.max_problems == nifc_wildfires.MAX_PROBLEMS


@pytest.mark.unit
def test_client_is_frozen_and_comparable():
    """Test that a client cannot be changed and compares by its settings."""
    client = NIFCClient(strict=False)
    assert client == NIFCClient(strict=False)
    with pytest.raises(FrozenInstanceError):
        client.strict = True


@pytest.mark.unit
@pytest.mark.parametrize(
    "name", ["timeout", "page_size", "max_pages", "max_attempts", "max_problems"]
)
@pytest.mark.parametrize("value", [0, -1])
def test_settings_must_be_above_zero(name, value):
    """Test that settings that could never work are rejected up front."""
    with pytest.raises(ValueError, match=f"{name} must be above zero"):
        NIFCClient(**{name: value})


@pytest.mark.unit
def test_settings_are_used_for_each_request():
    """Test that the timeout and page size reach every request."""
    fetch = Recorder(good_page())
    NIFCClient(get=fetch, timeout=7, page_size=25).get_incidents()
    url, params, timeout = fetch.calls[0]
    assert timeout == 7
    assert params["resultRecordCount"] == 25
    assert Layer.INCIDENTS.value in url


@pytest.mark.unit
def test_one_client_can_download_many_times():
    """Test that a client is reusable and keeps its settings between downloads."""
    fetch = Recorder(good_page())
    client = NIFCClient(get=fetch)
    client.get_incidents()
    client.get_incidents()
    assert len(fetch.calls) == 2


@pytest.mark.unit
def test_methods_choose_the_right_layer():
    """Test that each named method asks for its own layer."""
    fetch = Recorder(
        good_page(),
        Reply({"type": "FeatureCollection", "features": []}),
        Reply({"editingInfo": {"lastEditDate": 0}}),
        Reply({"editingInfo": {"lastEditDate": 0}}),
    )
    client = NIFCClient(get=fetch)
    client.get_incidents()
    client.get_active_perimeters()
    client.get_incidents_last_edited()
    client.get_active_perimeters_last_edited()
    urls = [call[0] for call in fetch.calls]
    assert Layer.INCIDENTS.value in urls[0]
    assert Layer.PERIMETERS.value in urls[1]
    assert Layer.INCIDENTS.value in urls[2]
    assert Layer.PERIMETERS.value in urls[3]


@pytest.mark.unit
def test_download_and_last_edited_take_any_layer():
    """Test the general methods that the named ones are built on."""
    fetch = Recorder(good_page(), Reply({"editingInfo": {"lastEditDate": 0}}))
    client = NIFCClient(get=fetch)
    assert len(client.download(Layer.INCIDENTS)["features"]) == 1
    assert client.last_edited(Layer.INCIDENTS) == datetime(1970, 1, 1, tzinfo=UTC)


@pytest.mark.unit
def test_page_limits_belong_to_the_client():
    """Test that paging limits come from the client's own settings."""
    fetch = Recorder(good_page(more=True, start=1), good_page(more=True, start=2))
    with pytest.raises(NIFCError, match="2-page safety limit"):
        NIFCClient(get=fetch, max_pages=2).get_incidents()


@pytest.mark.unit
def test_attempt_limit_belongs_to_the_client():
    """Test that how often a download starts over comes from the client."""
    repeat = [good_page(more=True, start=1), good_page(start=1)]
    fetch = Recorder(*repeat * 2)
    with pytest.raises(NIFCError, match="kept changing during 2 download attempts"):
        NIFCClient(get=fetch, max_attempts=2).get_incidents()
    assert len(fetch.calls) == 4


@pytest.mark.unit
def test_strictness_belongs_to_the_client():
    """Test that each client decides its own strictness."""
    bad = Reply(
        {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}}],
        }
    )
    with pytest.raises(NIFCValidationError):
        NIFCClient(get=Recorder(bad)).get_incidents()
    assert (
        len(NIFCClient(get=Recorder(bad), strict=False).get_incidents()["features"])
        == 1
    )


@pytest.mark.unit
def test_problem_limit_belongs_to_the_client():
    """Test that how many problems an error keeps comes from the client."""
    bad = Reply(
        {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}}] * 10,
        }
    )
    with pytest.raises(NIFCValidationError) as caught:
        NIFCClient(get=Recorder(bad), max_problems=3).get_incidents()
    assert len(caught.value.problems) == 3
    assert caught.value.problem_count == 10


@pytest.mark.unit
def test_options_pass_through_the_client():
    """Test that query options reach the request."""
    fetch = Recorder(good_page())
    NIFCClient(get=fetch).get_incidents(QueryOptions(where="a=1", geometry_precision=5))
    assert fetch.calls[0][1]["where"] == "a=1"
    assert fetch.calls[0][1]["geometryPrecision"] == 5


@pytest.mark.unit
def test_functions_are_shortcuts_for_a_client():
    """Test that the old functions give the same answer as a client does."""
    fetch = Recorder(good_page(count=3))
    assert (
        nifc_wildfires.get_incidents(get=fetch) == NIFCClient(get=fetch).get_incidents()
    )


@pytest.mark.unit
def test_functions_still_read_the_module_settings(monkeypatch):
    """Test that changing a module setting still changes the next download."""
    fetch = Recorder(good_page())
    monkeypatch.setattr(nifc_wildfires, "TIMEOUT", 3)
    monkeypatch.setattr(nifc_wildfires, "PAGE_SIZE", 11)
    nifc_wildfires.get_incidents(get=fetch)
    assert fetch.calls[0][2] == 3
    assert fetch.calls[0][1]["resultRecordCount"] == 11


@pytest.mark.unit
def test_everything_old_is_still_importable():
    """Test that every name that could be imported before still can be."""
    for name in (
        "BASE_URL",
        "TIMEOUT",
        "PAGE_SIZE",
        "MAX_PAGES",
        "MAX_ATTEMPTS",
        "MAX_PROBLEMS",
        "NIFCError",
        "NIFCValidationError",
        "ValidationProblem",
        "QueryOptions",
        "Layer",
        "Fetcher",
        "Reply",
        "get_active_perimeters",
        "get_incidents",
        "get_active_perimeters_last_edited",
        "get_incidents_last_edited",
    ):
        assert hasattr(nifc_wildfires, name), name
