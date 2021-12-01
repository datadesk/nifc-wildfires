#! /usr/bin/env python
# -*- coding: utf-8 -*-
import click
from nifc_wildfires import (
    get_active_perimeters,
    get_incidents
)


@click.group()
def cmd():
    """
    A command-line interface for downloading wildfire perimeter and incident points data from NIFC.
    Returns GeoJSON.
    """
    pass


@cmd.command(help="Perimeters of active fires")
def active_perimeters():
    click.echo(get_active_perimeters())


@cmd.command(help="All YTD fire incident points from NIFC situation reports")
def incidents():
    click.echo(get_incidents())


if __name__ == '__main__':
    cmd()
