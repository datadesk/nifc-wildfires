geomac-wildfires
================

Download wildfire data from GeoMAC

Installation
------------

::

    $ pipenv install geomac-wildfires


Command-line usage
------------------

::

    Usage: geomacwildfires [OPTIONS] COMMAND [ARGS]...

      A command-line interface for downloading wildfire perimeter data from
      GeoMAC. Returns GeoJSON.

    Options:
      --help  Show this message and exit.

    Commands:
      active-fires  Perimeters of active fires in a recent 24-hour period from...
      all-fires     Perimeters of all fires from GeoMAC
      nifc-sitrep   NIFC Sit Rep fire points from GeoMAC


Download data from GeoMAC. ::

    $ geomacwildfires active-fires
    $ geomacwildfires all-fires
    $ geomacwildfires nifc-sitrep


Python usage
------------

Import the library. ::

    >>> import geomac_wildfires

Download a GeoJSON of active fire perimeters from GeoMAC. Returns GeoJSON. ::

    >>> data = geomac_wildfires.get_active_fires()

Download a GeoJSON of all fire perimeters from GeoMAC. Returns GeoJSON. ::

    >>> data = geomac_wildfires.get_all_fires()

Download a GeoJSON of active fire points from NIFC Sit Rep from GeoMAC. Returns GeoJSON. ::

    >>> data = geomac_wildfires.get_nifc_sitrep()


Contributing
------------

Install dependencies for development. ::

    $ pipenv install --dev

Run tests.::

    $ make test

Shipping new version to PyPI. ::

    $ make ship


Developing the CLI
------------------

The command-line interface is implemented using Click and setuptools. To install it locally for development inside your virtual environment, run the following installation command, as `prescribed by the Click documentation <https://click.palletsprojects.com/en/7.x/setuptools/#setuptools-integration>`_. ::

    $ pip install --editable .
