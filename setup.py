import os
from setuptools import setup


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='nifc-wildfires',
    version='0.1.14',
    description="Download wildfires data from NIFC",
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Los Angeles Times Data and Graphics Department',
    author_email='datagraphics@caltimes.com',
    url='http://www.github.com/palewire/nifc-wildfires',
    license="MIT",
    packages=("nifc_wildfires",),
    install_requires=[
        "requests",
        "click"
    ],
    entry_points="""
        [console_scripts]
        nifcwldfires=nifc_wildfires.cli:cmd
    """,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License'
    ],
    project_urls={
        'Maintainer': 'https://github.com/palewire',
        'Source': 'https://github.com/palewire/nifc-wildfires',
        'Tracker': 'https://github.com/palewire/nifc-wildfires/issues',
    },
)
