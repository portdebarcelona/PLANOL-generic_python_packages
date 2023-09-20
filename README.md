## Python library for GIS, Oracle spatial and other miscellaneous utilities 
Python packages developed for GIS projects related with `QGIS`, `ESRI`, 
`Oracle`, `Postgis`, and other technologies used with spatial data.

### Configuration:
You must configure this environment variables to be able to run this project

- PATH_DEVELOPER_MODE_APB
- PATH_BASE_PACKAGES
- PATH_GISWEB_DADES
- DATA_DIR_DEV

### Docker configuration:
The docker configuration can be done changing the `.env.dev` file located on `docker_settings/.env.dev`

The configurations are:
- APB_ENTORN
- APB_DATA_DIR
- APB_GIS_LOGS_BASE
- APB_GIS_LOGS
- APB_PYTHON_LOGS_DIR
- ROSMIMAN_MAIL_LIST
- DATASOURCE_ORA_ROSMIMAN
- USER_ORA_ROSMIMAN
- PSW_ORA_ROSMIMAN
- DATA_REPO_GIS_DIR
- DATA_VIGENT_REPO_GIS_DIR
- DATA_HISTORICA_REPO_GIS_DIR
- APB_REPO_URN_LOGS
- APB_REPO_GIS_MAIL_USERS
- APB_DIR_PLANOL_GPKG
- DEV_ENVIRON
- MAIL_SERVER
- DEFAULT_FROM_MAIL
- PYTHON_LOGS_DIR
- HOST_POSTGIS_REPO_GIS
- PORT_POSTGIS_REPO_GIS
- DB_POSTGIS_REPO_GIS
- USER_POSTGIS_REPO_GIS
- PSW_POSTGIS_REPO_GIS
- geoserver_url_base:Base URL used for Geoserver

### Packages:
- #### [_extra_utils_](./extra_utils_pckg/README.md)
  Python modules to do different stuff about typical use cases in a python program

- #### [_spatial_utils_](./spatial_utils_pckg/README.md)
  Python modules to do different stuff with spatial data

- #### [_extra_osgeo_utils_](./extra_osgeo_utils_pckg/README.md)
  Python modules to do different stuff with spatial data using api OSGEO/GDAL

- #### [_cx_oracle_spatial_](./cx_oracle_spatial_pckg/README.md)
  Python modules to add spatial capabilities to cx_Oracle

- #### [_pandas_utils_](./pandas_utils_pckg/README.md)
  Python modules to add functionality over pandas and geopandas
