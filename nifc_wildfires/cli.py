"""Command-line interface for downloading wildfire data from NIFC."""

import json

import click

from nifc_wildfires import get_active_perimeters, get_incidents


@click.group()
def cmd() -> None:
    """Download wildfire perimeter and incident points data from NIFC.

    Returns GeoJSON.

    Examples:
        $ nifcwildfires active-perimeters
    """


@cmd.command(help="Perimeters of active fires")
def active_perimeters() -> None:
    """Print the perimeters of active fires as GeoJSON.

    Examples:
        $ nifcwildfires active-perimeters
    """
    click.echo(json.dumps(get_active_perimeters()))


@cmd.command(help="All YTD fire incident points from NIFC situation reports")
def incidents() -> None:
    """Print all year-to-date fire incident points as GeoJSON.

    Examples:
        $ nifcwildfires incidents
    """
    click.echo(json.dumps(get_incidents()))


if __name__ == "__main__":
    cmd()
