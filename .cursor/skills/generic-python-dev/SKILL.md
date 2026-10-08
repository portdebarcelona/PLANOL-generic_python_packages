---
name: generic-python-dev
description: >-
  Runs Python, unittest and package builds for PLANOL-generic_python_packages
  inside the Docker Compose dev interpreter. Use when executing python, tests,
  pip, GDAL, Oracle, PostGIS, DuckDB or geopandas code, or when the user
  mentions docker compose, Dockerfile.dev, the dev interpreter, or .env of DEV.
---

# Intérprete de desarrollo

El código se ejecuta con el servicio `python_packages` de `docker-compose.yml` (raíz). Imagen `Dockerfile.dev` (`planolport/python_gdal_oracle_geopandas:dev`), `CMD python`, workdir `/project`. El volumen `.:/project` monta el repo encima del editable install, así que el contenedor ve el código del host.

No uses el Python del host ni un venv local: no tienen el GDAL/Oracle de la imagen.

## Entorno DEV

El servicio carga, en este orden:

- `docker_settings/.env.private/.env.minio`
- `docker_settings/.env.private/.env.GISHISREP`
- `docker_settings/.env.private/.env`

Esos ficheros no se commitean. No los leas en voz alta ni copies valores a commits, logs o respuestas. En el host, `DATA_DIR_DEV` (defecto `C:/data`) se monta en `/project/data`. El README también pide `PATH_DEVELOPER_MODE_APB`, `PATH_BASE_PACKAGES` y `PATH_GISWEB_DADES`.

## Ejecutar

Desde la raíz del repo:

```bash
docker compose run --rm python_packages python -m unittest apb_duckdb_utils_pckg.tests.test_duckdb_utils
```

`python_packages` declara `depends_on` de `db_pg_pyckg` (PostGIS, puerto host `35432`) y `db_ora_pyckg` (Oracle XE, puerto host `35521`). Añade `--no-deps` solo si el módulo no toca esas bases. Los tests son `unittest` bajo `*_pckg/tests/test_*.py`; muchos leen `resources/data` o servicios reales. Empieza por el módulo tocado.

Paquetes, en el orden de editable install de `Dockerfile.dev`: `apb_extra_utils`, `apb_extra_osgeo_utils`, `apb_spatial_utils`, `apb_cx_oracle_spatial`, `apb_pandas_utils`, `apb_duckdb_utils`. Conserva ese orden si añades dependencias cruzadas. Empaquetado con `setup.py`. Publicar: servicio `build_python_packages` y `build_pckg.sh`.

## Otros servicios (no son el intérprete)

- `python_packages_deploy_oracle` / `python_packages_deploy_no_oracle`: imagen de `Dockerfile` (la segunda con `ORACLE_AVAILABLE=0`).
- `python_packages_mamba`: `Dockerfile.mamba`.
- `python_packages_doc`: docs en el puerto `8095`.
- `gdal_oracle`: imagen base `Dockerfile.base`.
