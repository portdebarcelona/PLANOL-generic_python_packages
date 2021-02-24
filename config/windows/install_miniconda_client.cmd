rem Instala miniconda client desde el programa de instalación Miniconda3-latest-Windows-x86_64.exe
rem  ==== CONDA ====
set "DIR_INSTALLER_CONDA=%~dp0"
@IF NOT EXIST %DIR_INSTALLER_CONDA% (
    set "DIR_INSTALLER_CONDA=%USERPROFILE%\Downloads"
    SET /p DIR_INSTALLER_CONDA="Enter path directory with conda installer 'Miniconda3-latest-Windows-x86_64.exe' (default=%USERPROFILE%\Downloads): "
    )

@IF NOT EXIST "%DIR_INSTALLER_CONDA%\Miniconda3-latest-Windows-x86_64.exe" (
    echo "No se ha encontrado el installer 'Miniconda3-latest-Windows-x86_64.exe' en el directori %DIR_INSTALLER_CONDA%"
    pause
    goto :EOF
)    

:install_conda
SET /p CONDA_ROOT="Enter directory conda install (default=%USERPROFILE%\Miniconda3): "
pushd "%DIR_INSTALLER_CONDA%"
start /wait "" Miniconda3-latest-Windows-x86_64.exe /AddToPath=1 /RegisterPython=0 /S /D=%CONDA_ROOT%
setx CONDA_ROOT "%CONDA_ROOT%"
popd
mkdir "%CONDA_ROOT%\..\conda_cache_pkgs"
setx CONDA_PKGS_DIRS "%CONDA_ROOT%\..\conda_cache_pkgs"

pause