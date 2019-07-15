import click
from geomac_wildfires import get_active_fires, get_nifc_sitrep


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


@cmd.command(help="NIFC Sit Rep fire points from GeoMAC")
def nifc_sitrep():
    click.echo(get_nifc_sitrep())


if __name__ == '__main__':
    cmd()
