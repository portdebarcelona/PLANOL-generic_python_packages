@echo off

pushd "%~dp0"
call set_environ
call set_conda_base.cmd
if %errorlevel% neq 0 exit /b %errorlevel%
popd

rem =========== CONDA ============
IF DEFINED CONDA_ENV (ECHO Valor CONDA_ENV=%CONDA_ENV%) ELSE (SET CONDA_ENV=python_packages)

call conda activate "%CONDA_ENV%"
if %errorlevel% neq 0 exit /b %errorlevel%

rem Añadir scripts del Conda Environment a la sesion
set "PATH=%CONDA_PREFIX%\scripts;%PATH%"