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
collection. If NIFC cannot be reached or sends back an error, they raise
`nifc_wildfires.NIFCError`.

Choose which features, fields and coordinate precision to download.

```python
data = nifc_wildfires.get_active_perimeters(
    where="attr_IncidentTypeCategory='WF'",
    out_fields="OBJECTID,poly_IncidentName",
    geometry_precision=5,
)
```

The same settings are available on the command line as `--where`,
`--out-fields` and `--geometry-precision`.

Find out when NIFC last edited its data, for example to skip a download when
nothing has changed.

```python
edited = nifc_wildfires.get_active_perimeters_last_edited()
```

Make requests with your own function to add retries, logging or custom headers.
It is called like `requests.get(url, params=params, timeout=seconds)` and must
return something with `status_code` and `json()`.

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
