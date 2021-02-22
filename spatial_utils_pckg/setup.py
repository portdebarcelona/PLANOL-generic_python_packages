#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: setup.py
#   Created: 29/01/2020, 19:16
#   Last modified: 29/01/2020, 19:16
#   Copyright (c) 2020

from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='spatial_utils',
    version='0.9',
    packages=['spatial_utils'],
    url='https://github.com/ernestone/python_packages/tree/master/spatial_utils_pckg',
    author='Ernesto Arredondo Martinez',
    author_email='ernestone@gmail.com',
    description='Miscelanous spatial utils for python',
    long_description=readme(),
    # Ver posibles clasifiers aqui [https://pypi.org/classifiers/]
    classifiers=[
        'Programming Language :: Python :: 3.7',
        'Topic :: Utilities',
        'Operating System :: OS Independent'
    ],
    install_requires=[
        'shapely',
        'geopandas',
        'extra_utils'
    ],
    python_requires='>=3.7'
)
