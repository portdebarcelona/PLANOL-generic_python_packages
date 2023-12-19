@echo off

pushd "%~dp0"
call set_environ
popd

WHERE micromamba
IF %ERRORLEVEL% NEQ 0 (
    set "PATH=%PATH%;%MAMBA_ROOT_PREFIX%;%MAMBA_ROOT_PREFIX%\Library\bin;%MAMBA_ROOT_PREFIX%\condabin;%MAMBA_ROOT_PREFIX%\scripts"
    set ERRORLEVEL=0
    )
