#!/bin/bash

cd `dirname ${0}`

source set_environ.sh

# =========== CONDA ============
if [ ! "${CONDA_ENV}" ]
then
    CONDA_ENV=python_packages
fi

conda activate ${CONDA_ENV}

# Añadir scripts del Conda Environment a la sesion
PATH="${CONDA_PREFIX}/scripts:${PATH}"
