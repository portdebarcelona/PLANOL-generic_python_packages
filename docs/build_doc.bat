pushd "%~dp0"

pip install pdoc

pdoc apb_cx_oracle_spatial apb_extra_osgeo_utils apb_extra_utils apb_duckdb_utils apb_pandas_utils apb_spatial_utils -t ./templates -d google --logo ./logo.png -o ./html

popd
