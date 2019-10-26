import fiona
from geojson import Feature, FeatureCollection


def get_active_fires():
    """
    Get GeoMAC data
    """
    url = 'active_perimeters_dd83.zip'
    return _parse_shapefile(url)


def get_all_fires():
    """
    Get GeoMAC data for all fires
    """
    url = 'perimeters_dd83.zip'
    return _parse_shapefile(url)


def get_nifc_sitrep():
    """
    Get NIFC Sit Rep data
    """
    url = 'nifc_sit_rep_dd83.zip'
    return _parse_shapefile(url)


def _parse_shapefile(name):
    """
    Download the provided list of shapefile components and convert them to GeoJSON.
    """
    # Figure out the url
    domain = 'rmgsc.cr.usgs.gov'
    base_dir = 'outgoing/GeoMAC/current_year_fire_data/current_year_all_states'
    url = f'https://{domain}/{base_dir}/{name}'
    # Get the shapefile zip from the web
    with fiona.open(f'zip+{url}') as shp:
        # Convert the shapefile to GeoJSON and return it
        feature_list = [Feature(geometry=d['geometry'], properties=d) for d in shp]
        return FeatureCollection(feature_list)
