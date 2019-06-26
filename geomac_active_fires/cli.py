import click
from geomac_active_fires import get_geomac


@click.group()
def cmd():
    """
    A command-line interface for downloading wildfire perimeter data from GeoMAC.
    Returns GeoJSON.
    """
    pass


@cmd.command(help="Perimeters of active fires in a recent 24-hour period from GeoMAC")
def geomac():
    click.echo(get_geomac())


if __name__ == '__main__':
    cli()
