#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: setup.py
#   Created: 29/01/2020, 19:16
#   Last modified: 29/01/2020, 19:16
#   Copyright (c) 2020

from setuptools import setup, find_packages
import os

GIT_REPO = os.getenv('GIT_REPO', 'https://github.com/ernestone/python_packages')


def format_requirement(n_pckg):
    str_req = f'{n_pckg} @ git+{GIT_REPO}#egg={n_pckg}&subdirectory={n_pckg}_pckg'

    path_dev = os.getenv('PATH_DEVELOPER_MODE')
    if path_dev and os.path.exists(path_dev):
        str_req = f'{n_pckg} @ ' \
                  f'file://{os.path.join(path_dev, "{}_pckg".format(n_pckg))}' \
                  f'#egg={n_pckg}'

    print(str_req)
    return str_req


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='osgeo_utils',
    version='0.9',
    packages=find_packages(),
    url=f'{GIT_REPO}/tree/master/osgeo_utils_pckg',
    author='Ernesto Arredondo Martinez',
    author_email='ernestone@gmail.com',
    description='Osgeo GDAL utils for python',
    long_description=readme(),
    # Ver posibles clasifiers aqui [https://pypi.org/classifiers/]
    classifiers=[
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
        'Operating System :: OS Independent'
    ],
    install_requires=[
        format_requirement('extra_utils')
    ],
    python_requires='>=3.6'
)
