cd "$(dirname "${0}")" || exit

pip install pdoc

PACKAGES_DOC=${PACKAGES_DOC:-cx_oracle_spatial extra_osgeo_utils extra_utils pandas_utils spatial_utils}

pdoc $PACKAGES_DOC -t ./templates -d google --logo ./logo.png -o ./html

cd ./html || exit

python -m http.server ${PORT_SERVER_DOC:-80}
