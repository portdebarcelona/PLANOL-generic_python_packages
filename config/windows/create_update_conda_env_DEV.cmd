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

set CONDA_ENV=python_packages_DEV

call conda env create --name=python_packages_DEV --file="../../environment.yml"
@IF %ERRORLEVEL% NEQ 0 (
  call conda env update --name=python_packages_DEV --file="../../environment.yml"
)

call start_conda_env.cmd

@REM call post_install_python.cmd

rem Variables to install generic packages from PATH DEV REPO (if exists)
pushd "%~dp0../.."
set "PATH_DEVELOPER_MODE=%CD%"
call pip install --editable "%PATH_DEVELOPER_MODE%\extra_utils_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\extra_osgeo_utils_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\spatial_utils_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\cx_oracle_spatial_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\pandas_utils_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\duckdb_utils_pckg"

popd