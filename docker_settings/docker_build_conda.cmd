pushd %~dp0..

set TAG_IMAGE=planolport/conda_gdal_oracle_geopandas:latest

docker build --tag %TAG_IMAGE% --file Dockerfile.conda %CD%

docker push %TAG_IMAGE%

popd
