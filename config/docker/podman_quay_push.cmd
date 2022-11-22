podman login -u %~1

podman push --format v2s1 localhost/python_gdal_oracle_geopandas:latest quay.io/apb_arredoer/python_gdal_oracle_geopandas
