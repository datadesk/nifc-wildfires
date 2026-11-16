"""Models that check the shape of what NIFC sends back and what callers ask for."""

from typing import Any, Literal

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


class QueryOptions(BaseModel):
    """The settings a caller can choose for a download.

    Examples:
        >>> QueryOptions(where="OBJECTID > 5", geometry_precision=5).out_fields
        '*'
    """

    where: str = Field(default="1=1", min_length=1)
    out_fields: str = Field(default="*", min_length=1)
    geometry_precision: int | None = Field(default=None, ge=0)


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
