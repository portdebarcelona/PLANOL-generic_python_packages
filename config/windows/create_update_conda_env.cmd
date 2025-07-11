@echo off

rem ===============================================================
rem Argumentos:
rem ===============================================================

where conda
@if [%errorlevel%] NEQ [0] (
  @IF NOT DEFINED CONDA_ROOT (SET CONDA_ROOT=E:\Miniconda3)
  ECHO "CONDA_ROOT=%CONDA_ROOT%"
  @IF NOT EXIST "%CONDA_ROOT%" SET /p CONDA_ROOT="Enter path Anaconda (default=%CONDA_ROOT%): "
)

pushd "%~dp0"

call set_conda_base.cmd

call conda env create --file="../../environment.yml"
@IF %ERRORLEVEL% NEQ 0 (
  call conda env update --file="../../environment.yml"
)

call start_conda_env.cmd

rem Set for the environment test.pypi as main repo and the pypi repo as secondary
pip config --site set global.extra-index-url https://test.pypi.org/simple

rem Install packages from the generic repository
pip install apb_extra_utils
pip install apb_extra_osgeo_utils
pip install apb_spatial_utils
pip install apb_cx_oracle_spatial
pip install apb_pandas_utils
pip install apb_duckdb_utils

rem call post_install_python.cmd

popd