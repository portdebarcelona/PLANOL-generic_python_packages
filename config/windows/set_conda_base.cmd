@echo off

pushd "%~dp0"
call set_environ
popd

WHERE conda
IF %ERRORLEVEL% NEQ 0 (
    set "PATH=%PATH%;%CONDA_ROOT%;%CONDA_ROOT%\Library\bin;%CONDA_ROOT%\condabin;%CONDA_ROOT%\scripts"
    set ERRORLEVEL=0
    )
