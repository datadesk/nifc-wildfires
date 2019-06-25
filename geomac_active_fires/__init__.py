import requests
import zipfile
# import tempfile
import io
import os
import shapefile
import json


def get_geomac():
    """
    Get GeoMAC data
    """
    tmp = io.BytesIO()
    active_fire_url = 'https://rmgsc.cr.usgs.gov/outgoing/GeoMAC/current_year_fire_data/current_year_all_states/active_perimeters_dd83.zip'
    r = requests.get(active_fire_url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    # dirpath = tempfile.mkdtemp()
    # print(dirpath)
    z.extractall('tmp')
    shp = [ f for f in os.listdir('tmp') if f.endswith(".shp") ][0]
    sf = shapefile.Reader('tmp/{}'.format(shp))
    print(sf.__geo_interface__)
    # with open('geomac.geojson', 'w') as outfile:
    #     json.dump(sf.__geo_interface__, outfile)

if __name__ == '__main__':
    get_geomac()
