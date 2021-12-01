nifc-wildfires
================

Download wildfires data from NIFC

.. image:: https://travis-ci.org/datadesk/geomac-wildfires.svg?branch=master
    :target: https://travis-ci.org/datadesk/geomac-wildfires

Installation
------------

::

    $ pipenv install nifc-wildfires


Command-line usage
------------------

::

    Usage: nifcwildfires [OPTIONS] COMMAND [ARGS]...

      A command-line interface for downloading wildfire perimeter data from
      NIFC. Returns GeoJSON.

    Options:
      --help  Show this message and exit.

    Commands:
      current-perimeters   Perimeters of active fires
      nifc-incidents      Fire incident points from NIFC situation reports


Download data from NIFC. ::

    $ geomacwildfires current-perimeters
    $ geomacwildfires get-nifc-incidents


Python usage
------------

Import the library. ::

    >>> import nifc_wildfires
    >>> data = geomac_wildfires.get_current_perimeters()
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
