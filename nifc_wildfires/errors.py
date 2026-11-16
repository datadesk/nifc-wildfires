"""The errors this package raises."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationProblem:
    """One thing that was wrong with the data NIFC sent back.

    Attributes:
        location: Where the problem is, as the path of keys and list positions
            from the top of the reply, such as ``("features", 3, "geometry")``.
        message: A plain description of the problem.

    Examples:
        >>> ValidationProblem(("features", 3, "geometry"), "Field required")
        ValidationProblem(location=('features', 3, 'geometry'), message='Field required')
    """

    location: tuple[str | int, ...]
    message: str


class NIFCError(Exception):
    """Raised when NIFC sends back an error, a failed status or something unexpected."""


class NIFCValidationError(NIFCError):
    """Raised when NIFC's data does not have the shape this package expects.

    This is different from a failed request or an error message from NIFC, which
    raise the plain ``NIFCError``. Catch this one to handle a shape problem on
    its own, for example by trying again with ``strict=False``.

    Attributes:
        what: A short description of the data that failed, such as ``"reply"``.
        problems: The problems found, which may be cut short.
        problem_count: How many problems there were in all.

    Examples:
        >>> error = NIFCValidationError("reply", [ValidationProblem(("type",), "bad")])
        >>> error.problem_count
        1
    """

    def __init__(
        self,
        what: str,
        problems: list[ValidationProblem],
        problem_count: int | None = None,
    ) -> None:
        """Describe a shape failure.

        Args:
            what: A short description of the data that failed.
            problems: The problems found, which may be cut short.
            problem_count: How many problems there were in all. Defaults to the
                number of problems given.
        """
        self.what = what
        self.problems = problems
        self.problem_count = len(problems) if problem_count is None else problem_count
        summary = "; ".join(
            f"{'.'.join(str(part) for part in p.location)}: {p.message}"
            for p in problems[:3]
        )
        super().__init__(f"NIFC {what} is not in the expected shape ({summary}).")


class DataChangedError(NIFCError):
    """Raised when NIFC's data shifts in the middle of a paged download."""
