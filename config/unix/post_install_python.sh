#!/bin/bash

# !ATENCION! - Ejecutar despues de activar el entorno de Python (default o python2)

cd "${CONDA_PREFIX}"

# Instalacion NODEJS (package NPM) para copiar comandos para convertir GEOJSONs a TOPOJSONs
npm install topojson-server
npm install topojson-simplify
