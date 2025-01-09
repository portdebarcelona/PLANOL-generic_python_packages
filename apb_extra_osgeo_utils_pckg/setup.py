#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: setup.py
#   Created: 29/01/2020, 19:16
#   Last modified: 29/01/2020, 19:16
#   Copyright (c) 2020
import importlib
import os

from setuptools import setup, find_packages

GIT_REPO = 'https://github.com/portdebarcelona/PLANOL-generic_python_packages'


def format_requirement(n_pckg, version=None):
    git_repo = os.getenv('GIT_REPO', GIT_REPO)

    if git_repo and git_repo.lower().startswith('https://github.com/portdebarcelona/'):
        if git_repo_branch := os.getenv('GIT_REPO_BRANCH'):
            if not git_repo.endswith(f'@{git_repo_branch}'):
                git_repo = f'{git_repo}@{git_repo_branch}'

        str_req = f'{n_pckg} @ git+{git_repo}#egg={n_pckg}&subdirectory={n_pckg}_pckg'
    else:
        str_req = f'{n_pckg}'
        if version:
            str_req = f'{str_req}{version}'

    path_dev = os.getenv('PATH_DEVELOPER_MODE', '')
    path_pckg = os.path.join(path_dev, "{}_pckg".format(n_pckg))
    if os.path.exists(path_pckg):
        str_req = f'{n_pckg}'
        try:
            importlib.import_module(n_pckg)
            print(f"In 'developer mode' no file path for required package '{n_pckg}' already installed")
        except ImportError:
            print(f"In 'developer mode' install required package '{n_pckg} from file path")
            str_req = f'{n_pckg} @ ' \
                      f'file://{path_pckg}' \
                      f'#egg={n_pckg}'

    print(str_req)
    return str_req


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='apb_extra_osgeo_utils',
    version='1.0.0',
    packages=find_packages(),
    url=f'{GIT_REPO}/tree/master/apb_extra_osgeo_utils_pckg',
    author='Ernesto Arredondo Martinez',
    author_email='ernestone@gmail.com',
    maintainer='Port de Barcelona',
    maintainer_email='planolport@portdebarcelona.cat',
    description='Osgeo GDAL utils for python',
    long_description=readme(),
    # Ver posibles clasifiers aqui [https://pypi.org/classifiers/]
    classifiers=[
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
        'Operating System :: OS Independent'
    ],
    install_requires=[
        format_requirement('apb_extra_utils', '<1.1')
    ],
    python_requires='>=3.6'
)
