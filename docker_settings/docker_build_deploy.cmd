pushd %~dp0..

set TEST_PYPI=%1
echo TEST_PYPI=%TEST_PYPI%

call docker_settings/create_volumes.cmd

docker compose --progress plain build gdal_oracle

docker compose --progress plain build python_packages_deploy_oracle

docker compose --progress plain build python_packages_deploy_no_oracle

popd
