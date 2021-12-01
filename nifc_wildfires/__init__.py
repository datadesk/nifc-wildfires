#! /usr/bin/env python
# -*- coding: utf-8 -*-
import requests


def get_active_perimeters():
    """
    Get fire perimeters of all active fires from NIFC

    Returns a GeoJSON object with multipolygon geometry.
    """
    r = requests.get("https://opendata.arcgis.com/datasets/2191f997056547bd9dc530ab9866ab61_0.geojson")
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()


def get_incidents():
    """
    Get year-to-date fire incident points from NIFC situation reports. Includes active and inctive incidents.

    Returns a GeoJSON object with point geometry.
    """
    r = requests.get("https://opendata.arcgis.com/datasets/51192330d3f14664bd69b6faed0fdf05_0.geojson")
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()
