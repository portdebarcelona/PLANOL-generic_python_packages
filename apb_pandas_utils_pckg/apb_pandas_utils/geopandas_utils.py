#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019
import json
from typing import Optional

from geopandas import GeoDataFrame, GeoSeries
from pandas import DataFrame
from shapely import wkt


def gdf_to_geojson(gdf: GeoDataFrame, name: Optional[str] = None, with_crs: bool = True, show_bbox: bool = True,
                   drop_id: bool = False, path_file: str = None) -> dict:
    """
    Convierte un GeoDataFrame a diccionario geojson

    Args:
        gdf (GeoDataFrame):
        name (str=None):
        with_crs (bool=True):
        show_bbox (bool=True):
        drop_id (bool=False):
        path_file (str=None): Si se indica se guarda el geojson en el path indicado

    Returns:
        dict_geojson (dict)
    """
    dict_geojson = gdf.to_geo_dict(show_bbox=show_bbox, drop_id=drop_id)
    if name:
        dict_geojson["name"] = name
    if with_crs and gdf.crs is not None:
        auth = gdf.crs.to_authority()
        dict_geojson["crs"] = {"type": "name", "properties": {"name": f"urn:ogc:def:crs:{auth[0]}::{auth[1]}"}}

    if path_file:
        geojson = json.dumps(dict_geojson, default=str, ensure_ascii=False)
        with open(path_file, 'w', encoding='utf-8') as f:
            f.write(geojson)

    return dict_geojson


def gdf_to_df(gdf: GeoDataFrame, as_wkb=False) -> DataFrame:
    """
    Convert a GeoDataFrame to DataFrame converting the geometry columns to a str column in WKT format (WKB if as_wkb=True)

    Args:
        gdf (GeoDataFrame):
        as_wkb (bool=False): If True, the geometry column is converted to WKB format

    Returns:
        DataFrame
    """
    f_conv = 'to_wkb' if as_wkb else 'to_wkt'

    # Convert all columns type geometry to WKT
    gdf_aux = gdf.copy()
    for col in df_geometry_columns(gdf_aux):
        gdf_aux[col] = getattr(gdf_aux[col], f_conv)()
    return DataFrame(gdf_aux)


def df_geometry_columns(df: GeoDataFrame | DataFrame) -> list:
    """
    Devuelve las columnas tipo geometría de un GeoDataFrame

    Args:
        df (GeoDataFrame | DataFrame):

    Returns:
        list
    """
    return df.select_dtypes(include=["geometry"]).columns.tolist()


def df_to_crs(df: GeoDataFrame | DataFrame, crs: str) -> GeoDataFrame | DataFrame:
    """
    Convierte todas las columnas tipo geometría de un GeoDataFrame o DataFrame al CRS indicado

    Args:
        df (GeoDataFrame | DataFrame):
        crs (str): name CRS (EPSG) coord .sys. destino de las geometrías (e.g. 'EPSG:25831')
                    [Can be anything accepted by pyproj.CRS.from_user_input()]

    Returns:
        GeoDataFrame | DataFrame
    """
    df_aux = df.copy()
    for geom in df_geometry_columns(df_aux):
        df_aux[geom] = df_aux[geom].to_crs(crs)

    df_aux = df_aux.to_crs(crs)

    return df_aux


def gdf_from_df(df: DataFrame, geom_col: str, crs: str, cols_geom: list[str] = None) -> GeoDataFrame:
    """
    Crea un GeoDataFrame a partir de un DataFrame

    Args:
        df (DataFrame):
        geom_col (str): Columna geometría con el que se creará el GeoDataFrame
        crs (str): CRS (EPSG) coord .sys. origen de las geometrías (e.g. 'EPSG:25831')
                    [Can be anything accepted by pyproj.CRS.from_user_input()]
        cols_geom (list=None): Columnas con geometrías

    Returns:
        GeoDataFrame
    """
    if cols_geom is None:
        cols_geom = []

    cols_geom = set(cols_geom)
    cols_geom.add(geom_col)

    df_aux = df.copy()
    idx_prev = df_aux.index
    # We only deal with index when has names setted referred to possible columns
    set_idx = None not in idx_prev.names
    if set_idx:
        df_aux.reset_index(inplace=True)

    def convert_to_wkt(val_col):
        return wkt.loads(val_col) if isinstance(val_col, str) else None

    gdf = GeoDataFrame(df_aux)
    for col in (col for col in gdf.columns if col in cols_geom):
        ds_col = gdf[col]
        if isinstance(ds_col, GeoSeries):
            continue

        if (dtype := ds_col.dtype.name) == 'object':
            gdf[col] = gdf[col].apply(convert_to_wkt)

        gdf.set_geometry(col, inplace=True, crs=crs)

    if set_idx:
        gdf = gdf.set_index(idx_prev.names, drop=True)

    gdf.set_geometry(geom_col, crs=crs, inplace=True)

    return gdf
