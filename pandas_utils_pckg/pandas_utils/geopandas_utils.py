#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019
import json
from typing import Optional

from geopandas import GeoDataFrame


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
