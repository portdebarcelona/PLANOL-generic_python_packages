@echo off
rem ***************************************************************************************
rem * Lanza proceso para convertir DDL de tabla Oracle en forma versionada tipo SCD
rem * Los parametros que se pueden pasar se pueden averiguar con "-- --help"
rem ***************************************************************************************

python -m apb_extra_utils.ddl_to_scd.ddl_to_scd %*
