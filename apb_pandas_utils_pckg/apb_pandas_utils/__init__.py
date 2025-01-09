#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 
#  Copyright (c)
"""
.. include:: ../README.md
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, time, date
from typing import Union

import numpy as np
import pandas as pd
from geopandas import GeoDataFrame
from pandas import DataFrame, Timestamp, NaT, CategoricalDtype

EXCLUDED_TYPES_TO_CATEGORIZE = ['datetime', 'category', 'geometry']
DEFAULT_MAX_UNIQUE_VALS_COL_CATEGORY = 0.5
MAX_DATETIME = datetime(2250, 12, 31, 23, 59, 59)


def optimize_df(df: DataFrame | GeoDataFrame, max_perc_unique_vals: float = DEFAULT_MAX_UNIQUE_VALS_COL_CATEGORY,
                floats_as_categ: bool = False) -> DataFrame | GeoDataFrame:
    """
    Retorna el pd.Dataframe optimizado segun columnas que encuentre

    Args:
        df (Dataframe | GeoDataFrame): Dataframe a optimizar
        max_perc_unique_vals (float=DEFAULT_MAX_UNIQUE_VALS_COL_CATEGORY): Màxim percentatge de valors únics respecte total files per a convertir en categoria, expressat entre 0 i 1 (Default 0.5 -> 50%)
        floats_as_categ (bool=False): Si True, els floats es converteixen a categoria

    Returns:
        opt_df (Dataframe | GeoDataFrame): Dataframe optimizado
    """
    opt_df = df.copy()
    df_ints = opt_df.select_dtypes(include=['int64'])
    opt_df[df_ints.columns] = df_ints.apply(pd.to_numeric, downcast='signed')
    df_floats = opt_df.select_dtypes(include='float')
    opt_df[df_floats.columns] = df_floats.apply(pd.to_numeric, downcast='float')

    excl_types_cat = EXCLUDED_TYPES_TO_CATEGORIZE
    if not floats_as_categ:
        excl_types_cat.append('float')

    for col in opt_df.select_dtypes(exclude=excl_types_cat).columns:
        try:
            unic_vals = opt_df[col].unique()
        except (pd.errors.DataError, TypeError):
            continue

        num_unique_values = len(unic_vals)
        num_total_values = len(opt_df[col]) - len(opt_df.loc[opt_df[col].isnull()])
        if num_total_values > 0 and (num_unique_values / num_total_values) < max_perc_unique_vals:
            try:
                opt_df[col] = opt_df[col].astype(CategoricalDtype(ordered=True))
            except (NotImplementedError, TypeError):
                continue

    return opt_df


def df_filtered_by_prop(df: DataFrame | GeoDataFrame, filter_prop: dict[str, object]) -> DataFrame | GeoDataFrame | None:
    """
    Filtra el dataframe amb el diccionari passat, on la clau fa referència a la columna i el valor o llistat de valors
    separats per comes son els que s’apliquen al filtre. Si la clau/columna no existeix es desestima. Si la clau/columna
    comença per alguns d’aquest signes “=, !, -, >, <” s’aplica la corresponent operació de filtre.
    En el cas de “!” i “–“ s’aplica la mateixa operació de negat o que no contingui el valor o valors passats.
    Els filtres “<“ i “>” no apliquen a camps text i es desestimen. Es poden passar la mateixa columna amb operadors
    i valors distints per aplicar filtres diferents

    Args:
        df (DataFrame | GeoDataFrame): DataFrame a filtrar
        filter_prop (dict[str, object]): Propietats de filtrat

    Returns:
        DataFrame | GeoDataFrame: DataFrame filtrat
    """
    if df is None or not filter_prop:
        return df

    idx_names = [idx_col for idx_col in df.index.names if idx_col]
    if idx_names:
        df = df.reset_index()

    def _df_individual_filter(_df_ind: DataFrame, type_col_ind, column: str, value, col_operator: str = '='):
        type_column = type_col_ind.categories.dtype if (type_col_name := type_col_ind.name) == 'category' else type_col_ind

        if type_col_name == 'object':
            if col_operator == '=':
                _df_ind = _df_ind[_df_ind[column].str.contains(str(value), case=False, na=False)]
            elif col_operator == '-' or col_operator == '!':
                _df_ind = _df_ind[~_df_ind[column].str.contains(str(value), case=False, na=False)]
        else:
            value = type_column.type(value)
            if col_operator == '=':
                _df_ind = _df_ind.loc[_df_ind[column] == value]
            elif col_operator == '-' or col_operator == '!':
                _df_ind = _df_ind.loc[_df_ind[column] != value]
            elif col_operator == '>':
                _df_ind = _df_ind.loc[_df_ind[column] > value]
            elif col_operator == '<':
                _df_ind = _df_ind.loc[_df_ind[column] < value]

        return _df_ind

    col_names = df.columns.values.tolist()
    for k, v in filter_prop.items():
        k_operator = "="
        if k.startswith(('-', '=', '<', '>', '!')):
            k_operator = k[0:1]
            k = k[1:]
        if k.upper() in (col_names + idx_names):
            k = k.upper()
        elif k.lower() in (col_names + idx_names):
            k = k.lower()

        if k in col_names and v is not None:
            type_col = df.dtypes.get(k)
            if isinstance(v, list):
                # es fa amb un bucle i no amb isin perque no val per floats
                df_list = None
                for ind_val in v:
                    df_temp = _df_individual_filter(df, type_col, k, ind_val, k_operator)
                    if df_list is None:
                        df_list = df_temp
                    elif k_operator == '=':
                        df_list = pd.concat([df_list, df_temp])
                    if k_operator != '=':
                        # per als operadors que exclouen s'ha de treballar sobre el df filtrat resultant
                        df = df_list = df_temp
                df = df_list
            else:
                df = _df_individual_filter(df, type_col, k, v, k_operator)

    if idx_names:
        df.set_index(idx_names, inplace=True)

    return df


def rename_and_drop_columns(df: Union[DataFrame, GeoDataFrame], map_old_new_col_names: dict[str, str],
                            drop_col: bool = True, strict: bool = False, reordered: bool = False) -> Union[
    DataFrame, GeoDataFrame]:
    """
    Function to rename and remove columns from a dataframe. If the drop_col parameter is True,
    the columns that are not in the map will be removed. If the strict parameter is True,
    the names that do not exist in the map as a column will be skipped.
    Args:
        df: to remove and rename
        map_old_new_col_names: the key is the actual name and the value is the new name
        drop_col: True to remove columns that are not included in the map
        strict: False to skip names that are not included in the map
        reordered: True to reorder columns of dataframe

    Returns: modified DataFrame

    """
    if df is not None and map_old_new_col_names:
        col_names = df.columns.values.tolist()
        col_names_to_drop = col_names.copy()
        final_map = {}
        for k, v in map_old_new_col_names.items():
            if k in col_names:
                final_map[k] = v
                col_names_to_drop.remove(k)
        if drop_col:
            df = df.drop(col_names_to_drop, axis=1)
        if strict:
            final_map = map_old_new_col_names
        df = df.rename(columns=final_map)
        if reordered:
            new_cols = list(map_old_new_col_names.values())
            act_cols = df.columns.tolist()
            reord_cols = [value for value in new_cols if value in act_cols]
            df = df[reord_cols]
        return df


def set_null_and_default_values(df: DataFrame | GeoDataFrame) -> DataFrame | GeoDataFrame:
    """
    Function to replace NaN values with None in a DataFrame
    Args:
        df (DataFrame | GeoDataFrame): DataFrame to replace NaN values with None

    Returns:
        DataFrame | GeoDataFrame: DataFrame with NaN values replaced with None
    """
    df = df.replace({np.nan: None})
    return df


def replace_values_with_null(df: Union[DataFrame | GeoDataFrame], dict_col_values: dict) -> Union[
    DataFrame | GeoDataFrame]:
    """
    Function to replace values with None in a DataFrame
    Args:
        df (DataFrame | GeoDataFrame): DataFrame to replace values with None
        dict_col_values (dict): Dictionary with the column name and the value to replace with None

    Returns:
        DataFrame | GeoDataFrame: DataFrame with values replaced with None
    """
    if df is not None and not df.empty and dict_col_values:
        for name_col, value in dict_col_values.items():
            df[name_col] = df[name_col].replace(value, None)
    return df


def convert_to_datetime_col_df(df: DataFrame, cols: list[str],
                               set_end_day: bool = False, set_nat: bool = False) -> DataFrame:
    """
    Force convert date columns to datetime format.
    If init_date is True, the time is set to 00:00:00 if not to 23:59:59

    Args:
        df (DataFrame): DataFrame
        cols (list[str]): Columns to convert
        set_end_day (bool=False): If False the time is set to 00:00:00 if not to 23:59:59
        set_nat (bool=False): If True set NaT to MAX_DATETIME

    Returns:
        DataFrame: DataFrame with datetime columns
    """
    if not set_end_day:
        delta_time = time.min
    else:
        delta_time = time(23, 59, 59)

    def _convert_date(value):
        if type(value) is date:
            value = datetime.combine(value, time.min)

        if set_nat and (value is NaT or value is None):
            return MAX_DATETIME
        elif value is NaT:
            return value
        elif ((isinstance(value, Timestamp) or isinstance(value, datetime))
              and set_end_day and value.time() == time.min):
            return datetime.combine(value, delta_time)
        else:
            return value

    for col in cols:
        df[col] = df[col].apply(_convert_date)

    return df


def df_memory_usage(df: DataFrame | GeoDataFrame) -> float:
    """
    Return the memory usage of a DataFrame in MB

    Args:
        df (DataFrame | GeoDataFrame): DataFrame

    Returns:
        float: Memory usage in MB
    """
    return df.memory_usage(deep=True).sum() / 1024 ** 2


def extract_operator(input_string):
    """
    Extract sql operator from input string

    Args:
        input_string:

    Returns:

    """
    special_opers = ('-', '!') # Special operators for negation
    sql_opers = ('=', '!=', '<>', '>', '<', '>=', '<=') # SQL operators

    match = re.match(r'^(\W+)', input_string)
    if match:
        symbols = match.group(1)

        if symbols not in special_opers and symbols not in sql_opers:
            raise ValueError(f"Operator '{symbols}' not supported")

        return symbols

    return None


def sql_from_filter_by_props(**filter_by_props: dict) -> str:
    """
    Get SQL from filter by properties

    Args:
        **filter_by_props: The filter by properties

    Returns:
        sql (str): The SQL from filter by properties
    """
    sql_parts = []
    for k_fld_oper, value in filter_by_props.items():
        if k_operator := extract_operator(k_fld_oper):
            k_fld = k_fld_oper.replace(k_operator, '')
        else:
            k_operator = "="
            k_fld = k_fld_oper

        if isinstance(value, str):
            value = f"'{value}'"
        elif isinstance(value, Iterable):
            value = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) for v in value])
            value = f"({value})"
            if k_operator in ('=', '!=', '-'):
                k_operator = "IN" if k_operator == "=" else "NOT IN"
            else:
                raise ValueError(f"Operator '{k_operator}' not supported for iterable values")

        sql_parts.append(f"{k_fld} {k_operator} {value}")

    sql_filter = ' AND '.join(sql_parts)

    return sql_filter
