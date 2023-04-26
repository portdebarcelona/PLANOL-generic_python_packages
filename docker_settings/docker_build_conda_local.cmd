pushd %~dp0..

set TAG_IMAGE=planolport/conda_gdal_oracle_geopandas:training

docker build --tag %TAG_IMAGE% --file Dockerfile.conda %CD%

popd
