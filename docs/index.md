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
  download           Download any layer by name.
  incidents          Current fire incident points, recently active only,...
  last-edited        When NIFC last edited a layer, as a UTC time.
```

From the shell:

```sh
nifcwildfires active-perimeters
nifcwildfires incidents
```

`incidents` is the *current* layer: fires that are still active or were updated
recently, a few hundred at a time. It is not the whole year. Use `download` to
reach every layer, including the year-to-date ones (see
[Which layer is which](#which-layer-is-which)):

```sh
nifcwildfires download incidents-last-24-hours
nifcwildfires download incidents-year-to-date --exclude-incident-type RX
```

All of the download commands print valid JSON, and share these options.

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

## Which layer is which

NIFC publishes several layers of the same data. Only the first two were available
in earlier versions, and **neither of them is the whole year**. The counts below
were seen on November 16, 2026.

| `Layer` | Command-line name | What it holds | Records |
| --- | --- | --- | --- |
| `CURRENT_PERIMETERS` | `current-perimeters` (or `active-perimeters`) | Outlines of fires that are not out yet. | 54 |
| `CURRENT_INCIDENTS` | `current-incidents` (or `incidents`) | Points for incidents that are active or were updated recently. | about 410 |
| `INCIDENTS_LAST_24_HOURS` | `incidents-last-24-hours` | Points for incidents started or updated in the last day. | about 90 |
| `INCIDENTS_YEAR_TO_DATE` | `incidents-year-to-date` | Points for every incident since January 1. | 45,390 |
| `PERIMETERS_YEAR_TO_DATE` | `perimeters-year-to-date` | Outlines for every fire since January 1. | 8,414 |

NIFC's description of its current perimeters layer says a fire drops out once it
is declared contained, controlled or out, once its fire report is certified, or
when it has not been updated for more than 3 days (under 10 acres), 8 days (10 to
100 acres) or 14 days (over 100 acres). That is checked hourly. Fires that started
before December of the previous year are left out. The current incidents layer
behaves the same way in the data (nothing older than December 2025, and every
record updated within the last two weeks), but I read the rule only for the
perimeters.

The year-to-date layers are large. The year-to-date perimeters were about 115 MB
with full coordinates, and the incidents took about 30 seconds to download. Narrow
them with `--incident-type`, `--where`, `--out-fields` and `--geometry-precision`.
NIFC also has layers for all years (432,000 incidents and 43,000 perimeters). They
are bigger than this package's safety limit of 100 pages, so they are not offered.

```python
from nifc_wildfires import Layer, NIFCClient

data = NIFCClient().download(Layer.INCIDENTS_YEAR_TO_DATE)
```

## About the data

The data comes from NIFC's Wildland Fire Interagency Geospatial Services (WFIGS).
Its [published metadata](https://www.arcgis.com/sharing/rest/content/items/d1c32af3212341869b3c810f1a215824/info/metadata/metadata.xml?format=default&output=html)
says:

- The data is refreshed every 5 minutes, and changes to a perimeter's source can
  take up to 15 minutes to show.
- Perimeters are not available for every incident.
- It credits the Department of the Interior's Office of Wildland Fire (IRWIN),
  the USDA Forest Service, National Park Service, Fish and Wildlife Service,
  Bureau of Indian Affairs, Bureau of Land Management, National Association of
  State Foresters, US Fire Administration and National Wildfire Coordinating
  Group.
- It states **no license**, and says NIFC "gives no warranty, expressed or
  implied, as to the accuracy, reliability, or completeness of these data".

This package's MIT license covers its code, not the data. Check NIFC's terms before
you republish the data, and credit NIFC and its partners.

## About this package

AI tools assisted in writing this package's code, tests and documentation. A person
directed and reviewed the work.

## Wildfires and prescribed burns

**The incident points include prescribed burns.** A prescribed burn is a fire lit
on purpose, to manage land. NIFC reports them alongside wildfires, so unless you
say otherwise `incidents` returns both. In November 2026, about two thirds of the
current incident points were prescribed burns, not wildfires. Over the whole
year the share was much lower, about 14 percent (6,424 of 45,390), so the mix
depends on which layer you use. Check it before counting or mapping them.

### The codes

NIFC's layers do not define their codes. They come from the
[NWCG Event Kind and Event Category standard](https://wildfireweb-prod-media-bucket.s3.us-gov-west-1.amazonaws.com/s3fs-public/2024-03/Event%20Kind%20and%20Event%20Category.pdf)
(dated December 14, 2021). Every record has a **kind** (`IncidentTypeKind`) and a
**category** (`IncidentTypeCategory`) within it. The standard covers all kinds of
event, including hazards, accidents and training. These are the two kinds that
are fire, and their categories.

| Kind | In Python | Meaning |
| --- | --- | --- |
| `FI` | `IncidentKind.FIRE` | Fire. |
| `FM` | `IncidentKind.FIRE_MANAGEMENT_ACTION` | Fire management action. |

| Code | In Python | Name in the standard | Kind | In the data? |
| --- | --- | --- | --- | --- |
| `WF` | `IncidentType.WILDFIRE` | Wildfire | `FI` | Yes |
| `RX` | `IncidentType.PRESCRIBED_FIRE` | Prescribed Fire | `FI` | Yes |
| `CX` | `IncidentType.COMPLEX` | Incident Complex | `FM` | Yes |
| `DF` | `IncidentType.DEBRIS_FIRE` | Debris / Product Fire | `FI` | No |
| `NS` | `IncidentType.NON_STATISTICAL` | Non-Statistical / Other | `FI` | No |
| `SF` | `IncidentType.STRUCTURE_FIRE` | Structure Fire | `FI` | No |
| `VF` | `IncidentType.VEHICLE_FIRE` | Vehicle Fire | `FI` | No |
| `BR` | `IncidentType.EMERGENCY_STABILIZATION` | Emergency Stabilization | `FM` | No |
| `FA` | `IncidentType.FALSE_ALARM` | False Alarm | `FM` | No |
| `FR` | `IncidentType.FIRE_REHABILITATION` | Fire Rehabilitation | `FM` | No |
| `SU` | `IncidentType.INCIDENT_SUPPORT` | Incident / Event Support | `FM` | No |
| `OR` | `IncidentType.OUT_OF_AREA_RESPONSE` | Out of Area Response | `FM` | No |
| `PP` | `IncidentType.PREPAREDNESS` | Preparedness / Prepositioning | `FM` | No |

The last column was checked against the live service in November 2026. NIFC's own
description of the perimeters layer says it holds wildfires and prescribed fires
only, but the data also holds complexes, so do not rely on the description.
`IncidentType.kind` and `IncidentType.label` give a category's kind and its name.

### Leaving prescribed burns out

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
perimeters were prescribed burns, but the year-to-date perimeters had some, so
apply the same filter if you need wildfires only. The year-to-date perimeters
had no complexes, and the current ones had two.

The two layers spell the field differently, `attr_IncidentTypeCategory` for
perimeters and `IncidentTypeCategory` for incidents. These options use the right
one for each layer. If you write your own `where` filter instead, you have to
use the right spelling yourself. Your filter and these options can be combined,
and both apply.

### Complexes

A complex (`CX`) is two or more wildfires in the same general area that are
managed together under one commander. The wildfires inside it stay in the data as
`WF` records, marked `IsCpxChild = 1` and carrying the complex's name in
`CpxName` (`attr_IsCpxChild` and `attr_CpxName` in the perimeters). It is the only
field whose metadata lists coded values: `0` for no and `1` for yes.

- **In the incident points,** both the complex and its member fires are present.
  Adding up their sizes may count the same acres twice. Check the totals before
  you rely on them.
- **In the perimeters,** the complexes seen so far had no outline of their own,
  only their member fires did. The two `CX` perimeters, Esau Canyon and Grand
  Park 2, are small fires that NIFC labeled as complexes. They are not members of
  another complex (`IsCpxChild = 0`). A wildfires-only filter leaves them out.

## Field reference

NIFC's service describes none of its fields: across the 97 incident fields and 119
perimeter fields there is no description and no list of allowed values. The
layer's [published metadata](https://www.arcgis.com/sharing/rest/content/items/d1c32af3212341869b3c810f1a215824/info/metadata/metadata.xml?format=default&output=html)
has a sentence about most fields, but no value lists. Because of that, only the
incident kind and category above are backed by a published standard.

The values below are only what was **seen on November 16, 2026**. They are not
complete lists, NIFC can add to them at any time, and a value may also be empty.
None of them are checked or enumerated by this package, so a filter on one of them
is your own `where` filter.

| Field | Values seen |
| --- | --- |
| `GACC` | `AICC`, `EACC`, `GBCC`, `NRCC`, `NWCC`, `ONCC`, `OSCC`, `RMCC`, `SACC`, `SWCC` |
| `FireCause` | `Human`, `Natural`, `Undetermined`. NIFC's metadata says "human, natural or unknown". |
| `FireBehaviorGeneral` | `Minimal`, `Moderate`, `Active`, `Extreme` |
| `ICS209ReportStatus` | `I`, `U`, `F`. The metadata mentions "initial, update, or final". |
| `IncidentComplexityLevel` | `Type 1 Incident` to `Type 5 Incident` |
| `WFDSSDecisionStatus` | `Approved Decision`, `Pending Decision`, `No Decision` |
| `POOLandownerKind` | `Federal`, `Local`, `Other`, `Private`, `Soverei`, `State` |
| `poly_MapMethod` (perimeters) | `GPS-Driven`, `GPS-Flight`, `GPS-Walked`, `IR Image Interpretation`, `Image Interpretation`, `Mixed Methods`, `Phone/Tablet`, `Remote Sensing Derived`, `Auto-generated for InFORM` |

**Cut-off values.** NIFC stores some text in fields that are too short, so values
are cut off: `Soverei` is "Sovereign", and `OrganizationalAssessment` has
`Complex Incident Manageme`. Filter on the cut-off spelling, not the full word.

**Matching fields between the layers.** The perimeters layer repeats the incident
fields with an `attr_` in front, so `FireCause` becomes `attr_FireCause`. That is
true of 83 of the 97 incident fields. The other fields are renamed or missing:

| Incident points | Perimeters |
| --- | --- |
| `FinalFireReportApprovedByTitle`, `...ByUnit`, `...Date` | `attr_FFReportApprovedByTitle`, `...ByUnit`, `...Date` |
| `FireStrategyFullSuppPercent`, `FireStrategyPointZonePercent` | `attr_FireStrategyFullSuppPrcnt`, `attr_FireStrategyPointZonePrcnt` |
| `ICS209ReportForTimePeriodFrom`, `...To` | `attr_ICS209RptForTimePeriodFrom`, `...To` |
| `IncidentManagementOrganization` | `attr_IncidentManagementOrg` |
| `POOJurisdictionalUnitParentUnit` | `attr_POOJurisdictUnitParentUnit` |
| `POOLegalDescPrincipalMeridian` | `attr_POOLegalDescPrincipalMerid` |
| `PercentPerimeterToBeContained` | `attr_PercentPerimToBeContained` |
| `StrategicDecisionPublishDate` | `attr_StratDecisionPublishDate` |
| `OBJECTID`, `GlobalID` | No `attr_` copy. Each layer numbers its own rows, so these do not link an incident to its perimeter. |

The perimeters also have `poly_` fields about the outline itself, and three
`attr_` fields with no incident match: `attr_CalculatedAcres`, `attr_FORID` and
`attr_Source`.

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
data = client.download(Layer.CURRENT_PERIMETERS)
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
