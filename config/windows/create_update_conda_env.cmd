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

rem call post_install_python.cmd

popd