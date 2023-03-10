pushd "%~dp0../.."

rem Docker build VENV image
docker build -t ernestone/python_gdal_oracle_geopandas:latest -t planolport/python_gdal_oracle_geopandas:training .

rem Docker build CONDA image
docker build -f Dockerfile.conda -t ernestone/conda_gdal_oracle_geopandas:latest -t planolport/conda_gdal_oracle_geopandas:training .

rem Docker compose build
docker compose build python_packages

rem Docker Push
docker push ernestone/python_gdal_oracle_geopandas:latest

popd
