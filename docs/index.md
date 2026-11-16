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

  Download wildfire perimeter and incident points data from NIFC.

  Returns GeoJSON.

Options:
  --help  Show this message and exit.

Commands:
  active-perimeters  Perimeters of active fires
  incidents          All YTD fire incident points from NIFC situation reports
  last-edited        When NIFC last edited a layer, as a UTC time.
```

From the shell:

```sh
nifcwildfires active-perimeters
nifcwildfires incidents
```

Both download commands print valid JSON, and share these options.

| Option | What it does |
| --- | --- |
| `--where TEXT` | A SQL-style filter that picks which features to return. |
| `--out-fields TEXT` | The fields to return, separated by commas. |
| `--geometry-precision INTEGER` | The decimal places to keep in coordinates. |
| `--incident-type [WF\|RX\|CX]` | Keep only this kind of incident. Repeat to keep several. |
| `--exclude-incident-type [WF\|RX\|CX]` | Leave out this kind of incident. Repeat to leave out several. |
| `--strict / --no-strict` | Stop on data that is not in the expected shape (the default), or log it and carry on. |
| `--timeout FLOAT` | Seconds to wait for each request. The default is 60. |
| `--verbose` | When a download fails, list every problem found. |

```sh
nifcwildfires active-perimeters --where "attr_IncidentTypeCategory='WF'" --geometry-precision 5
```

Ask when NIFC last edited a layer, for example to skip a download when nothing
has changed. The time is in UTC. `last-edited` also takes `--timeout` and
`--verbose`.

```sh
nifcwildfires last-edited active-perimeters
```

A failure prints one line starting with `Error:` to standard error and exits with
a non-zero code, with nothing written to standard output. Data in an unexpected
shape adds a hint to run again with `--verbose` or `--no-strict`.

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

## Wildfires and prescribed burns

**The incident points include prescribed burns.** A prescribed burn is a fire lit
on purpose, to manage land. NIFC reports them alongside wildfires, so unless you
say otherwise `incidents` returns both. When this was written, in November 2026,
about two thirds of the incident points were prescribed burns, not wildfires.
Check this before counting or mapping them.

NIFC labels each record with an incident type:

| Code | In Python | Meaning |
| --- | --- | --- |
| `WF` | `IncidentType.WILDFIRE` | Wildfire. |
| `RX` | `IncidentType.PRESCRIBED_FIRE` | Prescribed fire, set on purpose. |
| `CX` | `IncidentType.COMPLEX` | Understood to be a complex, several fires managed together. NIFC's layer metadata does not define the codes, so confirm this before relying on it. |

To leave prescribed burns out:

```python
from nifc_wildfires import IncidentType, QueryOptions

options = QueryOptions(exclude_incident_types={IncidentType.PRESCRIBED_FIRE})
data = nifc_wildfires.get_incidents(options)
```

To keep wildfires only, name them instead. This also drops anything with another
code, such as `CX`.

```python
options = QueryOptions(incident_types={IncidentType.WILDFIRE})
```

Use one or the other, not both. Excluding keeps records that have no incident
type at all, and keeping only a type drops them. Plain codes such as `"RX"` work
too, and an unknown code is rejected as soon as the options are created.

The same on the command line:

```sh
nifcwildfires incidents --exclude-incident-type RX
nifcwildfires incidents --incident-type WF
nifcwildfires active-perimeters --incident-type WF
```

The perimeters carry the same codes. At the last check none of the current
perimeters were prescribed burns, but that can change, so apply the same filter
if you need wildfires only.

The two layers spell the field differently, `attr_IncidentTypeCategory` for
perimeters and `IncidentTypeCategory` for incidents. These options use the right
one for each layer. If you write your own `where` filter instead, you have to
use the right spelling yourself. Your filter and these options can be combined,
and both apply.

## Using a client

The functions above are shortcuts. To keep settings in one place and reuse them
across several downloads, make a `NIFCClient`. Besides the fetch function and
strictness, it holds the request timeout, the page size, and the limits on pages
and restarts. All have sensible defaults.

```python
from nifc_wildfires import Layer, NIFCClient, QueryOptions

client = NIFCClient(get=my_get, strict=False, timeout=30)
perimeters = client.get_active_perimeters()
incidents = client.get_incidents(QueryOptions(out_fields="OBJECTID,IncidentName"))
edited = client.get_incidents_last_edited()

# The same, for any layer by name:
data = client.download(Layer.PERIMETERS)
```

A client cannot be changed once made. To change a setting, make another one.

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
