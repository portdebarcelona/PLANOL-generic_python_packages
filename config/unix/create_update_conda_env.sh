#!/bin/bash

OPER_CONDA=create

if [ $1 ]
then
    OPER_CONDA=%~1
fi

cd `dirname ${0}`
CUR_DIR=`pwd`
source ${CUR_DIR}/set_environ.sh

if [ "${OPER_CONDA}" == "create" ]
then
    conda ${OPER_CONDA} --name ${CONDA_ENV} python=3.7 -y -c conda-forge
fi
conda env update --name=${CONDA_ENV} --file="${CUR_DIR}/../conda_env.yml"

source "${CUR_DIR}/start_conda_env.sh"
source "${CUR_DIR}/post_install_python.sh"
