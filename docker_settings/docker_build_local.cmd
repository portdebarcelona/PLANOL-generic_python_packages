pushd %~dp0..

call docker_settings/create_volumes.cmd

docker compose --progress plain build gdal_oracle

docker compose --progress plain build python_packages

popd
