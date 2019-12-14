@echo off
rem ***************************************************************************************
rem * Envia mail cons los parmámetros indicados.
rem * Los parametros que se pueden pasar se pueden averiguar con "-- --help"
rem ***************************************************************************************

"%~dp0..\..\run_py3.bat" -m apb_utils.apbSendMail enviar-mail %*

@echo on