Download wildfires data from NIFC

## Installation

```sh
pipenv install nifc-wildfires
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
  incidents      All fire incident points in 2021, from NIFC situation reports
```

From the shell:

```sh
nifcwildfires active-perimeters
nifcwildfires incidents
```

## Python usage

Import the library and go.

```python
>>> import nifc_wildfires
>>> data = nifc_wildfires.get_active_perimeters()
>>> data = nifc_wildfires.get_incidents()
```

## Contributing

Install dependencies for development.

```sh
pipenv install --dev
```

Run tests.

```sh
make test
```

Shipping new version to PyPI.

```sh
make ship
```

## Developing the CLI

The command-line interface is implemented using Click and setuptools. To install it locally for development inside your virtual environment, run the following installation command, as [prescribed by the Click documentation](https://click.palletsprojects.com/en/7.x/setuptools/#setuptools-integration).

```sh
pip install --editable .
```
