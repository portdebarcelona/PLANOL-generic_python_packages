#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: setup.py
#   Created: 29/01/2020, 19:16
#   Last modified: 29/01/2020, 19:16
#   Copyright (c) 2020

from setuptools import setup, find_packages
import os

GIT_REPO = 'https://github.com/portdebarcelona/PLANOL-generic_python_packages'


def readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), 'r', encoding='utf-8') as f:
        return f.read()


setup(
    name='apb_extra_utils',
    version='1.0.2',
    packages=find_packages(),
    url=f'{GIT_REPO}/tree/master/apb_extra_utils_pckg',
    author='Ernesto Arredondo Martinez',
    author_email='ernestone@gmail.com',
    maintainer='Port de Barcelona',
    maintainer_email='planolport@portdebarcelona.cat',
    description='Miscellaneous utils for python',
    long_description=readme(),
    # Ver posibles clasifiers aqui [https://pypi.org/classifiers/]
    classifiers=[
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
        'Operating System :: OS Independent'
    ],
    install_requires=[
        'pyparsing<2.4',
        'docutils',
        'fire',
        'Pillow',
        'jellyfish',
        'pyyaml',
        'sqlparse==0.2.4',
        'openpyxl',
        'psycopg2-binary',
        'sqlalchemy',
        'tdqm',
        'sendgrid==6.10.0'
    ],
    python_requires='>=3.6',
    package_data={
        # If any package contains *.txt, *.md or *.yml files, include them:
        "": ["*.txt", "*.md", "*.yml", "*.sql", "*.cmd"]
    }
)
