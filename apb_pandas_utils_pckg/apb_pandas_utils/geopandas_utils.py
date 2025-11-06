#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019
import json
from typing import Optional

import requests
from geopandas import GeoDataFrame, GeoSeries
from pandas import DataFrame, Series
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


def gdf_from_url(url_rest_api, api_params=None, crs_api=None, headers=None, crs_gdf=None, add_goto_url=False):
    """
    Fetch paginated GeoJSON from a REST API and return a GeoPandas GeoDataFrame.

    Assumes the API returns a GeoJSON FeatureCollection with 'features' and optionally 'next' for pagination.
    If 'next' is present, it should be the full URL for the next page.

    Args:
        url_rest_api (str): The base URL of the API endpoint.
        api_params (dict, optional): Query parameters for the initial request.
        crs_api (str, optional): CRS (EPSG) coord .sys. origen de las geometrías (e.g. 'EPSG:25831')
                    [Can be anything accepted by pyproj.CRS.from_user_input()]
        headers (dict, optional): HTTP headers for the request.
        crs_gdf (str, optional): CRS (EPSG) coord .sys. destino de las geometrías (e.g. 'EPSG:25831')
                    [Can be anything accepted by pyproj.CRS.from_user_input()]
        add_goto_url (bool, optional): If True, adds a 'goto_url' to the GeoDataFrame as new column.

    Returns:
        gpd.GeoDataFrame | None: A GeoDataFrame containing all features from all pages.

    Raises:
        requests.HTTPError: If any request fails.
    """
    gdf = None
    all_features = []
    url = url_rest_api
    params = api_params or {}
    first_request = True

    while url:
        if first_request:
            response = requests.get(url, params=params, headers=headers)
            first_request = False
        else:
            response = requests.get(url, headers=headers)

        response.raise_for_status()
        data = response.json()

        # Assuming GeoJSON FeatureCollection. Test results or data directly
        all_features.extend(data.get('results', data).get('features', []))

        # Check for next page
        url = data.get('next')

    # Create GeoDataFrame from all features
    if all_features:
        gdf = GeoDataFrame.from_features(all_features, crs=crs_api)

    if add_goto_url:
        centroids = gdf.geometry.centroid.to_crs('EPSG:4326')
        mask = centroids.notna()
        gdf['goto_url'] = Series([None] * len(gdf), index=gdf.index)
        gdf.loc[mask, 'goto_url'] = \
            ("https://www.google.com/maps?q=" +
             centroids.loc[mask].y.astype(str) + "," +
             centroids.loc[mask].x.astype(str))

    if crs_gdf:
        gdf = gdf.to_crs(crs_gdf)

    return gdf
