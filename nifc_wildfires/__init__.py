"""Download wildfires data from the National Interagency Fire Center."""

from typing import Any

import requests

BASE_URL = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services"
TIMEOUT = 60


def _get_geojson(service: str) -> dict[str, Any]:
    """Request every feature from one NIFC feature service as GeoJSON.

    Args:
        service: The name of the NIFC feature service to query.

    Returns:
        The GeoJSON response parsed into a dictionary.

    Raises:
        Exception: If NIFC answers with anything other than a 200 status code.

    Examples:
        >>> data = _get_geojson("WFIGS_Incident_Locations_Current")
        >>> data["type"]
        'FeatureCollection'
    """
    r = requests.get(
        f"{BASE_URL}/{service}/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson",
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()


def get_active_perimeters() -> dict[str, Any]:
    """Get fire perimeters of all active fires from NIFC.

    Returns:
        A GeoJSON object with multipolygon geometry.

    Raises:
        Exception: If NIFC answers with anything other than a 200 status code.

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
        Exception: If NIFC answers with anything other than a 200 status code.

    Examples:
        >>> data = get_incidents()
        >>> data["type"]
        'FeatureCollection'
    """
    return _get_geojson("WFIGS_Incident_Locations_Current")
