#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 
#  Copyright (c)
"""
.. include:: ../README.md
"""
from __future__ import annotations

import os
import warnings
from typing import Iterable

import duckdb
import ibis
from geopandas import GeoDataFrame
from ibis.expr.datatypes import GeoSpatial
from pandas import DataFrame

from apb_extra_utils.misc import create_dir
from apb_extra_utils.utils_logging import get_base_logger
from apb_pandas_utils.geopandas_utils import df_geometry_columns

# Suppress specific warning
warnings.filterwarnings("ignore", message="Geometry column does not contain geometry")

MEMORY_DDBB = ':memory:'
CACHE_DUCK_DDBBS = {}
CURRENT_DB_PATH = None
GZIP = 'gzip'
SECRET_S3 = 'secret_s3'


def set_current_db_path(db_path: str):
    """
    Set used db path

    Args:
        db_path (str): path to duckdb database file
    """
    global CURRENT_DB_PATH
    CURRENT_DB_PATH = parse_path(db_path)


def get_duckdb_connection(db_path: str = None, as_current: bool = False, no_cached: bool = False,
                          extensions: list[str] = None,
                          **connect_args) -> duckdb.DuckDBPyConnection:
    """
    Get duckdb connection

    Args:
        db_path (str=None): path to duckdb database file. By default, use CURRENT_DB_PATH
        as_current (bool=False): set db_path as current db path
        no_cached (bool=False): not use cached connection
        extensions (list[str]=None): list of extensions to load
        **connect_args (dict): duckdb.connect args 

    Returns:
         duckdb connection
    """
    if not db_path:
        if CURRENT_DB_PATH and not no_cached:
            db_path = CURRENT_DB_PATH
        else:
            db_path = MEMORY_DDBB

    parsed_path = parse_path(db_path)
    k_path = parsed_path.lower()
    if no_cached or not (conn_db := CACHE_DUCK_DDBBS.get(k_path)):
        conn_db = CACHE_DUCK_DDBBS[k_path] = duckdb.connect(parsed_path, **connect_args)

    if extensions:
        for ext in extensions:
            conn_db.install_extension(ext)
            conn_db.load_extension(ext)

    if as_current:
        set_current_db_path(parsed_path)

    return conn_db


def export_database(dir_db: str, duck_db_conn: duckdb.DuckDBPyConnection = None, parquet: bool = True):
    """
    Save duckdb database to dir path as parquets or csvs files

    Args:
        dir_db (str=None): Path to save database
        duck_db_conn (duckdb.DuckDBPyConnection=None): Duckdb database connection.
            If None, get connection default with get_duckdb_connection
        parquet (bool=True): Save as parquet file
    """
    create_dir(dir_db)

    if not duck_db_conn:
        duck_db_conn = get_duckdb_connection()

    if parquet:
        format_db = "(FORMAT PARQUET)"
    else:
        format_db = "(FORMAT CSV, COMPRESSION 'GZIP')"

    duck_db_conn.sql(f"EXPORT DATABASE '{parse_path(dir_db)}' {format_db}")


def current_schema_duckdb(conn_db: duckdb.DuckDBPyConnection = None) -> str:
    """
    Get current schema

    Args:
        conn_db (duckdb.DuckDBPyConnection=None): connection to duckdb

    Returns:
        current schema
    """
    if not conn_db:
        conn_db = get_duckdb_connection()

    return conn_db.sql("SELECT current_schema()").fetchone()[0]


def list_tables_duckdb(conn_db: duckdb.DuckDBPyConnection = None, schemas: tuple[str] = None) -> list[str]:
    """
    List tables in duckdb

    Args:
        conn_db (duckdb.DuckDBPyConnection=None): connection to duckdb
        schemas (tuple[str]=None): tuple schemas. If not informed, list all tables

    Returns:
        list of tables
    """
    if not conn_db:
        conn_db = get_duckdb_connection()

    current_schema = current_schema_duckdb(conn_db)

    def get_table_name(row):
        """
        Get table name with schema if not current schema

        Args:
            row:

        Returns:
            str
        """
        schema = quote_name_duckdb(row['schema'])
        table = quote_name_duckdb(row['name'])
        return f"{schema}.{table}" if schema != current_schema else table

    sql_tables = conn_db.sql(f"SHOW ALL TABLES")
    if schemas:
        sql_tables = sql_tables.filter(f"schema in {schemas}")

    tables = []
    if sql_tables.count('name').fetchone()[0] > 0:
        tables = sql_tables.df().apply(get_table_name, axis=1).tolist()

    return tables


def quote_name_duckdb(object_sql_name: str) -> str:
    """
    Quote name to use on duckdb if has spaces

    Args:
        object_sql_name (str): name to quote (table, view, schema, index, ...)

    Returns:
        quoted name (str)
    """
    object_sql_name = object_sql_name.strip().replace('"', '')

    res_name = ''
    if '.' in object_sql_name:
        schema, name_obj = object_sql_name.split('.')
        res_name = f'"{schema}".' if " " in schema else f'{schema}.'
    else:
        name_obj = object_sql_name

    name_obj = f'"{name_obj}"' if ' ' in name_obj else name_obj

    res_name += name_obj

    return res_name


def exists_table_duckdb(table_name: str, conn_db: duckdb.DuckDBPyConnection = None) -> bool:
    """
    Check if table exists in duckdb

    Args:
        table_name (str): table name
        conn_db (duckdb.DuckDBPyConnection=None): connection to duckdb

    Returns:
        bool: True if table exists
    """
    if not conn_db:
        conn_db = get_duckdb_connection()

    return quote_name_duckdb(table_name) in list_tables_duckdb(conn_db)


def parse_path(path):
    """
    Parse path to duckdb format
    Args:
        path (str): path to use on duckdb

    Returns:
        normalized path (str)
    """
    if path.startswith('s3://'):
        normalize_path = path
    else:
        normalize_path = os.path.normpath(path).replace('\\', '/')

    return normalize_path


def escape_name_table_view(name: str):
    """
    Escape characters and lowercase name table/view to use on duckdb
    Args:
        name (str): name to use on duckdb

    Returns:
        normalized name (str)
    """
    return name.replace(
        '-', '_').replace(
        '(', '').replace(
        ')', '').lower()


def check_columns_in_sql(cols_to_check: Iterable[str], sql: duckdb.DuckDBPyRelation):
    """
    Check columns in sql relation

    Args:
        cols_to_check (Iterable[str]): list of columns to check
        sql (duckdb.DuckDBPyRelation): sql relation

    Returns:
        list[str]: list of columns to check
    """
    cols_to_check_lower = [cols_geom.lower() for cols_geom in cols_to_check]
    cols_sql = [col.lower() for col in sql.columns]

    if not all(col in cols_sql for col in cols_to_check_lower):
        raise ValueError(f"There are columns {cols_to_check} not found on sql columns {cols_sql}")

    return cols_to_check


def set_types_geom_to_cols_wkt_on_sql(cols_wkt: list[str], sql: duckdb.DuckDBPyRelation):
    """
    Set columns to GEOMETRY from WKT text

    Args:
        cols_wkt (list[str]): list of columns WKT to set as geometry
        sql (duckdb.DuckDBPyRelation): sql relation

    Returns:
        duckdb.DuckDBPyRelation: Duckdb database relation
    """
    check_columns_in_sql(cols_wkt, sql)

    cols_wkt_lower = [col.lower() for col in cols_wkt]
    sql_wkt_cols = {
        col: f'ST_GeomFromText("{col}")'
        for col in sql.columns if col.lower() in cols_wkt_lower
    }
    return replace_cols_on_sql(sql_wkt_cols, sql)


def replace_cols_on_sql(replace_cols: dict[str, str], sql: duckdb.DuckDBPyRelation):
    """
    Replace columns by the passed sql function

    Args:
        replace_cols (dict[str]): dict of columns with the sql function to use instead
        sql (duckdb.DuckDBPyRelation): sql relation

    Returns:
        duckdb.DuckDBPyRelation: Duckdb database relation
    """
    check_columns_in_sql(replace_cols.keys(), sql)

    sql_replace = ", ".join(
        f'{sql_func} AS "{col}"'
        for col, sql_func in replace_cols.items()
    )
    return sql.select(f"* REPLACE ({sql_replace})")


def rename_cols_on_sql(alias_cols: dict[str, str], sql: duckdb.DuckDBPyRelation):
    """
    Rename columns in sql select

    Args:
        alias_cols (dict[str]): dict of renamed columns with alias
        sql (duckdb.DuckDBPyRelation): sql relation

    Returns:
        duckdb.DuckDBPyRelation: Duckdb database relation
    """
    check_columns_in_sql(alias_cols.keys(), sql)
    alias_cols = {col.lower(): alias for col, alias in alias_cols.items()}

    sql_cols = ", ".join(
        f'"{col}" AS "{alias_col}"' if (alias_col := alias_cols.get(col.lower())) else f'"{col}"'
        for col in sql.columns
    )

    return sql.select(f"{sql_cols}")


def exclude_cols_on_sql(excluded_cols: list[str], sql: duckdb.DuckDBPyRelation):
    """
    Exclude columns in sql select

    Args:
        excluded_cols (list[str]): list of columns to exclude
        sql (duckdb.DuckDBPyRelation): sql relation

    Returns:
        duckdb.DuckDBPyRelation: Duckdb database relation
    """
    check_columns_in_sql(excluded_cols, sql)

    str_cols = ", ".join(f'"{col}"' for col in excluded_cols)
    sql_cols = f'* EXCLUDE ({str_cols})'

    return sql.select(f"{sql_cols}")


def config_sql_duckdb(a_sql: duckdb.DuckDBPyRelation, cols_wkt: list[str] = None, cols_exclude: list[str] = None,
                      cols_alias: dict[str, str] = None, cols_replace: dict[str, str] = None,
                      table_or_view_name: str = None, col_id: str = None, as_view: bool = False,
                      overwrite: bool = False, conn_db=None) -> duckdb.DuckDBPyRelation:
    """
    Set new config to a Duckdb SQL Relation

    Args:
        a_sql (duckdb.DuckDBPyRelation): Duckdb database relation
        cols_wkt (list[str] | dict=None): list of columns WKT to use as geometry
        cols_exclude (list[str]=None): list of columns to exclude
        cols_alias (dict[str, str]=None): dictionary of columns aliases
        cols_replace (dict[str, str]=None): dictionary of columns to replace
        table_or_view_name (str=None): table or view name. If informed, create table or view
        col_id (str=None): column primary key and index unique if create table
        as_view (bool=False): create sql as view instead of table
        overwrite (bool=False): overwrite table_name if exists
        conn_db (duckdb.DuckDBPyConnection=None): connection to duckdb if create table or view

    Returns:
        a_sql (duckdb.DuckDBPyRelation): Duckdb database relation
    """
    if cols_exclude:
        a_sql = exclude_cols_on_sql(cols_exclude, a_sql)

    if cols_alias:
        a_sql = rename_cols_on_sql(cols_alias, a_sql)

    if cols_replace:
        a_sql = replace_cols_on_sql(cols_replace, a_sql)

    if cols_wkt:
        a_sql = set_types_geom_to_cols_wkt_on_sql(cols_wkt, a_sql)

    if table_or_view_name:
        if not conn_db:
            conn_db = get_duckdb_connection(extensions=['spatial', 'parquet'], no_cached=True)

        table_or_view_name = quote_name_duckdb(table_or_view_name)
        if as_view:
            a_sql.create_view(table_or_view_name, replace=overwrite)
        else:
            if overwrite:
                conn_db.execute(f"DROP TABLE IF EXISTS {table_or_view_name}")

            if col_id := (cols_alias or {}).get(col_id, col_id):
                a_sql = a_sql.order(f'"{col_id}"')

            a_sql.create(table_or_view_name)

            if col_id:
                n_idx = quote_name_duckdb(f"{table_or_view_name}_{col_id}_idx")
                conn_db.execute(
                    f'CREATE UNIQUE INDEX {n_idx} ON {table_or_view_name} ("{col_id}")'
                )

        a_sql = conn_db.sql(f"FROM {table_or_view_name}")

    return a_sql


def import_csv_to_duckdb(csv_path: str, table_or_view_name: str = None, header: bool = True, col_id: str = None,
                         cols_wkt: list[str] | dict = None, cols_exclude: list[str] = None,
                         cols_alias: dict[str, str] = None, cols_replace: dict[str, str] = None, as_view: bool = False,
                         conn_db: duckdb.DuckDBPyConnection = None, overwrite=False, zipped: bool = False) -> duckdb.DuckDBPyRelation:
    """
    Import csv file as table on duckdb

    Args:
        csv_path (str): path to csv file
        table_or_view_name (str=None): table or view name. If informed, create table or view
        header (bool=True): csv file has header
        col_id (str=None): column primary key and index unique if create table
        cols_wkt (list[str] = None): list of columns WKT to use as geometry
        cols_exclude (list[str]=None): list of columns to exclude
        cols_alias (dict[str, str]=None): dictionary of columns aliases
        cols_replace (dict[str, str]=None): dictionary of columns to replace
        conn_db (duckdb.DuckDBPyConnection = None): connection to duckdb
        as_view (bool=False): create table as view instead of table
        overwrite (bool=False): overwrite table_name if exists
        zipped (bool=False): compression type. If informed, use it

    Returns:
         a_sql (duckdb.DuckDBPyRelation): Duckdb database relation
    """
    if not conn_db:
        conn_db = get_duckdb_connection(extensions=['spatial'], no_cached=True)

    compression = f', compression={GZIP}' if zipped else ''

    a_sql = conn_db.sql(
        f"""
        FROM read_csv('{parse_path(csv_path)}', header={header}, auto_detect=True{compression})
        """
    )

    a_sql = config_sql_duckdb(a_sql, cols_wkt=cols_wkt, cols_exclude=cols_exclude, cols_alias=cols_alias,
                              cols_replace=cols_replace, table_or_view_name=table_or_view_name, col_id=col_id,
                              as_view=as_view, overwrite=overwrite, conn_db=conn_db)

    return a_sql


def import_gdal_file_to_duckdb(
        path_file: str,
        table_or_view_name: str = None,
        gdal_open_options: list[str] = None,
        col_id: str = None,
        cols_exclude: list[str] = None,
        cols_alias: dict[str, str] = None,
        cols_replace: dict[str, str] = None,
        conn_db: duckdb.DuckDBPyConnection = None,
        as_view: bool = False,
        overwrite: bool = False,
        **st_read_kwargs) -> duckdb.DuckDBPyRelation:
    """
    Load GDAL file driver on duckdb database

    Args:
        path_file (str): path to GDAL file
        table_or_view_name (str=None): table or view name. If informed, create table or view
        gdal_open_options (list[str]=None): list of GDAL open options.
                    See GDAL documentation (https://gdal.org/drivers/vector/index.html)
                    (e.g.['HEADERS=TRUE', 'X_POSSIBLE_NAMES=Longitude', 'Y_POSSIBLE_NAMES=Latitude'])
        col_id (str=None): column primary key and index unique if create table
        cols_exclude (list[str]=None): list of columns to exclude
        cols_alias (dict[str, str]=None): dictionary of columns aliases
        cols_replace (dict[str, str]=None): dictionary of columns to replace
        conn_db (duckdb.DuckDBPyConnection=None): Duckdb database connection
        as_view (bool=False): create sql as view instead of table
        overwrite (bool=False): overwrite table_name if exists
        **st_read_kwargs (str): ST_Read function kwargs. See ST_Read documentation
            (https://duckdb.org/docs/extensions/spatial/functions.html#st_read)

    Returns:
        a_sql (duckdb.DuckDBPyRelation): Duckdb database relation
    """
    params_st_read = f"'{parse_path(path_file)}'"
    if gdal_open_options:
        params_st_read = f"{params_st_read}, open_options={gdal_open_options}"
    if st_read_kwargs:
        params_st_read = f"{params_st_read}, {', '.join([f'{k}={v}' for k, v in st_read_kwargs.items()])}"

    query = f"""
        FROM ST_Read({params_st_read})
        """

    if not conn_db:
        conn_db = get_duckdb_connection(extensions=['spatial', 'parquet'], no_cached=True)

    a_sql = conn_db.sql(query)

    a_sql = config_sql_duckdb(a_sql, cols_exclude=cols_exclude, cols_alias=cols_alias, cols_replace=cols_replace,
                              table_or_view_name=table_or_view_name, col_id=col_id, as_view=as_view,
                              overwrite=overwrite, conn_db=conn_db)

    return a_sql


def import_dataframe_to_duckdb(df: DataFrame | GeoDataFrame, table_or_view_name: str = None, col_id: str = None,
                               cols_wkt: list[str] | dict = None, cols_exclude: list[str] = None,
                               cols_alias: dict[str, str] = None, cols_replace: dict[str, str] = None,
                               as_view: bool = False, conn_db: duckdb.DuckDBPyConnection = None,
                               overwrite=False) -> duckdb.DuckDBPyRelation:
    """
    Import DataFrame/GeoDataframe as table on duckdb

    Args:
        df (DataFrame | GeoDataFrame): A DataFrame/GeoDataFrame
        table_or_view_name (str=None): table or view name. If informed, create table or view
        col_id (str=None): column primary key and index unique if create table
        cols_wkt (list[str] = None): list of columns WKT to use as geometry
        cols_exclude (list[str]=None): list of columns to exclude
        cols_alias (dict[str, str]=None): dictionary of columns aliases
        cols_replace (dict[str, str]=None): dictionary of columns to replace
        conn_db (duckdb.DuckDBPyConnection = None): connection to duckdb
        as_view (bool=False): create table as view instead of table
        overwrite (bool=False): overwrite table_name if exists

    Returns:
         a_sql (duckdb.DuckDBPyRelation): Duckdb database relation
    """
    if not conn_db:
        conn_db = get_duckdb_connection(extensions=['spatial'], no_cached=True)

    for col in (cols_geom := df_geometry_columns(df)):
        df[col] = df[col].to_wkb(include_srid=True)

    cols_as_wkb = [f'ST_GeomFromWKB({col}) AS {col}' for col in cols_geom]
    alias_cols_geom = ', '.join(cols_as_wkb)
    exclude_geom_cols = ', '.join(cols_geom)

    select_expr = f"SELECT * EXCLUDE({exclude_geom_cols}), {alias_cols_geom}" if cols_geom else "SELECT *"
    a_sql = conn_db.sql(f"""
        {select_expr} FROM df
        """)

    a_sql = config_sql_duckdb(a_sql, cols_wkt=cols_wkt, cols_exclude=cols_exclude, cols_alias=cols_alias,
                              cols_replace=cols_replace, table_or_view_name=table_or_view_name, col_id=col_id,
                              as_view=as_view, overwrite=overwrite, conn_db=conn_db)

    return a_sql


def import_parquet_to_duckdb(parquet_path: str, table_or_view_name: str = None, col_id: str = None,
                             cols_geom: list[str] = None,
                             cols_wkt: list[str] | dict = None, cols_exclude: list[str] = None,
                             cols_alias: dict[str, str] = None, cols_replace: dict[str, str] = None,
                             as_view: bool = False, conn_db: duckdb.DuckDBPyConnection = None, overwrite=False,
                             **read_parquet_params) -> duckdb.DuckDBPyRelation:
    """
    Import Parquet/Geoparquet file as table on duckdb

    Args:
        parquet_path (str): path to parquet/geoparquet file
        table_or_view_name (str=None): table or view name. If informed, create table or view
        col_id (str=None): column primary key and index unique if create table
        cols_geom (list[str]=None): list of columns type geometry
        cols_wkt (list[str] = None): list of columns WKT to use as geometry
        cols_exclude (list[str]=None): list of columns to exclude
        cols_alias (dict[str, str]=None): dictionary of columns aliases
        cols_replace (dict[str, str]=None): dictionary of columns to replace
        conn_db (duckdb.DuckDBPyConnection = None): connection to duckdb
        as_view (bool=False): create table as view instead of table
        overwrite (bool=False): overwrite table_name if exists
        **read_parquet_params (Any): read_parquet function kwargs.
                See duckdb read_parquet documentation on https://duckdb.org/docs/data/parquet/overview.html#parameters

    Returns:
         a_sql (duckdb.DuckDBPyRelation): Duckdb database relation
    """
    if not conn_db:
        conn_db = get_duckdb_connection(extensions=['spatial'], no_cached=True)

    select_expr = 'SELECT *'
    if cols_geom:
        alias_cols_geom = ', '.join(f'{col}::GEOMETRY AS {col}' for col in cols_geom)
        exclude_geom_cols = ', '.join(cols_geom)
        select_expr = f"SELECT * EXCLUDE({exclude_geom_cols}), {alias_cols_geom}"

    sql_read_parquet_params = ''
    if read_parquet_params:
        sql_read_parquet_params += ', '
        sql_read_parquet_params += ', '.join([f'{k}={v}' for k, v in read_parquet_params.items()])

    a_sql = conn_db.sql(
        f"""
        {select_expr}
        FROM read_parquet('{parse_path(parquet_path)}'{sql_read_parquet_params})
        """
    )

    a_sql = config_sql_duckdb(a_sql, cols_wkt=cols_wkt, cols_exclude=cols_exclude, cols_alias=cols_alias,
                              cols_replace=cols_replace, table_or_view_name=table_or_view_name, col_id=col_id,
                              as_view=as_view, overwrite=overwrite, conn_db=conn_db)

    return a_sql


def filter_ibis_table(table: ibis.Table, sql_or_ibis_filter: str | ibis.expr) -> ibis.Table:
    """
    Filter ibis table

    Args:
        table (ibis.Table): The table to filter
        sql_or_ibis_filter (str | ibis.expr): The filter to apply to the table

    Returns:
        table (ibis.Table): The table filtered
    """
    if isinstance(sql_or_ibis_filter, str):  # Filter by SQL on duckdb backend
        # Check if geospatial fields to cast as geometry
        cols_geom = [col for col, fld in table.schema().fields.items()
                     if isinstance(fld, GeoSpatial)]
        if cols_geom:
            cast_geom_cols = ', '.join([f"CAST({col} AS geometry) AS {col}" for col in cols_geom])
            sql_select_cols = f"* EXCLUDE({', '.join(cols_geom)}), {cast_geom_cols}"
        else:
            sql_select_cols = "*"

        n_tab = table.get_name()
        sql_str = f"SELECT {sql_select_cols} FROM {n_tab} WHERE {sql_or_ibis_filter}"
        get_base_logger().debug(f"filter_ibis_table {n_tab}: {sql_str}")
        res = table.sql(sql_str)
    else:
        res = table.filter(sql_or_ibis_filter)

    return res


def set_secret_s3_storage(duckdb_conn: duckdb.DuckDBPyConnection, endpoint: str, access_key_id: str,
                          secret_access_key: str, url_style: str = 'path', use_ssl: bool = False, region: str = None,
                          secret_name: str = SECRET_S3) -> bool:
    """
    Set secret S3 storage on duckdb connection

    Args:
        duckdb_conn (duckdb.DuckDBPyConnection): duckdb connection
        endpoint (str): endpoint url. (e.g. 's3.amazonaws.com')
        access_key_id (str): access key id
        secret_access_key (str): secret access key
        url_style (str='path'): url style. 'path' or 'virtual_hosted'
        use_ssl (bool=False): use ssl
        region (str=None): region name
        secret_name (str=SECRET_S3): secret name

    Returns:
        ok
    """
    ok = False
    try:
        duckdb_conn.execute(f"""
        CREATE OR REPLACE SECRET {secret_name} (
            TYPE S3,
            KEY_ID '{access_key_id}',
            SECRET '{secret_access_key}',
            ENDPOINT '{endpoint}',
            URL_STYLE '{url_style}',
            USE_SSL {use_ssl},
            REGION '{region}'
        );
        """)
        ok = True
    except Exception as e:
        get_base_logger().error(f"Error setting S3 access keys: {e}")

    return ok


def exists_secret(duckdb_conn: duckdb.DuckDBPyConnection, secret_name: str = SECRET_S3) -> bool:
    """
    Check if secret exists on duckdb connection

    Args:
        duckdb_conn (duckdb.DuckDBPyConnection): duckdb connection
        secret_name (str=SECRET_S3): secret name

    Returns:
        bool: True if secret exists
    """
    exists = False
    try:
        exists = duckdb_conn.execute(
            f"SELECT COUNT(*) > 0 AS existe FROM duckdb_secrets() WHERE name = '{secret_name}'").fetchone()[0]
    except Exception as e:
        get_base_logger().error(f"Error checking secret existence: {e}")

    return exists
