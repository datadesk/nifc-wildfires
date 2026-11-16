"""A client that downloads wildfires data from the National Interagency Fire Center."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from nifc_wildfires.errors import (
    DataChangedError,
    NIFCError,
    NIFCValidationError,
    ValidationProblem,
)
from nifc_wildfires.schema import (
    Fetcher,
    Layer,
    LayerMetadata,
    Page,
    QueryOptions,
)

BASE_URL = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services"
TIMEOUT = 60
PAGE_SIZE = 1000
MAX_PAGES = 100
MAX_ATTEMPTS = 3
MAX_PROBLEMS = 100

logger = logging.getLogger("nifc_wildfires")

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class _PageInfo:
    """What a download needs to know about one page of features."""

    count: int
    object_ids: list[int]
    has_more: bool


@dataclass(frozen=True)
class NIFCClient:
    """Downloads wildfires data from NIFC, with settings kept in one place.

    Make one client, then call its methods as often as you like. The settings
    all have sensible defaults, so ``NIFCClient()`` is enough to get started.

    Attributes:
        get: A function that makes the web request, such as ``requests.get``
            (the default when None). Pass your own to add retries, logging or
            custom headers.
        strict: If True (the default), data that does not have the expected shape
            raises ``NIFCValidationError``. If False, the problems are logged to
            the ``nifc_wildfires`` logger and the data is returned as NIFC sent
            it.
        timeout: The seconds to wait for each request.
        page_size: How many features to ask for in each request.
        max_pages: The most pages one download may use before giving up.
        max_attempts: How many times a download starts over when NIFC's data
            changes partway through.
        max_problems: How many problems an error keeps. The count stays exact.

    Examples:
        >>> client = NIFCClient(strict=False, timeout=30)
        >>> data = client.get_incidents()
        >>> data["type"]
        'FeatureCollection'
    """

    get: Fetcher | None = None
    strict: bool = True
    timeout: float = TIMEOUT
    page_size: int = PAGE_SIZE
    max_pages: int = MAX_PAGES
    max_attempts: int = MAX_ATTEMPTS
    max_problems: int = MAX_PROBLEMS

    def __post_init__(self) -> None:
        """Reject settings that could never work.

        Raises:
            ValueError: If a number setting is not above zero.

        Examples:
            >>> NIFCClient(page_size=0)
            Traceback (most recent call last):
            ...
            ValueError: page_size must be above zero.
        """
        for name in (
            "timeout",
            "page_size",
            "max_pages",
            "max_attempts",
            "max_problems",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be above zero.")

    def get_active_perimeters(
        self, options: QueryOptions | None = None
    ) -> dict[str, Any]:
        """Get fire perimeters of all active fires from NIFC.

        Args:
            options: The settings that shape the query. The default returns every
                perimeter with every field.

        Returns:
            A GeoJSON object with multipolygon geometry.

        Raises:
            NIFCValidationError: If strict and the data does not have the expected
                shape, or if a reply has no list of features at all.
            NIFCError: If NIFC sends back an error or a failed status. Problems
                reaching NIFC at all raise the ``requests`` library's own errors.

        Examples:
            >>> data = NIFCClient().get_active_perimeters()
            >>> data["type"]
            'FeatureCollection'
        """
        return self.download(Layer.PERIMETERS, options)

    def get_incidents(self, options: QueryOptions | None = None) -> dict[str, Any]:
        """Get year-to-date fire incident points from NIFC situation reports.

        Includes active and inactive incidents, and prescribed burns (type
        ``RX``), which are fires lit on purpose and can be most of the points.
        Leave them out with ``exclude_incident_types`` in the options.

        Args:
            options: The settings that shape the query. The default returns every
                incident with every field.

        Returns:
            A GeoJSON object with point geometry.

        Raises:
            NIFCValidationError: If strict and the data does not have the expected
                shape, or if a reply has no list of features at all.
            NIFCError: If NIFC sends back an error or a failed status. Problems
                reaching NIFC at all raise the ``requests`` library's own errors.

        Examples:
            >>> data = NIFCClient().get_incidents()
            >>> data["type"]
            'FeatureCollection'
        """
        return self.download(Layer.INCIDENTS, options)

    def get_active_perimeters_last_edited(self) -> datetime:
        """Get when NIFC last edited its active fire perimeters.

        Useful for skipping a download when nothing has changed.

        Returns:
            The last edit time, in UTC.

        Raises:
            NIFCValidationError: If NIFC does not report a usable edit time. There
                is nothing to pass along in that case, so ``strict`` does not
                apply here.
            NIFCError: If NIFC sends back an error or a failed status. Problems
                reaching NIFC at all raise the ``requests`` library's own errors.

        Examples:
            >>> NIFCClient().get_active_perimeters_last_edited().tzinfo
            datetime.timezone.utc
        """
        return self.last_edited(Layer.PERIMETERS)

    def get_incidents_last_edited(self) -> datetime:
        """Get when NIFC last edited its fire incident points.

        Useful for skipping a download when nothing has changed.

        Returns:
            The last edit time, in UTC.

        Raises:
            NIFCValidationError: If NIFC does not report a usable edit time.
            NIFCError: If NIFC sends back an error or a failed status. Problems
                reaching NIFC at all raise the ``requests`` library's own errors.

        Examples:
            >>> NIFCClient().get_incidents_last_edited().tzinfo
            datetime.timezone.utc
        """
        return self.last_edited(Layer.INCIDENTS)

    def download(
        self, layer: Layer, options: QueryOptions | None = None
    ) -> dict[str, Any]:
        """Download every feature from one NIFC layer as GeoJSON.

        NIFC returns a limited number of features per request, so this keeps
        asking for the next page until NIFC says there are no more. NIFC edits its
        data all the time, so a download that catches a change halfway through
        starts over, up to ``max_attempts`` times.

        Args:
            layer: The NIFC layer to download.
            options: The settings that shape the query. The default returns every
                feature with every field.

        Returns:
            A GeoJSON feature collection with the features from every page.

        Raises:
            NIFCValidationError: If strict and the data fails the shape checks, or
                if a reply has no list of features at all.
            NIFCError: If a request fails, the pages stop before NIFC says it is
                done, there are more than ``max_pages`` pages, or NIFC's data
                keeps changing during ``max_attempts`` download attempts.

        Examples:
            >>> data = NIFCClient().download(Layer.INCIDENTS, QueryOptions())
            >>> data["type"]
            'FeatureCollection'
        """
        options = options or QueryOptions()
        for _ in range(self.max_attempts):
            try:
                return self._download_pages(layer, options)
            except DataChangedError:
                continue
        raise NIFCError(
            f"NIFC data kept changing during {self.max_attempts} download attempts. "
            "Try again."
        )

    def last_edited(self, layer: Layer) -> datetime:
        """Ask NIFC when a layer's data was last edited.

        Args:
            layer: The NIFC layer to ask about.

        Returns:
            The last edit time, in UTC.

        Raises:
            NIFCValidationError: If NIFC does not report a usable last edit time.
            NIFCError: If the request fails or NIFC sends back an error.

        Examples:
            >>> NIFCClient().last_edited(Layer.INCIDENTS).tzinfo
            datetime.timezone.utc
        """
        reply = self._get_json(f"{BASE_URL}/{layer}/FeatureServer/0", {"f": "json"})
        metadata = self._check(LayerMetadata, reply, "layer metadata")
        last_edit = metadata.editingInfo.lastEditDate
        try:
            return datetime.fromtimestamp(last_edit / 1000, UTC)
        except (OverflowError, OSError, ValueError) as error:
            raise NIFCError(
                "NIFC layer metadata has an invalid lastEditDate."
            ) from error

    def _download_pages(self, layer: Layer, options: QueryOptions) -> dict[str, Any]:
        """Download every page from a layer, once through.

        If an edit lands while the pages are being read, later pages shift and the
        same feature can show up twice, which means another feature was skipped.
        That is detected by repeated feature IDs.

        Args:
            layer: The NIFC layer to download.
            options: The settings that shape the query.

        Returns:
            A GeoJSON feature collection with the features from every page.

        Raises:
            NIFCValidationError: If strict and the data fails the shape checks, or
                if a reply has no list of features at all.
            NIFCError: If a request fails, the pages stop before NIFC says it is
                done, or there are more than ``max_pages`` pages.
            DataChangedError: If a feature ID is repeated across pages.

        Examples:
            >>> data = NIFCClient()._download_pages(Layer.INCIDENTS, QueryOptions())
            >>> data["type"]
            'FeatureCollection'
        """
        features: list[Any] = []
        seen_ids: set[int] = set()
        offset = 0
        for _ in range(self.max_pages):
            params: dict[str, Any] = {
                "outFields": options.out_fields,
                "where": options.where_for(layer),
                "orderByFields": "OBJECTID",
                "resultOffset": offset,
                "resultRecordCount": self.page_size,
                "f": "geojson",
            }
            if options.geometry_precision is not None:
                params["geometryPrecision"] = options.geometry_precision
            reply = self._get_json(f"{BASE_URL}/{layer}/FeatureServer/0/query", params)
            page = self._read_page(reply, layer)
            for object_id in page.object_ids:
                if object_id in seen_ids:
                    raise DataChangedError(
                        f"NIFC repeated feature {object_id} across pages."
                    )
                seen_ids.add(object_id)
            features.extend(reply["features"])
            if not page.has_more:
                return {"type": "FeatureCollection", "features": features}
            if not page.count:
                raise NIFCError("NIFC paging ended before all features were read.")
            offset += page.count
        raise NIFCError(f"NIFC exceeded the {self.max_pages}-page safety limit.")

    def _read_page(self, reply: dict[str, Any], layer: Layer) -> _PageInfo:
        """Check one page of features and pull out what the download needs.

        Args:
            reply: One reply from NIFC.
            layer: The layer being downloaded, which decides the allowed shapes.

        Returns:
            The number of features, their IDs, and whether more pages are waiting.

        Raises:
            NIFCValidationError: If the page fails the checks and the client is
                strict, or if the reply has no list of features at all, which
                cannot be read even leniently.

        Examples:
            >>> reply = {"type": "FeatureCollection", "features": []}
            >>> NIFCClient()._read_page(reply, Layer.INCIDENTS)
            _PageInfo(count=0, object_ids=[], has_more=False)
        """
        try:
            page = self._check(
                Page, reply, "reply", {"geometry_types": layer.geometry_types}
            )
        except NIFCValidationError as error:
            features = reply.get("features")
            if self.strict or not isinstance(features, list):
                raise
            logger.warning(
                "Letting %s problem(s) pass in a page of %s: %s",
                error.problem_count,
                layer.name.lower(),
                error,
            )
            ids = [
                f["properties"]["OBJECTID"]
                for f in features
                if isinstance(f, dict)
                and isinstance(f.get("properties"), dict)
                and type(f["properties"].get("OBJECTID")) is int
            ]
            properties = reply.get("properties")
            flag = (properties if isinstance(properties, dict) else {}).get(
                "exceededTransferLimit", reply.get("exceededTransferLimit")
            )
            return _PageInfo(len(features), ids, flag is True)
        ids = [
            f.properties["OBJECTID"]
            for f in page.features
            if "OBJECTID" in f.properties
        ]
        return _PageInfo(len(page.features), ids, page.has_more)

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make one request to NIFC and return its reply as a dictionary.

        NIFC reports many errors as a normal successful reply with an error
        message inside, so this checks for that as well as for failed requests.

        Args:
            url: The address to request.
            params: The query parameters to send.

        Returns:
            The reply parsed into a dictionary.

        Raises:
            NIFCError: If the request fails, the reply is not a JSON object, or
                the reply contains an error message.

        Examples:
            >>> layer = f"{Layer.INCIDENTS}/FeatureServer/0"
            >>> NIFCClient()._get_json(f"{BASE_URL}/{layer}", {"f": "json"})["name"]
            'WFIGS_Incident_Locations_Current'
        """
        fetch: Fetcher = self.get or requests.get
        r = fetch(url, params=params, timeout=self.timeout)
        if r.status_code != 200:
            raise NIFCError(f"Request for data failed with {r.status_code} status code")
        try:
            payload = r.json()
        except ValueError as error:
            raise NIFCError("NIFC returned invalid JSON.") from error
        if not isinstance(payload, dict):
            raise NIFCError("NIFC returned an unexpected response.")
        if "error" in payload:
            raise NIFCError(f"NIFC reported an API error: {payload['error']}")
        return payload

    def _check(
        self,
        model: type[ModelT],
        data: object,
        what: str,
        context: dict[str, Any] | None = None,
    ) -> ModelT:
        """Check data against a model and turn any problems into an error.

        Args:
            model: The Pydantic model the data must fit.
            data: The data to check.
            what: A short description of the data, used in the error message.
            context: Extra information the model's checks may use.

        Returns:
            The data as a model object.

        Raises:
            NIFCValidationError: If the data does not fit the model. The message
                lists the first few problems, without echoing the data itself.

        Examples:
            >>> page = {"type": "FeatureCollection", "features": []}
            >>> NIFCClient()._check(Page, page, "page").has_more
            False
        """
        try:
            return model.model_validate(data, context=context)
        except ValidationError as error:
            found = error.errors()
            problems = [
                ValidationProblem(tuple(e["loc"]), e["msg"])
                for e in found[: self.max_problems]
            ]
            raise NIFCValidationError(what, problems, len(found)) from error
