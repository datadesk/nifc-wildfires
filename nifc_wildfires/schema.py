"""Typed objects for what callers ask for and what NIFC sends back."""

from enum import StrEnum
from typing import Any, Literal, Protocol, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    ValidationInfo,
    field_validator,
    model_validator,
)


class IncidentKind(StrEnum):
    """The broad kind of event, from the NWCG Event Kind standard.

    The standard defines nine kinds. Only these two describe fire, and only these
    two appear in NIFC's fire layers, so only these two are listed here.

    Examples:
        >>> IncidentKind("FM").label
        'Fire Management Action'
    """

    FIRE = "FI"
    FIRE_MANAGEMENT_ACTION = "FM"

    @property
    def label(self) -> str:
        """The name the standard gives this kind.

        Returns:
            The kind's name.

        Examples:
            >>> IncidentKind.FIRE.label
            'Fire'
        """
        return "Fire" if self is IncidentKind.FIRE else "Fire Management Action"


class IncidentType(StrEnum):
    """The categories of incident NIFC labels its records with.

    These are the fire and fire management categories of the NWCG Event Kind and
    Event Category standard, dated December 14, 2021, which is what NIFC's
    ``IncidentTypeCategory`` field holds. NIFC's own layers do not define the
    codes. The standard also has categories for hazards, accidents, training and
    other events that are not fire, which do not belong in these layers.

    Prescribed burns (``RX``) are fires lit on purpose, to manage land. They are
    in the incident points by default, and are most of them at the time of
    writing, so leave them out with ``exclude_incident_types`` if you want
    wildfires only. A complex (``CX``) is two or more wildfires in the same area
    managed together, and it is in the fire management kind.

    Not every category appears in NIFC's data. At the time of writing only
    ``WF``, ``RX`` and ``CX`` do.

    Examples:
        >>> IncidentType.PRESCRIBED_FIRE.value
        'RX'
        >>> IncidentType("WF") is IncidentType.WILDFIRE
        True
        >>> IncidentType.COMPLEX.kind is IncidentKind.FIRE_MANAGEMENT_ACTION
        True
    """

    DEBRIS_FIRE = "DF"
    NON_STATISTICAL = "NS"
    PRESCRIBED_FIRE = "RX"
    STRUCTURE_FIRE = "SF"
    VEHICLE_FIRE = "VF"
    WILDFIRE = "WF"
    EMERGENCY_STABILIZATION = "BR"
    FALSE_ALARM = "FA"
    FIRE_REHABILITATION = "FR"
    COMPLEX = "CX"
    INCIDENT_SUPPORT = "SU"
    OUT_OF_AREA_RESPONSE = "OR"
    PREPAREDNESS = "PP"

    @property
    def kind(self) -> IncidentKind:
        """The kind this category belongs to.

        Returns:
            ``FIRE`` or ``FIRE_MANAGEMENT_ACTION``.

        Examples:
            >>> IncidentType.WILDFIRE.kind
            <IncidentKind.FIRE: 'FI'>
        """
        return _INCIDENT_TYPE_INFO[self][0]

    @property
    def label(self) -> str:
        """The name the standard gives this category.

        Returns:
            The category's name.

        Examples:
            >>> IncidentType.COMPLEX.label
            'Incident Complex'
        """
        return _INCIDENT_TYPE_INFO[self][1]


_FIRE = IncidentKind.FIRE
_MANAGEMENT = IncidentKind.FIRE_MANAGEMENT_ACTION
_INCIDENT_TYPE_INFO: dict[IncidentType, tuple[IncidentKind, str]] = {
    IncidentType.DEBRIS_FIRE: (_FIRE, "Debris / Product Fire"),
    IncidentType.NON_STATISTICAL: (_FIRE, "Non-Statistical / Other"),
    IncidentType.PRESCRIBED_FIRE: (_FIRE, "Prescribed Fire"),
    IncidentType.STRUCTURE_FIRE: (_FIRE, "Structure Fire"),
    IncidentType.VEHICLE_FIRE: (_FIRE, "Vehicle Fire"),
    IncidentType.WILDFIRE: (_FIRE, "Wildfire"),
    IncidentType.EMERGENCY_STABILIZATION: (_MANAGEMENT, "Emergency Stabilization"),
    IncidentType.FALSE_ALARM: (_MANAGEMENT, "False Alarm"),
    IncidentType.FIRE_REHABILITATION: (_MANAGEMENT, "Fire Rehabilitation"),
    IncidentType.COMPLEX: (_MANAGEMENT, "Incident Complex"),
    IncidentType.INCIDENT_SUPPORT: (_MANAGEMENT, "Incident / Event Support"),
    IncidentType.OUT_OF_AREA_RESPONSE: (_MANAGEMENT, "Out of Area Response"),
    IncidentType.PREPAREDNESS: (_MANAGEMENT, "Preparedness / Prepositioning"),
}


class Layer(StrEnum):
    """The NIFC layers this package can download, named by their service.

    Examples:
        >>> Layer.INCIDENTS.value
        'WFIGS_Incident_Locations_Current'
        >>> sorted(Layer.PERIMETERS.geometry_types)
        ['MultiPolygon', 'Polygon']
    """

    PERIMETERS = "WFIGS_Interagency_Perimeters_Current"
    INCIDENTS = "WFIGS_Incident_Locations_Current"

    @property
    def geometry_types(self) -> frozenset[str]:
        """The GeoJSON geometry types this layer should return.

        Returns:
            The allowed geometry type names.

        Examples:
            >>> sorted(Layer.INCIDENTS.geometry_types)
            ['Point']
        """
        if self is Layer.PERIMETERS:
            return frozenset({"Polygon", "MultiPolygon"})
        return frozenset({"Point"})

    @property
    def incident_type_field(self) -> str:
        """The name of the field that holds the incident type in this layer.

        The two layers spell it differently, which is easy to get wrong in a
        hand-written filter.

        Returns:
            The field name.

        Examples:
            >>> Layer.INCIDENTS.incident_type_field
            'IncidentTypeCategory'
            >>> Layer.PERIMETERS.incident_type_field
            'attr_IncidentTypeCategory'
        """
        if self is Layer.PERIMETERS:
            return "attr_IncidentTypeCategory"
        return "IncidentTypeCategory"


class QueryOptions(BaseModel):
    """The settings that shape which data a download returns.

    The defaults return every feature and every field, with coordinates exactly
    as NIFC sends them. Mistakes such as an empty filter, a negative precision or
    a misspelled setting are rejected when the object is created.

    Attributes:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The number of decimal places to keep in coordinates,
            or None to keep everything NIFC sends.
        incident_types: If given, return only these kinds of incident.
        exclude_incident_types: Leave out these kinds of incident. Records with
            no incident type are kept. This cannot be combined with
            ``incident_types``.

    Examples:
        >>> options = QueryOptions(
        ...     out_fields="OBJECTID,poly_IncidentName",
        ...     geometry_precision=5,
        ...     incident_types={IncidentType.WILDFIRE},
        ... )
        >>> QueryOptions().out_fields
        '*'
        >>> QueryOptions(exclude_incident_types={"RX"}).where_for(Layer.INCIDENTS)
        "(IncidentTypeCategory IS NULL OR IncidentTypeCategory NOT IN ('RX'))"
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    where: str = Field(default="1=1", min_length=1)
    out_fields: str = Field(default="*", min_length=1)
    geometry_precision: int | None = Field(default=None, ge=0)
    incident_types: frozenset[IncidentType] | None = None
    exclude_incident_types: frozenset[IncidentType] = frozenset()

    @model_validator(mode="after")
    def check_incident_types(self) -> Self:
        """Reject incident type settings that make no sense together.

        Returns:
            The same options.

        Raises:
            ValueError: If ``incident_types`` is empty, or is combined with
                ``exclude_incident_types``.

        Examples:
            >>> QueryOptions(incident_types=set())  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
            ...
            pydantic_core._pydantic_core.ValidationError: incident_types cannot be empty
        """
        if self.incident_types is not None and not self.incident_types:
            raise ValueError(
                "incident_types cannot be empty. Leave it out to keep every type."
            )
        if self.incident_types and self.exclude_incident_types:
            raise ValueError("Use incident_types or exclude_incident_types, not both.")
        return self

    def where_for(self, layer: Layer) -> str:
        """Build the filter to send to NIFC for a layer.

        This joins the ``where`` filter with any incident type settings, using the
        field name that this layer calls the incident type.

        Args:
            layer: The layer the filter is for.

        Returns:
            The filter. With no incident type settings it is ``where`` as given.

        Examples:
            >>> QueryOptions(incident_types={"WF"}).where_for(Layer.PERIMETERS)
            "attr_IncidentTypeCategory IN ('WF')"
            >>> QueryOptions(where="OBJECTID > 5").where_for(Layer.INCIDENTS)
            'OBJECTID > 5'
        """
        field = layer.incident_type_field
        clauses = []
        if self.incident_types:
            codes = ", ".join(f"'{t.value}'" for t in sorted(self.incident_types))
            clauses.append(f"{field} IN ({codes})")
        if self.exclude_incident_types:
            codes = ", ".join(
                f"'{t.value}'" for t in sorted(self.exclude_incident_types)
            )
            clauses.append(f"({field} IS NULL OR {field} NOT IN ({codes}))")
        if not clauses:
            return self.where
        if self.where != "1=1":
            clauses.insert(0, f"({self.where})")
        return " AND ".join(clauses)


class Reply(Protocol):
    """What a fetcher must hand back: a status code and a way to read the JSON.

    A ``requests.Response`` fits this.
    """

    status_code: int

    def json(self) -> object:
        """Read the body of the reply as JSON.

        Returns:
            The parsed JSON.
        """
        ...


class Fetcher(Protocol):
    """A function that makes a web request for this package.

    Pass one as ``get`` to add retries, logging or custom headers. ``requests.get``
    fits this, and is the default.

    Examples:
        >>> import requests
        >>> fetcher: Fetcher = requests.get
    """

    def __call__(self, url: str, *, params: dict[str, Any], timeout: float) -> Reply:
        """Request a web address.

        Args:
            url: The address to request.
            params: The query parameters to send.
            timeout: The seconds to wait before giving up.

        Returns:
            The reply.
        """
        ...


class Geometry(BaseModel):
    """A GeoJSON geometry. Only its type and the presence of coordinates are checked.

    The type must be one of the types allowed for the layer, which the caller
    passes in as ``geometry_types`` in the validation context. Every coordinate
    is deliberately not checked, because perimeters can hold thousands of them.

    Examples:
        >>> Geometry(type="Point", coordinates=[-120.5, 38.1]).type
        'Point'
    """

    model_config = ConfigDict(extra="allow")

    type: str
    coordinates: list[Any]

    @field_validator("type")
    @classmethod
    def check_type(cls, value: str, info: ValidationInfo) -> str:
        """Require the geometry type to be allowed for the layer.

        Args:
            value: The geometry type NIFC sent.
            info: The validation details, which may carry ``geometry_types``.

        Returns:
            The same geometry type.

        Raises:
            ValueError: If the type is not one of the allowed types.

        Examples:
            >>> Geometry.check_type("Point", None)
            'Point'
        """
        allowed = (info.context or {}).get("geometry_types") if info else None
        if allowed and value not in allowed:
            raise ValueError(f"geometry type {value!r} is not one of {sorted(allowed)}")
        return value


class Feature(BaseModel):
    """One GeoJSON feature.

    Examples:
        >>> Feature(
        ...     type="Feature",
        ...     geometry={"type": "Point", "coordinates": [1, 2]},
        ...     properties={"OBJECTID": 1},
        ... ).properties["OBJECTID"]
        1
    """

    model_config = ConfigDict(extra="allow")

    type: Literal["Feature"]
    geometry: Geometry
    properties: dict[str, Any]

    @field_validator("properties")
    @classmethod
    def check_object_id(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Require ``OBJECTID``, when it is present, to be a whole number.

        Args:
            value: The properties NIFC sent for the feature.

        Returns:
            The same properties.

        Raises:
            ValueError: If ``OBJECTID`` is present but is not a whole number.

        Examples:
            >>> Feature.check_object_id({"OBJECTID": 4})
            {'OBJECTID': 4}
        """
        object_id = value.get("OBJECTID")
        if "OBJECTID" in value and (
            isinstance(object_id, bool) or not isinstance(object_id, int)
        ):
            raise ValueError("OBJECTID must be a whole number")
        return value


class PageProperties(BaseModel):
    """The extra information NIFC sometimes attaches to a page of GeoJSON."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    exceeded_transfer_limit: StrictBool | None = Field(
        default=None, alias="exceededTransferLimit"
    )


class Page(BaseModel):
    """One page of features from a NIFC query.

    NIFC puts the "more pages are waiting" flag inside ``properties`` in GeoJSON
    replies and at the top level in other formats, so both are accepted.

    Examples:
        >>> page = Page.model_validate(
        ...     {
        ...         "type": "FeatureCollection",
        ...         "features": [],
        ...         "properties": {"exceededTransferLimit": True},
        ...     }
        ... )
        >>> page.has_more
        True
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: Literal["FeatureCollection"]
    features: list[Feature]
    properties: PageProperties | None = None
    exceeded_transfer_limit: StrictBool | None = Field(
        default=None, alias="exceededTransferLimit"
    )

    @model_validator(mode="after")
    def check_unique_object_ids(self) -> "Page":
        """Reject a page that repeats an ``OBJECTID`` within itself.

        Returns:
            The same page.

        Raises:
            ValueError: If two features on the page share an ``OBJECTID``.
        """
        ids = [
            f.properties["OBJECTID"]
            for f in self.features
            if "OBJECTID" in f.properties
        ]
        if len(ids) != len(set(ids)):
            raise ValueError("a feature ID is repeated on this page")
        return self

    @property
    def has_more(self) -> bool:
        """Whether NIFC says more features are waiting after this page.

        Returns:
            True if there are more pages to request.
        """
        if self.properties and self.properties.exceeded_transfer_limit is not None:
            return self.properties.exceeded_transfer_limit
        return bool(self.exceeded_transfer_limit)


class EditingInfo(BaseModel):
    """When a NIFC layer was last edited, in milliseconds since 1970."""

    model_config = ConfigDict(extra="allow")

    lastEditDate: StrictInt | StrictFloat  # noqa: N815 - Matches NIFC's name.


class LayerMetadata(BaseModel):
    """The part of a NIFC layer's description that says when it last changed.

    Examples:
        >>> LayerMetadata.model_validate(
        ...     {"editingInfo": {"lastEditDate": 1794865327701}}
        ... ).editingInfo.lastEditDate
        1794865327701
    """

    model_config = ConfigDict(extra="allow")

    editingInfo: EditingInfo  # noqa: N815 - Matches NIFC's name.
