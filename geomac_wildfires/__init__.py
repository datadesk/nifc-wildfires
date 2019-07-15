import fiona
from geojson import Feature, FeatureCollection


def get_active_fires():
    """
    Get GeoMAC data
    """
    url = 'https://rmgsc.cr.usgs.gov/outgoing/GeoMAC/current_year_fire_data/current_year_all_states/active_perimeters_dd83.zip'
    with fiona.open(f'zip+{url}') as f:
        return FeatureCollection([Feature(geometry=d['geometry'], properties=d) for d in f])

def get_nifc_sitrep():
    """
    Get NIFC Sit Rep data
    """
    url = 'https://rmgsc.cr.usgs.gov/outgoing/GeoMAC/current_year_fire_data/current_year_all_states/nifc_sit_rep_dd83.zip'
    with fiona.open(f'zip+{url}') as f:
        print(FeatureCollection([Feature(geometry=d['geometry'], properties=d) for d in f]))
        return FeatureCollection([Feature(geometry=d['geometry'], properties=d) for d in f])
