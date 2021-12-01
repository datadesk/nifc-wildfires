#! /usr/bin/env python
# -*- coding: utf-8 -*-
import requests


def get_current_perimeters():
    """
    Get geojson fire perimeters from new 2021 feed.

    Returns a GeoJSON object.
    """
    r = requests.get("https://opendata.arcgis.com/datasets/2191f997056547bd9dc530ab9866ab61_0.geojson")
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()


def get_nifc_incidents():
    """
    Get fire incident points from NIFC situation reports. Starts from Jan 1st of current year -

    Returns a GeoJSON object.
    """
    r = requests.get("https://opendata.arcgis.com/datasets/51192330d3f14664bd69b6faed0fdf05_0.geojson")
    if r.status_code != 200:
        raise Exception(f"Request for data failed with {r.status_code} status code")
    return r.json()
