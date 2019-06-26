import click
from geomac_active_fires import get_active_fire_perimeters


@click.group()
def cmd():
    """
    A command-line interface for downloading wildfire perimeter data from GeoMAC.
    Returns GeoJSON.
    """
    pass


@cmd.command(help="Perimeters of active fires in a recent 24-hour period from GeoMAC")
def active_fire_perimeters():
    click.echo(get_active_fire_perimeters())


if __name__ == '__main__':
    cli()
