rem Docker build VENV image
docker build -t ernestone/python_gdal_oracle_geopandas .

rem Docker build CONDA image
docker build -f Dockerfile.conda -t ernestone/conda_gdal_oracle_geopan
das .

rem Docker compose build
docker compose build python_packages

rem Docker Push
docker push ernestone/python_gdal_oracle_geopandas:latest
