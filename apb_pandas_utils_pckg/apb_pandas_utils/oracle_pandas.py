#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: oracle_pandas.py
#   Created: 05/04/2020, 17:41
#   Last modified: 10/11/2019, 11:24
#   Copyright (c) 2020

import geopandas as gpd
import pandas as pd
from pandas.api.types import CategoricalDtype
from functools import wraps

try:
    from apb_cx_oracle_spatial.gestor_oracle import sql_tab
    _HAS_ORACLE_DEPS = True
except ImportError:
    _HAS_ORACLE_DEPS = False

from . import optimize_df


def requires_oracle_deps(func):
    """Decorator to check if Oracle dependencies are installed"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _HAS_ORACLE_DEPS:
            raise ImportError(
                "Oracle functionality requires additional dependencies. "
                "Install with 'pip install apb_pandas_utils[oracle]'"
            )
        return func(*args, **kwargs)
    return wrapper


@requires_oracle_deps
def df_for_sqlgen(a_ora_generator, columns_index=None, columns=None,
                  optimize=False,
                  **params_df):
    """
    A partir de generator de gestor_oracle devuelve pandas.Dataframe

    Args:
        a_ora_generator:
        columns_index:
        columns: lista con nombre de columnas a mostrar
        optimize: indica si se intentará optimizar el espacio ocupado por el Dataframe
        params_df: parametros creación Dataframe

    Returns:
        pandas.Dataframe
    """
    df = pd.DataFrame(a_ora_generator, **params_df)
    if not df.empty and columns_index:
        df.set_index([c.upper() for c in columns_index], inplace=True)

    if columns:
        df = df[[c.upper() for c in columns if c in df.columns]]

    if optimize:
        df = optimize_df(df)

    return df


@requires_oracle_deps
def gdf_for_sqlgen(a_ora_generator, column_geom, crs=None, **params_df_for_sqlgen):
    """
    A partir de generator de gestor_oracle devuelve geopandas.Dataframe

    Args:
        a_ora_generator:
        column_geom:
        crs (str=None): name EPSG crs
        **params_df_for_sqlgen: parametros opcionales funcion df_for_sqlgen()

    Returns:
        geopandas.Dataframe
    """
    column_geom = column_geom.upper()
    cols = params_df_for_sqlgen.pop('columns', [])
    if cols:
        params_df_for_sqlgen['columns'] = cols_sql(cols, [column_geom])

    gdf = gpd.GeoDataFrame(df_for_sqlgen(a_ora_generator,
                                         **params_df_for_sqlgen),
                           geometry=column_geom,
                           crs=crs)

    return gdf


@requires_oracle_deps
def cols_sql(cols, *l_cols_add):
    """
    Retorna lista de columnas

    Args:
        cols (list):
        *l_cols_add: listas de columnas a añadir

    Returns:
        list
    """
    if cols:
        cols = [c.upper() for c in cols]
        for added_cols in l_cols_add:
            cols += list(map(str.upper, added_cols))

        return list(set(cols))


@requires_oracle_deps
def df_table(gest_ora, nom_tab, filter_sql=None, *args_filter_sql, **params_df_for_sqlgen):
    """
    Devuelve pandas.DataFrame para una tablas de oracle

    Args:
        gest_ora:
        nom_tab:
        filter_sql:
        *args_filter_sql:
        **params_df_for_sqlgen: parametros opcionales funcion df_for_sqlgen()

    Returns:
        pandas.Dataframe
    """
    dd_tab = gest_ora.get_dd_table(nom_tab)
    cols = params_df_for_sqlgen.get("columns", []).copy()
    cols_idx = params_df_for_sqlgen.pop('columns_index', dd_tab.pk())

    df_tab = df_for_sqlgen(
        gest_ora.generator_rows_sql(sql_tab(nom_tab,
                                            filter_sql,
                                            cols_sql(cols,
                                                     cols_idx)),
                                    *args_filter_sql,
                                    geom_format="as_geojson"),
        columns_index=cols_idx,
        **params_df_for_sqlgen)

    if not cols:
        df_tab = df_tab[[c for c in dd_tab.cols if c in df_tab.columns]]

    return df_tab


@requires_oracle_deps
def gdf_table(gest_ora, nom_tab, column_geom, other_cols_geom=False, null_geoms=False,
              filter_sql=None, *args_filter_sql, **params_gdf_for_sqlgen):
    """
    Devuelve geopandas.GeoDataframe para una tablas de oracle

    Args:
        gest_ora:
        nom_tab:
        column_geom:
        other_cols_geom:
        null_geoms:
        filter_sql:
        *args_filter_sql:
        **params_gdf_for_sqlgen:

    Returns:
        geopandas.GeoDataframe
    """
    dd = gest_ora.get_dd_table(nom_tab)
    column_geom = column_geom.upper()
    cols = params_gdf_for_sqlgen.pop('columns', [])
    if not other_cols_geom:
        if not cols:
            cols = [c for c in dd.alfas(include_pk=False)]
        else:
            other_geoms = [g for g in dd.geoms().keys() if g != column_geom.upper()]
            cols = [c for c in cols
                    if c.upper() not in other_geoms]

    cols_idx = params_gdf_for_sqlgen.pop('columns_index', dd.pk())

    if not null_geoms:
        not_null_geoms_sql = "{} is not null".format(column_geom)
        if filter_sql:
            filter_sql = "{} and ({})".format(not_null_geoms_sql, filter_sql)
        else:
            filter_sql = not_null_geoms_sql

    crs_epsg = None
    if (tip_geom := gest_ora.get_tip_camp_geom(nom_tab, column_geom)) and \
            (epsg_code := gest_ora.get_epsg_for_srid(tip_geom.SRID)):
        crs_epsg = f'EPSG:{epsg_code}'

    gdf_tab = gdf_for_sqlgen(gest_ora.generator_rows_sql(sql_tab(nom_tab,
                                                                 filter_sql,
                                                                 cols_sql(cols,
                                                                          cols_idx,
                                                                          [column_geom])),
                                                         *args_filter_sql,
                                                         geom_format="as_shapely"),
                             column_geom=column_geom,
                             crs=crs_epsg,
                             columns_index=cols_idx,
                             columns=cols, **params_gdf_for_sqlgen)

    if not cols:
        gdf_tab = gdf_tab[[c for c in dd.cols if c in gdf_tab.columns]]

    return gdf_tab


@requires_oracle_deps
def dtype_categorical_from_tab_column(gest_ora, nom_tab, nom_col):
    """
    Retorna pandas.dtype de tipo categorico para la columna de una tabla

    Args:
        gest_ora:
        nom_tab:
        nom_col:

    Returns:
        pandas.CategoricalDtype
    """
    return CategoricalDtype(categories=gest_ora.iter_distinct_vals_camp_tab(nom_tab, nom_col))
