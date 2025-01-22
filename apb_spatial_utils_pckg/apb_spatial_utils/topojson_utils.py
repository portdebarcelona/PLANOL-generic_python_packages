#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 12:42
#  Copyright (c) 2019

import os
from apb_extra_utils import misc as utils


def geojson_to_topojson(geojson_path, dir_topo=None, nom_layer=None, simplify=True, overwrite=True):
    """
    Callback a funciones de linea de comandos para conversion a Topojson.
    Son comandos lanzados sobre nodejs.

    Ver documentacion en github https://github.com/topojson/topojson-server.
    Vease tambien tutorial de como utlizarlo en https://medium.com/@mbostock/command-line-cartography-part-3-1158e4c55a1e

    Args:
        geojson_path:
        dir_topo:
        nom_layer:
        simplify:
        overwrite:

    Returns:
        str: path del fichero generado si va bien
    """
    __factor_quant__ = "9e5"
    __factor_simpl__ = "0.0000000000003"
    dir_name, json_name = os.path.split(geojson_path)
    base_name, ext = os.path.splitext(json_name)
    base_name = base_name.split(".geo")[0]
    topo_name = "{base_name}.topo{ext}".format(base_name=base_name,
                                               ext=ext)
    if not nom_layer:
        nom_layer = base_name

    from_path = "{nom_layer}={path}".format(nom_layer=nom_layer,
                                            path=os.path.normpath(geojson_path))

    if not dir_topo:
        dir_topo = os.path.normpath(os.path.join(dir_name, "topojson"))

    topojson_path = os.path.normpath(os.path.join(dir_topo, topo_name))

    if overwrite or not os.path.exists(topojson_path):
        if not os.path.exists(dir_topo):
            os.makedirs(dir_topo)

        params = []
        if simplify:
            params += ("-q", __factor_quant__)
            t_path_aux = "{}.aux".format(topojson_path)
            params += (from_path, ">", t_path_aux)
            ok = utils.call_command("geo2topo", *params)
            if ok:
                params = []
                params += ("-p", __factor_simpl__, "-f")
                params += ("<", t_path_aux, ">", topojson_path)
                ok = utils.call_command("toposimplify", *params)
                if ok:
                    os.remove(t_path_aux)
        else:
            params += (from_path, ">", topojson_path)
            ok = utils.call_command("geo2topo", *params)

        if ok:
            return topojson_path


def convert_geojson_files_to_topojson(dir_geojson, dir_topo, overwrite=True):
    """
    A partir de un directorio con geojson los convierte a Topojson

    Args:
        dir_geojson:
        dir_topo:
        overwrite:

    Returns:

    """
    directory = os.fsencode(dir_geojson)

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".geo.json") or filename.endswith(".geojson"):
            topo_file = geojson_to_topojson(
                os.path.normpath(os.path.join(dir_geojson, filename)),
                os.path.normpath(dir_topo), overwrite=overwrite)


if __name__ == '__main__':
    import fire
    fire.Fire()
