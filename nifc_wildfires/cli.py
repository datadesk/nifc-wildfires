"""Command-line interface for downloading wildfire data from NIFC."""

import json
from collections.abc import Callable

import click
from pydantic import ValidationError

from nifc_wildfires import QueryOptions, get_active_perimeters, get_incidents


@click.group()
def cmd() -> None:
    """Download wildfire perimeter and incident points data from NIFC.

    Returns GeoJSON.

    Examples:
        $ nifcwildfires active-perimeters
    """


def shared_options(function: Callable[..., None]) -> Callable[..., None]:
    """Add the options that shape and check what a command downloads.

    Args:
        function: The command function to add the options to.

    Returns:
        The same function with the ``--where``, ``--out-fields``,
        ``--geometry-precision`` and ``--strict/--no-strict`` options attached.

    Examples:
        >>> @click.command()
        ... @shared_options
        ... def example(where, out_fields, geometry_precision, strict): ...
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
            click.option(
                "--strict/--no-strict",
                default=True,
                help="Stop on data that is not in the expected shape (default), "
                "or log it and carry on.",
            ),
        ]
    ):
        function = option(function)
    return function


def build_options(
    where: str, out_fields: str, geometry_precision: int | None
) -> QueryOptions:
    """Turn the command-line options into a checked options object.

    Args:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The decimal places to keep in coordinates.

    Returns:
        The options object.

    Raises:
        click.UsageError: If an option is not valid, such as an empty filter or a
            negative precision.

    Examples:
        >>> build_options("1=1", "*", 5).geometry_precision
        5
    """
    try:
        return QueryOptions(
            where=where, out_fields=out_fields, geometry_precision=geometry_precision
        )
    except ValidationError as error:
        problems = "; ".join(
            f"{e['loc'][0]}: {e['msg']}" for e in error.errors() if e["loc"]
        )
        raise click.UsageError(problems) from error


@cmd.command(help="Perimeters of active fires")
@shared_options
def active_perimeters(
    where: str, out_fields: str, geometry_precision: int | None, strict: bool
) -> None:
    """Print the perimeters of active fires as GeoJSON.

    Args:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The decimal places to keep in coordinates.
        strict: Whether to stop on data that is not in the expected shape.

    Examples:
        $ nifcwildfires active-perimeters
        $ nifcwildfires active-perimeters --where "attr_IncidentTypeCategory='WF'"
    """
    data = get_active_perimeters(
        build_options(where, out_fields, geometry_precision), strict=strict
    )
    click.echo(json.dumps(data))


@cmd.command(help="All YTD fire incident points from NIFC situation reports")
@shared_options
def incidents(
    where: str, out_fields: str, geometry_precision: int | None, strict: bool
) -> None:
    """Print all year-to-date fire incident points as GeoJSON.

    Args:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The decimal places to keep in coordinates.
        strict: Whether to stop on data that is not in the expected shape.

    Examples:
        $ nifcwildfires incidents
        $ nifcwildfires incidents --out-fields OBJECTID,IncidentName
    """
    data = get_incidents(
        build_options(where, out_fields, geometry_precision), strict=strict
    )
    click.echo(json.dumps(data))


if __name__ == "__main__":
    cmd()
