import requests


def get_active_perimeters():
    """Get fire perimeters of all active fires from NIFC.

    Returns a GeoJSON object with multipolygon geometry.
    """
    r = requests.get(
        "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Interagency_Perimeters_Current/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    )
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()


def get_incidents():
    """Get year-to-date fire incident points from NIFC situation reports. Includes active and inctive incidents.

    Returns a GeoJSON object with point geometry.
    """
    r = requests.get(
        "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Incident_Locations_Current/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    )
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()
