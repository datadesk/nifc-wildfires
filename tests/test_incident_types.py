"""Test the incident type codes and the options built on them."""

import pytest
from pydantic import ValidationError

from nifc_wildfires import IncidentKind, IncidentType, Layer, NIFCClient, QueryOptions


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
def test_codes_follow_the_nwcg_standard():
    """Test that each category has its NWCG code, kind and name."""
    expected = {
        "DF": ("FI", "Debris / Product Fire"),
        "NS": ("FI", "Non-Statistical / Other"),
        "RX": ("FI", "Prescribed Fire"),
        "SF": ("FI", "Structure Fire"),
        "VF": ("FI", "Vehicle Fire"),
        "WF": ("FI", "Wildfire"),
        "BR": ("FM", "Emergency Stabilization"),
        "FA": ("FM", "False Alarm"),
        "FR": ("FM", "Fire Rehabilitation"),
        "CX": ("FM", "Incident Complex"),
        "SU": ("FM", "Incident / Event Support"),
        "OR": ("FM", "Out of Area Response"),
        "PP": ("FM", "Preparedness / Prepositioning"),
    }
    assert {t.value: (t.kind.value, t.label) for t in IncidentType} == expected
    assert IncidentType("RX") is IncidentType.PRESCRIBED_FIRE


@pytest.mark.unit
def test_kinds():
    """Test the two fire kinds and their names."""
    assert {k.value: k.label for k in IncidentKind} == {
        "FI": "Fire",
        "FM": "Fire Management Action",
    }


@pytest.mark.unit
def test_complexes_are_fire_management_not_fire():
    """Test that the standard puts complexes in the fire management kind."""
    assert IncidentType.COMPLEX.kind is IncidentKind.FIRE_MANAGEMENT_ACTION
    assert IncidentType.WILDFIRE.kind is IncidentKind.FIRE


@pytest.mark.integration
def test_live_codes_are_all_defined():
    """Test that every category NIFC uses today is one the standard defines."""
    small_layers = [
        Layer.CURRENT_PERIMETERS,
        Layer.CURRENT_INCIDENTS,
        Layer.INCIDENTS_LAST_24_HOURS,
    ]
    for layer in small_layers:
        field = layer.incident_type_field
        data = NIFCClient().download(
            layer, QueryOptions(out_fields=f"OBJECTID,{field}")
        )
        seen = {f["properties"][field] for f in data["features"]}
        assert seen <= {t.value for t in IncidentType}, seen


@pytest.mark.integration
def test_live_kind_matches_category():
    """Test that NIFC's own kind for each record matches the standard's."""
    data = NIFCClient().get_incidents(
        QueryOptions(out_fields="OBJECTID,IncidentTypeCategory,IncidentTypeKind")
    )
    for f in data["features"]:
        props = f["properties"]
        category = IncidentType(props["IncidentTypeCategory"])
        assert category.kind.value == props["IncidentTypeKind"]


@pytest.mark.unit
def test_each_layer_names_its_own_field():
    """Test that the two layers spell the incident type field differently."""
    assert Layer.CURRENT_PERIMETERS.incident_type_field == "attr_IncidentTypeCategory"
    assert Layer.CURRENT_INCIDENTS.incident_type_field == "IncidentTypeCategory"


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
        options.where_for(Layer.CURRENT_INCIDENTS)
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


@pytest.mark.unit
def test_every_layer_has_a_distinct_service_and_command_name():
    """Test that the five layers have their own service and command-line name."""
    assert len({layer.value for layer in Layer}) == 5
    assert [layer.cli_name for layer in Layer] == [
        "current-perimeters",
        "current-incidents",
        "incidents-last-24-hours",
        "incidents-year-to-date",
        "perimeters-year-to-date",
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("layer", "service", "polygons"),
    [
        (Layer.CURRENT_PERIMETERS, "WFIGS_Interagency_Perimeters_Current", True),
        (Layer.CURRENT_INCIDENTS, "WFIGS_Incident_Locations_Current", False),
        (Layer.INCIDENTS_LAST_24_HOURS, "WFIGS_Incident_Locations_Last24h", False),
        (Layer.INCIDENTS_YEAR_TO_DATE, "WFIGS_Incident_Locations_YearToDate", False),
        (
            Layer.PERIMETERS_YEAR_TO_DATE,
            "WFIGS_Interagency_Perimeters_YearToDate",
            True,
        ),
    ],
)
def test_layers_name_their_service_shape_and_field(layer, service, polygons):
    """Test each layer's service, allowed shapes and incident type field."""
    assert layer.value == service
    assert layer.is_perimeters is polygons
    assert layer.geometry_types == (
        {"Polygon", "MultiPolygon"} if polygons else {"Point"}
    )
    assert layer.incident_type_field == (
        "attr_IncidentTypeCategory" if polygons else "IncidentTypeCategory"
    )


@pytest.mark.unit
def test_the_old_ambiguous_layer_names_are_gone():
    """Test that nothing called just INCIDENTS or PERIMETERS can be mistaken for all."""
    assert not hasattr(Layer, "INCIDENTS")
    assert not hasattr(Layer, "PERIMETERS")


@pytest.mark.integration
@pytest.mark.parametrize(
    "layer", [Layer.INCIDENTS_LAST_24_HOURS, Layer.CURRENT_INCIDENTS]
)
def test_live_small_incident_layers_pass_the_strict_checks(layer):
    """Test that the real data in the small incident layers passes every check."""
    field = layer.incident_type_field
    data = NIFCClient().download(layer, QueryOptions(out_fields=f"OBJECTID,{field}"))
    assert {f["properties"][field] for f in data["features"]} <= {
        t.value for t in IncidentType
    }


@pytest.mark.integration
def test_live_year_to_date_perimeters_slice_passes_the_strict_checks():
    """Test a slice of the large year-to-date perimeters, which are too big to fetch."""
    options = QueryOptions(
        out_fields="OBJECTID,attr_IncidentTypeCategory",
        geometry_precision=0,
        incident_types={IncidentType.PRESCRIBED_FIRE},
        where="OBJECTID > 0",
    )
    data = NIFCClient().download(Layer.PERIMETERS_YEAR_TO_DATE, options)
    kinds = {f["properties"]["attr_IncidentTypeCategory"] for f in data["features"]}
    assert kinds <= {"RX"}
    assert data["features"]


@pytest.mark.unit
def test_type_information_ships_with_the_package():
    """Test that the py.typed marker is in the package, so others see our types."""
    from importlib.resources import files

    assert files("nifc_wildfires").joinpath("py.typed").is_file()
