rem !ATENCION! - Ejecutar despues de activar el entorno de Python (default o python2)

pushd "%CONDA_PREFIX%"

rem Instalacion NODEJS (package NPM) para copiar comandos para convertir GEOJSONs a TOPOJSONs
call npm install topojson-server
call npm install topojson-simplify

popd