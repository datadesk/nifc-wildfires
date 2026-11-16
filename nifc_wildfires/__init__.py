"""Download wildfires data from the National Interagency Fire Center."""

from datetime import datetime
from typing import Any

from nifc_wildfires import client as _client
from nifc_wildfires.client import (
    BASE_URL,
    MAX_ATTEMPTS,
    MAX_PAGES,
    MAX_PROBLEMS,
    PAGE_SIZE,
    TIMEOUT,
    NIFCClient,
)
from nifc_wildfires.errors import NIFCError, NIFCValidationError, ValidationProblem
from nifc_wildfires.schema import (
    Fetcher,
    IncidentKind,
    IncidentType,
    Layer,
    QueryOptions,
    Reply,
)

__all__ = [
    "BASE_URL",
    "MAX_ATTEMPTS",
    "MAX_PAGES",
    "MAX_PROBLEMS",
    "PAGE_SIZE",
    "TIMEOUT",
    "Fetcher",
    "IncidentKind",
    "IncidentType",
    "Layer",
    "NIFCClient",
    "NIFCError",
    "NIFCValidationError",
    "QueryOptions",
    "Reply",
    "ValidationProblem",
    "get_active_perimeters",
    "get_active_perimeters_last_edited",
    "get_incidents",
    "get_incidents_last_edited",
]

# The download functions below read the settings above each time they run, so
# changing one of them still changes the next download, as it always has.
requests = _client.requests


def _client_for(get: Fetcher | None, strict: bool) -> NIFCClient:
    """Make a client from the current module-level settings.

    Args:
        get: The function that makes the web request, or None for the default.
        strict: Whether to stop on data that does not have the expected shape.

    Returns:
        A client ready to download.

    Examples:
        >>> _client_for(None, True).page_size
        1000
    """
    return NIFCClient(
        get=get,
        strict=strict,
        timeout=TIMEOUT,
        page_size=PAGE_SIZE,
        max_pages=MAX_PAGES,
        max_attempts=MAX_ATTEMPTS,
        max_problems=MAX_PROBLEMS,
    )


def get_active_perimeters(
    options: QueryOptions | None = None,
    *,
    get: Fetcher | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Get fire perimeters of all active fires from NIFC.

    This is a shortcut for ``NIFCClient(get=get, strict=strict)``. Make a client
    yourself to reuse settings across several downloads.

    Args:
        options: The settings that shape the query. The default returns every
            perimeter with every field.
        get: A function that makes the web request, such as ``requests.get``
            (the default). Pass your own to add retries, logging or custom
            headers.
        strict: If True (the default), data that does not have the expected
            shape raises ``NIFCValidationError``. If False, the problems are
            logged to the ``nifc_wildfires`` logger and the data is returned as
            NIFC sent it.

    Returns:
        A GeoJSON object with multipolygon geometry.

    Raises:
        NIFCValidationError: If strict and the data does not have the expected
            shape, or if a reply has no list of features at all.
        NIFCError: If NIFC sends back an error or a failed status. Problems
            reaching NIFC at all raise the ``requests`` library's own errors.

    Examples:
        >>> data = get_active_perimeters()
        >>> data["type"]
        'FeatureCollection'
        >>> wildfires = get_active_perimeters(
        ...     QueryOptions(
        ...         where="attr_IncidentTypeCategory='WF'",
        ...         out_fields="OBJECTID,poly_IncidentName",
        ...         geometry_precision=5,
        ...     )
        ... )
    """
    return _client_for(get, strict).get_active_perimeters(options)


def get_incidents(
    options: QueryOptions | None = None,
    *,
    get: Fetcher | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Get year-to-date fire incident points from NIFC situation reports.

    Includes active and inactive incidents, and prescribed burns (type ``RX``),
    which are fires lit on purpose and can be most of the points. Leave them out
    with ``QueryOptions(exclude_incident_types={IncidentType.PRESCRIBED_FIRE})``.
    This is a shortcut for
    ``NIFCClient(get=get, strict=strict)``. Make a client yourself to reuse
    settings across several downloads.

    Args:
        options: The settings that shape the query. The default returns every
            incident with every field.
        get: A function that makes the web request, such as ``requests.get``
            (the default). Pass your own to add retries, logging or custom
            headers.
        strict: If True (the default), data that does not have the expected
            shape raises ``NIFCValidationError``. If False, the problems are
            logged to the ``nifc_wildfires`` logger and the data is returned as
            NIFC sent it.

    Returns:
        A GeoJSON object with point geometry.

    Raises:
        NIFCValidationError: If strict and the data does not have the expected
            shape, or if a reply has no list of features at all.
        NIFCError: If NIFC sends back an error or a failed status. Problems
            reaching NIFC at all raise the ``requests`` library's own errors.

    Examples:
        >>> data = get_incidents()
        >>> data["type"]
        'FeatureCollection'
        >>> names = get_incidents(QueryOptions(out_fields="OBJECTID,IncidentName"))
        >>> lenient = get_incidents(strict=False)
        >>> wildfires = get_incidents(
        ...     QueryOptions(exclude_incident_types={IncidentType.PRESCRIBED_FIRE})
        ... )
    """
    return _client_for(get, strict).get_incidents(options)


def get_active_perimeters_last_edited(*, get: Fetcher | None = None) -> datetime:
    """Get when NIFC last edited its active fire perimeters.

    Useful for skipping a download when nothing has changed.

    Args:
        get: A function that makes the web request, such as ``requests.get``
            (the default). Pass your own to add retries, logging or custom
            headers.

    Returns:
        The last edit time, in UTC.

    Raises:
        NIFCValidationError: If NIFC does not report a usable edit time.
        NIFCError: If NIFC sends back an error or a failed status. Problems
            reaching NIFC at all raise the ``requests`` library's own errors.

    Examples:
        >>> get_active_perimeters_last_edited().tzinfo
        datetime.timezone.utc
    """
    return _client_for(get, True).get_active_perimeters_last_edited()


def get_incidents_last_edited(*, get: Fetcher | None = None) -> datetime:
    """Get when NIFC last edited its fire incident points.

    Useful for skipping a download when nothing has changed.

    Args:
        get: A function that makes the web request, such as ``requests.get``
            (the default). Pass your own to add retries, logging or custom
            headers.

    Returns:
        The last edit time, in UTC.

    Raises:
        NIFCValidationError: If NIFC does not report a usable edit time.
        NIFCError: If NIFC sends back an error or a failed status. Problems
            reaching NIFC at all raise the ``requests`` library's own errors.

    Examples:
        >>> get_incidents_last_edited().tzinfo
        datetime.timezone.utc
    """
    return _client_for(get, True).get_incidents_last_edited()
