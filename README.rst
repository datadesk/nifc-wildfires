geomac-wildfires
================

Download wildfire data from GeoMAC

Installation
------------

::

    $ pipenv install geomac_wildfires


Command-line usage
------------------

::

    Usage: geomacwildfires [OPTIONS] COMMAND [ARGS]...

      A command-line interface for downloading wildfire data from NASA
      satellites.

      Returns GeoJSON.

    Options:
      --help  Show this message and exit.

    Commands:
      active-fires  Download latest active fire perimeter data from GeoMAC


Download latest active fire perimeter data from GeoMAC. ::

    $ geomacwildfires active-fires


Python usage
------------

Import the library. ::

    >>> import geomac_wildfires

Download a GeoJSON of active fire perimeters from GeoMAC. Returns GeoJSON. ::

    >>> data = geomac_wildfires.get_active_fires()


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
