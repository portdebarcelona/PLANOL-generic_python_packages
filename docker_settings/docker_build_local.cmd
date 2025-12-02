pushd %~dp0..

call docker_settings/create_volumes.cmd

set GDAL_VERSION=3.10.3

docker compose --progress plain build --no-cache --build-arg  GDAL_VERSION=%GDAL_VERSION% gdal_oracle

docker compose --progress plain build python_packages

popd
