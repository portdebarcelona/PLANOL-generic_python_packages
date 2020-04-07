#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: setup.py
#   Created: 29/01/2020, 19:16
#   Last modified: 29/01/2020, 19:16
#   Copyright (c) 2020

from setuptools import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='extra_utils',
    version='0.9',
    packages=find_packages(),
    url='https://github.com/ernestone/python_packages/tree/master/extra_utils_pckg',
    author='Ernesto Arredondo Martinez',
    author_email='ernestone@gmail.com',
    description='Miscelanous utils for python',
    long_description=readme(),
    # Ver posibles clasifiers aqui [https://pypi.org/classifiers/]
    classifiers=[
        'Programming Language :: Python :: 3.7',
        'Topic :: Utilities',
        'Operating System :: OS Independent'
    ],
    install_requires=[
        'pyparsing<2.4',
        'docutils-python3==0.13',
        'fire',
        'Pillow',
        'jellyfish',
        'pyyaml',
        'sqlparse==0.2.4',
        'openpyxl',
        'psycopg2',
        'sqlalchemy'
    ],
    python_requires='<3.8',
    package_data={
        # If any package contains *.txt, *.md or *.yml files, include them:
        "": ["*.txt", "*.md", "*.yml"]
    }
)