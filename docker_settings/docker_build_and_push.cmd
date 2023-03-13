set URL_REPO_GITHUB=https://github.com/portdebarcelona/PLANOL-generic_python_packages.git#training

set TAG_IMAGE=planolport/python_gdal_oracle_geopandas:training

docker build --tag %TAG_IMAGE% %URL_REPO_GITHUB%

docker push %TAG_IMAGE%
