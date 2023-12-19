pushd %~dp0..

call docker_settings/create_volumes.cmd

docker compose build python_packages

popd
