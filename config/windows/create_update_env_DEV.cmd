@echo off

rem ===============================================================
rem Argumentos:
rem ===============================================================

where micromamba
@if [%errorlevel%] NEQ [0] (
    @IF NOT DEFINED MAMBA_ROOT_PREFIX (SET MAMBA_ROOT_PREFIX=%USERPROFILE%\micromamba)
    ECHO "MAMBA_ROOT_PREFIX=%MAMBA_ROOT_PREFIX%"
    @IF NOT EXIST "%MAMBA_ROOT_PREFIX%" SET /p MAMBA_ROOT_PREFIX="Enter path Micromamba (default=%MAMBA_ROOT_PREFIX%): "
)

pushd "%~dp0"

call set_micromamba_base.cmd

call micromamba env create --name=python_packages_DEV --file="../../environment.yml"
@IF %ERRORLEVEL% NEQ 0 (
  call micromamba update --name=python_packages_DEV --file="../../environment.yml"
)

call micromamba activate "python_packages_DEV"

rem Variables to install generic packages from PATH DEV REPO (if exists)
pushd "%~dp0../.."
set "PATH_DEVELOPER_MODE=%CD%"
call pip install --editable "%PATH_DEVELOPER_MODE%\extra_utils_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\extra_osgeo_utils_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\spatial_utils_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\cx_oracle_spatial_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\pandas_utils_pckg"
call pip install --editable "%PATH_DEVELOPER_MODE%\duckdb_utils_pckg"
