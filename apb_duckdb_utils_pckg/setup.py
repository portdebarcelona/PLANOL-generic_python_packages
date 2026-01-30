#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: setup.py
#   Created: 05/04/2020, 00:21
#   Last modified: 30/01/2026, 18:41
#   Copyright (c) 2020
import importlib
import os

from setuptools import setup, find_packages


GIT_REPO = 'https://github.com/portdebarcelona/PLANOL-generic_python_packages'


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='apb_duckdb_utils',
    version='1.1.1',
    packages=find_packages(),
    url=f'{GIT_REPO}/tree/master/apb_duckdb_utils_pckg',
    author='Ernesto Arredondo Martínez',
    author_email='ernestone@gmail.com',
    maintainer='Port de Barcelona',
    maintainer_email='planolport@portdebarcelona.cat',
    description='DuckDB utils',
    long_description=readme(),
    # Ver posibles clasifiers aqui [https://pypi.org/classifiers/]
    classifiers=[
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
        'Operating System :: OS Independent'
    ],
    install_requires=[
        'duckdb<1.5',
        'ibis-framework[duckdb,geospatial]',
        'duckdb-engine',
        'polars[pyarrow]',
        'apb_extra_utils<1.1',
        'apb_pandas_utils<1.2',
        # TODO - revisar en versions futures si cal actualitzar aquesta dependència
        "sqlglot<28.7",  # Per evitar problemes de compatibilitat ibis-framework
    ],
    python_requires='>=3.6',
    package_data={
        # If any package contains *.txt, *.md or *.yml files, include them:
        "": ["*.txt", "*.md", "*.yml"]
    }
)
