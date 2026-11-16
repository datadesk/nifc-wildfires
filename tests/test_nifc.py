"""Test the NIFC downloads, with fake responses and against the live service."""

from datetime import UTC, datetime

import pytest

import nifc_wildfires

FAKE_DATA = {"type": "FeatureCollection", "features": []}


class FakeResponse:
    """A stand-in for a response from the NIFC service."""

    def __init__(self, status_code=200, data=None, invalid=False):
        """Store the status code and data to hand back."""
        self.status_code = status_code
        self.data = FAKE_DATA if data is None else data
        self.invalid = invalid

    def json(self):
        """Return the fake data, or fail as a broken reply would."""
        if self.invalid:
            raise ValueError("not JSON")
        return self.data


@pytest.fixture
def fake_get(monkeypatch):
    """Replace the network request and record the calls made."""
    calls = []
    state = {"response": FakeResponse(), "pages": []}

    def get(url, **kwargs):
        calls.append((url, kwargs))
        if state["pages"]:
            return state["pages"].pop(0)
        return state["response"]

    monkeypatch.setattr(nifc_wildfires.requests, "get", get)
    return calls, state


@pytest.mark.unit
def test_active_perimeters_asks_for_the_perimeters_service(fake_get):
    """Test that perimeters come from the perimeters service."""
    calls, _ = fake_get
    assert nifc_wildfires.get_active_perimeters() == FAKE_DATA
    assert "WFIGS_Interagency_Perimeters_Current" in calls[0][0]


@pytest.mark.unit
def test_incidents_asks_for_the_incidents_service(fake_get):
    """Test that incidents come from the incident locations service."""
    calls, _ = fake_get
    assert nifc_wildfires.get_incidents() == FAKE_DATA
    assert "WFIGS_Incident_Locations_Current" in calls[0][0]


@pytest.mark.unit
def test_request_asks_for_everything_as_geojson_with_a_timeout(fake_get):
    """Test the query asks for all rows and fields as GeoJSON, and can time out."""
    calls, _ = fake_get
    nifc_wildfires.get_incidents()
    _, kwargs = calls[0]
    assert kwargs["params"]["outFields"] == "*"
    assert kwargs["params"]["where"] == "1=1"
    assert kwargs["params"]["f"] == "geojson"
    assert kwargs["timeout"] == nifc_wildfires.TIMEOUT


@pytest.mark.unit
@pytest.mark.parametrize("function", ["get_active_perimeters", "get_incidents"])
def test_failed_request_raises_with_the_status_code(fake_get, function):
    """Test that a non-200 answer raises an error naming the status code."""
    _, state = fake_get
    state["response"] = FakeResponse(status_code=503)
    with pytest.raises(nifc_wildfires.NIFCError, match="503"):
        getattr(nifc_wildfires, function)()


@pytest.mark.unit
def test_error_reply_with_a_200_status_raises(fake_get):
    """Test that an error message inside a successful reply is not returned as data."""
    _, state = fake_get
    state["response"] = FakeResponse(data={"error": {"code": 400, "message": "bad"}})
    with pytest.raises(nifc_wildfires.NIFCError, match="API error"):
        nifc_wildfires.get_incidents()


@pytest.mark.unit
def test_invalid_json_raises(fake_get):
    """Test that a reply that is not JSON raises a clear error."""
    _, state = fake_get
    state["response"] = FakeResponse(invalid=True)
    with pytest.raises(nifc_wildfires.NIFCError, match="invalid JSON"):
        nifc_wildfires.get_incidents()


@pytest.mark.unit
@pytest.mark.parametrize("data", [["a"], {"type": "FeatureCollection"}])
def test_unexpected_reply_raises(fake_get, data):
    """Test that a reply that is not a list of features raises a clear error."""
    _, state = fake_get
    state["response"] = FakeResponse(data=data)
    with pytest.raises(nifc_wildfires.NIFCError):
        nifc_wildfires.get_incidents()


def page(count, more=None, top_level=False):
    """Build a fake reply with some features and an optional paging flag."""
    data = {"type": "FeatureCollection", "features": [{"type": "Feature"}] * count}
    if more is not None:
        if top_level:
            data["exceededTransferLimit"] = more
        else:
            data["properties"] = {"exceededTransferLimit": more}
    return FakeResponse(data=data)


@pytest.mark.unit
@pytest.mark.parametrize("top_level", [False, True])
def test_every_page_is_downloaded(fake_get, top_level):
    """Test that pages are followed until NIFC says there are no more."""
    calls, state = fake_get
    state["pages"] = [
        page(2, more=True, top_level=top_level),
        page(2, more=True, top_level=top_level),
        page(1, more=False, top_level=top_level),
    ]
    data = nifc_wildfires.get_incidents()
    assert len(data["features"]) == 5
    assert data["type"] == "FeatureCollection"
    assert [c[1]["params"]["resultOffset"] for c in calls] == [0, 2, 4]


@pytest.mark.unit
def test_options_shape_the_query(fake_get):
    """Test that the filter, fields and precision are sent to NIFC."""
    calls, _ = fake_get
    nifc_wildfires.get_active_perimeters(
        where="attr_IncidentTypeCategory='WF'",
        out_fields="OBJECTID",
        geometry_precision=5,
    )
    params = calls[0][1]["params"]
    assert params["where"] == "attr_IncidentTypeCategory='WF'"
    assert params["outFields"] == "OBJECTID"
    assert params["geometryPrecision"] == 5


@pytest.mark.unit
def test_precision_is_left_out_by_default(fake_get):
    """Test that coordinates are not rounded unless asked."""
    calls, _ = fake_get
    nifc_wildfires.get_incidents()
    assert "geometryPrecision" not in calls[0][1]["params"]


@pytest.mark.integration
def test_live_filter_and_fields():
    """Test that a live filter and field list change what comes back."""
    data = nifc_wildfires.get_active_perimeters(
        where="attr_IncidentTypeCategory='WF'",
        out_fields="OBJECTID,poly_IncidentName",
        geometry_precision=5,
    )
    for feature in data["features"]:
        assert set(feature["properties"]) <= {"OBJECTID", "poly_IncidentName"}


@pytest.mark.unit
def test_paging_asks_for_a_stable_order_and_page_size(fake_get):
    """Test that each page request sorts the same way and sets a page size."""
    calls, _ = fake_get
    nifc_wildfires.get_incidents()
    params = calls[0][1]["params"]
    assert params["orderByFields"] == "OBJECTID"
    assert params["resultRecordCount"] == nifc_wildfires.PAGE_SIZE


@pytest.mark.unit
def test_empty_page_with_more_to_come_raises(fake_get):
    """Test that paging that stalls is an error and not an endless loop."""
    _, state = fake_get
    state["pages"] = [page(1, more=True), page(0, more=True)]
    with pytest.raises(nifc_wildfires.NIFCError, match="paging ended"):
        nifc_wildfires.get_incidents()


@pytest.mark.unit
def test_too_many_pages_raises(fake_get, monkeypatch):
    """Test that the page safety limit stops a runaway download."""
    _, state = fake_get
    monkeypatch.setattr(nifc_wildfires, "MAX_PAGES", 3)
    state["response"] = page(1, more=True)
    with pytest.raises(nifc_wildfires.NIFCError, match="3-page safety limit"):
        nifc_wildfires.get_incidents()


@pytest.mark.unit
def test_invalid_paging_flag_raises(fake_get):
    """Test that a paging flag that is not true or false is an error."""
    _, state = fake_get
    state["response"] = page(1, more="yes")
    with pytest.raises(nifc_wildfires.NIFCError, match="paging flag"):
        nifc_wildfires.get_incidents()


@pytest.mark.integration
def test_live_paging_returns_everything(monkeypatch):
    """Test that tiny pages against the live service add up to the full count."""
    whole = nifc_wildfires.get_incidents()
    monkeypatch.setattr(nifc_wildfires, "PAGE_SIZE", 50)
    paged = nifc_wildfires.get_incidents()
    assert len(paged["features"]) == len(whole["features"])


@pytest.mark.integration
def test_live_active_perimeters():
    """Test that live active perimeters come back as polygons."""
    data = nifc_wildfires.get_active_perimeters()
    assert data["type"] == "FeatureCollection"
    for feature in data["features"]:
        assert feature["geometry"]["type"] in {"Polygon", "MultiPolygon"}


@pytest.mark.integration
def test_live_incidents():
    """Test that live incidents come back as points."""
    data = nifc_wildfires.get_incidents()
    assert data["type"] == "FeatureCollection"
    for feature in data["features"]:
        assert feature["geometry"]["type"] == "Point"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("function", "service"),
    [
        ("get_active_perimeters_last_edited", "WFIGS_Interagency_Perimeters_Current"),
        ("get_incidents_last_edited", "WFIGS_Incident_Locations_Current"),
    ],
)
def test_last_edited_reads_the_layer_metadata(fake_get, function, service):
    """Test that the last edit time comes from the right layer, in UTC."""
    calls, state = fake_get
    state["response"] = FakeResponse(
        data={"editingInfo": {"lastEditDate": 1794865327701}}
    )
    result = getattr(nifc_wildfires, function)()
    assert result == datetime(2026, 11, 16, 21, 42, 7, 701000, tzinfo=UTC)
    assert service in calls[0][0]
    assert calls[0][1]["params"] == {"f": "json"}


@pytest.mark.unit
@pytest.mark.parametrize(
    "data",
    [
        {},
        {"editingInfo": []},
        {"editingInfo": {}},
        {"editingInfo": {"lastEditDate": "soon"}},
        {"editingInfo": {"lastEditDate": True}},
        {"editingInfo": {"lastEditDate": 1e30}},
    ],
)
def test_last_edited_rejects_bad_metadata(fake_get, data):
    """Test that missing or nonsense edit times raise a clear error."""
    _, state = fake_get
    state["response"] = FakeResponse(data=data)
    with pytest.raises(nifc_wildfires.NIFCError):
        nifc_wildfires.get_incidents_last_edited()


@pytest.mark.integration
def test_live_last_edited():
    """Test that the live layers report a recent edit time in UTC."""
    for function in (
        nifc_wildfires.get_active_perimeters_last_edited,
        nifc_wildfires.get_incidents_last_edited,
    ):
        assert function().tzinfo is not None


@pytest.mark.unit
def test_custom_fetcher_is_used_for_every_request(fake_get):
    """Test that a supplied fetch function replaces the default web request."""
    default_calls, _ = fake_get
    mine = []

    def get(url, **kwargs):
        mine.append((url, kwargs))
        return FakeResponse(data={"editingInfo": {"lastEditDate": 0}})

    nifc_wildfires.get_incidents_last_edited(get=get)
    nifc_wildfires.get_active_perimeters_last_edited(get=get)
    assert len(mine) == 2
    assert mine[0][1]["timeout"] == nifc_wildfires.TIMEOUT
    assert default_calls == []


@pytest.mark.unit
@pytest.mark.parametrize("function", ["get_active_perimeters", "get_incidents"])
def test_custom_fetcher_downloads_every_page(fake_get, function):
    """Test that a supplied fetch function is used on every page."""
    default_calls, _ = fake_get
    pages = [page(1, more=True), page(1, more=False)]
    mine = []

    def get(url, **kwargs):
        mine.append(kwargs["params"]["resultOffset"])
        return pages.pop(0)

    data = getattr(nifc_wildfires, function)(get=get)
    assert len(data["features"]) == 2
    assert mine == [0, 1]
    assert default_calls == []


@pytest.mark.unit
def test_custom_fetcher_errors_are_checked_too(fake_get):
    """Test that replies from a supplied fetch function get the same checks."""

    def get(url, **kwargs):
        return FakeResponse(data={"error": {"code": 500}})

    with pytest.raises(nifc_wildfires.NIFCError, match="API error"):
        nifc_wildfires.get_incidents(get=get)
