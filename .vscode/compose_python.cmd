@echo off
rem Ejecuta python dentro del servicio Compose de este repo.
rem Uso: compose_python.cmd <servicio> [args python...]
rem Convierte backslashes de rutas Windows a / para el contenedor.
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if "%~1"=="" (
  echo Uso: %~nx0 ^<servicio^> [args python...]
  exit /b 1
)

set "SERVICE=%~1"
shift

set "ARGS="
:loop
if "%~1"=="" goto run
set "ARG=%~1"
set "ARG=!ARG:\=/!"
set "ARGS=!ARGS! "!ARG!""
shift
goto loop

:run
docker compose run --rm "%SERVICE%" python %ARGS%
exit /b %ERRORLEVEL%
