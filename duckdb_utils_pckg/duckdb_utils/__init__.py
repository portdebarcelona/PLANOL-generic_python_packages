#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 
#  Copyright (c)
"""
.. include:: ../README.md
"""

import duckdb

MEMORY_DDBB = ':memory:'
CACHE_DUCK_DDBBS = {}


def get_duckdb_connection(db_path: str = MEMORY_DDBB) -> duckdb.DuckDBPyConnection:
    """
    Get duckdb connection

    Args:
        db_path (str=MEMORY_DDBB): path to duckdb database file

    Returns:
         duckdb connection
    """
    k_path = db_path.lower()
    if not (conn_db := CACHE_DUCK_DDBBS.get(k_path)):
        conn_db = CACHE_DUCK_DDBBS[k_path] = duckdb.connect(db_path)

    return conn_db
