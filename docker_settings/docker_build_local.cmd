pushd %~dp0..

set TAG_IMAGE=planolport/python_gdal_oracle_geopandas:latest

docker build --tag %TAG_IMAGE% --file Dockerfile %CD%

popd
