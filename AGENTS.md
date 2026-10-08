# AGENTS.md

## Qué es
Monorepo Python de utilidades GIS del Port: GDAL/OSGeo, Oracle Spatial, pandas/geopandas y DuckDB. Cada paquete es `*_pckg` con `setup.py` (no `pyproject.toml`). Comentarios y README en catalán o castellano.

Orden de instalación editable en `Dockerfile.dev` (hay que respetarlo):

1. `apb_extra_utils_pckg`
2. `apb_extra_osgeo_utils_pckg`
3. `apb_spatial_utils_pckg`
4. `apb_cx_oracle_spatial_pckg` (usa `ORACLE_CLIENT_PATH`)
5. `apb_pandas_utils_pckg`
6. `apb_duckdb_utils_pckg` (extensiones `sqlite`, `spatial`, `json`, `httpfs`)

`Dockerfile` es la imagen de despliegue (`python_packages_deploy_oracle`). `Dockerfile.base` construye `gdal_oracle`. `Dockerfile.mamba` es la variante mamba.

## Intérprete de DEV
El intérprete es el servicio `python_packages` de `docker-compose.yml` en la raíz (contenedor `python_packages_dev`, `Dockerfile.dev`). Workdir `/project`; el repo va montado ahí. Entorno DEV: `docker_settings/.env.private/.env`, `.env.minio` y `.env.GISHISREP`. No vuelques esos ficheros. Procedimiento de ejecución: skill `generic-python-dev`.

`DATA_DIR_DEV` del host se monta en `/project/data`. PostGIS local: `db_pg_pyckg` (`35432`). Oracle XE local: `db_ora_pyckg` (`35521`). Volúmenes `db_postgis_vol-generic_python` y `oracle_xe_vol-generic_python` son externos (`docker_settings/create_volumes.cmd`).

## Tests y empaquetado
Tests `unittest` en `*_pckg/tests/test_*.py`. Varios pegan contra Postgres, Oracle o ficheros de `resources/data`; no des por hecho que son offline. Corre solo el módulo afectado con `docker compose run --rm python_packages python -m unittest ...`.

CI (`Jenkinsfile`) publica cada paquete en PyPI/TestPyPI con `build_pckg.sh` y construye la imagen con `Dockerfile.dev`. Rama y tag deciden el destino.

## Al cambiar código
- Un import entre paquetes tiene que seguir el orden del Dockerfile.
- `apb_cx_oracle_spatial` no funciona en la imagen `python_packages_deploy_no_oracle` (`ORACLE_AVAILABLE=0`).
- GDAL 3.10: notas en `gdal_310_migration/`.
- El contenedor `python_packages_doc` publica los README; un cambio de README sale en la doc del puerto `8095`.
