import fiona
from geojson import Feature, FeatureCollection


def get_geomac():
    """
    Get GeoMAC data
    """
    active_fire_url = 'https://rmgsc.cr.usgs.gov/outgoing/GeoMAC/current_year_fire_data/current_year_all_states/active_perimeters_dd83.zip'
    with fiona.open('zip+{}'.format(active_fire_url)) as src:
        features = []
        for rec in src:
            features.append(
                    Feature(
                        geometry=rec['geometry'],
                        properties=rec
                    )
                )
        collection = FeatureCollection(features)
        with open("{}.geojson".format('geomac'), "w") as f:
            f.write('%s' % collection)


if __name__ == '__main__':
    get_geomac()
