#! /usr/bin/env python
# -*- coding: utf-8 -*-
import io
import fiona
import requests
from geojson import Feature, FeatureCollection


def get_json_perimeters():
    """
    Get geojson fire perimeters from new 2020 feed.

    Returns a GeoJSON object.
    """
    r = requests.get("https://opendata.arcgis.com/datasets/5da472c6d27b4b67970acc7b5044c862_0.geojson")
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()


def get_nifc_incidents_new():
    """
    Get fire incident points from NIFC situation reports.

    Returns a GeoJSON object.
    """
    r = requests.get("https://opendata.arcgis.com/datasets/68637d248eb24d0d853342cba02d4af7_0.geojson")
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()


def get_active_perimeters():
    """
    Get perimeters of active fires in a recent 24-hour period.

    Returns a GeoJSON object.
    """
    return _parse_shapefile('active_perimeters_dd83.zip')


def get_all_perimeters():
    """
    Get perimeters of all fires.

    Returns a GeoJSON object.
    """
    return _parse_shapefile('perimeters_dd83.zip')


def get_nifc_incidents():
    """
    Get fire incident points from NIFC situation reports.

    Returns a GeoJSON object.
    """
    return _parse_shapefile('nifc_sit_rep_dd83.zip')


def _parse_shapefile(name):
    """
    Downloads the provided shapefile from GeoMAC.

    Returns a GeoJSON object.
    """
    # Figure out the url
    domain = 'rmgsc.cr.usgs.gov'
    base_dir = 'outgoing/GeoMAC/current_year_fire_data/current_year_all_states'
    url = f'https://{domain}/{base_dir}/{name}'

    # Get the zipfile
    r = requests.get(url)
    buffer = io.BytesIO(bytes(r.content))
    shp = fiona.BytesCollection(buffer.getvalue())

    # Convert it GeoJSON and return it
    feature_list = [
        Feature(geometry=d['geometry'], properties=d['properties']) for d in shp
    ]
    return FeatureCollection(feature_list)
