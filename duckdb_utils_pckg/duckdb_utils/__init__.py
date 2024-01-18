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
from typing import List

import duckdb

MEMORY_DDBB = ':memory:'
CACHE_DUCK_DDBBS = {}
CURRENT_DB_PATH = None


def set_current_db_path(db_path: str):
    """
    Set used db path

    Args:
        db_path (str): path to duckdb database file
    """
    global CURRENT_DB_PATH
    CURRENT_DB_PATH = parse_path(db_path)


def get_duckdb_connection(db_path: str = None, as_current: bool = False, no_cached: bool = False, extensions: List[str] = None,
                          **connect_args) -> duckdb.DuckDBPyConnection:
    """
    Get duckdb connection

    Args:
        db_path (str=None): path to duckdb database file. By default, use CURRENT_DB_PATH
        as_current (bool=False): set db_path as current db path
        no_cached (bool=False): not use cached connection
        extensions (List[str]=None): list of extensions to load
        **connect_args (dict): duckdb.connect args 

    Returns:
         duckdb connection
    """
    if not db_path:
        db_path = CURRENT_DB_PATH or MEMORY_DDBB

    parsed_path = parse_path(db_path)
    k_path = parsed_path.lower()
    if no_cached or not (conn_db := CACHE_DUCK_DDBBS.get(k_path)):
        conn_db = CACHE_DUCK_DDBBS[k_path] = duckdb.connect(parsed_path, **connect_args)

    if extensions:
        for ext in extensions:
            conn_db.load_extension(ext)

    if as_current:
        set_current_db_path(parsed_path)

    return conn_db


def list_tables_duckdb(all_schemas: bool = False, conn_db: duckdb.DuckDBPyConnection = None) -> List[str]:
    """
    List tables in duckdb

    Args:
        all_schemas (bool=False): list tables from all schemas
        conn_db (duckdb.DuckDBPyConnection=None): connection to duckdb

    Returns:
        list of tables
    """
    if not conn_db:
        conn_db = get_duckdb_connection()

    all_opt = ''
    if all_schemas:
        all_opt = 'ALL'

    return conn_db.sql(f"SHOW {all_opt} TABLES").df()['name'].tolist()


def parse_path(path):
    """
    Parse path to duckdb format
    Args:
        path (str): path to use on duckdb

    Returns:
        normalized path (str)
    """
    normalize_path = os.path.normpath(path).replace('\\', '/')
    return normalize_path


def import_csv_to_duckdb(csv_path: str, table_name: str = None, cols_geom: List[str] | dict = None,
                         conn_db: duckdb.DuckDBPyConnection = None, overwrite=False) -> duckdb.DuckDBPyRelation:
    """
    Import csv file to duckdb

    Args:
        csv_path (str): path to csv file
        table_name (str=None): table name. Default: csv file name without extension
        cols_geom (List[str] | dict=None): list of columns to use as geometry
        conn_db (duckdb.DuckDBPyConnection = None): connection to duckdb
        overwrite (bool=False): overwrite table_name if exists

    Returns:
         duckdb relation for table_name created
    """
    if not conn_db:
        conn_db = get_duckdb_connection()

    if not table_name:
        table_name = os.path.splitext(os.path.basename(csv_path))[0]

    sql_cols = '*'
    if cols_geom:
        conn_db.load_extension('spatial')
        geom_cols = ", ".join(
            (f"ST_GeomFromText({col}) AS {col}" for col in cols_geom)
        )
        exclude_cols = ", ".join(cols_geom)
        sql_cols = f'* EXCLUDE ({exclude_cols}), {geom_cols}'

    if overwrite:
        conn_db.execute(f"DROP TABLE IF EXISTS {table_name}")

    conn_db.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS 
        SELECT {sql_cols} FROM read_csv_auto('{csv_path}')
        """)
    conn_db.sql(f"DESCRIBE {table_name}")

    return conn_db.sql(f"SELECT * FROM {table_name}")
