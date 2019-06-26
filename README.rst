nasa-wildfires
==============

Download wildfire data from NASA satellites

Installation
------------

::

    $ pipenv install geomac_active_fires


Command-line usage
-----------------

::

    Usage: geomacactivefires [OPTIONS] COMMAND [ARGS]...

      A command-line interface for downloading wildfire data from NASA
      satellites.

      Returns GeoJSON.

    Options:
      --help  Show this message and exit.

    Commands:
      active-fire-perimeters  Download latest active fire perimeter data from GeoMAC


Download latest active fire perimeter data from GeoMAC. ::

    $ geomacactivefires active-fire-perimeters


Python usage
------------

Import the library. ::

    >>> import geomac_active_fires

Download a GeoJSON of active fire perimeters from GeoMAC. Returns GeoJSON. ::

    >>> data = geomac_active_fires.get_active_fire_perimeters()


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

The command-line interface is implemented using Click and setuptools. To install it locally for development inside your virtual environment, run the following installation command, as `prescribed by the Click documentation <https://click.palletsprojects.com/en/7.x/setuptools/#setuptools-integration>`. ::

    $ pip install --editable .
