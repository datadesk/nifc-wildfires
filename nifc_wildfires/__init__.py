"""Download wildfires data from the National Interagency Fire Center."""

from typing import Any

import requests

BASE_URL = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services"
TIMEOUT = 60


class NIFCError(Exception):
    """Raised when NIFC cannot be reached or sends back something unexpected."""


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """Make one request to NIFC and return its reply as a dictionary.

    NIFC reports many errors as a normal successful reply with an error message
    inside, so this checks for that as well as for failed requests.

    Args:
        url: The address to request.
        params: The query parameters to send.

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
    r = requests.get(url, params=params, timeout=TIMEOUT)
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


def _get_geojson(service: str) -> dict[str, Any]:
    """Request every feature from one NIFC feature service as GeoJSON.

    Args:
        service: The name of the NIFC feature service to query.

    Returns:
        The GeoJSON response parsed into a dictionary.

    Raises:
        NIFCError: If the request fails or the reply is not a list of features.

    Examples:
        >>> data = _get_geojson("WFIGS_Incident_Locations_Current")
        >>> data["type"]
        'FeatureCollection'
    """
    data = _get_json(
        f"{BASE_URL}/{service}/FeatureServer/0/query",
        {"outFields": "*", "where": "1=1", "f": "geojson"},
    )
    if not isinstance(data.get("features"), list):
        raise NIFCError("NIFC response is missing its feature list.")
    return data


def get_active_perimeters() -> dict[str, Any]:
    """Get fire perimeters of all active fires from NIFC.

    Returns:
        A GeoJSON object with multipolygon geometry.

    Raises:
        NIFCError: If NIFC cannot be reached or sends back an error.

    Examples:
        >>> data = get_active_perimeters()
        >>> data["type"]
        'FeatureCollection'
    """
    return _get_geojson("WFIGS_Interagency_Perimeters_Current")


def get_incidents() -> dict[str, Any]:
    """Get year-to-date fire incident points from NIFC situation reports.

    Includes active and inactive incidents.

    Returns:
        A GeoJSON object with point geometry.

    Raises:
        NIFCError: If NIFC cannot be reached or sends back an error.

    Examples:
        >>> data = get_incidents()
        >>> data["type"]
        'FeatureCollection'
    """
    return _get_geojson("WFIGS_Incident_Locations_Current")
