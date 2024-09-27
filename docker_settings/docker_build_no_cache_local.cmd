pushd %~dp0..

call docker_settings/create_volumes.cmd

docker compose --progress plain build --no-cache python_packages

popd
