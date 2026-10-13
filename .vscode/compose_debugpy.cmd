@echo off
rem Arranca debugpy en el servicio Compose y espera al cliente (attach).
rem Uso: compose_debugpy.cmd <servicio> <workdir> <puerto> <script_o_modulo_flag> <target> [args...]
rem   script_o_modulo_flag = file | module | unittest
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if "%~4"=="" (
  echo Uso: %~nx0 ^<servicio^> ^<workdir^> ^<puerto^> ^<file^|module^|unittest^> ^<target^> [args...]
  exit /b 1
)

set "SERVICE=%~1"
set "WORKDIR=%~2"
set "PORT=%~3"
set "MODE=%~4"
set "TARGET=%~5"
rem Sustituir \ por / con expansion retardada. La forma con porcentaje deja el literal TARGET:\=
set "TARGET=!TARGET:\=/!"
shift
shift
shift
shift
shift

set "EXTRA="
:loop
if "%~1"=="" goto run
set "ARG=%~1"
set "ARG=!ARG:\=/!"
set "EXTRA=!EXTRA! !ARG!"
shift
goto loop

:run
if /I "!MODE!"=="file" (
  set "PY_TAIL=--wait-for-client !TARGET! !EXTRA!"
) else if /I "!MODE!"=="module" (
  set "PY_TAIL=--wait-for-client -m !TARGET! !EXTRA!"
) else if /I "!MODE!"=="unittest" (
  set "PY_TAIL=--wait-for-client -m unittest !TARGET! !EXTRA!"
) else (
  echo MODE invalido: !MODE!
  exit /b 1
)

docker compose run --rm --no-deps -p !PORT!:!PORT! -w "!WORKDIR!" "!SERVICE!" bash -c "python -m debugpy --version >/dev/null 2>&1 || pip install -q debugpy; exec python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:!PORT! !PY_TAIL!"
exit /b %ERRORLEVEL%
