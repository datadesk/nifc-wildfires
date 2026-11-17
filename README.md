# nifc-wildfires

Download wildfire data from the [National Interagency Fire Center](https://www.nifc.gov/) (NIFC): fire perimeters and incident points, as GeoJSON.

## Install

```sh
uv add nifc-wildfires
```

## Use it from the command line

```sh
nifcwildfires active-perimeters > perimeters.json
nifcwildfires incidents --exclude-incident-type RX > incidents.json
nifcwildfires download incidents-year-to-date --incident-type WF > year.json
nifcwildfires last-edited active-perimeters
```

## Use it from Python

```python
from nifc_wildfires import IncidentType, Layer, NIFCClient, QueryOptions

client = NIFCClient()
perimeters = client.get_active_perimeters()
wildfires = client.get_incidents(QueryOptions(incident_types={IncidentType.WILDFIRE}))
year = client.download(Layer.INCIDENTS_YEAR_TO_DATE)
```

## Things to know

* **`incidents` is not the whole year.** It is NIFC's current layer: a few hundred incidents that are active or were updated recently. Use the year-to-date layer for the year.
* **Prescribed burns are included.** They are fires lit on purpose, and they are most of the current incident points. Leave them out with `--exclude-incident-type RX`.
* **The data has no license and no warranty.** The code is MIT. Check NIFC's terms before you republish the data.
* **AI helped write this package.** AI tools assisted in writing its code, tests and documentation. A person directed and reviewed the work.

The documentation has the full list of layers, options, codes and errors.

### Links

* Docs: [palewi.re/docs/nifc-wildfires/](https://palewi.re/docs/nifc-wildfires/)
* Issues: [github.com/datadesk/nifc-wildfires/issues](https://github.com/datadesk/nifc-wildfires/issues)
* Packaging: [pypi.python.org/pypi/nifc-wildfires](https://pypi.python.org/pypi/nifc-wildfires)
* Testing: [github.com/datadesk/nifc-wildfires/actions](https://github.com/datadesk/nifc-wildfires/actions)
