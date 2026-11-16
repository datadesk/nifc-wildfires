"""Download wildfires data from the National Interagency Fire Center."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import requests

BASE_URL = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services"
TIMEOUT = 60
PAGE_SIZE = 1000
MAX_PAGES = 100


class NIFCError(Exception):
    """Raised when NIFC cannot be reached or sends back something unexpected."""


def _get_json(
    url: str, params: dict[str, Any], get: Callable[..., Any] | None = None
) -> dict[str, Any]:
    """Make one request to NIFC and return its reply as a dictionary.

    NIFC reports many errors as a normal successful reply with an error message
    inside, so this checks for that as well as for failed requests.

    Args:
        url: The address to request.
        params: The query parameters to send.
        get: A function that makes the web request, called like
            ``requests.get(url, params=params, timeout=seconds)`` and returning
            something with ``status_code`` and ``json()``. The default is
            ``requests.get``. Pass your own to add retries, logging or custom
            headers.

    Returns:
        The reply parsed into a dictionary.

    Raises:
        NIFCError: If the request fails, the reply is not a JSON object, or the
            reply contains an error message.

    Examples:
        >>> layer = "WFIGS_Incident_Locations_Current/FeatureServer/0"
        >>> _get_json(f"{BASE_URL}/{layer}", {"f": "json"})["name"]
        'WFIGS_Incident_Locations_Current'
    """
    r = (get or requests.get)(url, params=params, timeout=TIMEOUT)
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
    service: str,
    where: str = "1=1",
    out_fields: str = "*",
    geometry_precision: int | None = None,
    get: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Request features from one NIFC feature service as GeoJSON.

    NIFC returns a limited number of features per request, so this keeps asking
    for the next page until NIFC says there are no more.

    Args:
        service: The name of the NIFC feature service to query.
        where: A SQL-style filter that picks which features to return. The
            default returns all of them.
        out_fields: The fields to return, as a comma-separated string. The
            default returns all of them.
        geometry_precision: The number of decimal places to keep in coordinates.
            The default keeps everything NIFC sends.
        get: A function that makes the web request, called like
            ``requests.get(url, params=params, timeout=seconds)`` and returning
            something with ``status_code`` and ``json()``. The default is
            ``requests.get``. Pass your own to add retries, logging or custom
            headers.

    Returns:
        A GeoJSON feature collection with the features from every page.

    Raises:
        NIFCError: If a request fails, a reply is not a list of features, the
            pages stop before NIFC says it is done, or there are more than
            ``MAX_PAGES`` pages.

    Examples:
        >>> data = _get_geojson("WFIGS_Incident_Locations_Current")
        >>> data["type"]
        'FeatureCollection'
    """
    features: list[Any] = []
    offset = 0
    for _ in range(MAX_PAGES):
        params: dict[str, Any] = {
            "outFields": out_fields,
            "where": where,
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "geojson",
        }
        if geometry_precision is not None:
            params["geometryPrecision"] = geometry_precision
        page = _get_json(f"{BASE_URL}/{service}/FeatureServer/0/query", params, get)
        page_features = page.get("features")
        if not isinstance(page_features, list):
            raise NIFCError("NIFC response is missing its feature list.")
        features.extend(page_features)
        if not _has_more_pages(page):
            return {"type": "FeatureCollection", "features": features}
        if not page_features:
            raise NIFCError("NIFC paging ended before all features were read.")
        offset += len(page_features)
    raise NIFCError(f"NIFC exceeded the {MAX_PAGES}-page safety limit.")


def _has_more_pages(page: dict[str, Any]) -> bool:
    """Check whether NIFC says more features are waiting after this page.

    NIFC puts the flag inside ``properties`` in GeoJSON replies, and at the top
    level in other formats, so both places are checked.

    Args:
        page: One reply from NIFC.

    Returns:
        True if there are more pages to request.

    Raises:
        NIFCError: If the flag is present but is not true or false.

    Examples:
        >>> _has_more_pages({"properties": {"exceededTransferLimit": True}})
        True
        >>> _has_more_pages({"features": []})
        False
    """
    properties = page.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    flag = properties.get("exceededTransferLimit", page.get("exceededTransferLimit"))
    if flag is None:
        return False
    if not isinstance(flag, bool):
        raise NIFCError("NIFC returned an invalid paging flag.")
    return flag


def _get_last_edited(service: str, get: Callable[..., Any] | None = None) -> datetime:
    """Ask NIFC when a feature service's data was last edited.

    Args:
        service: The name of the NIFC feature service to ask about.
        get: A function that makes the web request, called like
            ``requests.get(url, params=params, timeout=seconds)`` and returning
            something with ``status_code`` and ``json()``. The default is
            ``requests.get``. Pass your own to add retries, logging or custom
            headers.

    Returns:
        The last edit time, in UTC.

    Raises:
        NIFCError: If NIFC does not report a usable last edit time.

    Examples:
        >>> _get_last_edited("WFIGS_Incident_Locations_Current", get).tzinfo
        datetime.timezone.utc
    """
    layer = _get_json(f"{BASE_URL}/{service}/FeatureServer/0", {"f": "json"}, get)
    editing_info = layer.get("editingInfo")
    if not isinstance(editing_info, dict):
        raise NIFCError("NIFC layer metadata is missing editingInfo.")
    last_edit = editing_info.get("lastEditDate")
    if isinstance(last_edit, bool) or not isinstance(last_edit, int | float):
        raise NIFCError("NIFC layer metadata has an invalid lastEditDate.")
    try:
        return datetime.fromtimestamp(last_edit / 1000, UTC)
    except (OverflowError, OSError, ValueError) as error:
        raise NIFCError("NIFC layer metadata has an invalid lastEditDate.") from error


def get_active_perimeters(
    where: str = "1=1",
    out_fields: str = "*",
    geometry_precision: int | None = None,
    get: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Get fire perimeters of all active fires from NIFC.


    Args:
        where: A SQL-style filter that picks which features to return. The
            default returns all of them.
        out_fields: The fields to return, as a comma-separated string. The
            default returns all of them.
        geometry_precision: The number of decimal places to keep in coordinates.
            The default keeps everything NIFC sends.
        get: A function that makes the web request, called like
            ``requests.get(url, params=params, timeout=seconds)`` and returning
            something with ``status_code`` and ``json()``. The default is
            ``requests.get``. Pass your own to add retries, logging or custom
            headers.

    Returns:
        A GeoJSON object with multipolygon geometry.

    Raises:
        NIFCError: If NIFC cannot be reached or sends back an error.

    Examples:
        >>> data = get_active_perimeters()
        >>> data["type"]
        'FeatureCollection'
        >>> wildfires = get_active_perimeters(
        ...     where="attr_IncidentTypeCategory='WF'",
        ...     out_fields="OBJECTID,poly_IncidentName",
        ...     geometry_precision=5,
        ... )
    """
    return _get_geojson(
        "WFIGS_Interagency_Perimeters_Current",
        where,
        out_fields,
        geometry_precision,
        get,
    )


def get_incidents(
    where: str = "1=1",
    out_fields: str = "*",
    geometry_precision: int | None = None,
    get: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Get year-to-date fire incident points from NIFC situation reports.

    Includes active and inactive incidents.

    Args:
        where: A SQL-style filter that picks which features to return. The
            default returns all of them.
        out_fields: The fields to return, as a comma-separated string. The
            default returns all of them.
        geometry_precision: The number of decimal places to keep in coordinates.
            The default keeps everything NIFC sends.
        get: A function that makes the web request, called like
            ``requests.get(url, params=params, timeout=seconds)`` and returning
            something with ``status_code`` and ``json()``. The default is
            ``requests.get``. Pass your own to add retries, logging or custom
            headers.

    Returns:
        A GeoJSON object with point geometry.

    Raises:
        NIFCError: If NIFC cannot be reached or sends back an error.

    Examples:
        >>> data = get_incidents()
        >>> data["type"]
        'FeatureCollection'
    """
    return _get_geojson(
        "WFIGS_Incident_Locations_Current", where, out_fields, geometry_precision, get
    )


def get_active_perimeters_last_edited(
    get: Callable[..., Any] | None = None,
) -> datetime:
    """Get when NIFC last edited its active fire perimeters.

    Useful for skipping a download when nothing has changed.

    Args:
        get: A function that makes the web request, called like
            ``requests.get(url, params=params, timeout=seconds)`` and returning
            something with ``status_code`` and ``json()``. The default is
            ``requests.get``. Pass your own to add retries, logging or custom
            headers.

    Returns:
        The last edit time, in UTC.

    Raises:
        NIFCError: If NIFC cannot be reached or does not report an edit time.

    Examples:
        >>> get_active_perimeters_last_edited().tzinfo
        datetime.timezone.utc
    """
    return _get_last_edited("WFIGS_Interagency_Perimeters_Current", get)


def get_incidents_last_edited(get: Callable[..., Any] | None = None) -> datetime:
    """Get when NIFC last edited its fire incident points.

    Useful for skipping a download when nothing has changed.

    Args:
        get: A function that makes the web request, called like
            ``requests.get(url, params=params, timeout=seconds)`` and returning
            something with ``status_code`` and ``json()``. The default is
            ``requests.get``. Pass your own to add retries, logging or custom
            headers.

    Returns:
        The last edit time, in UTC.

    Raises:
        NIFCError: If NIFC cannot be reached or does not report an edit time.

    Examples:
        >>> get_incidents_last_edited().tzinfo
        datetime.timezone.utc
    """
    return _get_last_edited("WFIGS_Incident_Locations_Current", get)
