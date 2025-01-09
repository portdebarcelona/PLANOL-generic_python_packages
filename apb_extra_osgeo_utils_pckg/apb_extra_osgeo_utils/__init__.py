#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 14:27
#  Copyright (c) 2019
"""
.. include:: ../README.md
"""

import logging
import os
import re
from collections import OrderedDict, namedtuple

import math
from osgeo import ogr, osr
from osgeo.ogr import ODsCCreateLayer, OLCAlterFieldDefn, OLCCreateField, ODsCTransactions, \
    ODsCDeleteLayer, OLCTransactions, Geometry, ODrCCreateDataSource, GeomFieldDefn

from apb_extra_utils import misc as utils

SIMPLIFY_TOLERANCE = 1e-6
DRIVERS_GDAL_NOT_DELETE_LAYERS = ('POSTGRESQL',)
DRIVERS_OLD_SRS_AXIS_MAPPING_4326 = ('GEOJSON', 'GPKG', 'POSTGRESQL')
PREFFIX_GEOMS_LAYERS_GDAL = 'geom_'
PREFFIX_GEOMS_LAYERS_GDAL_CSV = '_WKT'

print_debug = logging.debug
print_warning = logging.warning


def srs_ref_from_epsg_code(code_epsg: int, old_axis_mapping=False) -> osr.SpatialReference:
    """

    Args:
        code_epsg (int):
        old_axis_mapping (bool=False): Por cambio entre GDAL2.0 y GDAL3.0 se (vease
    https://github.com/OSGeo/gdal/blob/master/gdal/MIGRATION_GUIDE.TXT) por defecto se utiliza el mapeo de ejes
    clasico LONG,LAT

    Returns:
        srs (osr.SpatialReference)
    """
    srs = osr.SpatialReference()
    if old_axis_mapping:
        try:
            from osgeo.osr import OAMS_TRADITIONAL_GIS_ORDER
            print_debug("OAMS_TRADITIONAL_GIS_ORDER")
            srs.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER)
        except ImportError:
            print_warning("OAMS_TRADITIONAL_GIS_ORDER not available")

    ret = srs.ImportFromEPSG(code_epsg)
    if ret != 0:
        raise Warning("No se puede retornar un osgeo.osr.SpatialReference EPSG para el codigo '{}'!!".format(code_epsg))

    return srs


def layer_gdal_from_file(path_file: str,
                         nom_driver: str = 'GeoJSON',
                         nom_geom: str = None,
                         default_srs_epsg_code: int = 4326,
                         default_order_long_lat: bool = True):
    """

    Args:
        path_file (str):
        nom_driver (str='GeoJSON'):
        nom_geom (str=None): si se informa devolverá la layer solo con la geometria especificada
        default_srs_epsg_code (int=4326): codigo del sistema de coordenadas que asignará por defecto si la layer
                                          NO tiene sistema definido
        default_order_long_lat (bool=True): si no viene informado el SRS y se usa el default EPSG4326 entonces se supone
                                          por defecto que las geometria vienen en orden antiguo LONGITUD, LATITUD

    Returns:
        layer_gdal (osgeo.ogr.Layer), nom_layer (str), datasource_gdal (osgeo.ogr.DataSource)
    """
    drvr = ogr.GetDriverByName(nom_driver)

    nom_layer, ext = utils.split_ext_file(os.path.basename(path_file))
    if ext.lower().endswith("zip"):
        path_file = "/vsizip/{}".format(path_file)

    ds_vector_file = drvr.Open(path_file, 0)

    a_layer = None
    if ds_vector_file:
        a_layer = ds_vector_file.GetLayer(0)

        if nom_geom:
            lay_def = a_layer.GetLayerDefn()
            nom_geom = nom_geom.strip().upper()

            if lay_def.GetGeomFieldCount() > 1:
                idx_geom = lay_def.GetGeomFieldIndex(nom_geom)
                if idx_geom < 0:
                    raise Exception("El fichero vectorial '{}' no contiene una geometria con el nombre '{}'".format(
                        ds_vector_file.GetName(), nom_geom))
                elif idx_geom > 0:
                    # Convertimos a layer en MEMORY para poder cambiar estructura
                    ds_mem = ds_gdal_memory()
                    a_layer = create_layer_from_layer_gdal_on_ds_gdal(ds_mem, a_layer, nom_layer, nom_geom,
                                                                      exclude_cols_geoms=False, null_geoms=True)
                    if a_layer:
                        ds_vector_file = ds_mem

            elif not a_layer.GetGeometryColumn() and lay_def.GetGeomFieldDefn(0):
                lay_def.GetGeomFieldDefn(0).SetName(nom_geom)

        if a_layer:
            # Por si no carga el SRS se asigna el :default_srs_epsg_code (defecto epsg:4326)
            for gf in geom_fields_layer_gdal(a_layer):
                if not gf.GetSpatialRef():
                    gf.SetSpatialRef(srs_ref_from_epsg_code(default_srs_epsg_code, default_order_long_lat))

    return a_layer, nom_layer, ds_vector_file


def datasource_gdal_vector_file(nom_driver_gdal, nom_ds, a_dir, create=None, from_zip=False, **create_options):
    """
    Crea datasource gdal para driver de tipo fichero
    Args:
        nom_driver_gdal (str):
        nom_ds (str):
        a_dir (str):
        create (bool=None): Por defecto crea el datasource si este no existe y se abre sin problemas previamente.
                        Si False entonces NO lo crea en ningún caso, y si True lo creará sin intentar abrirlo
        from_zip (bool=False):
        **create_options: lista claves valores con opciones de creacion para el datasource de GDAL
                        p.e.: NameField="SEQENTITAT", DescriptionField="SW_URN"

    Returns:
        datasource_gdal (osgeo.ogr.DataSource), overwrited (bool)
    """
    driver, exts_driver = driver_gdal(nom_driver_gdal)
    if not exts_driver:
        raise Exception("ERROR! - El driver GDAL {} no es de tipo fichero vectorial".format(driver))

    base_path_file = os.path.normpath(os.path.join(a_dir, nom_ds.strip().lower()))
    _, ext_base = os.path.splitext(base_path_file)

    vsi_prefix = ""
    if from_zip:
        ext_file = "zip"
        vsi_prefix = "/vsizip/"
    else:
        if "topojson" in (ext.lower() for ext in exts_driver):
            ext_file = "topojson"
        else:
            ext_file = exts_driver[0]

    if (os.path.exists(base_path_file) and os.path.isfile(
            base_path_file)) or ext_base.lower() == f'.{ext_file.lower()}':
        path_file = base_path_file
    else:
        path_file = "{}.{}".format(base_path_file, ext_file)

    overwrited = False
    datasource_gdal = None
    if not create and os.path.exists(path_file):
        open_path_file = "{}{}".format(vsi_prefix, path_file)
        datasource_gdal = driver.Open(open_path_file, 1)
        if datasource_gdal is None:
            datasource_gdal = driver.Open(open_path_file)

    if datasource_gdal:
        overwrited = True

    if create or (create is not False and datasource_gdal is None and driver.TestCapability(ODrCCreateDataSource)):
        datasource_gdal = driver.CreateDataSource(path_file,
                                                  list("{}={}".format(opt, val) for opt, val in create_options.items()))

    return datasource_gdal, overwrited


def driver_gdal(nom_driver):
    """
    Devuelve el driver GDAL solicitado y si es de tipo fichero vectorial tambien devuelve la extension
    Si no coincide exactamente devuelve el que tiene nombre más parecido.
    Verificar con drivers_ogr_gdal_disponibles() los disponibles

    Args:
        nom_driver:
    Returns:
        driver_gdal (osgeo.ogr.Driver), exts_driver (list)
    """
    driver_gdal = ogr.GetDriverByName(nom_driver)
    exts_drvr = driver_gdal.GetMetadata().get('DMD_EXTENSIONS', "").split(" ")

    return driver_gdal, exts_drvr


def ds_gdal_memory():
    """
    Devuelve un osgeo.ogr.DataSource de tipo "memory"

    Returns:
        datasource_gdal (osgeo.ogr.DataSource)
    """
    return ogr.GetDriverByName("memory").CreateDataSource("")


def set_create_option_list_for_layer_gdal(layer_gdal, drvr_name="GPKG", **extra_opt_list):
    """
    Devuelve la lista de create options GDAL a partir de una layer, el driver para el que se quiere crear y options
    pasadas por defecto

    Args:
        layer_gdal (ogr.Layer):
        drvr_name (str="GPKG"): nombre de driver GDAL
        extra_opt_list: lista pares claves-valores que se corresponden con option create list del driver GDAL

    Returns:
        opt_list (dict)
    """
    opt_list = set_create_option_list_for_driver_gdal(drvr_name, **extra_opt_list)

    opt_geom_name = "GEOMETRY_NAME"
    if opt_geom_name not in opt_list:
        nom_geom_src = layer_gdal.GetGeometryColumn()
        if nom_geom_src:
            opt_list[opt_geom_name] = "{}={}".format(opt_geom_name, nom_geom_src)

    return opt_list


def set_create_option_list_for_driver_gdal(drvr_name="GPKG", **extra_opt_list):
    """
    Devuelve la lista de create options GDAL a partir de una layer, el driver para el que se quiere crear y options
    pasadas por defecto

    Args:
        drvr_name (str="GPKG"): nombre de driver GDAL
        extra_opt_list: lista pares claves-valores que se corresponden con option create list del driver GDAL

    Returns:
        opt_list (dict)
    """
    # Se quitan las options que no son de creacion para el driver especificado
    drvr, exts_drvr = driver_gdal(drvr_name)
    if not drvr:
        Exception("!ERROR! - El nombre de driver '{}' no es un driver GDAL disponible".format(drvr_name))

    opt_list = {k.upper(): v.upper() for k, v in extra_opt_list.items()}

    if not "FID" in opt_list and drvr.name == 'GPKG':
        opt_list["FID"] = 'FID=FID_GPKG'

    if drvr.name == "GeoJSON":
        if "WRITE_BBOX" not in opt_list:
            opt_list["WRITE_BBOX"] = 'WRITE_BBOX=YES'

    if drvr.name == "CSV":
        if "CREATE_CSVT" not in opt_list:
            opt_list["CREATE_CSVT"] = 'CREATE_CSVT=YES'
        if "GEOMETRY" not in opt_list:
            opt_list["GEOMETRY"] = 'GEOMETRY=AS_WKT'

    if drvr.GetMetadataItem('DS_LAYER_CREATIONOPTIONLIST'):
        list_opts_drvr = drvr.GetMetadataItem('DS_LAYER_CREATIONOPTIONLIST')
        keys_opt_list = list(opt_list.keys())
        for n_opt in keys_opt_list:
            if list_opts_drvr.find(n_opt) < 0:
                opt_list.pop(n_opt)

        if "SPATIAL_INDEX" not in opt_list and \
                list_opts_drvr.find("SPATIAL_INDEX") >= 0 and drvr.name != 'PostgreSQL':
            opt_list["SPATIAL_INDEX"] = 'SPATIAL_INDEX=YES'

    return opt_list


def copy_layer_gdal_to_ds_gdal(layer_src, ds_gdal_dest, nom_layer=None, nom_geom=None,
                               overwrite=True, **extra_opt_list):
    """
    Copia una layer_gdal a otro datasource gdal

    Args:
        layer_src:
        ds_gdal_dest:
        nom_layer (str=None): OPC - Si no viene informado cogerá el nombre de la layer
        nom_geom (str=None): OPC - Si se informa se cogerá como el nombre de la geometria de la nueva layer
        overwrite (bool=True):
        **extra_opt_list (str): Lista claves-valores de opciones para copylayer o createLayer
                                del driver de ds_gdal indicado

    Returns:
        layer_dest (ogr.layer)
    """
    if not nom_layer:
        nom_layer = layer_src.GetName()
    nom_layer = nom_layer.strip().lower()

    layer_dest = ds_gdal_dest.GetLayerByName(nom_layer)
    if layer_dest:
        if not overwrite:
            return layer_dest
        else:
            ds_gdal_dest.DeleteLayer(nom_layer)

    drvr_name = ds_gdal_dest.GetDriver().GetName()

    extra_opt_list["IDENTIFIER"] = "IDENTIFIER={}".format(nom_layer)

    opt_list = set_create_option_list_for_layer_gdal(layer_src, drvr_name=drvr_name,
                                                     **{k.upper(): v.upper() for k, v in extra_opt_list.items()})

    layer_dest = ds_gdal_dest.CopyLayer(layer_src, nom_layer, list(opt_list.values()))

    if layer_dest:
        if not layer_dest.GetGeometryColumn() and layer_dest.GetLayerDefn().GetGeomFieldDefn(0) and \
                (layer_src.GetGeometryColumn() or nom_geom):
            if not nom_geom:
                nom_geom = layer_src.GetGeometryColumn()
            else:
                nom_geom = nom_geom.upper()

            layer_dest.GetLayerDefn().GetGeomFieldDefn(0).SetName(nom_geom)

        if drvr_name == "GPKG":
            create_spatial_index_layer_gpkg(ds_gdal_dest, nom_layer)

    return layer_dest


def layer_gtype_from_geoms(layer_gdal, nom_geom=None):
    """
    A partir de la 1º geometria informada de una layer_gdal devuelve el tipo de geometria que es. Si no encuentra
    devuelve el geom_type de la layer (layer_gdal.GetGeomType())

    Args:
        layer_gdal (osgeo.ogr.Layer):
        nom_geom (str=None): Nombre geometria

    Returns:
        geom_type (int=layer_gdal.GetGeomType()): Si no encuentra devuelve 0 por defecto (GEOMETRY)
    """
    idx_geom = 0
    if nom_geom:
        idx_geom = layer_gdal.GetLayerDefn().GetGeomFieldIndex(nom_geom)

    if idx_geom >= 0:
        layer_gdal.ResetReading()
        return next((f.GetGeomFieldRef(idx_geom).GetGeometryType()
                     for f in layer_gdal if f.GetGeomFieldRef(idx_geom)),
                    layer_gdal.GetGeomType())


def srs_for_layer(layer_src, nom_geom_src=None):
    """
    Devuelve el SpatialReference de la layer_gdal
    Args:
        layer_src (ogr.Layer)
        nom_geom_src (str=None): Nombre geometria

    Returns:
        srs_lyr_src (osgeo.osr.SpatialReference)
    """
    srs_lyr_src = layer_src.GetSpatialRef()
    layer_src_def = layer_src.GetLayerDefn()

    if act_geom_field := layer_src_def.GetGeomFieldDefn(0):
        if nom_geom_src:
            idx_act_geom_field = layer_src_def.GetGeomFieldIndex(nom_geom_src)
            if idx_act_geom_field >= 0:
                act_geom_field = layer_src_def.GetGeomFieldDefn(idx_act_geom_field)

        if act_geom_field.GetSpatialRef():
            srs_lyr_src = act_geom_field.GetSpatialRef()

    return srs_lyr_src


def create_layer_from_layer_gdal_on_ds_gdal(ds_gdal_dest, layer_src, nom_layer=None, nom_geom_src=None, sel_camps=None,
                                            exclude_cols_geoms=True, tolerance_simplify=None, null_geoms=False,
                                            gtype_layer_from_geoms=True, epsg_code_dest=None,
                                            epsg_code_src_default=4326, old_axis_mapping_srs=None, **extra_opt_list):
    """
    Crea nuevo layer a partir de layer_gdal.

    Args:
        ds_gdal_dest (ogr.DataSource):
        layer_src (ogr.Layer):
        nom_layer (str=None):
        nom_geom_src (str=None): Si el nombre no se corresponde con ninguna de las geometrias de la layer_src se utilizará
                            como ALIAS de la geometria 0 (la defecto) de la nueva layer resultante
        sel_camps (list=None): OPC - Lista de campos a escoger de la layer original
        exclude_cols_geoms (bool=True): Por defecto de la lista de columnas alfanuméricas (no geometrias) excluirá las
                                       columnas que hagan referencia a alguna de las geometrias
        tolerance_simplify (float=None): Tolerancia (distancia minima) en unidades del srs de la layer
             Mirar método Simplify() sobre osgeo.ogr.Geometry
        null_geoms (bool=False): Por defecto no grabará las filas que la geometria principal (nom_geom) es nula
        gtype_layer_from_geoms (bool=True): Por defecto, si gtype de layer origen == 0 (GEOMETRY) deducirá el tipo de
                                geometria (POINT, LINE o POLYGON) a partir de la primera informada
                                encontrada en la layer_origen
        epsg_code_dest (int=None): Codigo EPSG para le que se transformarán las geometrias desde el SRS original
        epsg_code_src_default (int=4326): Codigo EPSG que se usará para las layer_src que NO tengan SRS asignado
        old_axis_mapping_srs (bool=None): setea si quieres usar old mapping axes en (LONG, LAT) (GDAL >3.2)  
        **extra_opt_list (str): Lista claves-valores de opciones para createLayer del driver de ds_gdal indicado

    Returns:
        layer_out (ogr.Layer)
    """
    desc_ds_gdal = ds_gdal_dest.GetDescription()
    drvr_name = ds_gdal_dest.GetDriver().GetName().upper()
    print_debug("Inici crear layer '{}' en ds_gdal '{}'".format(
        (nom_layer if nom_layer else layer_src.GetName()).upper(),
        desc_ds_gdal if desc_ds_gdal else drvr_name))

    geoms_src = geoms_layer_gdal(layer_src)
    camps_src = cols_layer_gdal(layer_src)

    if nom_geom_src:
        nom_geom_src = nom_geom_src.upper()
        if len(geoms_src) > 1:
            if nom_geom_src not in map(lambda ng: ng.upper(), geoms_src):
                raise Exception("Argumento :NOM_GEOM = '{}' erróneo ya que "
                                "LAYER_GDAL original no contiene dicha geometria".format(nom_geom_src))
        elif len(geoms_src) == 0:
            raise Exception("Argumento :NOM_GEOM = '{}' erróneo ya que "
                            "LAYER_GDAL original no contiene geometrias".format(nom_geom_src))

    if sel_camps:
        sel_camps = {ng.upper() for ng in sel_camps}
        if not sel_camps.issubset(camps_src):
            raise Exception("Argumento :SEL_CAMPS = '[{}]' erróneo ya que "
                            "LAYER_GDAL no contiene alguno de los campos indicados".format(",".join(sel_camps)))
    else:
        sel_camps = set()

    if not nom_layer:
        nom_layer = layer_src.GetName()
    else:
        nom_layer = nom_layer.strip()

    nom_layer = nom_layer.lower()

    gtype = layer_src.GetGeomType()
    srs_lyr_src = layer_src.GetSpatialRef()

    layer_src_def = layer_src.GetLayerDefn()
    act_geom_field = layer_src_def.GetGeomFieldDefn(0)
    nom_geom_out = None

    if act_geom_field:
        if nom_geom_src:
            idx_act_geom_field = layer_src_def.GetGeomFieldIndex(nom_geom_src)
            if idx_act_geom_field >= 0:
                act_geom_field = layer_src_def.GetGeomFieldDefn(idx_act_geom_field)
                nom_geom_out = fix_affix_geom_name_layer_gdal(nom_geom_src, layer_src)

        gtype = act_geom_field.GetType()
        if gtype_layer_from_geoms and not gtype:
            gtype = layer_gtype_from_geoms(layer_src, nom_geom_src)

        if act_geom_field.GetSpatialRef():
            srs_lyr_src = act_geom_field.GetSpatialRef()

    if sel_camps:
        sel_camps = {c.strip().upper() for c in sel_camps}

    geoms_src_minus_affix = geoms_layer_gdal(layer_src, PREFFIX_GEOMS_LAYERS_GDAL)
    if exclude_cols_geoms:
        if sel_camps:
            sel_camps.difference_update(geoms_src_minus_affix)
        else:
            sel_camps = cols_layer_gdal(layer_src).difference(geoms_src_minus_affix)

    srs_lyr_dest = None
    if not srs_lyr_src and epsg_code_src_default:
        srs_lyr_src = srs_ref_from_epsg_code(epsg_code_src_default, old_axis_mapping=old_axis_mapping_srs)
    if srs_lyr_src:
        if old_axis_mapping_srs is None and epsg_code_dest == 4326:
            old_axis_mapping_srs = drvr_name in DRIVERS_OLD_SRS_AXIS_MAPPING_4326

        if epsg_code_dest:
            srs_lyr_dest = srs_ref_from_epsg_code(epsg_code_dest, old_axis_mapping=old_axis_mapping_srs)
        else:
            srs_lyr_dest = srs_lyr_src

    if ds_gdal_dest.TestCapability(ODsCCreateLayer):
        # To avoid message "Warning"
        if ds_gdal_dest.TestCapability(ODsCDeleteLayer) and ds_gdal_dest.GetLayerByName(nom_layer):
            ds_gdal_dest.DeleteLayer(nom_layer)

        layer_out, nom_layer = create_layer_on_ds_gdal(ds_gdal_dest, nom_layer, nom_geom_out, gtype, srs_lyr_dest,
                                                       **extra_opt_list)
    else:
        layer_out = ds_gdal_dest.GetLayer(0)

    geom_field_out = None
    if layer_out.TestCapability(OLCAlterFieldDefn):
        layer_out_def = layer_out.GetLayerDefn()
        geom_field_out = layer_out_def.GetGeomFieldDefn(0)
        if geom_field_out:
            if not nom_geom_out:
                nom_geom_out = act_geom_field.GetNameRef()
                if not nom_geom_out:
                    nom_geom_out = "GEOMETRY"
            geom_field_out.SetName(nom_geom_out)

    if layer_out.TestCapability(OLCCreateField):
        for fd in fields_layer_gdal(layer_src):
            nom_fd = fd.GetNameRef().upper()
            if layer_out.FindFieldIndex(nom_fd, True) < 0 and (not sel_camps or nom_fd in sel_camps) and \
                    nom_fd not in (gn.upper() for gn in geoms_src_minus_affix):
                layer_out.CreateField(fd)

        for gfd in geom_fields_layer_gdal(layer_src):
            nom_gfd = fix_affix_geom_name_layer_gdal(gfd.GetNameRef(), layer_src).upper()
            if (not sel_camps or nom_gfd in sel_camps) and \
                    (nom_gfd not in geoms_src or not exclude_cols_geoms) and \
                    nom_gfd != nom_geom_out:
                gfd_def_src = layer_src_def.GetGeomFieldDefn(layer_src_def.GetGeomFieldIndex(gfd.GetNameRef()))
                gfd_def_dest = GeomFieldDefn(nom_gfd, gfd_def_src.GetType())
                if srs_lyr_dest:
                    gfd_def_dest.SetSpatialRef(srs_lyr_dest)
                layer_out.CreateGeomField(gfd_def_dest)

    if not geom_field_out:
        null_geoms = True  # Si no hay geom siempre se añaden

    add_layer_features_to_layer(layer_src, ds_gdal_dest, layer_out, nom_geom_src, nom_geom_out,
                                srs_lyr_dest=srs_lyr_dest,
                                null_geoms=null_geoms,
                                tolerance_simplify=tolerance_simplify,
                                epsg_code_src_default=epsg_code_src_default,
                                old_axis_mapping_srs=old_axis_mapping_srs)

    if drvr_name == "GPKG":
        create_spatial_index_layer_gpkg(ds_gdal_dest, nom_layer)

    if drvr_name == 'CSV':
        path_csv = ds_gdal_dest.GetName()
        if os.path.exists(path_csv):
            rename_wkt_geoms_csv(path_csv)

    return ds_gdal_dest.GetLayerByName(nom_layer)


def rename_wkt_geoms_csv(path_csv):
    """
    Remove "_WKT" affix from WKT geometry fields in CSV file

    Args:
        path_csv (str): Path to CSV file

    Returns:

    """
    with open(path_csv, 'r', encoding='utf-8') as r_file:
        content_csv = r_file.readlines()
        first_line = next(iter(content_csv), None)
    if first_line:
        new_first_line = first_line.replace(PREFFIX_GEOMS_LAYERS_GDAL_CSV, '')
        if new_first_line != first_line:
            content_csv[0] = new_first_line
            with open(path_csv, 'w', encoding='utf-8') as w_file:
                w_file.writelines(content_csv)


def add_layer_features_to_layer(layer_src, ds_gdal_dest, layer_dest, nom_geom_src=None, nom_geom_dest=None,
                                srs_lyr_dest=None, null_geoms=False, tolerance_simplify=None,
                                remove_prev_features=False, epsg_code_src_default=4326, old_axis_mapping_srs=None):
    """
    From a layer of a dataset, add the features to another layer of another dataset.

    Args:
        layer_src (ogr.Layer): Layer origen
        ds_gdal_dest (gdal.Dataset): Dataset destino
        layer_dest (ogr.Layer): Layer destino
        nom_geom_src (str=None): Si el nombre no se corresponde con ninguna de las geometrias de la layer_src se utilizará
                            como ALIAS de la geometria 0 (la defecto) de la nueva layer resultante
        nom_geom_dest (str):
        srs_lyr_dest (ogr.SpatialReference=None): Spatial Reference System de la layer_dest
        null_geoms (bool=False): Por defecto no grabará las filas que la geometria principal (nom_geom) es nula
        tolerance_simplify (float=None): Tolerancia (distancia minima) en unidades del srs de la layer
             Mirar método Simplify() sobre osgeo.ogr.Geometry
        remove_prev_features (bool=False): Si es True, se eliminarán las features previas de la layer_dest
        epsg_code_src_default (int=4326): EPSG code del srs de la layer_src si no se encuentra
        old_axis_mapping_srs (bool=None): setea si quieres usar old mapping axes en (LONG, LAT) (GDAL >3.2)

    Returns:

    """
    geoms_out = geoms_layer_gdal(layer_dest)
    cols_out = cols_layer_gdal(layer_dest)

    geom_transform = None
    srs_lyr_src = srs_for_layer(layer_src, nom_geom_src)
    if not srs_lyr_src:
        srs_lyr_src = srs_ref_from_epsg_code(epsg_code_src_default, old_axis_mapping_srs)

    if srs_lyr_dest is None:
        srs_lyr_dest = srs_for_layer(layer_dest, nom_geom_dest)

    if srs_lyr_dest and not srs_lyr_src.IsSame(srs_lyr_dest):
        geom_transform = osr.CoordinateTransformation(srs_lyr_src, srs_lyr_dest)

    ds_trans = ds_gdal_dest.TestCapability(ODsCTransactions)

    if remove_prev_features:
        if ds_trans:
            layer_dest.StartTransaction()
        for feat in layer_dest:
            layer_dest.DeleteFeature(feat.GetFID())
        if ds_trans:
            layer_dest.CommitTransaction()

    if ds_trans:
        layer_dest.StartTransaction()

    i = 0
    for feat_src, geom_src, nt_src in feats_layer_gdal(layer_src, nom_geom_src):
        cols_out_chk = [col.upper() for col in cols_out.union(geoms_out)]
        vals_camps = {nc: val for nc, val in nt_src._asdict().items()
                      if nc.upper() in cols_out_chk}
        if null_geoms or geom_src:
            if nom_geom_dest:
                vals_camps[nom_geom_dest.upper()] = geom_src

            add_feature_to_layer_gdal(layer_dest,
                                      tolerance_simplify=tolerance_simplify,
                                      geom_trans=geom_transform,
                                      **vals_camps)

            if i > 0 and (i % 1000) == 0:
                print_debug("{} registres tractats...".format(str(i)))
            i += 1
    if ds_trans:
        layer_dest.CommitTransaction()


def create_layer_on_ds_gdal(ds_gdal_dest, nom_layer, nom_geom=None, gtype=None, srs_lyr_out=None, **extra_opt_list):
    """

    Args:
        ds_gdal_dest (ogr.DataSource):
        nom_layer (str):
        nom_geom (str=None):
        gtype (OGRwkbGeometryType=None): Indicar integer representativo del tipo de geometria de la layer (ogr.wkbPoint, ogr.wkbPolygon, ogr.LineString, ...)
        srs_lyr_out (osr.SpatialReference=None): codigo epsg del sistema de coordenadas de la geometria
        **extra_opt_list: Calves valores option list creacion layer gdal

    Returns:
        layer_gdal (ogr.Layer), nom_layer (str)
    """
    drvr_name = ds_gdal_dest.GetDriver().GetName().upper()

    opt_list = {k.upper(): v.upper() for k, v in extra_opt_list.items()}

    opt_geom_name = "GEOMETRY_NAME"
    if nom_geom:
        opt_list[opt_geom_name] = "{}={}".format(opt_geom_name, nom_geom.upper())
    else:
        if opt_geom_name in opt_list:
            opt_list.pop(opt_geom_name)
        gtype = ogr.wkbNone

    opt_list["IDENTIFIER"] = opt_list.get("IDENTIFIER", "IDENTIFIER={}".format(nom_layer))

    opt_list = set_create_option_list_for_driver_gdal(drvr_name, **{k.upper(): v.upper() for k, v in opt_list.items()})

    if ds_gdal_dest.TestCapability(ODsCDeleteLayer) and ds_gdal_dest.GetLayerByName(nom_layer):
        print_warning("!ATENCION! - Se sobreescribirá la layer '{}' sobre el datasource GDAL '{}'".format(
            nom_layer, ds_gdal_dest.GetDescription()))
        ds_gdal_dest.DeleteLayer(nom_layer)

    if drvr_name.upper() == "KML":
        nom_layer = nom_layer.replace("-", "__")

    layer_out = ds_gdal_dest.CreateLayer(nom_layer, srs_lyr_out, geom_type=gtype, options=list(opt_list.values()))

    return layer_out, layer_out.GetName() if layer_out else None


def create_spatial_index_layer_gpkg(ds_gpkg, nom_layer):
    """
    Crea spatial index sobre una layer (layer_gpkg) de un datosource gpkg (ds_gpkg)

    Args:
        ds_gpkg (osgeo.ogr.DataSource):
        layer_gpkg (ogr.Layer):

    Returns:
        bool
    """
    layer_gpkg = ds_gpkg.GetLayerByName(nom_layer)
    if layer_gpkg and layer_gpkg.GetGeometryColumn():
        # Se crea spatial_index ya que GDAL NO lo hace
        ds_gpkg.StartTransaction()
        ds_gpkg.ExecuteSQL("SELECT CreateSpatialIndex('{tab_name}', '{geom_name}') ".format(
            tab_name=layer_gpkg.GetName(),
            geom_name=layer_gpkg.GetGeometryColumn()))
        ds_gpkg.CommitTransaction()

        return True
    else:
        return False


def add_feature_to_layer_gdal(layer_gdal, tolerance_simplify=None, geom_trans=None, commit=False, **valors_camps):
    """

    Args:
        layer_gdal (ogr.Layer):
        tolerance_simplify (float=None): Tolerancia (distancia minima) en unidades del srs de la layer.
                                        Mirar método Simplify() sobre osgeo.ogr.Geometry
        geom_trans (osr.CoordinateTransformation=None): transformacion para convertir las geometrias a otro SRS
        commit (bool=False): Per defecte no farà commit de la transaccio
        **valors_camps: pares nombre_campo=valor de la feature a crear

    Returns:
        feat (ogr.Feature)
    """
    dd_feat = ogr.Feature(layer_gdal.GetLayerDefn())

    for camp, val in valors_camps.items():
        idx_geom = dd_feat.GetGeomFieldIndex(camp)
        es_geom = idx_geom >= 0
        if es_geom:
            if val:
                if tolerance_simplify:
                    val = val.Simplify(tolerance_simplify)
                if val and geom_trans:
                    val.Transform(geom_trans)

            dd_feat.SetGeomField(idx_geom, val)

        idx_fld = dd_feat.GetFieldIndex(camp)
        if idx_fld >= 0:
            if val:
                if es_geom or hasattr(val, "ExportToIsoWkt"):
                    val = val.ExportToIsoWkt()
                dd_feat.SetField(camp, val)
            else:
                dd_feat.SetFieldNull(camp)

        if idx_fld < 0 and idx_geom < 0:
            if isinstance(val, Geometry):
                if geom_trans:
                    val.Transform(geom_trans)
                dd_feat.SetGeometry(val)
            elif val:
                print_warning("!ATENCION! - La :layer_gdal no contiene el campo '{}'".format(camp))

    commit_trans = commit and layer_gdal.TestCapability(OLCTransactions)
    if commit_trans:
        layer_gdal.StartTransaction()

    new_feat = layer_gdal.CreateFeature(dd_feat)

    if commit_trans:
        layer_gdal.CommitTransaction()

    return new_feat


def drivers_ogr_gdal_disponibles():
    """
    Retorna lista de drivers disponibles a través de la librería osgeo-gdal-ogr

    Returns:
        dict
    """
    cnt = ogr.GetDriverCount()
    driver_list = []
    drivers = OrderedDict()

    for i in range(cnt):
        driver = ogr.GetDriver(i)
        driver_name = driver.GetName()
        driver_list.append(driver_name)

    for driver_name in driver_list:
        # Is File GeoDatabase available?
        drv = ogr.GetDriverByName(driver_name)
        if drv is None:
            print_warning("{} !!ATENTION - driver NOT available!!".format(driver_name))
        else:
            drivers[driver_name] = drv
            print_debug(driver_name)

    return drivers


def drivers_ogr_gdal_vector_file():
    """
    Devuelve diccionario con los driver gdal para fichero vectorial

    Returns:
        dict
    """
    return {nd: d for nd, d in drivers_ogr_gdal_disponibles().items()
            if hasattr(d, "GetMetadata_Dict") and d.GetMetadata_Dict().get('DMD_EXTENSIONS')}


def format_nom_column(nom_col):
    """

    Args:
        nom_col:

    Returns:
        str
    """
    return nom_col.replace(" ", "_")


def namedtuple_layer_gdal(layer_gdal, extract_affix_geom_fld=None):
    """
    Devuelve namedTuple con los campos del layer pasado por parametro

    Args:
        layer_gdal:
        extract_affix_geom_fld (str=None):

    Returns:
        namedtuple: con nombre "gdalFeatDef_{NOM_LAYER}" y con los campos de la layer
    """
    camps_layer = set()
    for fld in fields_layer_gdal(layer_gdal):
        camps_layer.add(format_nom_column(fld.GetNameRef()))

    for nom_geom in geoms_layer_gdal(layer_gdal, extract_affix=extract_affix_geom_fld):
        camps_layer.add(format_nom_column(nom_geom))

    nom_layer = layer_gdal.GetName().upper().split(".")[0].replace("-", "_")
    return namedtuple(f"gdalFeatDef_{nom_layer}", camps_layer)


def feats_layer_ds_gdal(ds_gdal, nom_layer=None, filter_sql=None):
    """
    Itera las features (registros de una layer de gdal) y los devuelve como un namdetuple

    Args:
        ds_gdal: datasource gdal
        nom_layer (str=None): Si no viene informado cogerá la primera layer que encuentre en el datasource
        filter_sql (str=None): Si viene informado se aplicará como filtro sql a la layer seleccionada.
                            Utiliza OGR SQL (vease https://www.gdal.org/ogr_sql.html)

    Returns:
        ogr.Feature, ogr.Geometry, namedtuple_layer_gdal
    """
    if not nom_layer:
        layer_gdal = ds_gdal.GetLayer()
    else:
        layer_gdal = ds_gdal.GetLayerByName(nom_layer)

    if layer_gdal:
        for feat, geom, vals in feats_layer_gdal(layer_gdal, filter_sql=filter_sql):
            yield feat, geom, vals


def feats_layer_gdal(layer_gdal, nom_geom=None, filter_sql=None, extract_affix_geom_fld=PREFFIX_GEOMS_LAYERS_GDAL):
    """
    Itera las features (registros de una layer de gdal) y los devuelve como un namdtuple

    Args:
        layer_gdal (ogr.Layer):
        nom_geom (str=None): Por defecto la geometria activa o principal
        filter_sql (str=None): Si viene informado se aplicará como filtro sql a la layer seleccionada.
                            Utiliza OGR SQL (vease https://www.gdal.org/ogr_sql.html)
        extract_affix_geom_fld (str=SUFFIX_GEOMS_LAYERS_GDAL): Por defecto quita el sufijo 'geom_' a los campos geom

    Returns:
        ogr.Feature, ogr.Geometry, namedtuple_layer_gdal
    """
    layer_gdal.ResetReading()
    ntup_layer = namedtuple_layer_gdal(layer_gdal, extract_affix_geom_fld)
    n_geoms_layer = {nom_geom_feat: fix_affix_geom_name_layer_gdal(nom_geom_feat, layer_gdal, extract_affix_geom_fld)
                     for nom_geom_feat in geoms_layer_gdal(layer_gdal)}

    if filter_sql:
        layer_gdal.SetAttributeFilter(filter_sql)

    def vals_feature_gdal(feat_gdal):
        vals = {}
        for camp, val in feat_gdal.items().items():
            vals[format_nom_column(camp)] = val

        for camp_geom, camp_geom_val in n_geoms_layer.items():
            idx_geom = feat_gdal.GetGeomFieldIndex(camp_geom)
            if idx_geom >= 0:
                vals[camp_geom_val] = feat_gdal.GetGeomFieldRef(idx_geom)

        return vals

    if layer_gdal:
        for f_tab in layer_gdal:
            idx_geom = f_tab.GetGeomFieldIndex(nom_geom) if nom_geom else -1
            yield f_tab, \
                f_tab.GetGeomFieldRef(idx_geom) if idx_geom >= 0 else f_tab.geometry(), \
                ntup_layer(**vals_feature_gdal(f_tab))

        layer_gdal.ResetReading()


def distinct_vals_camp_layer_gdal(layer_gdal, nom_camp, filter_sql=None):
    """
    Devuelve set con distintos valores para el campo indicado del layer GDAL indicada

    Args:
        layer_gdal (ogr.Layer):
        nom_camp (str):
        filter_sql (str=None):

    Returns:
        set
    """
    if nom_camp.upper() not in cols_layer_gdal(layer_gdal):
        raise Exception("Argumento :NOM_CAMP = '{}' erróneo ya que "
                        "LAYER_GDAL no contiene el campo indicado".format(nom_camp))

    return {getattr(nt_feat, nom_camp.upper())
            for feat, geom, nt_feat in feats_layer_gdal(layer_gdal, filter_sql=filter_sql)}


def fields_layer_gdal(layer_gdal):
    """
    Itera sobre los FieldDefn de una layer gdal

    Args:
        layer_gdal:

    Yields:
        osgeo.ogr.FieldDefn
    """
    layer_def = layer_gdal.GetLayerDefn()
    for i in range(0, layer_def.GetFieldCount()):
        yield layer_def.GetFieldDefn(i)

    layer_def = None


def geom_fields_layer_gdal(layer_gdal):
    """
    Itera sobre los GeomFieldDefn de una layer gdal

    Args:
        layer_gdal:

    Yields:
        osgeo.ogr.GeomFieldDefn
    """
    layer_def = layer_gdal.GetLayerDefn()
    for i in range(0, layer_def.GetGeomFieldCount()):
        yield layer_def.GetGeomFieldDefn(i)

    layer_def = None


def nom_layers_datasource_gdal(ds_gdal):
    """

    Args:
        ds_gdal (ogr.Datasource:

    Returns:
        set
    """
    return {l.GetName() for l in ds_gdal}


def cols_layer_gdal(layer_gdal):
    """
    Retorna lista con las columnas de una layer gdal

    Args:
        layer_gdal:

    Returns:
        set
    """
    camps = set()
    for fd in fields_layer_gdal(layer_gdal):
        # camps.add(fd.GetName().upper())
        camps.add(fd.GetNameRef())

    return camps


def geoms_layer_gdal(layer_gdal, extract_affix=None):
    """
    Retorna lista con las columnas geométricas de una layer gdal

    Args:
        layer_gdal:
        extract_affix (str=None=): if informed extract the affix passed

    Returns:
        set
    """
    camps_geom = set()
    for gdf in geom_fields_layer_gdal(layer_gdal):
        # camps_geom.add(gdf.GetName().upper())
        name_ref = gdf.GetNameRef()
        if extract_affix:
            name_ref = fix_affix_geom_name_layer_gdal(name_ref, layer_gdal, extract_affix)
        camps_geom.add(name_ref)

    return camps_geom


def fix_affix_geom_name_layer_gdal(geom_name, layer_gdal, affix=PREFFIX_GEOMS_LAYERS_GDAL):
    """
    Extract affix (default=PREFFIX_GEOMS_LAYERS_GDAL) from name geoms if correspond with other column
    Fix GDAL > 3.4 where geoms on GeoCSV arrive with preffix 'geom_'

    Args:
          geom_name (str):
          layer_gdal:
          affix (str=PREFFIX_GEOMS_LAYERS_GDAL):

    Returns:
        str
    """
    cols_layer = cols_layer_gdal(layer_gdal)
    geom_name_layer = geom_name
    if geom_name.lower().startswith(affix):
        geom_name_aux = re.sub(affix, '', geom_name, flags=re.IGNORECASE)
        if geom_name_aux.lower() in (col.lower() for col in cols_layer):
            geom_name_layer = geom_name_aux

    return geom_name_layer


def add_layer_gdal_to_ds_gdal(ds_gdal, layer_gdal, nom_layer=None, lite=False, srs_epsg_code=None, multi_geom=False,
                              nom_geom=None, null_geoms=False, **extra_opt_list):
    """
    Añade una layer_gdal a un datasource_gdal. Si es una layer con multigeometrias las separa en una layer por geometria

    Args:
        ds_gdal (osgeo.ogr.Datasource):
        layer_gdal (osgeo.ogr.Layer):
        nom_layer (str=None):
        lite (bool=False):
        srs_epsg_code (int=None): codigo EPSG para el sistema de coordenadas con el que se quieren convertir
                                  las geometrias
        nom_geom (str=None): nombre de geometria de layer origen (layer_gdal) que se copiará, si no todas
        multi_geom (bool=False): Si el DS_GDAL destino permite multigeometria
        null_geoms (bool=False): Indica si se admitirán registros con NULL geoms. Por defecto NO
        **extra_opt_list (str): Lista claves-valores de opciones para createLayer del driver de ds_gdal indicado

    Returns:
        new_layers_ds_gdal (list)
    """
    new_layers_ds_gdal = []

    if not nom_layer:
        nom_layer = layer_gdal.GetName()

    geoms_layer = geoms_layer_gdal(layer_gdal)
    if nom_geom:
        if nom_geom.upper() not in (g.upper() for g in geoms_layer):
            Exception("!ERROR! - Nombre de geometria '{}' no existe en la layer GDAL origen")
        else:
            geoms_layer = (nom_geom,)

    if geoms_layer:
        tol = None
        if lite:
            tol = SIMPLIFY_TOLERANCE

        nom_layer_base = nom_layer.split("-")[0]
        if not multi_geom:
            for geom_name in geoms_layer:
                # Fix GDAL > 3.4 where geoms on GeoCSV arrive with preffix 'geom_'
                geom_name_layer = fix_affix_geom_name_layer_gdal(geom_name, layer_gdal)

                nom_layer = "{}-{}".format(nom_layer_base, geom_name_layer).lower()
                extra_opt_list["GEOMETRY_NAME"] = "GEOMETRY_NAME={}".format(geom_name_layer)
                lyr = create_layer_from_layer_gdal_on_ds_gdal(ds_gdal, layer_gdal, nom_layer, geom_name,
                                                              tolerance_simplify=tol, null_geoms=null_geoms,
                                                              epsg_code_dest=srs_epsg_code, **extra_opt_list)
                new_layers_ds_gdal.append(lyr)
        else:
            lyr = create_layer_from_layer_gdal_on_ds_gdal(ds_gdal, layer_gdal, nom_layer, exclude_cols_geoms=False,
                                                          tolerance_simplify=tol, null_geoms=True,
                                                          epsg_code_dest=srs_epsg_code, **extra_opt_list)
            new_layers_ds_gdal.append(lyr)
    else:
        if ds_gdal.GetDriver().GetName() == 'PostgreSQL':
            extra_opt_list.update(dict(
                precision=extra_opt_list.get('precision', 'PRECISION=NO')
            ))

        lyr = copy_layer_gdal_to_ds_gdal(layer_gdal, ds_gdal, nom_layer.lower(), **extra_opt_list)
        new_layers_ds_gdal.append(lyr)

    return new_layers_ds_gdal


def copy_layers_gpkg(ds_gpkg, driver, dir_base, lite=False, srs_epsg_code=None, zipped=True):
    """

    Args:
        ds_gpkg (osgeo.ogr.Datasource):
        driver (str):
        dir_base (str=None):
        lite (bool=False):
        srs_epsg_code (int=None): codigo EPSG para el sistema de coordenadas con el que se quieren convertir
                                  las geometrias
        zipped (bool=False):

    Returns:
        num_layers (int)
    """
    num_layers = 0
    subdir_drvr = os.path.normpath(os.path.join(dir_base, driver.upper()))
    utils.create_dir(subdir_drvr)

    for layer_gpkg in (ds_gpkg.GetLayer(id_lyr) for id_lyr in range(ds_gpkg.GetLayerCount() - 1)):
        if driver == "GPKG":
            nom_ds, ext = utils.split_ext_file(os.path.basename(ds_gpkg.name))
        else:
            nom_ds = f"{layer_gpkg.GetName()}".lower()

        ds_gdal, existia = datasource_gdal_vector_file(driver, nom_ds, subdir_drvr)

        add_layer_gdal_to_ds_gdal(ds_gdal, layer_gpkg, lite=lite, srs_epsg_code=srs_epsg_code)

        num_layers += 1

    return num_layers


def set_csvt_for_layer_csv(path_csv, **tipus_camps):
    """
    Crea/Modifica el CSVT asociado con los tipos indicados para cada columna

    Args:
        path_csv (str):
        **tipus_camps: clave=valor con el nombre del campo y el tipo de campo asociado (p.e. String(25), WKT, Integer,...)

    Returns:
        path_csvt (str)
    """
    lyr_csv, nom_layer, ds_lyr = layer_gdal_from_file(path_csv, "CSV")
    if not lyr_csv:
        print_warning("!ATENCIO! - No s'ha pogut obrir la layer CSV '{}'".format(path_csv))
        return

    path_lyr_csvt = os.path.join(os.path.dirname(path_csv), "{}.csvt".format(nom_layer))
    tips_lyr = {}
    for fld in fields_layer_gdal(lyr_csv):
        tip_fld = fld.GetFieldTypeName(fld.GetType())
        sufix = ""
        w = fld.GetWidth()
        if w:
            sufix = "{}".format(w)
        p = fld.GetPrecision()
        if p:
            sufix += ".{}".format(p)
        if sufix:
            tip_fld += "({})".format(sufix)

        tips_lyr[fld.name.upper()] = tip_fld

    for nom_camp, tip_camp in tipus_camps.items():
        nom_camp = nom_camp.upper()
        if nom_camp not in tips_lyr:
            print_warning("!ATENCIO! - Camp '{}' no existeix sobre la layer CSV '{}'".format(nom_camp, path_csv))
            continue

        tips_lyr[nom_camp] = tip_camp

    with open(path_lyr_csvt, mode="w", encoding="utf8") as f_csvt:
        f_csvt.write(",".join(tips_lyr.values()))


def zip_and_clean_ds_csv(path_csv):
    """
    # Zipea datasource osgeo CSV y como GDAL no crea los tipos WKT para las geometrias en el CSVT se fuerza

    Args:
        path_csv (str): path Datasource osgeo CSV

    Returns:
        zip_path (str)
    """
    ds_gdal_csv, dummy = datasource_gdal_vector_file("CSV", os.path.basename(path_csv).split(".")[0],
                                                     os.path.dirname(path_csv))
    layer_csv = ds_gdal_csv.GetLayer(0)
    tips_geoms = {gn: "WKT" for gn in
                  (*geoms_layer_gdal(layer_csv, extract_affix=PREFFIX_GEOMS_LAYERS_GDAL),
                   *geoms_layer_gdal(layer_csv, extract_affix=PREFFIX_GEOMS_LAYERS_GDAL_CSV))}
    path_csv = ds_gdal_csv.GetDescription()
    ds_gdal_csv = None  # Cerramos el datasource para que se guarden los cambios
    if path_csv and os.path.exists(path_csv):
        if tips_geoms:
            set_csvt_for_layer_csv(path_csv, **tips_geoms)
        rename_wkt_geoms_csv(path_csv)
    dir_base_csv = os.path.dirname(path_csv)
    nom_layer = os.path.basename(path_csv).split(".")[0]
    l_files_csv = [os.path.join(dir_base_csv, nf) for nf in os.listdir(dir_base_csv)
                   if nf.lower().startswith(nom_layer.lower()) and
                   any(nf.lower().endswith(ext) for ext in ('csv', 'csvt'))]
    zip_path = utils.zip_files(os.path.join(dir_base_csv, "{}.zip".format(nom_layer)), l_files_csv)
    if zip_path:
        for fl_csv in l_files_csv:
            os.remove(fl_csv)

    return zip_path


def convert_angle(pt_xy, deg_ang, orig_srs, dest_srs):
    """

    Args:
        pt_xy (tuple):
        deg_ang (float):
        orig_srs (osr.SpatialReference):
        dest_srs (osr.SpatialReference):

    Returns:

    """
    trans = osr.CoordinateTransformation(orig_srs, dest_srs)
    x, y = pt_xy
    dx = math.sin(math.radians(deg_ang)) * 0.00000001
    dy = math.cos(math.radians(deg_ang)) * 0.00000001
    pt1 = ogr.CreateGeometryFromWkt("POINT ({} {})".format(x, y))
    pt2 = ogr.CreateGeometryFromWkt("POINT ({} {})".format(x + dx, y + dy))
    pt1.Transform(trans)
    pt2.Transform(trans)
    x1, y1, z1 = pt1.GetPoint()
    x2, y2, z2 = pt2.GetPoint()

    return math.degrees(math.atan2(y2 - y1, x2 - x1))


def transform_ogr_geom(a_ogr_geom, from_espg_code, to_epsg_code):
    """
    Transforma una geometria OGR según los EPSG indicados

    Args:
        a_ogr_geom (ogr.geometry): una geometria del tipo OGR
        from_espg_code (int): codigo numérico del EPSG actual para la geometria
        to_epsg_code (int): codigo numérico del EPSG al que se quiere transformar

    Returns:
        ogr.geometry
    """
    source = osr.SpatialReference()
    source.ImportFromEPSG(from_espg_code)

    target = osr.SpatialReference()
    target.ImportFromEPSG(to_epsg_code)

    a_transform = osr.CoordinateTransformation(source, target)
    a_ogr_geom.Transform(a_transform)

    return a_ogr_geom


def ds_postgis(dbname='POSTGRES', host='localhost', port='5432', user='postgres', password='postgres', schema='public'):
    """
    Retorna datasource GDAL para ddbb postgis

    Args:
        dbname:
        host:
        port:
        user:
        password:
        schema:

    Returns:
        osgeo.ogr.DataSource
    """
    pg_conn = f"PG:dbname='{dbname}' host='{host}' port='{port}' user='{user}' password='{password}' active_schema='{schema}'"
    drvr, exts = driver_gdal('PostgreSQL')
    return drvr.Open(pg_conn, 1)


def reset_sequence_layer_postgis(ds_postgis, nom_layer):
    """
    Resetea la secuencia de la layer PostGIS indicada

    Args:
        ds_postgis (osgeo.ogr.DataSource): datasource de la ddbb PostGIS:
        nom_layer (str): nombre de la layer PostGIS

    Returns:
        bool: True si se ha reseteado correctamente
    """
    ok = False
    layer_dest = ds_postgis.GetLayerByName(nom_layer)
    fid_column = layer_dest.GetFIDColumn()
    get_seq_sql = f"SELECT pg_get_serial_sequence('{nom_layer}', '{fid_column}') FROM information_schema.columns " \
                  f"WHERE table_name = '{nom_layer}' AND column_default LIKE 'nextval%'"

    if res_get_seq := ds_postgis.ExecuteSQL(get_seq_sql):
        seq_name = res_get_seq.GetNextFeature().GetField(0)
        ds_postgis.StartTransaction()
        reset_seq = f"SELECT setval('{seq_name}', 1, false);"
        ds_postgis.ExecuteSQL(reset_seq)
        ds_postgis.CommitTransaction()
        ok = True

    return ok


if __name__ == '__main__':
    import fire

    fire.Fire()
