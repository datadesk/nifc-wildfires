import os
from setuptools import setup


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='GeoMAC-active-fires',
    version='0.0.1',
    description="Download latest fire perimeters from GeoMAC",
    long_description=read('README.rst'),
    author='Los Angeles Times Data Desk',
    author_email='datadesk@latimes.com',
    url='http://www.github.com/datadesk/GeoMAC-active-fires',
    license="MIT",
    packages=("GeoMAC-active-fires",),
    entry_points="""
        [console_scripts]
        geomacactivefires=geomac_active_fires.cli:cmd
    """,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: MIT License',
    ],
)
