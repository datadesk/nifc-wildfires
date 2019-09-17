import os
from setuptools import setup


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='geomac-wildfires',
    version='0.0.11',
    description="Download latest fire perimeters from GeoMAC",
    long_description=read('README.rst'),
    author='Los Angeles Times Data Desk',
    author_email='datadesk@latimes.com',
    url='http://www.github.com/datadesk/geomac-wildfires',
    license="MIT",
    packages=("geomac_wildfires",),
    install_requires=[
        "fiona",
        "geojson",
        "click",
    ],
    entry_points="""
        [console_scripts]
        geomacwildfires=geomac_wildfires.cli:cmd
    """,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: MIT License',
    ],
    project_urls={
        'Maintainer': 'https://github.com/datadesk',
        'Source': 'https://github.com/datadesk/geomac-wildfires',
        'Tracker': 'https://github.com/datadesk/geomac-wildfires/issues'
    },
)
