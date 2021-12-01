#! /usr/bin/env python
# -*- coding: utf-8 -*-
import click
from nifc_wildfires import (
    get_current_perimeters,
    get_incidents
)


@click.group()
def cmd():
    """
    A command-line interface for downloading wildfire perimeter and incident points data from NIFC.
    Returns GeoJSON.
    """
    pass


@cmd.command(help="Perimeters of active fires in new 2021 feed")
def current_perimeters():
    click.echo(get_current_perimeters())


@cmd.command(help="Fire incident points from NIFC situation reports")
def incidents():
    click.echo(get_incidents())


if __name__ == '__main__':
    cmd()
