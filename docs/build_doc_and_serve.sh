cd "$(dirname "${0}")" || exit

pip install pdoc

PACKAGES_DOC=${PACKAGES_DOC:-cx_oracle_spatial extra_osgeo_utils extra_utils pandas_utils spatial_utils}
URL_LOGO_APB=${URL_LOGO_APB:-http://planoldev.portdebarcelona.cat:8022/sftp/api/public/dl/cq4LBWhn?inline=true}

pdoc $PACKAGES_DOC -t ./templates -d google --logo ${URL_LOGO_APB} -o ./html

cd ./html || exit

python -m http.server ${PORT_SERVER_DOC:-80}
