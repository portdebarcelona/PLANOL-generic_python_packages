@echo off
rem ***************************************************************************************
rem * Envia mail cons los parmámetros indicados.
rem * Los parametros que se pueden pasar se pueden averiguar con "-- --help"
rem ***************************************************************************************

python -m extra_utils.send_mail enviar-mail %*

@echo on