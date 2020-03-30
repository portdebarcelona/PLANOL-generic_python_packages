#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 12:42
#  Copyright (c) 2019

from functools import partial
import pyproj
from shapely.ops import transform


def transform_shapely_geom(a_shp, from_espg_code, to_epsg_code):
    """
    Transforma una geometria shapely según los EPSG indicados

    Args:
        a_shp (shapely.geometry.geo): una geometria del tipo shapely
        from_espg_code (int): codigo numérico del EPSG actual para la geometria
        to_epsg_code (int): codigo numérico del EPSG al que se quiere transformar

    Returns:
        shapely.geometry.geo
    """
    project = partial(
        pyproj.transform,
        pyproj.Proj(init=f'epsg:{from_espg_code}'),  # source coordinate system
        pyproj.Proj(init=f'epsg:{to_epsg_code}'))  # destination coordinate system

    return transform(project, a_shp)


if __name__ == '__main__':
    import fire
    fire.Fire()
