"""Test the incident type codes and the options built on them."""

import pytest
from pydantic import ValidationError

from nifc_wildfires import IncidentType, Layer, NIFCClient, QueryOptions


class Reply:
    """A stand-in for a response from the NIFC service."""

    status_code = 200

    def json(self):
        """Return an empty page of features."""
        return {"type": "FeatureCollection", "features": []}


def asked_for(layer, options):
    """Download with a fake web and return the filter that was sent."""
    sent = []

    def fetch(url, *, params, timeout):
        sent.append(params["where"])
        return Reply()

    NIFCClient(get=fetch).download(layer, options)
    return sent[0]


@pytest.mark.unit
def test_codes_and_names():
    """Test that each kind of incident has its NIFC code."""
    assert {t.name: t.value for t in IncidentType} == {
        "WILDFIRE": "WF",
        "PRESCRIBED_FIRE": "RX",
        "COMPLEX": "CX",
    }
    assert IncidentType("RX") is IncidentType.PRESCRIBED_FIRE


@pytest.mark.unit
def test_each_layer_names_its_own_field():
    """Test that the two layers spell the incident type field differently."""
    assert Layer.PERIMETERS.incident_type_field == "attr_IncidentTypeCategory"
    assert Layer.INCIDENTS.incident_type_field == "IncidentTypeCategory"


@pytest.mark.unit
@pytest.mark.parametrize("layer", list(Layer))
def test_no_incident_types_leaves_the_filter_alone(layer):
    """Test that without type settings the filter is exactly what was given."""
    assert QueryOptions().where_for(layer) == "1=1"
    assert QueryOptions(where="OBJECTID > 5").where_for(layer) == "OBJECTID > 5"


@pytest.mark.unit
@pytest.mark.parametrize("layer", list(Layer))
def test_only_these_types(layer):
    """Test that incident_types builds an IN filter with the layer's field."""
    field = layer.incident_type_field
    options = QueryOptions(incident_types={IncidentType.WILDFIRE})
    assert options.where_for(layer) == f"{field} IN ('WF')"
    both = QueryOptions(incident_types={"CX", "WF"})
    assert both.where_for(layer) == f"{field} IN ('CX', 'WF')"


@pytest.mark.unit
@pytest.mark.parametrize("layer", list(Layer))
def test_exclude_types_keeps_records_with_no_type(layer):
    """Test that excluding a type does not drop records that have no type."""
    field = layer.incident_type_field
    options = QueryOptions(exclude_incident_types={IncidentType.PRESCRIBED_FIRE})
    assert options.where_for(layer) == f"({field} IS NULL OR {field} NOT IN ('RX'))"


@pytest.mark.unit
def test_type_settings_join_the_callers_own_filter():
    """Test that a hand-written filter and the types are both applied."""
    options = QueryOptions(where="OBJECTID > 5", incident_types={"WF"})
    assert (
        options.where_for(Layer.INCIDENTS)
        == "(OBJECTID > 5) AND IncidentTypeCategory IN ('WF')"
    )


@pytest.mark.unit
def test_codes_may_be_given_as_text():
    """Test that plain codes are turned into the typed values."""
    options = QueryOptions(incident_types=["WF"])
    assert options.incident_types == {IncidentType.WILDFIRE}


@pytest.mark.unit
@pytest.mark.parametrize(
    "settings",
    [
        {"incident_types": set()},
        {"incident_types": {"WF"}, "exclude_incident_types": {"RX"}},
        {"incident_types": {"ZZ"}},
        {"exclude_incident_types": {"ZZ"}},
    ],
)
def test_bad_type_settings_are_rejected(settings):
    """Test that empty, clashing or unknown incident types are rejected."""
    with pytest.raises(ValidationError):
        QueryOptions(**settings)


@pytest.mark.unit
@pytest.mark.parametrize("layer", list(Layer))
def test_download_sends_the_built_filter(layer):
    """Test that the filter built for the layer is the one sent to NIFC."""
    options = QueryOptions(incident_types={"WF"})
    assert asked_for(layer, options) == f"{layer.incident_type_field} IN ('WF')"


@pytest.mark.integration
def test_live_exclude_prescribed_fire():
    """Test that excluding RX removes prescribed burns from the live incidents."""
    fields = "OBJECTID,IncidentTypeCategory"
    everything = NIFCClient().get_incidents(QueryOptions(out_fields=fields))
    kept = NIFCClient().get_incidents(
        QueryOptions(out_fields=fields, exclude_incident_types={"RX"})
    )
    kinds = {f["properties"]["IncidentTypeCategory"] for f in kept["features"]}
    assert "RX" not in kinds
    assert len(kept["features"]) <= len(everything["features"])


@pytest.mark.integration
def test_live_only_wildfires():
    """Test that asking for wildfires only returns only wildfires."""
    options = QueryOptions(
        out_fields="OBJECTID,IncidentTypeCategory", incident_types={"WF"}
    )
    data = NIFCClient().get_incidents(options)
    assert {f["properties"]["IncidentTypeCategory"] for f in data["features"]} <= {"WF"}
