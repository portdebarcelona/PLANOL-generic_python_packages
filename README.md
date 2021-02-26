## Python library for GIS and spatial stuff, plus miscellaneous functionality 
Python packages developed by the years as requirements for my different projects as GIS developer with `QGIS`, `ESRI`, 
`Oracle`, `Postgis`, and other technologies used in this kind of projects with spatial data.
### Package _extra_utils_
Packages and modules used on different commonly problems founded in typical projects dealing with strings, mails, 
logging, sql, xml and others.

To install:
```shell script
pip install "git+https://github.com/ernestone/python_packages#egg=extra_utils&subdirectory=extra_utils_pckg"
```
### Package _spatial_utils_
Modules to deal with spatial data using common used spatial libraries as `Shapely`, 
`Topojsons` (requires `Nodejs` installed), ...

To install:
```shell script
pip install "git+https://github.com/ernestone/python_packages#egg=spatial_utils&subdirectory=spatial_utils_pckg"
```
### Package _osgeo_utils_
Modules to add common functionality to `OSGEO GDAL`. Requires `GDAL` library C previously installed 
(see how here https://gdal.org/download.html#binaries).

To install:
```shell script
pip install "git+https://github.com/ernestone/python_packages#egg=spatial_utils&subdirectory=spatial_utils_pckg"
```
### Package _cx_oracle_spatial_
Modules to connect to `Oracle` database and treat his objects in a `sqlalchemy` style but dealing with spatial data as one more type. Added the functionality of common used libraries in this kind of projects from the `spatial_utils` package to convert the `Oracle` data on different open source data types.

To install:
```shell script
pip install "git+https://github.com/ernestone/python_packages#egg=cx_oracle_spatial&subdirectory=cx_ora_spatial_pckg"
```
### Package _pandas_utils_
Modules to add functionality over `pandas` and `geopandas` 

To install:
```shell script
pip install "git+https://github.com/ernestone/python_packages#egg=pandas_utils&subdirectory=pandas_utils_pckg"
```
