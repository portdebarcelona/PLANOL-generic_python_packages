pushd "%~dp0"

pip install pdoc

pdoc cx_oracle_spatial extra_osgeo_utils extra_utils pandas_utils spatial_utils -t ./templates -d google --logo ./logo.png -o ./html

popd
