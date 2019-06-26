import click
from geomac_wildfires import get_active_fires


@click.group()
def cmd():
    """
    A command-line interface for downloading wildfire perimeter data from GeoMAC.
    Returns GeoJSON.
    """
    pass


@cmd.command(help="Perimeters of active fires in a recent 24-hour period from GeoMAC")
def active_fires():
    click.echo(get_active_fires())


if __name__ == '__main__':
    cmd()
