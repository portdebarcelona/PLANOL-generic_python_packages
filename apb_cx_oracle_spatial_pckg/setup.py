#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: setup.py
#   Created: 05/04/2020, 00:21
#   Last modified: 05/04/2020, 00:21
#   Copyright (c) 2020
import importlib
import os

from setuptools import setup, find_packages


GIT_REPO = 'https://github.com/portdebarcelona/PLANOL-generic_python_packages'


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='apb_cx_oracle_spatial',
    version='1.0.1',
    packages=find_packages(),
    url=f'{GIT_REPO}/tree/master/apb_cx_oracle_spatial_pckg',
    author='Ernesto Arredondo Martínez',
    author_email='ernestone@gmail.com',
    maintainer='Port de Barcelona',
    maintainer_email='planolport@portdebarcelona.cat',
    description='cx_Oracle with spatial capabilities (SDO_GEOM and OGC)',
    long_description=readme(),
    # Ver posibles clasifiers aqui [https://pypi.org/classifiers/]
    classifiers=[
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
        'Operating System :: OS Independent'
    ],
    install_requires=[
        'cx_oracle <9',
        'lxml',
        'apb_extra_osgeo_utils<1.1',
        'apb_spatial_utils<1.1'
    ],
    python_requires='>=3.6',
    package_data={
        # If any package contains *.txt, *.md or *.yml files, include them:
        "": ["*.txt", "*.md", "*.yml"]
    }
)
