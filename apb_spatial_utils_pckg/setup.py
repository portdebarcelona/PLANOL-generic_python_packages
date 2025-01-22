#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: setup.py
#   Created: 29/01/2020, 19:16
#   Last modified: 29/01/2020, 19:16
#   Copyright (c) 2020
import importlib
import os

from setuptools import setup


GIT_REPO = 'https://github.com/portdebarcelona/PLANOL-generic_python_packages'


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='apb_spatial_utils',
    version='0.1.2',
    packages=['apb_spatial_utils'],
    url=f'{GIT_REPO}/tree/master/apb_spatial_utils_pckg',
    author='Ernesto Arredondo Martinez',
    author_email='ernestone@gmail.com',
    maintainer='Port de Barcelona',
    maintainer_email='planolport@portdebarcelona.cat',
    description='Miscellaneous spatial utils for python',
    long_description=readme(),
    # Ver posibles clasifiers aqui [https://pypi.org/classifiers/]
    classifiers=[
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
        'Operating System :: OS Independent'
    ],
    install_requires=[
        'shapely',
        'pyproj',
        'apb_extra_utils<1.1'
    ],
    python_requires='>=3.6'
)
