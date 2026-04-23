#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019
from __future__ import annotations

import json
from functools import partial
from typing import Optional

import requests
from geopandas import GeoDataFrame, GeoSeries
from pandas import DataFrame, Series
from shapely import wkt, GEOSException, wkb

from apb_extra_utils.postgres_pckg.psql_alchemy import EngPsqlAlchemy
from apb_extra_utils.utils_logging import get_base_logger
from apb_pandas_utils import df_from_url, df_from_pg_table

logger = get_base_logger(__name__)


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


def gdf_from_df(df: DataFrame, geom_col: str, crs: str | None, cols_geom: list[str] = None) -> GeoDataFrame:
    """
    Crea un GeoDataFrame a partir de un DataFrame

    Args:
        df (DataFrame):
        geom_col (str): Columna geometría con el que se creará el GeoDataFrame
        crs (str | None): CRS (EPSG) coord .sys. origen de las geometrías (e.g. 'EPSG:25831')
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

    def convert_to_wkb(val_col):
        return wkb.loads(val_col) if isinstance(val_col, str) else None

    gdf = GeoDataFrame(df_aux)
    for col in (col for col in gdf.columns if col in cols_geom):
        ds_col = gdf[col]
        if isinstance(ds_col, GeoSeries):
            continue

        if (dtype := ds_col.dtype.name) in ('str', 'object'):
            try:
                gdf[col] = gdf[col].apply(convert_to_wkt)
            except GEOSException:
                gdf[col] = gdf[col].apply(convert_to_wkb)

        if crs:
            gdf.set_geometry(col, inplace=True, crs=crs)
        else:
            gdf.set_geometry(col, inplace=True)

    if set_idx:
        gdf = gdf.set_index(idx_prev.names, drop=True)

    if crs:
        gdf.set_geometry(geom_col, crs=crs, inplace=True)
    else:
        gdf.set_geometry(geom_col, inplace=True)

    return gdf


def gdf_from_pg_table(table: str, geom_col: str | None = None, filter_sql: str | None = None,
                      crs_gdf: str | None = None,
                      add_goto_url: bool = False, user: str | None = None, psw: str | None = None,
                      srvr_db: str = 'localhost', port_db: int = 5432, db: str = 'postgres',
                      schemas: str | None = None, a_logger=None,
                      url_conn_string: str | None = None) -> GeoDataFrame | DataFrame:
    """
    Carga una tabla/vista de PostgreSQL como GeoDataFrame cuando existe una columna geométrica usable.

    Si no se informa ``geom_col``, intenta detectar la primera geometría con ``EngPsqlAlchemy.geoms_table``.
    Si no hay geometrías hace fallback a ``df_from_pg_table``.
    Si la columna indicada no existe/no es geométrica lanza exception ValueError

    Args:
        table (str): Nombre de tabla o vista.
        geom_col (str | None): Columna geométrica a usar como activa.
        filter_sql (str | None): Condición SQL opcional para cláusula WHERE. ATENCIÓN: en PG si hay campos en MAYÚSCULAS hay que indicarlos entre ""
        crs_gdf (str | None): CRS destino opcional (e.g. ``'EPSG:4326'``).
        add_goto_url (bool): Si True añade columna ``goto_url`` basada en centroides.
        user (str | None): Usuario PostgreSQL.
        psw (str | None): Password PostgreSQL.
        srvr_db (str): Host del servidor.
        port_db (int): Puerto del servidor.
        db (str): Nombre de la base de datos.
        schemas (str | None): Schemas separados por coma para ``search_path``.
        a_logger (logging.Logger | None): Logger opcional.
        url_conn_string (str | sqlalchemy.engine.urlURL | None): Connection string completa o URL de SQLAlchemy (ver apb_extra_utils.postgres_pckg.psql_alchemy.url_pg_string_connection). Si se proporciona, se ignoran los parámetros anteriores.

    Returns:
        GeoDataFrame | DataFrame
    """
    df_call = partial(
        df_from_pg_table,
        table=table,
        filter_sql=filter_sql,
        user=user,
        psw=psw,
        srvr_db=srvr_db,
        port_db=port_db,
        db=db,
        schemas=schemas,
        a_logger=a_logger,
        url_conn_string=url_conn_string,
    )

    def _fallback_df(reason: str) -> DataFrame:
        logger.warning(f"{reason} Fallback a df_from_pg_table para '{table}'.")
        return df_call()

    eng = EngPsqlAlchemy.get_cached(
        user=user,
        psw=psw,
        srvr_db=srvr_db,
        port_db=port_db,
        db=db,
        schemas=schemas,
        a_logger=a_logger,
        url_conn_string=url_conn_string,
    )

    try:
        geoms_info = eng.geoms_table_view(table)
    except Exception as exc:
        return _fallback_df(f"No se pudo inspeccionar geometrías ({exc}).")

    if not geoms_info:
        return _fallback_df("La tabla/vista no tiene columnas geométricas.")

    selected_geom_col = geom_col if geom_col else next(iter(geoms_info.keys()))
    if selected_geom_col not in geoms_info:
        raise ValueError(f"geom_col='{selected_geom_col}' no existe o no es geométrica.")

    df = df_call()

    if selected_geom_col not in df.columns:
        return _fallback_df(f"La columna geométrica '{selected_geom_col}' no está en el resultado SQL.")

    srid = geoms_info[selected_geom_col].get('srid') if isinstance(geoms_info[selected_geom_col], dict) else None
    src_crs = f"EPSG:{srid}" if isinstance(srid, int) and srid > 0 else None

    if not src_crs and crs_gdf:
        logger.warning("No se ha podido determinar SRID de la geometría; no se reproyecta a crs_gdf.")

    gdf = gdf_from_df(df=df, geom_col=selected_geom_col, crs=src_crs)

    if add_goto_url:
        add_goto_google_maps_url_to_gdf(gdf)

    if crs_gdf and src_crs:
        gdf = gdf.to_crs(crs_gdf)

    return gdf


def gdf_from_url(url_rest_api: str, api_params: dict | None = None, crs_api: str | None = None,
                 headers: dict | None = None, crs_gdf: str | None = None, add_goto_url: bool = False,
                 features_key: str = 'features', next_key: str = 'next', results_key: str = 'results',
                 timeout: int | tuple[int, int] = (10, 30), max_retries: int = 3,
                 session: requests.Session | None = None) -> GeoDataFrame | DataFrame | None:
    """
    Fetch paginated GeoJSON from a REST API and return a GeoPandas GeoDataFrame.

    Delegates HTTP handling and pagination to :func:`apb_pandas_utils._fetch_pages`.
    Supports FeatureCollection responses (``features`` key) and optional CRS reprojection.

    Args:
        url_rest_api (str): The base URL of the API endpoint.
        api_params (dict, optional): Query parameters for the initial request.
        crs_api (str, optional): CRS of the geometries returned by the API
            (e.g. ``'EPSG:25831'``). Passed to :meth:`GeoDataFrame.from_features`.
        headers (dict, optional): HTTP headers for the request.
        crs_gdf (str, optional): Target CRS to reproject the GeoDataFrame to
            after fetching (e.g. ``'EPSG:4326'``). No reprojection if ``None``.
        add_goto_url (bool): If ``True``, adds a ``'goto_url'`` column with a
            Google Maps link for each feature centroid. Defaults to ``False``.
        features_key (str): Key in the JSON response dict that contains the
            GeoJSON features list. Defaults to ``'features'``.
        next_key (str): Key in the JSON response containing the next-page URL.
            Defaults to ``'next'``.
        results_key (str): Key in the JSON response containing the results:
        timeout (int | tuple[int, int]): Request timeout ``(connect, read)`` in seconds.
            Defaults to ``(10, 30)``.
        max_retries (int): Retries on transient HTTP errors (429, 500-504).
            Defaults to ``3``.
        session (requests.Session, optional): Existing session to reuse.
            If None, a new session with retry logic is created and closed after use.

    Returns:
        GeoDataFrame | Dataframe | None: A GeoDataFrame with all features, or ``None`` if empty.

    Raises:
        requests.HTTPError: If any HTTP request returns an error status.
        requests.ConnectionError: If the connection fails after all retries.
        ValueError: If a page response has an unexpected structure.
    """
    from apb_pandas_utils import _iter_fetch_pages

    all_features: list = []
    try_as_df: bool = False

    for data in _iter_fetch_pages(url_rest_api, api_params, headers, next_key, timeout, max_retries, session):
        page_features = None

        if isinstance(data, list):
            page_features = data

        elif isinstance(data, dict):
            # Standard GeoJSON FeatureCollection — look for features_key directly
            # or nested inside a 'results' wrapper (e.g. DRF + djangorestframework-gis)
            if features_key in data:
                page_features = data[features_key]
            elif results_key in data and isinstance(data[results_key], dict):
                page_features = data[results_key].get(features_key, data)
        else:
            raise ValueError(
                f"Unexpected JSON structure: expected list or dict, got {type(data).__name__}"
            )

        if page_features and len(page_features) > 0 and isinstance(page_features[0], dict) and page_features[0].get(
                'type') == 'Feature':
            all_features.extend(page_features)
            logger.debug(f"Got {len(page_features)} features (total so far: {len(all_features)})")
        else:
            logger.warning(f"Data with unexpected structure for GeoDataframe! Using instead as Dataframe")
            try_as_df = True
            break

    if try_as_df:
        return df_from_url(
            url_rest_api=url_rest_api,
            api_params=api_params,
            headers=headers,
            results_key=results_key,
            next_key=next_key,
            max_retries=max_retries,
            session=session)

    if not all_features:
        return None

    gdf = GeoDataFrame.from_features(all_features, crs=crs_api)
    logger.debug(f"GeoDataFrame created with {len(gdf)} rows and CRS={crs_api}")

    if add_goto_url:
        add_goto_google_maps_url_to_gdf(gdf)

    if crs_gdf:
        gdf = gdf.to_crs(crs_gdf)
        logger.debug(f"Reprojected GeoDataFrame to CRS={crs_gdf}")

    return gdf


def add_goto_google_maps_url_to_gdf(gdf: GeoDataFrame):
    """
    Add goto URL to Google Maps URL to GeoDataFrame on column 'goto_url'.

    Args:
        gdf (GeoDataFrame): GeoDataFrame to add URL to.

    Returns:
        None: Modifies the GeoDataFrame in place.
    """
    centroids = gdf.geometry.centroid.to_crs('EPSG:4326')
    mask = centroids.notna()
    gdf['goto_url'] = Series([None] * len(gdf), index=gdf.index)
    gdf.loc[mask, 'goto_url'] = centroids.loc[mask].apply(
        lambda p: f"https://www.google.com/maps?q={p.y},{p.x}"
    )
