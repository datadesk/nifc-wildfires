# nifc-wildfires

Download wildfires data from the [National Interagency Fire Center](https://www.nifc.gov/)

```{contents} Table of contents
:local:
:depth: 2
```

## Installation

```sh
uv add nifc-wildfires
```

## Command-line usage

```sh
Usage: nifcwildfires [OPTIONS] COMMAND [ARGS]...

  A command-line interface for downloading wildfire perimeter and incident points data from
  NIFC. Returns GeoJSON.

Options:
  --help  Show this message and exit.

Commands:
  active-perimeters  Perimeters of active fires
  incidents          All YTD fire incident points from NIFC situation reports
```

From the shell:

```sh
nifcwildfires active-perimeters
nifcwildfires incidents
```

## Python usage

Import the library and go.

```python
import nifc_wildfires

data = nifc_wildfires.get_active_perimeters()
data = nifc_wildfires.get_incidents()
```

Both functions download every page of results and return a GeoJSON feature
collection. The data is checked as it arrives: every feature needs a shape of
the right type for its layer (polygons for perimeters, points for incidents),
and feature IDs must be whole numbers that do not repeat. If NIFC cannot be
reached, sends back an error, or sends data in an unexpected shape, they raise
`nifc_wildfires.NIFCError`. NIFC edits its data constantly, so a download that
catches a change halfway through starts over, up to three times.

Choose which features, fields and coordinate precision to download with a
`QueryOptions` object. The defaults return everything, and mistakes such as an
empty filter, a negative precision or a misspelled setting are rejected as soon
as the object is created.

```python
from nifc_wildfires import QueryOptions

options = QueryOptions(
    where="attr_IncidentTypeCategory='WF'",
    out_fields="OBJECTID,poly_IncidentName",
    geometry_precision=5,
)
data = nifc_wildfires.get_active_perimeters(options)
```

The same settings are available on the command line as `--where`,
`--out-fields` and `--geometry-precision`.

By default the data is checked strictly. If anything has the wrong shape,
`nifc_wildfires.NIFCValidationError` is raised. It is a kind of `NIFCError`, so
existing handlers still catch it, but it can also be caught on its own. Its
`problems` list says where each problem is, and `problem_count` says how many
there were in all.

```python
try:
    data = nifc_wildfires.get_incidents()
except nifc_wildfires.NIFCValidationError as error:
    for problem in error.problems:
        print(problem.location, problem.message)
```

To carry on regardless, pass `strict=False`, or `--no-strict` on the command
line. The problems are written to the `nifc_wildfires` logger as warnings and the
data is returned exactly as NIFC sent it. A reply with no list of features at
all cannot be read, so it still raises.

Find out when NIFC last edited its data, for example to skip a download when
nothing has changed.

```python
edited = nifc_wildfires.get_active_perimeters_last_edited()
```

Make requests with your own function to add retries, logging or custom headers.
It is called like `requests.get(url, params=params, timeout=seconds)` and must
return something with `status_code` and `json()`. The `Fetcher` and `Reply`
types describe this, so a type checker can confirm your function fits.

```python
data = nifc_wildfires.get_incidents(get=my_get)
```

## API reference

```{eval-rst}
.. automodule:: nifc_wildfires
```

## Contributing

Install dependencies for development.

```sh
make bootstrap
```

Run the fast checks and the tests.

```sh
make check
make test
```

Run everything CI runs.

```sh
make verify
```

## Links

* Docs: [palewi.re/docs/nifc-wildfires/](https://palewi.re/docs/nifc-wildfires/)
* Issues: [github.com/datadesk/nifc-wildfires/issues](https://github.com/datadesk/nifc-wildfires/issues)
* Packaging: [pypi.python.org/pypi/nifc-wildfires](https://pypi.python.org/pypi/nifc-wildfires)
* Testing: [github.com/datadesk/nifc-wildfires/actions](https://github.com/datadesk/nifc-wildfires/actions)
