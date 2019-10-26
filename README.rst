geomac-wildfires
================

Download wildfires data from GeoMAC

.. image:: https://travis-ci.org/datadesk/geomac-wildfires.svg?branch=master
    :target: https://travis-ci.org/datadesk/geomac-wildfires

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
      active-perimeters   Perimeters of active fires in a recent 24-hour period
      all-perimeters      Perimeters of all fires
      nifc-incidents      Fire incident points from NIFC situation reports


Download data from GeoMAC. ::

    $ geomacwildfires active-perimeters
    $ geomacwildfires all-perimeters
    $ geomacwildfires get-nifc-incidents


Python usage
------------

Import the library. ::

    >>> import geomac_wildfires
    >>> data = geomac_wildfires.get_active_perimeters()
    >>> data = geomac_wildfires.get_all_perimeters()
    >>> data = geomac_wildfires.get_nifc_incidents()


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
