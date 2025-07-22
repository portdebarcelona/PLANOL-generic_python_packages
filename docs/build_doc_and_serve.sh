cd "$(dirname "${0}")" || exit

pip install pdoc==15.0.3

PACKAGES_DOC=${PACKAGES_DOC:-apb_cx_oracle_spatial apb_extra_osgeo_utils apb_extra_utils apb_duckdb_utils  apb_pandas_utils apb_spatial_utils}
URL_LOGO_APB=${URL_LOGO_APB:-https://www.portdebarcelona.cat/themes/custom/portbcn/logo.svg}
MAIN_README_DOC=${MAIN_README_DOC:-README.md}
JINJA_TEMPLATES=${JINJA_TEMPLATES:-./templates}
PREFIX_DOCS=${PREFIX_DOCS:-generic_python_packages}

pdoc $PACKAGES_DOC -t "${JINJA_TEMPLATES}" -d google --logo ${URL_LOGO_APB} -o "./html/${PREFIX_DOCS}"

cp "${JINJA_TEMPLATES}/favicon.ico" "./html/${PREFIX_DOCS}/"

cd ./html || exit

python -m http.server ${PORT_SERVER_DOC:-80}
