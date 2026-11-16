"""Test the NIFC downloads, with fake responses and against the live service."""

import pytest

import nifc_wildfires

FAKE_DATA = {"type": "FeatureCollection", "features": []}


class FakeResponse:
    """A stand-in for a response from the NIFC service."""

    def __init__(self, status_code=200, data=None):
        """Store the status code and data to hand back."""
        self.status_code = status_code
        self.data = FAKE_DATA if data is None else data

    def json(self):
        """Return the fake data."""
        return self.data


@pytest.fixture
def fake_get(monkeypatch):
    """Replace the network request and record the calls made."""
    calls = []
    state = {"response": FakeResponse()}

    def get(url, **kwargs):
        calls.append((url, kwargs))
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
    url, kwargs = calls[0]
    assert "outFields=*" in url
    assert "where=1%3D1" in url
    assert "f=geojson" in url
    assert kwargs["timeout"] == nifc_wildfires.TIMEOUT


@pytest.mark.unit
@pytest.mark.parametrize("function", ["get_active_perimeters", "get_incidents"])
def test_failed_request_raises_with_the_status_code(fake_get, function):
    """Test that a non-200 answer raises an error naming the status code."""
    _, state = fake_get
    state["response"] = FakeResponse(status_code=503)
    with pytest.raises(Exception, match="503"):
        getattr(nifc_wildfires, function)()


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
