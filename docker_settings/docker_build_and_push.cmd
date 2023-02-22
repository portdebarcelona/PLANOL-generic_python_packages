set URL_REPO_GITHUB=https://github.com/portdebarcelona/PLANOL-generic_python_packages.git#master

set TAG_IMAGE=planolport/python_gdal_oracle_geopandas:latest

docker build --tag %TAG_IMAGE% %URL_REPO_GITHUB%

docker push %TAG_IMAGE%
