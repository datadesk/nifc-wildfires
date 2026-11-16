"""Download wildfires data from the National Interagency Fire Center."""

from datetime import UTC, datetime
from typing import Any, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from nifc_wildfires.schema import (
    Fetcher,
    Layer,
    LayerMetadata,
    Page,
    QueryOptions,
    Reply,
)

__all__ = [
    "Fetcher",
    "Layer",
    "NIFCError",
    "QueryOptions",
    "Reply",
    "get_active_perimeters",
    "get_active_perimeters_last_edited",
    "get_incidents",
    "get_incidents_last_edited",
]

BASE_URL = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services"
TIMEOUT = 60
PAGE_SIZE = 1000
MAX_PAGES = 100
MAX_ATTEMPTS = 3

ModelT = TypeVar("ModelT", bound=BaseModel)


class NIFCError(Exception):
    """Raised when NIFC cannot be reached or sends back something unexpected."""


class _DataChangedError(NIFCError):
    """Raised when NIFC's data shifts in the middle of a paged download."""


def _check(
    model: type[ModelT],
    data: object,
    what: str,
    context: dict[str, Any] | None = None,
) -> ModelT:
    """Check data against a model and turn any problems into a ``NIFCError``.

    Args:
        model: The Pydantic model the data must fit.
        data: The data to check.
        what: A short description of the data, used in the error message.
        context: Extra information the model's checks may use.

    Returns:
        The data as a model object.

    Raises:
        NIFCError: If the data does not fit the model. The message lists the
            first few problems, without echoing the data itself.

    Examples:
        >>> _check(Page, {"type": "FeatureCollection", "features": []}, "page").has_more
        False
    """
    try:
        return model.model_validate(data, context=context)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}"
            for e in error.errors()[:3]
        )
        raise NIFCError(
            f"NIFC {what} is not in the expected shape ({problems})."
        ) from error


def _get_json(
    url: str, params: dict[str, Any], get: Fetcher | None = None
) -> dict[str, Any]:
    """Make one request to NIFC and return its reply as a dictionary.

    NIFC reports many errors as a normal successful reply with an error message
    inside, so this checks for that as well as for failed requests.

    Args:
        url: The address to request.
        params: The query parameters to send.
        get: The function that makes the web request, or None for
            ``requests.get``.

    Returns:
        The reply parsed into a dictionary.

    Raises:
        NIFCError: If the request fails, the reply is not a JSON object, or the
            reply contains an error message.

    Examples:
        >>> layer = f"{Layer.INCIDENTS}/FeatureServer/0"
        >>> _get_json(f"{BASE_URL}/{layer}", {"f": "json"})["name"]
        'WFIGS_Incident_Locations_Current'
    """
    fetch: Fetcher = get or requests.get
    r = fetch(url, params=params, timeout=TIMEOUT)
    if r.status_code != 200:
        raise NIFCError(f"Request for data failed with {r.status_code} status code")
    try:
        payload = r.json()
    except ValueError as error:
        raise NIFCError("NIFC returned invalid JSON.") from error
    if not isinstance(payload, dict):
        raise NIFCError("NIFC returned an unexpected response.")
    if "error" in payload:
        raise NIFCError(f"NIFC reported an API error: {payload['error']}")
    return payload


def _get_geojson(
    layer: Layer, options: QueryOptions, get: Fetcher | None = None
) -> dict[str, Any]:
    """Request features from one NIFC layer as GeoJSON.

    NIFC returns a limited number of features per request, so this keeps asking
    for the next page until NIFC says there are no more. NIFC edits its data all
    the time, so a download that catches a change halfway through starts over.

    Args:
        layer: The NIFC layer to download.
        options: The settings that shape the query.
        get: The function that makes the web request, or None for
            ``requests.get``.

    Returns:
        A GeoJSON feature collection with the features from every page.

    Raises:
        NIFCError: If a request fails, a reply does not have the expected shape,
            the pages stop before NIFC says it is done, there are more than
            ``MAX_PAGES`` pages, or NIFC's data keeps changing during
            ``MAX_ATTEMPTS`` download attempts.

    Examples:
        >>> data = _get_geojson(Layer.INCIDENTS, QueryOptions())
        >>> data["type"]
        'FeatureCollection'
    """
    for _ in range(MAX_ATTEMPTS):
        try:
            return _download_pages(layer, options, get)
        except _DataChangedError:
            continue
    raise NIFCError(
        f"NIFC data kept changing during {MAX_ATTEMPTS} download attempts. Try again."
    )


def _download_pages(
    layer: Layer, options: QueryOptions, get: Fetcher | None
) -> dict[str, Any]:
    """Download every page from a layer, once through.

    NIFC edits its data all the time. If an edit lands while the pages are being
    read, later pages shift and the same feature can show up twice, which means
    another feature was skipped. That is detected by repeated feature IDs.

    Args:
        layer: The NIFC layer to download.
        options: The settings that shape the query.
        get: The function that makes the web request, or None for
            ``requests.get``.

    Returns:
        A GeoJSON feature collection with the features from every page.

    Raises:
        NIFCError: If a request fails, a reply does not have the expected shape,
            the pages stop before NIFC says it is done, or there are more than
            ``MAX_PAGES`` pages.
        _DataChangedError: If a feature ID is repeated across pages.

    Examples:
        >>> data = _download_pages(Layer.INCIDENTS, QueryOptions(), None)
        >>> data["type"]
        'FeatureCollection'
    """
    features: list[Any] = []
    seen_ids: set[int] = set()
    offset = 0
    for _ in range(MAX_PAGES):
        params: dict[str, Any] = {
            "outFields": options.out_fields,
            "where": options.where,
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "geojson",
        }
        if options.geometry_precision is not None:
            params["geometryPrecision"] = options.geometry_precision
        reply = _get_json(f"{BASE_URL}/{layer}/FeatureServer/0/query", params, get)
        page = _check(Page, reply, "reply", {"geometry_types": layer.geometry_types})
        for feature in page.features:
            object_id = feature.properties.get("OBJECTID")
            if object_id is None:
                continue
            if object_id in seen_ids:
                raise _DataChangedError(
                    f"NIFC repeated feature {object_id} across pages."
                )
            seen_ids.add(object_id)
        features.extend(reply["features"])
        if not page.has_more:
            return {"type": "FeatureCollection", "features": features}
        if not page.features:
            raise NIFCError("NIFC paging ended before all features were read.")
        offset += len(page.features)
    raise NIFCError(f"NIFC exceeded the {MAX_PAGES}-page safety limit.")


def _get_last_edited(layer: Layer, get: Fetcher | None = None) -> datetime:
    """Ask NIFC when a layer's data was last edited.

    Args:
        layer: The NIFC layer to ask about.
        get: The function that makes the web request, or None for
            ``requests.get``.

    Returns:
        The last edit time, in UTC.

    Raises:
        NIFCError: If NIFC does not report a usable last edit time.

    Examples:
        >>> _get_last_edited(Layer.INCIDENTS).tzinfo
        datetime.timezone.utc
    """
    reply = _get_json(f"{BASE_URL}/{layer}/FeatureServer/0", {"f": "json"}, get)
    metadata = _check(LayerMetadata, reply, "layer metadata")
    last_edit = metadata.editingInfo.lastEditDate
    try:
        return datetime.fromtimestamp(last_edit / 1000, UTC)
    except (OverflowError, OSError, ValueError) as error:
        raise NIFCError("NIFC layer metadata has an invalid lastEditDate.") from error


def get_active_perimeters(
    options: QueryOptions | None = None, *, get: Fetcher | None = None
) -> dict[str, Any]:
    """Get fire perimeters of all active fires from NIFC.

    Args:
        options: The settings that shape the query. The default returns every
            perimeter with every field.
        get: A function that makes the web request, such as ``requests.get``
            (the default). Pass your own to add retries, logging or custom
            headers.

    Returns:
        A GeoJSON object with multipolygon geometry.

    Raises:
        NIFCError: If NIFC cannot be reached, sends back an error, or sends data
            in an unexpected shape.

    Examples:
        >>> data = get_active_perimeters()
        >>> data["type"]
        'FeatureCollection'
        >>> wildfires = get_active_perimeters(
        ...     QueryOptions(
        ...         where="attr_IncidentTypeCategory='WF'",
        ...         out_fields="OBJECTID,poly_IncidentName",
        ...         geometry_precision=5,
        ...     )
        ... )
    """
    return _get_geojson(Layer.PERIMETERS, options or QueryOptions(), get)


def get_incidents(
    options: QueryOptions | None = None, *, get: Fetcher | None = None
) -> dict[str, Any]:
    """Get year-to-date fire incident points from NIFC situation reports.

    Includes active and inactive incidents.

    Args:
        options: The settings that shape the query. The default returns every
            incident with every field.
        get: A function that makes the web request, such as ``requests.get``
            (the default). Pass your own to add retries, logging or custom
            headers.

    Returns:
        A GeoJSON object with point geometry.

    Raises:
        NIFCError: If NIFC cannot be reached, sends back an error, or sends data
            in an unexpected shape.

    Examples:
        >>> data = get_incidents()
        >>> data["type"]
        'FeatureCollection'
        >>> names = get_incidents(QueryOptions(out_fields="OBJECTID,IncidentName"))
    """
    return _get_geojson(Layer.INCIDENTS, options or QueryOptions(), get)


def get_active_perimeters_last_edited(*, get: Fetcher | None = None) -> datetime:
    """Get when NIFC last edited its active fire perimeters.

    Useful for skipping a download when nothing has changed.

    Args:
        get: A function that makes the web request, such as ``requests.get``
            (the default). Pass your own to add retries, logging or custom
            headers.

    Returns:
        The last edit time, in UTC.

    Raises:
        NIFCError: If NIFC cannot be reached or does not report an edit time.

    Examples:
        >>> get_active_perimeters_last_edited().tzinfo
        datetime.timezone.utc
    """
    return _get_last_edited(Layer.PERIMETERS, get)


def get_incidents_last_edited(*, get: Fetcher | None = None) -> datetime:
    """Get when NIFC last edited its fire incident points.

    Useful for skipping a download when nothing has changed.

    Args:
        get: A function that makes the web request, such as ``requests.get``
            (the default). Pass your own to add retries, logging or custom
            headers.

    Returns:
        The last edit time, in UTC.

    Raises:
        NIFCError: If NIFC cannot be reached or does not report an edit time.

    Examples:
        >>> get_incidents_last_edited().tzinfo
        datetime.timezone.utc
    """
    return _get_last_edited(Layer.INCIDENTS, get)
