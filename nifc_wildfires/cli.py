"""Command-line interface for downloading wildfire data from NIFC."""

import json
from collections.abc import Callable, Generator
from contextlib import contextmanager

import click
import requests
from pydantic import ValidationError

from nifc_wildfires import (
    IncidentType,
    Layer,
    NIFCClient,
    NIFCError,
    NIFCValidationError,
    QueryOptions,
)

INCIDENT_TYPE_CHOICE = click.Choice(
    [t.value for t in IncidentType], case_sensitive=False
)


@click.group()
def cmd() -> None:
    """Download wildfire perimeter and incident points data from NIFC.

    Returns GeoJSON.

    Examples:
        $ nifcwildfires active-perimeters
    """


def common_options(function: Callable[..., None]) -> Callable[..., None]:
    """Add the options every command shares.

    Args:
        function: The command function to add the options to.

    Returns:
        The same function with the ``--timeout`` and ``--verbose`` options
        attached.

    Examples:
        >>> @click.command()
        ... @common_options
        ... def example(timeout, verbose): ...
    """
    for option in reversed(
        [
            click.option(
                "--timeout",
                type=click.FloatRange(min=0, min_open=True),
                default=None,
                help="Seconds to wait for each request. Defaults to 60.",
            ),
            click.option(
                "--verbose",
                is_flag=True,
                help="When a download fails, list every problem found.",
            ),
        ]
    ):
        function = option(function)
    return function


def download_options(function: Callable[..., None]) -> Callable[..., None]:
    """Add the options that shape and check what a download command fetches.

    Args:
        function: The command function to add the options to.

    Returns:
        The same function with the ``--where``, ``--out-fields``,
        ``--geometry-precision``, ``--incident-type``,
        ``--exclude-incident-type`` and ``--strict/--no-strict`` options attached.

    Examples:
        >>> @click.command()
        ... @download_options
        ... def example(
        ...     where,
        ...     out_fields,
        ...     geometry_precision,
        ...     incident_type,
        ...     exclude_incident_type,
        ...     strict,
        ... ): ...
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
                "--incident-type",
                type=INCIDENT_TYPE_CHOICE,
                metavar="CODE",
                multiple=True,
                help="Keep only this category of incident, by NWCG code: WF is "
                "wildfire, RX is prescribed fire, CX is an incident complex. "
                "Repeat to keep several.",
            ),
            click.option(
                "--exclude-incident-type",
                type=INCIDENT_TYPE_CHOICE,
                metavar="CODE",
                multiple=True,
                help="Leave out this category of incident, by NWCG code. "
                "Repeat to leave out several.",
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
    where: str,
    out_fields: str,
    geometry_precision: int | None,
    incident_type: tuple[str, ...] = (),
    exclude_incident_type: tuple[str, ...] = (),
) -> QueryOptions:
    """Turn the command-line options into a checked options object.

    Args:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The decimal places to keep in coordinates.
        incident_type: Incident type codes to keep, or none to keep every type.
        exclude_incident_type: Incident type codes to leave out.

    Returns:
        The options object.

    Raises:
        click.UsageError: If an option is not valid, such as an empty filter, a
            negative precision, or both keeping and excluding incident types.

    Examples:
        >>> build_options("1=1", "*", 5).geometry_precision
        5
        >>> build_options("1=1", "*", None, exclude_incident_type=("rx",))
        ... .exclude_incident_types == {IncidentType.PRESCRIBED_FIRE}
        True
    """
    try:
        return QueryOptions(
            where=where,
            out_fields=out_fields,
            geometry_precision=geometry_precision,
            incident_types=(
                frozenset(t.upper() for t in incident_type) if incident_type else None
            ),
            exclude_incident_types=frozenset(t.upper() for t in exclude_incident_type),
        )
    except ValidationError as error:
        problems = "; ".join(
            f"{e['loc'][0]}: {e['msg']}" if e["loc"] else e["msg"]
            for e in error.errors()
        )
        raise click.UsageError(problems) from error


def build_client(strict: bool = True, timeout: float | None = None) -> NIFCClient:
    """Make the client a command downloads with.

    Args:
        strict: Whether to stop on data that is not in the expected shape.
        timeout: The seconds to wait for each request, or None for the default.

    Returns:
        The client.

    Examples:
        >>> build_client(strict=False, timeout=30).timeout
        30
    """
    if timeout is None:
        return NIFCClient(strict=strict)
    return NIFCClient(strict=strict, timeout=timeout)


@contextmanager
def clean_errors(verbose: bool = False) -> Generator[None]:
    """Show a failed download as a short message and a failing exit code.

    Without this, a failure prints a long traceback. Nothing has been written to
    the output by the time a download fails, so a redirect such as
    ``> perimeters.json`` is left empty, never half full.

    Args:
        verbose: If True, list every problem found in data that was not in the
            expected shape, not only the first few.

    Yields:
        Nothing. Run the download inside the ``with`` block.

    Raises:
        click.ClickException: If the download fails for any reason this package
            knows about. Click prints ``Error: `` and the message to standard
            error and exits with code 1.

    Examples:
        >>> with clean_errors():
        ...     pass
    """
    try:
        yield
    except NIFCValidationError as error:
        lines = [str(error)]
        if verbose:
            shown = error.problems
            lines.append(
                f"{error.problem_count} problem(s) in all, {len(shown)} shown:"
            )
            lines += [
                f"  {'.'.join(str(part) for part in p.location)}: {p.message}"
                for p in shown
            ]
        else:
            lines.append(
                "Run again with --verbose to list every problem, or with --no-strict to carry on."
            )
        raise click.ClickException("\n".join(lines)) from error
    except NIFCError as error:
        raise click.ClickException(str(error)) from error
    except requests.Timeout as error:
        raise click.ClickException(
            "NIFC did not answer in time. Try again, or raise --timeout."
        ) from error
    except requests.RequestException as error:
        message = f"Could not reach NIFC ({type(error).__name__})."
        if verbose:
            message += f"\n{error}"
        else:
            message += (
                " Check your connection and try again, or use --verbose for details."
            )
        raise click.ClickException(message) from error


@cmd.command(help="Perimeters of active fires")
@download_options
@common_options
def active_perimeters(
    where: str,
    out_fields: str,
    geometry_precision: int | None,
    incident_type: tuple[str, ...],
    exclude_incident_type: tuple[str, ...],
    strict: bool,
    timeout: float | None,
    verbose: bool,
) -> None:
    """Print the perimeters of active fires as GeoJSON.

    Args:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The decimal places to keep in coordinates.
        incident_type: Incident type codes to keep, or none to keep every type.
        exclude_incident_type: Incident type codes to leave out.
        strict: Whether to stop on data that is not in the expected shape.
        timeout: The seconds to wait for each request, or None for the default.
        verbose: Whether to list every problem when a download fails.

    Examples:
        $ nifcwildfires active-perimeters
        $ nifcwildfires active-perimeters --incident-type WF
        $ nifcwildfires active-perimeters --timeout 120 --no-strict
    """
    options = build_options(
        where, out_fields, geometry_precision, incident_type, exclude_incident_type
    )
    with clean_errors(verbose):
        data = build_client(strict, timeout).get_active_perimeters(options)
    click.echo(json.dumps(data))


@cmd.command(
    help="All YTD fire incident points from NIFC situation reports, "
    "prescribed burns included"
)
@download_options
@common_options
def incidents(
    where: str,
    out_fields: str,
    geometry_precision: int | None,
    incident_type: tuple[str, ...],
    exclude_incident_type: tuple[str, ...],
    strict: bool,
    timeout: float | None,
    verbose: bool,
) -> None:
    """Print all year-to-date fire incident points as GeoJSON.

    This includes prescribed burns (type RX), fires lit on purpose, which can be
    most of the points. Leave them out with ``--exclude-incident-type RX``.

    Args:
        where: A SQL-style filter that picks which features to return.
        out_fields: The fields to return, as a comma-separated string.
        geometry_precision: The decimal places to keep in coordinates.
        incident_type: Incident type codes to keep, or none to keep every type.
        exclude_incident_type: Incident type codes to leave out.
        strict: Whether to stop on data that is not in the expected shape.
        timeout: The seconds to wait for each request, or None for the default.
        verbose: Whether to list every problem when a download fails.

    Examples:
        $ nifcwildfires incidents
        $ nifcwildfires incidents --out-fields OBJECTID,IncidentName
        $ nifcwildfires incidents --exclude-incident-type RX
    """
    options = build_options(
        where, out_fields, geometry_precision, incident_type, exclude_incident_type
    )
    with clean_errors(verbose):
        data = build_client(strict, timeout).get_incidents(options)
    click.echo(json.dumps(data))


@cmd.command(
    help="When NIFC last edited a layer, as a UTC time. Use it to skip a download."
)
@click.argument("layer", type=click.Choice(["active-perimeters", "incidents"]))
@common_options
def last_edited(layer: str, timeout: float | None, verbose: bool) -> None:
    """Print when NIFC last edited a layer, as an ISO 8601 time in UTC.

    Args:
        layer: Which layer to ask about, ``active-perimeters`` or ``incidents``.
        timeout: The seconds to wait for each request, or None for the default.
        verbose: Whether to list every problem when the request fails.

    Examples:
        $ nifcwildfires last-edited active-perimeters
        2026-11-16T21:42:07.701000+00:00
    """
    which = Layer.PERIMETERS if layer == "active-perimeters" else Layer.INCIDENTS
    with clean_errors(verbose):
        edited = build_client(timeout=timeout).last_edited(which)
    click.echo(edited.isoformat())


if __name__ == "__main__":
    cmd()
