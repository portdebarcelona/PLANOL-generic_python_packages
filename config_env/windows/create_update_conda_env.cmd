@echo off

rem ===============================================================
rem Argumentos:
rem     1 (%~1): La operacion a realizar sobre el conda_environment
rem              (create o update) (default=create)
rem ===============================================================

SET OPER_CONDA=%~1

IF "%OPER_CONDA%" EQU "" (SET OPER_CONDA=create)

@IF NOT DEFINED CONDA_ROOT (SET CONDA_ROOT=E:\Miniconda3)
ECHO "CONDA_ROOT=%CONDA_ROOT%"
@IF NOT EXIST "%CONDA_ROOT%" SET /p CONDA_ROOT="Enter path Anaconda (default=%CONDA_ROOT%): "

pushd "%~dp0"

call set_environ.cmd
call set_conda_base.cmd

if [%OPER_CONDA%] EQU [create] (
    call conda env create --name=%CONDA_ENV% --file="../../environment.yml"
    )
call conda env update --name=%CONDA_ENV% --file="../../environment.yml"

call start_conda_env.cmd

call post_install_python.cmd

popd