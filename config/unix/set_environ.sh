#!/bin/bash

# Substituye macro windows %~dp0 que devuelve directorio donde se ejecuta el batch
cd `dirname ${0}` # Se situa en el directorio del script
cd ../..
PROJECT_DIR=`pwd` # Guarda directorio donde estan todos los sources de los packages
echo "PROJECT_DIR = ${PROJECT_DIR}"

CONDA_ENV=python_packages
PATH_DEVELOPER_MODE=${PROJECT_DIR}
