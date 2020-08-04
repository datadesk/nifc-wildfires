#! /usr/bin/env python
# -*- coding: utf-8 -*-
import click
from geomac_wildfires import (
    get_json_perimeters,
    get_nifc_incidents_new,
    get_active_perimeters,
    get_all_perimeters,
    get_nifc_incidents
)


@click.group()
def cmd():
    """
    A command-line interface for downloading wildfire perimeter data from GeoMAC.
    Returns GeoJSON.
    """
    pass


@cmd.command(help="Perimeters of active fires in new 2020 feed")
def json_perimeters():
    click.echo(get_json_perimeters())


@cmd.command(help="Fire incident points from NIFC situation reports")
def nifc_incidents_new():
    click.echo(get_nifc_incidents_new())


@cmd.command(help="Perimeters of active fires in a recent 24-hour period")
def active_perimeters():
    click.echo(get_active_perimeters())


@cmd.command(help="Perimeters of all fires")
def all_perimeters():
    click.echo(get_all_perimeters())


@cmd.command(help="Fire incident points from NIFC situation reports")
def nifc_incidents():
    click.echo(get_nifc_incidents())


if __name__ == '__main__':
    cmd()
