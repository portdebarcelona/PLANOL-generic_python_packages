pushd %~dp0..

call docker_settings/create_volumes.cmd

set TAG_IMAGE=planolport/mamba_gdal_oracle_geopandas:training

docker build --tag %TAG_IMAGE% --file Dockerfile.mamba %CD%

popd
