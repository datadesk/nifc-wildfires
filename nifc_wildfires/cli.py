"""Command-line interface for downloading wildfire data from NIFC."""

import json
from collections.abc import Callable

import click

from nifc_wildfires import get_active_perimeters, get_incidents


@click.group()
def cmd() -> None:
    """Download wildfire perimeter and incident points data from NIFC.

    Returns GeoJSON.

    Examples:
        $ nifcwildfires active-perimeters
    """


def query_options(function: Callable[..., None]) -> Callable[..., None]:
    """Add the options that shape which data a command downloads.

    Args:
        function: The command function to add the options to.

    Returns:
        The same function with the ``--where``, ``--out-fields`` and
        ``--geometry-precision`` options attached.

    Examples:
        >>> @click.command()
        ... @query_options
        ... def example(where, out_fields, geometry_precision): ...
    """
    for option in reversed(
        [
            click.option("--where", default="1=1", help="A SQL-style filter."),
            click.option("--out-fields", default="*", help="Comma-separated fields."),
            click.option(
                "--geometry-precision",
                type=int,
                default=None,
                help="Decimal places to keep in coordinates.",
            ),
        ]
    ):
        function = option(function)
    return function


@cmd.command(help="Perimeters of active fires")
@query_options
def active_perimeters(
    where: str, out_fields: str, geometry_precision: int | None
) -> None:
    """Print the perimeters of active fires as GeoJSON.

    Args:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The decimal places to keep in coordinates.

    Examples:
        $ nifcwildfires active-perimeters
        $ nifcwildfires active-perimeters --where "attr_IncidentTypeCategory='WF'"
    """
    data = get_active_perimeters(where, out_fields, geometry_precision)
    click.echo(json.dumps(data))


@cmd.command(help="All YTD fire incident points from NIFC situation reports")
@query_options
def incidents(where: str, out_fields: str, geometry_precision: int | None) -> None:
    """Print all year-to-date fire incident points as GeoJSON.

    Args:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The decimal places to keep in coordinates.

    Examples:
        $ nifcwildfires incidents
        $ nifcwildfires incidents --out-fields OBJECTID,IncidentName
    """
    data = get_incidents(where, out_fields, geometry_precision)
    click.echo(json.dumps(data))


if __name__ == "__main__":
    cmd()
