# from shapely.geometry import shape, mapping
import fiona
import requests
from datetime import datetime, timezone
from geojson import Feature, FeatureCollection


def get_active_fires():
    """
    Get GeoMAC data
    """
    url = 'https://rmgsc.cr.usgs.gov/outgoing/GeoMAC/current_year_fire_data/current_year_all_states/active_perimeters_dd83.zip'
    with fiona.open(f'zip+{url}') as f:
        return FeatureCollection([Feature(geometry=d['geometry'], properties=d['properties']) for d in f])


def get_all_fires():
    """
    Get GeoMAC data for all fires
    """
    url = 'https://rmgsc.cr.usgs.gov/outgoing/GeoMAC/current_year_fire_data/current_year_all_states/perimeters_dd83.zip'
    with fiona.open(f'zip+{url}') as f:
        return FeatureCollection(
            [Feature(geometry=d['geometry'], properties=d['properties']) for d in f]
        )


def get_nifc_sitrep():
    """
    Get NIFC Sit Rep data
    """
    url = 'https://rmgsc.cr.usgs.gov/outgoing/GeoMAC/current_year_fire_data/current_year_all_states/nifc_sit_rep_dd83.zip'
    with fiona.open(f'zip+{url}') as f:
        return FeatureCollection(
            [Feature(geometry=d['geometry'], properties=d['properties']) for d in f]
        )
