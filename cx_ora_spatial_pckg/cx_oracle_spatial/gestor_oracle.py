#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: gestor_oracle.py
#   Created: 05/04/2020, 00:38
#   Last modified: 10/11/2019, 11:24
#   Copyright (c) 2020

import csv
import datetime
from functools import wraps
import inspect
import itertools
import json
import os
import shutil
import sys
from collections import namedtuple, OrderedDict
from subprocess import Popen, PIPE
from tempfile import SpooledTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED

import cx_Oracle
import lxml.etree as etree

from extra_utils import utils_logging
from spatial_utils import topojson_utils
from . import sdo_geom as m_sdo_geom
from extra_utils.sql_parser import x_sql_parser

# Nombres tipo geometria GTYPE oracle por orden valor GTYPE
GTYPES_ORA = ["DEFAULT",
              "POINT",
              "LINE",
              "POLYGON",
              "COLLECTION",
              "MULTIPOINT",
              "MULTILINE",
              "MULTIPOLYGON"]

# Se inicializan tipos de geometria Oracle
__class_tips_geom_ora = {}
for nom_tip in GTYPES_ORA:
    __class_tips_geom_ora[nom_tip] = namedtuple("gtype_" + nom_tip.upper(),
                                                ['TABLE_NAME', 'COLUMN_NAME', 'GTYPE', 'SRID'])


def class_tip_geom(gtype_ora="DEFAULT"):
    """
    Retorna NAMEDTUPLE 'cursor_desc_tip_geom_GTYPE' con columnas
    'TABLE_NAME', 'COLUMN_NAME', 'GTYPE', 'SRID'

    Args:
        gtype_ora: tipo geometrias como claves en __class_tips_geom_ora

    Returns:
        namedtuple('TABLE_NAME', 'COLUMN_NAME', 'GTYPE', 'SRID')

    """
    gtype_ora = gtype_ora.upper()

    if gtype_ora not in __class_tips_geom_ora:
        gtype_ora = "DEFAULT"

    return __class_tips_geom_ora.get(gtype_ora)


# Caches para atributos de tablas_o_vistas de Oracle
__cache_pks_tab = {}
__cache_row_desc_tab = {}
__cache_tips_geom_tab = {}
__cache_row_class_tab = {}


def get_nom_conexion(con_db):
    """
    Devuelve el nombre de la conexion a Oracle

    Args:
        con_db:

    Returns:

    """
    return "@".join((con_db.username.upper(), con_db.dsn.upper()))


def new_cursor(con_db, input_handler=None, output_handler=None):
    """
    Retorna cx_Oracle.Cursor con los handlers pasados por parámetro

    Args:
        con_db:
        input_handler:
        output_handler:

    Returns:
        cx_Oracle.cursor
    """
    try:
        curs = con_db.cursor()

        if input_handler:
            curs.inputtypehandler = input_handler

        if output_handler:
            curs.outputtypehandler = output_handler

        return curs

    except:
        print("!!ERROR!! - Error al instanciar Cursor para la conexion Oracle ".format(get_nom_conexion(con_db)))
        raise


def get_row_descriptor(curs, nom_base_desc=None):
    """
    Retorna instancia namedtuple indexada por las columnas de la query ejecutada en el cursor con los
    tipos de columna por valores.

    Si se pasa nom_base_desc se hará heredar el namedtuple de esa clase

    Args:
        curs:
        nom_base_desc:

    Returns:

    """
    ora_desc = None
    dd_reg = curs.description
    dict_camps = OrderedDict.fromkeys([def_col[0].replace(" ", "_") for def_col in dd_reg])
    if nom_base_desc:
        # Por si viene nombre de tabla con esquema delante nos quedamos solo con la ultima parte
        nom_base_desc = nom_base_desc.split(".")[-1]
        nom_base_desc += "_cursor"
    else:
        nom_base_desc = "cursor_" + str(id(curs))

    try:
        nt_class = namedtuple(nom_base_desc,
                              list(dict_camps))
        ora_desc = nt_class(*[def_cols[1] for def_cols in dd_reg])
    except ValueError:
        raise Exception("!ERROR! - No se puede crear descriptor de fila para el SQL especificado. "
                        "El nombre de la columna {} no es válido".format(str(sys.exc_info()[1]).split(":")[1]),
                        sys.exc_info())

    return ora_desc


def get_row_class_cursor(cursor_desc, con_db):
    """
    Retorna clase de fila por defecto (class row_cursor) para un cursor

    Args:
        cursor_desc: (opcional) clase de la que se quiera heredar
        con_db: conexión cx_Oracle

    Returns:
        class (default = row_cursor)
    """
    cls_curs_dsc = type(cursor_desc)

    class row_cursor(cls_curs_dsc):
        """
        Clase para fila devuelta por query SQL (para queries que NO sean sobre una tabla/vista)
        """
        ora_descriptor = cursor_desc
        con_ora = con_db

        def vals(self):
            """
            Valores de la fila

            Returns:
                OrderedDict
            """
            return self._asdict()

        def as_xml(self,
                   nom_root_xml="root_reg_sql",
                   atts_root_xml=None,
                   excluded_cols=None,
                   as_etree_elem=False):
            """
            Devuelve fila en formato XML

            Args:
                nom_root_xml: define el nombre del TAG root del XML. Por defecto 'root_reg_sql'
                atts_root_xml: lista que define las columnas que se asignarán
                               como atributos del TAG root
                excluded_cols: lista con nombres de columnas que no se quieran incluir
                as_etree_elem (default=False): Si True devuelve registro como objeto etree.Element.
                                              Si False (por defecto) como str en formato XML

            Returns:
                str (formato XML) OR etree.Element
            """
            if not excluded_cols:
                excluded_cols = list()

            atts_xml = None
            d_xml_elems = self.xml_elems()
            if atts_root_xml:
                atts_xml = OrderedDict({att.lower(): d_xml_elems[att.lower()]
                                        for att in atts_root_xml})

            tab_elem = etree.Element(nom_root_xml.lower(), atts_xml)
            excluded_cols = [c.lower() for c in excluded_cols]
            for tag, xml_val in d_xml_elems.items():
                if tag in excluded_cols:
                    continue

                try:
                    camp_elem = etree.SubElement(tab_elem, tag.lower())
                    camp_elem.text = xml_val
                except:
                    print("!ERROR! - No se ha podido añadir el campo '",
                          tag, "' al XML", sep="")

            ret = tab_elem

            if not as_etree_elem:
                ret = etree.tostring(tab_elem, encoding="unicode")

            return ret

        def xml_elems(self):
            """
            Itera los campos del registro y devuelve su nombre y su valor parseado para XML

            Yields:
                n_camp, val_camp
            """
            d_xml_elems = dict()
            for camp, val in self.vals().items():
                ret_val = ""
                if isinstance(val, datetime.datetime):
                    ret_val = val.strftime("%Y-%m-%dT%H:%M:%S")
                elif isinstance(val, m_sdo_geom.sdo_geom):
                    ret_val = val.as_wkt()
                elif val:
                    ret_val = str(val)

                d_xml_elems[camp.lower()] = ret_val

            return d_xml_elems

        def as_json(self):
            """
            Retorna la fila como JSON con las geometrias en formato GeoJson

            Returns:
                str con la fila en formato json
            """
            return json.dumps(self.vals(),
                              ensure_ascii=False,
                              cls=geojson_encoder)

        def as_geojson(self):
            """
            Retorna la fila como GEOJSON

            Returns:
                str con la fila en formato geojson
            """
            return json.dumps(self.__geo_interface__,
                              ensure_ascii=False,
                              cls=geojson_encoder)

        @property
        def __geo_interface__(self):
            """
            GeoJSON-like protocol for geo-spatial para toda una fila devuelta por query SQL

            Si la fila tiene varias geometrias devolverá geojson como "GeometryCollection"

            Returns:
                dict con las geometrias y campos alfanuméricos (properties de Feature) en formato geojson
            """
            geos = dict(**self.sdo_geoms)
            num_geos = len(geos)
            geom = None
            if num_geos == 1:
                geom = next(iter(geos.values()))
            elif num_geos > 1:
                geom = {"type": "GeometryCollection",
                        "geometries": list(geos.values())}

            if geom:
                return dict({"type": "Feature",
                             "geometry": geom,
                             "properties": {nc: val for nc, val in self.vals().items() if nc not in geos}})

        @property
        def sdo_geoms(self):
            """
            Devuelve diccionario indexado por los nombres de columnas que tienen valor geometrico de la clase sdo_geom

            Returns:
                dict {nom_column:sdo_geom}
            """
            return {nc: g.__geo_interface__
                    for nc, g in self.vals().items() if isinstance(g, m_sdo_geom.sdo_geom)}

        def geometries(self, as_format=None):
            """
            Itera por los campos geométricos informados

            Args:
                as_format (default=None): Se puede informar con nombre funcion 'as_XXXX' a la que responda SDO_GEOM

            Yields:
                nom_camp, geom
            """
            for ng, g in self.vals().items():
                if isinstance(g, m_sdo_geom.sdo_geom):
                    g_val = g
                    if as_format:
                        g_val = getattr(g, as_format)()

                    yield ng, g_val

        @property
        def cols_pts_angles(self):
            """
            Devuelve diccionario de campos angulo para geometrias puntuales con la clave el nombre del campo angulo y
            el valor el nombre del campo puntual al que hace referencia

            Returns:
                dict
            """
            sufix_ang = "_ANG"
            cols = self.cols
            cols_ang = {}
            for c in (c for c, gd in self.geoms_vals().items() if gd.GTYPE.endswith('POINT')):
                col_ang = x_sql_parser.get_nom_obj_sql(c, sufix=sufix_ang)
                if col_ang in cols:
                    cols_ang[col_ang] = c

            return cols_ang

        @property
        def cols(self):
            """
            Devuelve lista con el nombre de la columnas de la fila

            Returns:
                list con nombres columnas
            """
            return self._fields

    return row_cursor


def get_pk_tab(con_db, nom_tab_or_view):
    """
    Retorna la PRIMARY KEY de una tabla o vista de Oracle

    Args:
        con_db:
        nom_tab_or_view:

    Returns:
        lista nombre columnas clave
    """
    nom_pk_cache = get_nom_conexion(con_db) + ":" + nom_tab_or_view.upper()
    noms_camps_pk = __cache_pks_tab.get(nom_pk_cache)
    if not noms_camps_pk:
        sql_keys = "SELECT cols.column_name " \
                   "FROM user_constraints cons, user_cons_columns cols " \
                   "WHERE cols.table_name = :1 " \
                   "AND cons.constraint_type = 'P' " \
                   "AND cons.constraint_name = cols.constraint_name " \
                   "AND cons.owner = cols.owner " \
                   "ORDER BY cols.table_name, cols.position"

        noms_camps_pk = [fila_val.COLUMN_NAME for fila_val in
                         iter_execute_fetch_sql(con_db, sql_keys, nom_tab_or_view.upper())]
        __cache_pks_tab[nom_pk_cache] = noms_camps_pk

    return noms_camps_pk


def get_tips_geom_tab(con_db, nom_tab_or_view):
    """
    Retorna diccionario con nombre del campo como indice y los tipos de campos geométricos
    (class_tip_geom) registrados en la global __class_tips_geom_ora como clases 'c_desc_tip_geom_?' siendo ?
    el LAYER_GTYPE del indice de Oracle

    Args:
        con_db:
        nom_tab_or_view:

    Returns:
        dict indexado por nombre columnas geometria y la clase de geometria (__class_tips_geom_ora)
    """
    nom_con = get_nom_conexion(con_db)

    tips_geom_con = __cache_tips_geom_tab.get(nom_con)
    if not tips_geom_con:
        tips_geom_con = __cache_tips_geom_tab[nom_con] = {}
        sql_tip_geom = "select  /*+ result_cache */ " \
                       "        T_COLS.TABLE_NAME, " \
                       "        T_COLS.COLUMN_NAME, " \
                       "        V_IDX_META.SDO_LAYER_GTYPE GTYPE, " \
                       "        V_G_META.SRID " \
                       "from    user_tab_columns t_cols," \
                       "        user_sdo_geom_metadata v_g_meta," \
                       "        user_sdo_index_info v_idx_info," \
                       "        user_sdo_index_metadata v_idx_meta " \
                       "where v_g_meta.table_name = t_cols.table_name and " \
                       "v_g_meta.column_name = t_cols.column_name and" \
                       "    v_idx_info.table_name = t_cols.table_name and " \
                       "v_idx_info.column_name = t_cols.column_name and" \
                       "    v_idx_meta.sdo_index_name = v_idx_info.index_name"

        for reg_tip_geom in iter_execute_fetch_sql(con_db, sql_tip_geom):
            nom_cache = reg_tip_geom.TABLE_NAME.upper()
            cache_tips_geom = tips_geom_con.get(nom_cache)
            if not cache_tips_geom:
                cache_tips_geom = {}
                tips_geom_con[nom_cache] = cache_tips_geom

            tip_geom = class_tip_geom(reg_tip_geom.GTYPE)(*reg_tip_geom.vals().values())

            nom_camp_geom = reg_tip_geom.COLUMN_NAME.upper()
            cache_tips_geom[nom_camp_geom] = tip_geom

    tips_geom = tips_geom_con.get(nom_tab_or_view.upper())

    return tips_geom if tips_geom else {}


def get_row_desc_tab(con_db, nom_tab_or_view):
    """
    Retorna el descriptor (cursor con los tipos de campo para cada columna) de una tabla o vista de Oracle

    Args:
        con_db:
        nom_tab_or_view:

    Returns:
        namedtuple ó clase fila con las columnas y sus tipos
    """
    nom_dd_cache = get_nom_conexion(con_db) + ":" + nom_tab_or_view.upper()
    tab_desc = __cache_row_desc_tab.get(nom_dd_cache)
    if not tab_desc:
        row_class_tab = get_row_class_tab(con_db, nom_tab_or_view)

        camps_dd = row_class_tab.ora_descriptor
        dict_camps = camps_dd._asdict()
        dict_camps_geom = row_class_tab.geoms()
        if dict_camps_geom:
            for nom_camp, tip_camp_geom in dict_camps_geom.items():
                dict_camps[nom_camp] = tip_camp_geom

        tab_desc = row_class_tab(*dict_camps.values())
        __cache_row_desc_tab[nom_dd_cache] = tab_desc

    return tab_desc


def get_tip_camp(con_db, nom_tab_or_view, nom_camp):
    """
    Devuelve el tipo de campo para la tabla_vista y campo especificado. En el caso de campos alfanuméricos
    devuelve los tipos de cx_Oracle relacionados (cx_Oracle.NUMBER, cx_Oracle.STRING, ...) y para las
    geométricas del tipo CLASS_TIP_GEOM

    Args:
        con_db:
        nom_tab_or_view:
        nom_camp:

    Returns:
        object: (cx_Oracle.NUMBER, cx_Oracle.STRING, ...) o si geometria tipo en __class_tips_geom_ora
    """
    nom_tab_or_view = nom_tab_or_view.upper()
    nom_camp = nom_camp.upper()

    dd_tab = get_row_desc_tab(con_db, nom_tab_or_view)
    if dd_tab:
        return getattr(dd_tab, nom_camp, None)


def sql_tab(nom_tab_or_view, filter_sql=None, columns=None):
    """
    Devuelve sql para tabla o vista

    Args:
        nom_tab_or_view:
        filter_sql:
        columns (list): Lista nombre de columnas a mostrar. Default '*' (todas)

    Returns:
        str: con select sql para tabla o vista
    """
    cols = "*"
    if columns:
        cols = ",".join(columns)

    sql_tab = "select {cols} from {taula} TAB".format(
        taula=nom_tab_or_view,
        cols=cols)

    if filter_sql:
        sql_tab += " where " + filter_sql

    return sql_tab


def get_row_class_tab(con_db, nom_tab_or_view):
    """
    Retorna clase que hereda de namedtuple para instanciar con los valores de un nuevo registro

    Args:
        con_db:
        nom_tab_or_view:

    Returns:
        object: clase que hereda del namedtuple para una fila
    """
    nom_tab_or_view = nom_tab_or_view.upper()
    nom_row_class_tab_cache = get_nom_conexion(con_db) + ":" + nom_tab_or_view
    row_class_tab = __cache_row_class_tab.get(nom_row_class_tab_cache)

    if not row_class_tab:
        curs = con_db.cursor()
        curs.execute(sql_tab(nom_tab_or_view))
        ora_desc = get_row_descriptor(curs, nom_tab_or_view)

        row_cursor_cls = get_row_class_cursor(ora_desc, con_db)

        class row_table(row_cursor_cls):
            """
            Clase para fila devuelta por SQL sobre tabla
            """
            nom_tab = nom_tab_or_view

            def __repr__(self):
                """
                built_in que actua cuando se representa clase como STRING

                Returns:
                    str
                """
                repr_txt = nom_tab_or_view + "({pk_vals})"
                pk_txt = []
                for i, v in self.pk_vals().items():
                    pk_txt.append(str(i) + "=" + str(v))

                return repr_txt.format(pk_vals=",".join(pk_txt))

            @staticmethod
            def pk():
                """
                Retorna lista con los nombres de campos clave

                Returns:
                    list con nombres campos clave
                """
                return get_pk_tab(con_db, nom_tab_or_view)

            def pk_vals(self):
                """
                Retorna OrderedDict con los pares nombres:valor para los campos clave

                Returns:
                    OrderedDict
                """
                pk_vals = OrderedDict.fromkeys(self.pk())
                for k in self.pk():
                    pk_vals[k] = self.vals().get(k)

                return pk_vals

            @staticmethod
            def geoms():
                """
                Devuelve diccionario {nom_camp_geom:tip_geom} para todas las columnas de la tabla que son de
                tipo geométrico.
                Lo deduce de la definición de la tabla independientemente de si la columna está informada o no

                Returns:
                    dict {nom_geom:tip_geom} (vease funcion clas_tip_geom())
                """
                return get_tips_geom_tab(con_db, nom_tab_or_view)

            def geoms_vals(self):
                """
                Valores de los campos geometricos

                Returns:
                    dict
                """
                vals = self.vals()
                return {nc: vals[nc] for nc in self.geoms()}

            def as_xml(self, excluded_cols=[],
                       as_etree_elem=False):
                """
                Devuelve row como XML

                Args:
                    excluded_cols: lista de nombre de columnas que se quieren excluir
                    as_etree_elem {bool} (default=False): Si True devuelve registro como objeto etree.Element. Si False (por defecto) como str en formato XML

                Returns:
                    str (formato XML) OR etree.Element
                """
                return super(row_table, self).as_xml(nom_tab_or_view,
                                                     self.pk_vals(),
                                                     excluded_cols,
                                                     as_etree_elem)

            @staticmethod
            def get_row_desc():
                return get_row_desc_tab(con_db, nom_tab_or_view)

            @staticmethod
            def alfas(include_pk=True):
                """
                Devuelve diccionario {nom_camp:tip_camp} para las columnas alfanuméricas (NO son geométricas)
                Lo deduce de la definición de la tabla independientemente de si la columna está informada o no

                Args:
                    include_pk: incluir primary key

                Returns:
                    dict {nom_camp:tip_camp}
                """
                return {nc: tc
                        for nc, tc in get_row_desc_tab(con_db, nom_tab_or_view).vals().items()
                        if nc not in get_tips_geom_tab(con_db, nom_tab_or_view) and
                        (include_pk or nc not in get_pk_tab(con_db, nom_tab_or_view))}

            def alfas_vals(self):
                """
                Devuelve diccionario con valores campos alfanuméricos

                Returns:
                    dict {nom_camp:val_camp}
                """
                vals = self.vals()
                return {nc: vals[nc] for nc in self.alfas()}

        row_class_tab = row_table
        __cache_row_class_tab[nom_row_class_tab_cache] = row_class_tab

    return row_class_tab


def get_row_factory(curs, a_row_class=None):
    """
    Retorna funcion para crear instancia clase a partir de los valores de una fila

    Args:
        curs:
        a_row_class:

    Returns:
        function
    """
    if not a_row_class:
        cursor_desc = get_row_descriptor(curs)
        con_db = curs.connection
        a_row_class = get_row_class_cursor(cursor_desc, con_db)

    def row_factory_func(*vals_camps):
        return a_row_class(*vals_camps)

    return row_factory_func


def get_row_cursor(curs, rowfactory=None):
    """
    Retorna fila como clase que construye el rowfactory. Por defecto si no se informa esta clase heredará
    de 'namedtuple' con los campos como items más funcionalidad relacionada con la conexion y el descriptor de la fila
    con los tipos de campo para cada columna

    Args:
        curs:
        rowfactory:

    Returns:

    """
    if not rowfactory and not curs.rowfactory:
        rowfactory = get_row_factory(curs)

    if rowfactory:
        curs.rowfactory = rowfactory

    row = curs.fetchone()

    return row


def iter_execute_fetch_sql(con_db, sql_str, *args_sql, **extra_params):
    """
    Itera y devuelve cada fila devuelta para la consulta sql_str

    Args:
        con_db:
        sql_str:
        *args_sql:
        **extra_params: { "row_class": clase que se utilizará para cada fila. Vease get_row_factory()
                          "as_format": formato en el que se devuelve cada fila. Las clases base row_cursor y row_table
                                    (vease get_row_class_cursor() y get_row_class_tab()) responden por defecto a
                                    "as_xml()" y "as_json()" }

    Returns:
        row_class o string en formato especificado en **extra_params["as_format"]
    """
    curs = None

    try:
        curs = new_cursor(con_db,
                          input_handler=extra_params.pop("input_handler",
                                                         m_sdo_geom.get_sdo_input_handler()),
                          output_handler=extra_params.pop("output_handler",
                                                          m_sdo_geom.get_output_handler(
                                                              con_db,
                                                              extra_params.pop("geom_format", None))))

        curs.execute(sql_str,
                     args_sql)

        row_class = extra_params.pop("row_class", None)
        row_factory = None
        if row_class:
            row_factory = get_row_factory(curs, row_class)

        reg = get_row_cursor(curs, rowfactory=row_factory)
        while reg is not None:
            if "as_format" in extra_params:
                f_format = extra_params["as_format"]
                if f_format:
                    reg = getattr(reg, f_format)()

            yield reg

            reg = get_row_cursor(curs)

    except:
        if curs is not None:
            curs.close()
        raise

    if curs is not None:
        curs.close()


def execute_fetch_sql(con_db, sql_str, *args_sql, **extra_params):
    """
    Devuelve la primera iteración sobre la consulta sql_str

    Args:
        con_db:
        sql_str:
        *args_sql:
        **extra_params: { "row_class": clase que se utilizará para cada fila. Vease get_row_factory()
                          "as_format": formato en el que se devuelve cada fila. Las clases base row_cursor y row_table
                                    (vease get_row_class_cursor() y get_row_class_tab()) responden por defecto a
                                    "as_xml()" y "as_json()" }

    Returns:
        row_class o string en formato especificado en **extra_params["as_format"]
    """
    reg = None
    for row in iter_execute_fetch_sql(con_db,
                                      sql_str,
                                      *args_sql,
                                      input_handler=extra_params.pop("input_handler", None),
                                      output_handler=extra_params.pop("output_handler", None),
                                      row_class=extra_params.pop("row_class", None),
                                      **extra_params):
        reg = row
        break

    return reg


def dict_as_sql_bind_and_params(dict_vals, bool_rel="and", filter_oper="="):
    """
    A partir de un dict de {nom_camps:value_camps} devuelve un string en forma
    de SQL FILTER bindind (camp_a = :1 and camp_b = :2) y la lista de params que se asignarán via binding
    El BOOL_REL podrá ser 'AND', 'OR' o ',' para el SET de los updates
    El FILTER_OPER podrá ser '=', '!=' o ':=' para el SET de los updates

    Args:
        dict_vals:
        bool_rel:
        filter_oper:

    Returns:
        str, [params*]
    """
    query_elems = {}
    for nom_camp, val_clau in dict_vals.items():
        sql_str = str(nom_camp) + " " + filter_oper + " :" + str(nom_camp)
        query_elems[sql_str] = val_clau

    sql = (" " + bool_rel.strip().upper() + " ").join(query_elems.keys())

    return sql, list(query_elems.values())


class SerializableGenerator(list):
    """Generator that is serializable by JSON

    It is useful for serializing huge data by JSON
    It can be used in a generator of json chunks used e.g. for a stream
    ('[1', ']')
    # >>> for chunk in iter_json:
    # ...     stream.write(chunk)
    # >>> SerializableGenerator((x for x in range(3)))
    # [<generator object <genexpr> at 0x7f858b5180f8>]
    """

    def __init__(self, iterable):
        super().__init__()
        tmp_body = iter(iterable)
        try:
            self._head = iter([next(tmp_body)])
            self.append(tmp_body)
        except StopIteration:
            self._head = []

    def __iter__(self):
        return itertools.chain(self._head, *self[:1])


def geojson_from_gen_ora_sql(generator_sql, as_string=False):
    """
    Devuelve diccionario geojson para un generator de rows de Oracle

    Args:
        generator_sql (function generator):
        as_string (bool): (opcional) indica si se querrá el geojson como un string

    Returns:
        geojson (dict ó str)
    """
    vals = {"type": "FeatureCollection",
            "features": [getattr(r, "__geo_interface__")
                         for r in generator_sql
                         if getattr(r, "__geo_interface__")]}

    ret = vals
    if as_string:
        ret = json.dumps(vals,
                         ensure_ascii=False)

    return ret


def vector_file_from_gen_ora_sql(file_path, vector_format, func_gen, zipped=False, indent_json=None, cols_csv=None,
                                 tip_cols_csv=None):
    """
    A partir del resultado de una query SQL devuelve un file_object formateado segun formato

    Args:
        file_path (str): path del fichero a grabar
        vector_format (str): tipo formato (CSV, JSON, GEOJSON)
        func_gen (generator function): funcion que devuelva filas sql en forma de row_cursor o row_table
                                      (vease funciones generator_rows_sql() o generator_rows_table())
        zipped (bool=False): Devuelve fichero en un fichero comprimido (.zip)
        indent_json (int):
        cols_csv (list): Lista de columnes del CSV
        tip_cols_csv (list): Lista de tipos de columnas para CSV.
                             Revisar especificacion en https://giswiki.hsr.ch/GeoCSV
    Returns:
        str: pathfile del fichero generado
    """
    vector_format = vector_format.lower()
    newline = None if vector_format != "csv" else ""
    file_path_csvt = None
    str_csvt = None
    dir_base = os.path.dirname(file_path)
    if dir_base:
        os.makedirs(dir_base, exist_ok=True)

    # Se hace en memoria o recursos locales (SpooledTemporaryFile) para evitar trabajar lo minimo en la red
    # si se da el caso en el path fichero del fichero indicado. Cuando se quiere grabar en recurso local el tiempo
    # perdido por utilizar un fichero temporal debería ser despreciable comparado con la complejidad añadida al código
    # para decidir si usar o no el SpooledTemporaryFile
    with SpooledTemporaryFile(mode="w+", encoding="utf-8", newline=newline) as temp_file:
        if vector_format == "geojson":
            json.dump(geojson_from_gen_ora_sql(func_gen),
                      temp_file,
                      ensure_ascii=False,
                      indent=indent_json,
                      cls=geojson_encoder)
        elif vector_format == "json":
            json.dump(SerializableGenerator((r.vals() for r in func_gen)),
                      temp_file,
                      ensure_ascii=False,
                      indent=indent_json,
                      cls=geojson_encoder)
        elif vector_format == "csv":
            writer = csv.DictWriter(temp_file, fieldnames=cols_csv)
            writer.writeheader()

            for r in func_gen:
                writer.writerow(r.vals())

        temp_file.seek(0)
        if tip_cols_csv:
            file_path_csvt = ".".join((os.path.splitext(file_path)[0], "csvt"))
            str_csvt = ",".join(tip_cols_csv)

        if zipped:
            file_path_res = "{}.zip".format(os.path.splitext(file_path)[0])
            with SpooledTemporaryFile() as zip_temp_file:
                with ZipFile(zip_temp_file, "w", compression=ZIP_DEFLATED, allowZip64=True) as my_temp_zip:
                    my_temp_zip.writestr(zinfo_or_arcname=os.path.basename(file_path), data=temp_file.read())
                    if str_csvt:
                        my_temp_zip.writestr(zinfo_or_arcname=os.path.basename(file_path_csvt), data=str_csvt)

                zip_temp_file.seek(0)
                with open(file_path_res, mode="wb") as file_res:
                    shutil.copyfileobj(zip_temp_file, file_res)
        else:
            file_path_res = file_path
            with open(file_path_res, mode="w", encoding="utf-8") as file_res:
                shutil.copyfileobj(temp_file, file_res)
            if str_csvt:
                with open(file_path_csvt, mode="w") as csvt_file:
                    csvt_file.write(str_csvt)

    return file_path_res


class geojson_encoder(json.JSONEncoder):
    """
    Class Encoder to parser SDO_GEOM to GEOJSON
    """
    __num_decs__ = 9

    def default(self, obj_val):
        """
        Redefine default para tratar las geometrias SDO_GEOM y convertirlas a geojson y las fechas a iso_format
        Args:
            obj_val: valor

        Returns:
            object encoded
        """
        if isinstance(obj_val, m_sdo_geom.sdo_geom):
            return obj_val.as_geojson()
        elif isinstance(obj_val, (datetime.datetime, datetime.date)):
            return obj_val.isoformat()
        elif isinstance(obj_val, cx_Oracle.LOB):
            return obj_val.read()
        else:
            return json.JSONEncoder.default(self, obj_val)


def print_to_log_exception(a_type_exc=Exception, lanzar_exc=False):
    """
    Decorator para imprimir en el log una excepción capturada por un metodo de la clase

    Returns:
        function
    """

    def decor_print_log_exception(func):
        @wraps(func)
        def meth_wrapper(cls, *args, **kwargs):
            try:
                return func(cls, *args, **kwargs)
            except a_type_exc:
                error_type, error_instance, traceback = sys.exc_info()

                error_msg = "Error al executar funció '{clas}.{func}()' \n" \
                            "Arguments: {args}\n" \
                            "Fitxer:    {file}".format(
                    file=inspect.getmodule(func).__file__,
                    clas=cls.__class__.__name__,
                    func=func.__name__,
                    args=", ".join(["'{}'".format(arg) for arg in args] +
                                   ["'{}={}'".format(a, b) for a, b in kwargs.items()]))

                if hasattr(error_instance, "output"):
                    error_msg += "\n" \
                                 "Output: {}".format(error_instance.output)

                cls.print_log_exception(error_msg)
                if lanzar_exc:
                    raise error_instance

        return meth_wrapper

    return decor_print_log_exception


class gestor_oracle(object):
    """
    Clase que gestionará distintas conexiones a Oracle y facilitará operaciones sobre la BBDD
    """
    tip_number = cx_Oracle.NUMBER
    tip_string = cx_Oracle.STRING
    tip_clob = cx_Oracle.CLOB
    tip_blob = cx_Oracle.BLOB
    tip_date = cx_Oracle.DATETIME
    tip_fix_char = cx_Oracle.FIXED_CHAR

    __slots__ = 'nom_con_db', 'con_db', 'psw_con_db', 'logger'

    def __init__(self, user_ora, psw_ora, dsn_ora, a_logger=None):
        """
        Inicializa gestor de Oracle para una conexion cx_Oracle a Oracle
        Se puede pasar por parametro un logger o inicializar por defecto

        Args:
            user_ora {str}: Usuario/schema Oracle
            psw_ora {str}: Password usuario
            dsn_ora {str}: DSN Oracle (Nombre instancia/datasource de Oracle
                    según TSN o string tal cual devuelve cx_Oracle.makedsn())
            a_logger:
        """
        self.logger = a_logger
        self.__set_logger()
        self.__set_conexion(user_ora, psw_ora, dsn_ora)

    def __del__(self):
        """
        Cierra la conexion al matar la instancia
        """
        try:
            if hasattr(self, "con_db"):
                self.con_db.close()
        except:
            pass

    def __repr__(self):
        """
        built_in que actua cuando se representa clase como STRING

        Returns:
            str
        """
        repr_txt = "{}".format(self.nom_con_db)

        return repr_txt

    @staticmethod
    def log_dir():
        """
        Devuelve el directorio donde irán los logs indicado en la funcion apb_logging.logs_dir()

        Returns:
            {str} - path del directorio de logs
        """
        return utils_logging.logs_dir(True)

    def log_name(self):
        """
        Devuelve el nombre del fichero de log por defecto

        Returns:
            {str} - Nombre fichero log por defecto
        """
        return self.__class__.__name__

    def log_file_name(self):
        return "{}.(LOG_LEVEL).log".format(os.path.join(self.log_dir(), self.log_name()))

    def __set_logger(self):
        """
        Asigna el LOGGER po defecto si este no se ha informado al inicializar el gestor

        Returns:
        """
        if self.logger is None:
            self.logger = utils_logging.get_file_logger(self.log_name(), dir_log=self.log_dir())

    def path_logs(self, if_exist=True):
        """
        Devuelve lista paths base de los logs vinculados al gestor

        Args:
            if_exist (bool): Devuelve los paths si el fichero existe

        Returns:
            list:
        """
        path_logs = []
        if self.logger:
            for fn in [hdlr.baseFilename
                       for hdlr in self.logger.handlers if hasattr(hdlr, "baseFilename")]:
                if not if_exist or os.path.exists(fn):
                    path_logs.append(fn)

        return path_logs

    def print_log(self, msg):
        """
        Sobre el logger escribe mensaje de info

        Args:
            msg {str}: String con el mensaje
        """
        self.logger.info(msg)

    def print_log_error(self, msg):
        """
        Sobre el logger escribe mensaje de error

        Args:
            msg {str}: String con el mensaje
        """
        self.logger.error(msg)

    def print_log_exception(self, msg):
        """
        Sobre el logger escribe excepcion

        Args:
            msg {str}: String con el mensaje
        """
        self.logger.exception(msg)

    @print_to_log_exception(lanzar_exc=True)
    def __set_conexion(self, user_ora, psw_ora, dsn_ora):
        """
        Añade conexion Oracle al gestor a partir de nombre de usuario/schema (user_ora), contraseña (psw_ora) y
        nombre datasource de la bbdd según tns_names (ds_ora).

        La conexión quedará registrada como 'user_ora@ds_ora'

        Args:
            user_ora {str}: Usuario/schema Oracle
            psw_ora {str}: Password usuario
            dsn_ora {str}: DSN Oracle (Nombre instancia/datasource de Oracle según TSN o string tal cual devuelve cx_Oracle.makedsn())

        """
        nom_con = "@".join((user_ora.upper(), dsn_ora.upper()))
        self.nom_con_db = nom_con
        self.con_db = cx_Oracle.Connection(user_ora, psw_ora, dsn_ora, encoding="UTF-8", nencoding="UTF-8")
        self.psw_con_db = psw_ora

    @print_to_log_exception(cx_Oracle.DatabaseError)
    def exec_trans_db(self, sql_str, *args_sql, **types_sql_args):
        """
        Ejecuta transaccion SQL

        Args:
            sql_str (str): sql transaction (update, insert, delete}
            *args_sql: Lista argumentos a pasar
            **types_sql_args (OPCIONAL): Lista tipos cx_Oracle para cada argumento

        Returns:
            ok {bool}: Si ha ido bien True si no False
        """
        curs_db = None
        try:
            curs_db = new_cursor(self.con_db,
                                 input_handler=m_sdo_geom.get_sdo_input_handler())

            curs_db.setinputsizes(*types_sql_args.values())

            curs_db.execute(sql_str,
                            args_sql)
        finally:
            if curs_db:
                curs_db.close()

        return True

    @print_to_log_exception(cx_Oracle.DatabaseError)
    def exec_script_plsql(self, sql_str):
        """
        Ejecuta script SQL

        Args:
            sql_str {str}: sql script

        Returns:
            ok {bool}: Si ha ido bien True si no False
        """
        curs_db = None
        try:
            curs_db = new_cursor(self.con_db)
            curs_db.execute(sql_str)
        finally:
            if curs_db:
                curs_db.close()

        return True

    @print_to_log_exception(cx_Oracle.DatabaseError)
    def callfunc_sql(self, nom_func, ret_cx_ora_tipo, *args_func):
        """
        Ejecuta funcion PL/SQL y retorna el valor

        Args:
            nom_func (str): Nombre de la funcion PL/SQL
            ret_cx_ora_tipo (cx_Oracle TIPO): El retorno de la función en cx_Oracle (cx_Oracle.NUMBER,
                                            cx_Oracle.STRING,...)
            *args_func: Argumentos de la funcion PL/SQL

        Returns:
            Valor retornado por la función PL/SQL
        """
        curs = None
        try:
            curs = new_cursor(self.con_db)
            ret = curs.callfunc(nom_func,
                                ret_cx_ora_tipo,
                                args_func)
        finally:
            if curs:
                curs.close()

        return ret

    @print_to_log_exception(cx_Oracle.DatabaseError)
    def callproc_sql(self, nom_proc, *args_proc):
        """
        Ejecuta procedimiento PL/SQL

        Args:
            nom_proc (str): Nombre del procedimiento PL/SQL
            *args_proc: Argumentos del procedimiento

        Returns:
            ok {bool}: Si ha ido bien True si no False
        """
        curs = None
        try:
            curs = new_cursor(self.con_db)
            curs.callproc(nom_proc,
                          args_proc)
        finally:
            if curs:
                curs.close()

        return True

    @print_to_log_exception(cx_Oracle.DatabaseError)
    def row_sql(self, sql_str, *args_sql, **extra_params):
        """
        Retorna la fila resultante de la query sql SQL_STR con los parámetros *ARGS_SQL.
        Se puede informar **EXTRA_PARAMS con algunos de los siguientes parámetros:
            INPUT_HANDLER funcion que tratará los bindings de manera específica
            OUTPUT_HANLER funcion que tratará los valores de las columnas de modo específico
            ROW_CLASS define que con que clase se devolverá cada fila. Por defecto la que devuleve la funcion
                      'cx_oracle_spatial.get_row_class_cursor()'
            AS_FORMAT (as_xml, as_json, as_geojson) devuelve fila en el formato especificado. La row_class deberá
                        responder a esas funciones

        Args:
            sql_str:
            *args_sql:
            **extra_params:

        Returns:
            object (instancia que debería ser o heredar de las clases row_cursor o row_table)
        """
        return execute_fetch_sql(self.con_db,
                                 sql_str,
                                 *args_sql,
                                 input_handler=extra_params.pop("input_handler", None),
                                 output_handler=extra_params.pop(
                                     "output_handler",
                                     m_sdo_geom.get_output_handler(self.con_db,
                                                                   extra_params.pop("geom_format", None))),
                                 row_class=extra_params.pop("row_class", None),
                                 **extra_params)

    @print_to_log_exception(cx_Oracle.DatabaseError)
    def generator_rows_sql(self, sql_str, *args_sql, **extra_params):
        """
        Ejecuta consulta SQL de forma iterativa retornando cada fila como un objeto row_class (por defecto row_cursor)

        Se puede informar **EXTRA_PARAMS con algunos de los siguientes parámetros:
            INPUT_HANDLER funcion que tratará los bindings de manera específica
            OUTPUT_HANLER funcion que tratará los valores de las columnas de modo específico
            ROW_CLASS define que con que clase se devolverá cada fila. Por defecto la que devuleve la funcion
                      'cx_oracle_spatial.get_row_class_cursor()'
            AS_FORMAT (as_xml, as_json, as_geojson) devuelve fila en el formato especificado. La row_class deberá
                        responder a esas funciones

        Args:
            sql_str:
            *args_sql:
            **extra_params:

        Returns:
            object (instancia que debería ser o heredar de las clases row_cursor o row_table)
        """
        for reg in iter_execute_fetch_sql(self.con_db,
                                          sql_str,
                                          *args_sql,
                                          input_handler=extra_params.pop("input_handler", None),
                                          output_handler=extra_params.pop(
                                              "output_handler",
                                              m_sdo_geom.get_output_handler(self.con_db,
                                                                            extra_params.pop("geom_format", None))),
                                          row_class=extra_params.pop("row_class", None),
                                          **extra_params):
            yield reg

    def rows_sql(self, sql_str, *args_sql):
        """
        Vease funcion 'generator_rows_sql()'
        Args:
            sql_str:
            *args_sql:

        Returns:
            list
        """
        return list(self.generator_rows_sql(sql_str, *args_sql))

    def get_primary_key_table(self, nom_tab_or_view):
        """
        Retorna lista con las columnas que conforman la primary key de una tabla/vista
        Args:
            nom_tab_or_view:

        Returns:
            list con campos clave
        """
        return get_pk_tab(self.con_db, nom_tab_or_view)

    @print_to_log_exception(lanzar_exc=True)
    def get_dd_table(self, nom_tab_or_view):
        """
        Retorna instancia row_table con los tipos para cada columna
        Args:
            nom_tab_or_view:

        Returns:
            object de clase row_table con los tipos de cada columna como valores
        """
        return get_row_desc_tab(self.con_db, nom_tab_or_view)

    def generator_rows_table(self, nom_tab_or_view, filter_sql=None, *args_filter_sql, **extra_params):
        """
        Retorna los registros que cumplan con el FILTER_SQL sobre la tabla o vista indicada.

        La tabla se puede referenciar en el filtro con el alias 'TAB'

        Si el FILTER_SQL utiliza valores por binding (:1, :2,...) estos se indicaran por orden en ARGS_FILTER_SQL

        Args:
            nom_tab_or_view: Nombre de la tabla o vista sobre la que se hará la consulta
            filter_sql: Filtre sobre la taula
            args_filter_sql: Valors en ordre de binding per passar
            extra_params: Vease generator_rows_sql()

        Yields:
             row_table: regs. clase row_table (mirar get_row_class_tab())
        """
        for reg in self.generator_rows_sql(sql_tab(nom_tab_or_view,
                                                   filter_sql),
                                           *args_filter_sql,
                                           row_class=extra_params.pop(
                                               "row_class",
                                               get_row_class_tab(self.con_db, nom_tab_or_view)),
                                           **extra_params):
            yield reg

    def generator_rows_interact_geom(self, nom_tab, a_sdo_geom, cols_geom=None, geom_format=None):
        """
        Retorna las filas de una tabla que interactuan con una geometria

        Args:
            nom_tab: nombre de la tabla
            a_sdo_geom: geometria clase sdo_geom
            cols_geom (default=None): Lista con nombre de columnas geométricas sobre las que se quiere aplicar filtro
            geom_format:
        Yields:
            row_table: regs. clase row_table (mirar get_row_class_tab())
        """
        # Uso de " <>'FALSE'" por fallo de Oracle usando "= 'TRUE'"
        filter_interact_base = "SDO_ANYINTERACT({camp_geom}, :1) <> 'FALSE'"

        if not cols_geom:
            cols_geom = get_tips_geom_tab(self.con_db, nom_tab).keys()

        if cols_geom:
            filter_sql = " OR ".join([filter_interact_base.format(camp_geom=ng) for ng in cols_geom])
            for reg in self.generator_rows_table(nom_tab, filter_sql, a_sdo_geom.as_ora_sdo_geometry(),
                                                 geom_format=geom_format):
                yield reg

    def rows_table(self, nom_tab_or_view, filter_sql=None, *args_filter_sql):
        """
        Vease funcion 'generator_rows_table()'

        Args:
            nom_tab_or_view:
            filter_sql:
            *args_filter_sql:

        Returns:
            dict
        """
        gen_tab = self.generator_rows_table(nom_tab_or_view,
                                            filter_sql,
                                            *args_filter_sql)
        pk_tab = self.get_primary_key_table(nom_tab_or_view)
        l_pk = len(pk_tab)
        if l_pk == 0:
            return [r for r in gen_tab]
        else:
            def f_key(r):
                return getattr(r, pk_tab[0])

            if l_pk > 1:
                def f_key(r): return tuple(map(lambda nf: getattr(r, nf), pk_tab))
            return {f_key(r): r for r in gen_tab}

    def row_table(self, nom_tab_or_view, filter_sql=None, *args_filter_sql, **extra_params):
        """
        Retorna primer registro para el FILTER_SQL sobre la tabla o vista indicada
        Si el FILTER_SQL utiliza valores por binding (:1, :2,...) estos se indicaran por orden en ARGS_FILTER_SQL

        Args:
            nom_tab_or_view:
            filter_sql:
            *args_filter_sql:
            **extra_params:

        Returns:
            object de la clase row_table o especificada en **extra_params['row_class']
        """
        gen = self.generator_rows_table(nom_tab_or_view,
                                        filter_sql,
                                        *args_filter_sql,
                                        **extra_params)
        return next(gen, None)

    def row_table_at(self, nom_tab_or_view, *vals_key):
        """
        Devuelve row_tabla_class para el registro que de la tabla_vista que cumpla con la clave

        Args:
            nom_tab_or_view:
            *vals_key:

        Returns:
            object de la clase row_table o especificada en **extra_params['row_class']
        """
        return self.exist_row_tab(nom_tab_or_view,
                                  {nc: val for nc, val in zip(self.get_primary_key_table(nom_tab_or_view),
                                                              vals_key)})

    def test_row_table(self, row_tab, a_sql, *args_sql):
        """
        Testea un registro de tabla (clase rwo_table) cumpla con sql indicado

        Args:
            row_tab: registro de tabla en forma de clase row_table
            a_sql: string con sql a testear

        Returns:
            bool: True o False según cumpla con el SQL indicado
        """
        sql_pk = dict_as_sql_bind_and_params(row_tab.pk_vals())
        query_sql = "{} AND ({})".format(sql_pk[0], a_sql)

        ret = False
        if self.row_table(row_tab.nom_tab, query_sql, *(tuple(sql_pk[1]) + tuple(args_sql))):
            ret = True

        return ret

    def insert_row_tab(self, nom_tab, dict_vals_param=None, dict_vals_str=None, pasar_nulls=False):
        """
        Inserta registro en la tabla indicada. Los valores para cada columna se pasarán a través de dict_vals_param
        como bindings o a través de dict_vals_str directemente en el string del sql ejecutado
        Args:
            nom_tab: nombre de la tabla
            dict_vals_param: diccionario indexado por columnas-valores. Los valores se pasarán como bindings
            dict_vals_str: diccionario indexado por columnas-valores a asignar como strings. El valor se pasa
                        directamente como asignacion en la senetencia sql
            pasar_nulls: (opcional) por defecto False. Indica si los valores NULL se asignarán o no

        Returns:
            row_table (si genera el registro) o False si va mal la operación
        """
        if not dict_vals_param:
            dict_vals_param = {}
        if not dict_vals_str:
            dict_vals_str = {}

        ora_dict_vals_param = self.get_vals_tab_for_transdb(nom_tab, dict_vals_param, pasar_nulls=pasar_nulls)

        if pasar_nulls:
            # Se revisa que en un campo geometrico se asigne None y por lo tanto se asigne valor via STR
            geoms_null = [ng for ng, val in ora_dict_vals_param.items()
                          if not val and self.get_tip_camp_geom(nom_tab, ng)]
            if geoms_null:
                keys_str = [nc.upper() for nc in dict_vals_str.keys()]
                for gn in geoms_null:
                    ora_dict_vals_param.pop(gn)
                    if gn.upper() not in keys_str:
                        dict_vals_str[gn.upper()] = "NULL"

        params = []
        nom_camps = []
        vals_camps = []
        for nom_camp, val_camp in ora_dict_vals_param.items():
            if val_camp is None:
                continue
            nom_camps.append(nom_camp)
            vals_camps.append(":" + nom_camp)
            params.append(val_camp)

        for nom_camp, val_camp_str in dict_vals_str.items():
            if val_camp_str is None:
                continue
            nom_camps.append(nom_camp)
            vals_camps.append(val_camp_str)

        row_desc_tab = get_row_desc_tab(self.con_db, nom_tab)
        pk_binds = {k: new_cursor(self.con_db).var(ora_tip_camp) for k, ora_tip_camp in row_desc_tab.pk_vals().items()}
        str_pk_camps = ",".join(pk_binds.keys())
        str_pk_binds = ",".join(list(map(lambda x: ":ret_" + str(x), pk_binds.keys())))
        params += list(pk_binds.values())

        a_sql_res = f"insert into {nom_tab}({','.join(nom_camps)}) values({','.join(vals_camps)}) " \
                    f"returning {str_pk_camps} into {str_pk_binds}"

        ok = self.exec_trans_db(a_sql_res, *params)
        if ok:
            pk_vals = {k: curs_var.getvalue() for k, curs_var in pk_binds.items()}
            return self.exist_row_tab(nom_tab, pk_vals)

        return ok

    def update_row_tab(self, nom_tab, dict_clau_reg, dict_vals_param=None, dict_vals_str=None, pasar_nulls=None):
        """
        Actualiza registro en la tabla indicada que cunpla con la clave pasada por dict_clau_reg {clave:valor}
        Los valores para cada columna se pasarán a través de dict_vals_param como bindings o a través de
        dict_vals_str directemente en el string del sql ejecutado

        Args:
            nom_tab: nombre de la tabla
            dict_clau_reg: diccionario indexado por clave-valor del registro a actualizar
            dict_vals_param: diccionario indexado por columnas-valores. Los valores se pasarán como bindings
            dict_vals_str: diccionario indexado por columnas-valores a asignar como strings. El valor se pasa
                        directamente como asignacion en la senetencia sql
            pasar_nulls: (opcional) por defecto False. Indica si los valores NULL se asignarán o no

        Returns:
            row_table (si genera el registro) o False si va mal la operación
        """
        if not dict_vals_param:
            dict_vals_param = {}
        if not dict_vals_str:
            dict_vals_str = {}

        ora_dict_clau_reg = self.get_vals_tab_for_transdb(nom_tab, dict_clau_reg)
        ora_dict_vals_param = self.get_vals_tab_for_transdb(nom_tab, dict_vals_param, pasar_nulls=pasar_nulls)

        if pasar_nulls:
            # Se revisa que en un campo geometrico se asigne None y por lo tanto se asigne valor via STR
            geoms_null = [ng for ng, val in ora_dict_vals_param.items()
                          if not val and self.get_tip_camp_geom(nom_tab, ng)]
            if geoms_null:
                keys_str = [nc.upper() for nc in dict_vals_str.keys()]
                for gn in geoms_null:
                    ora_dict_vals_param.pop(gn)
                    if gn.upper() not in keys_str:
                        dict_vals_str[gn.upper()] = "NULL"

        (sql_set_camps, params_set_camps) = dict_as_sql_bind_and_params(ora_dict_vals_param,
                                                                        ",", "=")

        (query_clau, params_filter) = dict_as_sql_bind_and_params(ora_dict_clau_reg)

        params = params_set_camps + params_filter

        for nom_camp, val_camp_str in dict_vals_str.items():
            if sql_set_camps:
                sql_set_camps += " , "
            sql_set_camps += nom_camp + "=" + val_camp_str

        ok = None
        if sql_set_camps:
            a_sql_res = f"update {nom_tab} set {sql_set_camps} where {query_clau}"

            ok = self.exec_trans_db(a_sql_res, *params)

            if ok:
                return self.exist_row_tab(nom_tab, dict_clau_reg)

        return ok

    def remove_row_tab(self, nom_tab, dict_clau_reg):
        """
        Borra registro en la tabla indicada que cunpla con la clave pasada por dict_clau_reg {clave:valor}

        Args:
            nom_tab: nombre de la tabla
            dict_clau_reg: diccionario indexado por clave-valor del registro a actualizar

        Returns:
            bool según vaya la operación
        """
        ora_dict_clau_reg = self.get_vals_tab_for_transdb(nom_tab, dict_clau_reg)

        a_sql_tmpl = "delete {nom_tab} where {query_clau}"

        (sql_filter, params) = dict_as_sql_bind_and_params(ora_dict_clau_reg)

        a_sql_res = a_sql_tmpl.format(nom_tab=nom_tab,
                                      query_clau=sql_filter)

        return self.exec_trans_db(a_sql_res, *params)

    def exist_row_tab(self, nom_tab, dict_clau_reg, **extra_params):
        """
        Devuelve registro de la tabla indicada que cunpla con la clave pasada por dict_clau_reg {clave:valor}

        Args:
            nom_tab: nombre de la tabla
            dict_clau_reg: diccionario indexado por clave-valor del registro a actualizar
            **extra_params:

        Returns:
            object de la clase row_table o especificada en **extra_params['row_class']
        """
        ora_dict_clau_reg = self.get_vals_tab_for_transdb(nom_tab, dict_clau_reg)

        (filter_sql, params) = dict_as_sql_bind_and_params(ora_dict_clau_reg, "and", "=")

        return self.row_table(nom_tab, filter_sql, *params, **extra_params)

    def get_vals_tab_for_transdb(self, nom_tab, dict_camps_vals, pasar_nulls=True):
        """
        Para un tabla y diccionario columnas-valores devuelve diccionario indexado por las columnas con los valores
        convertidos a formato cx_Oracle según tipo de cada columna en Oracle
        Args:
            nom_tab: nombre de la tabla
            dict_camps_vals: diccionario indexado por columnas-valor a convertir a formato cx_Oracle
            pasar_nulls: (opcional) por defecto convertirá los None a NULL de Oracle

        Returns:
            dict indexado por columnas con los valores convertidos a tipo cx_Oracle
        """
        dd_tab = get_row_desc_tab(self.con_db, nom_tab)

        # Retorna dict con los campos a pasar por parametro
        d_params = {}

        # Los nombres de campo siempre se buscarán en mayúsculas
        dict_camps_vals = {k.upper(): v for k, v in dict_camps_vals.items()}

        for camp, tip_camp in dd_tab.vals().items():
            if camp not in dict_camps_vals:
                continue

            val_camp = dict_camps_vals.get(camp)
            if not pasar_nulls and val_camp is None:
                continue

            if isinstance(val_camp, m_sdo_geom.sdo_geom):
                var = val_camp.as_ora_sdo_geometry()
            else:
                try:
                    var = new_cursor(self.con_db).var(tip_camp)
                    var.setvalue(0, val_camp)
                except:
                    var = val_camp

            d_params[camp] = var

        return d_params

    @print_to_log_exception()
    def run_sql_script(self, filename):
        """
        Ejecuta slq script (filename) sobre SQLPLUS

        Args:
            filename: path del sql script

        Returns:

        """
        user_ora = self.con_db.username
        ds_ora = self.con_db.dsn
        nom_con = self.nom_con_db
        psw_ora = self.psw_con_db
        if psw_ora is None:
            print("ERROR - Conexión '" + nom_con + "' no está añadida al gestor!!")
            return

        with open(filename, 'rb') as a_file:
            a_sql_command = a_file.read()

        con_db_str = user_ora + "/" + psw_ora + "@" + ds_ora
        sqlplus = Popen(['sqlplus', '-S', con_db_str], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        # sqlplus.stdin.write(a_sql_command)

        (stdout, stderr) = sqlplus.communicate(a_sql_command)

        self.print_log("Resultado lanzar script '{}': \n"
                       "{}".format(filename,
                                   stdout.decode("utf-8")))

        if sqlplus is not None:
            sqlplus.terminate()

    @staticmethod
    def get_nom_obj_sql(nom_base, prefix="", sufix=""):
        """
        Retorna nombre propuesto con prefijo/sufijos formateado para que cumpla longitud máxima de 32 caracteres en
        objetos sql Oracle

        Args:
            nom_base: nombre propuesto
            prefix: (opc) prefijo
            sufix: (opc) sufijo

        Returns:
            str formateado
        """
        return x_sql_parser.get_nom_obj_sql(nom_base, prefix, sufix)

    def iter_sdo_gtypes_vals_camp_tab(self, nom_taula, nom_camp):
        """
        Retorna los distintos tipos de Geometria (codigo entero que define el tipo SDO_GTYPE)
        que se encuentran dentro de la columna sdo_geometry de una tabla

        Args:
            nom_taula: nombre de la tabla
            nom_camp: nombre campo geometrico

        Returns:
            int definiendo tipo de geometría
        """
        sql_tip_geoms = f"select distinct(tab.{nom_camp}.Get_GType()) as tip_geom from {nom_taula} tab " \
                        f"where {nom_camp} is not null"

        for reg in self.generator_rows_sql(sql_tip_geoms):
            yield reg.TIP_GEOM

    def iter_distinct_vals_camp_tab(self, nom_taula, nom_camp, filter_sql=None):
        """
        Retorna los distintos valores de la columna de una tabla

        Args:
            nom_taula (str): Nombre de tabla
            nom_camp (str): Nombre de campo
            filter_sql(str): Filtro SQL sobre la tabla indicada

        Returns:
            {str}: Itera los distintos valores encontrados en el campo indicado
        """
        sql_distinct_vals = f"select distinct(tab.{nom_camp}) as VAL from {nom_taula} tab"
        if filter_sql:
            sql_distinct_vals += " where " + filter_sql

        for reg in self.generator_rows_sql(sql_distinct_vals):
            yield reg.VAL

    def get_tip_camp_geom(self, nom_tab_or_view, nom_camp_geom):
        """
        Retorna el tipo de campo geométrico (class_tip_geom) registrados en la global __class_tips_geom_ora
        para el campo indicado

        Args:
            nom_tab_or_view: nombre tabla/vista
            nom_camp_geom: nombre campo geom

        Returns:
            namedtuple: con atributos ['TABLE_NAME', 'COLUMN_NAME', 'GTYPE', 'SRID'])
        """
        tips_geom_tab = get_tips_geom_tab(self.con_db, nom_tab_or_view)
        if tips_geom_tab:
            return tips_geom_tab.get(nom_camp_geom.upper())

    def get_epsg_for_srid(self, srid):
        """
        Rertorna WKT con la definicion del SRID dado
        """
        return self.callfunc_sql('SDO_CS.MAP_ORACLE_SRID_TO_EPSG', cx_Oracle.NUMBER, srid)

    def get_gtype_camp_geom(self, nom_tab_or_view, nom_camp_geom):
        """
        Retorna el tipo GTYPE (int) de la geometria

        Args:
            nom_tab_or_view: nombre tabla/vista
            nom_camp_geom: nombre campo geom

        Returns:
            int
        """
        gtype = 0
        g_tip_ora = self.get_tip_camp_geom(nom_tab_or_view, nom_camp_geom)
        if g_tip_ora:
            gtype = GTYPES_ORA.index(g_tip_ora.GTYPE)

        return gtype

    @staticmethod
    def verificar_path_vector_file(nom_tab_or_view, dir, file_name, ext, zipped):
        """
        Compone el/los path para el/los vector_file de una tabla y determina si exists
        Args:
            nom_tab_or_view:
            dir:
            file_name:
            ext:
            zipped:

        Returns:
            file_path (str), file_path_zip (str), exists (bool)
        """
        if file_name and not file_name.endswith(ext):
            file_name = ".".join((file_name, ext))
        elif not file_name:
            file_name = ".".join((nom_tab_or_view, ext)).lower()

        file_path = os.path.join(dir, file_name)
        file_path_zip = None
        if zipped:
            file_path_zip = "{}.zip".format(os.path.splitext(file_path)[0])

        exists = (os.path.exists(file_path) and not file_path_zip) or (file_path_zip and os.path.exists(file_path_zip))

        return file_path, file_path_zip, exists

    @print_to_log_exception()
    def create_json_tab_or_view(self, nom_tab_or_view, dir='.', file_name=None, overwrite=True, cols=None, zipped=True,
                                filter_sql=None, *args_sql):
        """

        Args:
            nom_tab_or_view (str): Nombre tabla o vista
            dir (str):
            file_name (str):
            overwrite (bool):
            cols (list): columnas
            zipped (bool):
            filter_sql (str):
            *args_sql: lista de argumentos a pasar al filtro sql
        Returns:
            file_path (str)
        """
        file_path, file_path_zip, exists = self.verificar_path_vector_file(
            nom_tab_or_view, dir, file_name, "json", zipped)

        if overwrite or not exists:
            # Se calculan las columnas para hacer get de la fila con el orden en las columnas de la tabla
            if not cols:
                dd_tab = self.get_dd_table(nom_tab_or_view)
                cols = dd_tab.cols
            sql = sql_tab(nom_tab_or_view,
                          filter_sql=filter_sql,
                          columns=cols)

            file_path_res = vector_file_from_gen_ora_sql(file_path, "json", self.generator_rows_sql(sql, *args_sql),
                                                         zipped=zipped)
        else:
            file_path_res = file_path if not zipped else file_path_zip

        return file_path_res

    @print_to_log_exception()
    def create_csv_tab_or_view(self, nom_tab_or_view, dir='.', file_name=None, overwrite=True, cols=None, zipped=True,
                               filter_sql=None, *args_sql):
        """

        Args:
            nom_tab_or_view (str): Nombre tabla o vista
            dir (str):
            file_name (str):
            overwrite (bool):
            cols (list): columnas
            zipped (bool):
            filter_sql (str):
            *args_sql: lista de argumentos a pasar al filtro sql

        Returns:
            file_path_res (str)
        """
        file_path, file_path_zip, exists = self.verificar_path_vector_file(
            nom_tab_or_view, dir, file_name, "csv", zipped)

        if overwrite or not exists:
            if not cols:
                dd_tab = self.get_dd_table(nom_tab_or_view)
                cols = dd_tab.cols
            sql = sql_tab(nom_tab_or_view,
                          filter_sql=filter_sql,
                          columns=cols)

            # Para el formato geocsv que acepta GDAL se añade fichero con los tipos de columna
            tip_cols_csv = []
            for col in cols:
                r_tip_col = self.row_table("user_tab_columns",
                                           "table_name = :1 and column_name = :2",
                                           nom_tab_or_view.upper(), col.upper())
                dtype = r_tip_col.DATA_TYPE
                dlength = r_tip_col.DATA_LENGTH
                dprecision = r_tip_col.DATA_PRECISION
                dscale = r_tip_col.DATA_SCALE

                if dtype == "DATE":
                    tip_cols_csv.append('"DateTime"')
                elif dtype == "FLOAT":
                    tip_cols_csv.append('"Real({}.{})"'.format(dlength, dprecision))
                elif dtype == "NUMBER":
                    if dscale and dscale != 0:
                        tip_cols_csv.append('"Real({}.{})"'.format(dprecision, dscale))
                    elif dprecision:
                        tip_cols_csv.append('"Integer({})"'.format(dprecision))
                    else:
                        tip_cols_csv.append('"Real(10.8)"')
                elif dtype == "SDO_GEOMETRY":
                    tip_cols_csv.append('"WKT"')
                else:
                    tip_cols_csv.append('"String({})"'.format(round(dlength * 1.25)))

            file_path_res = vector_file_from_gen_ora_sql(file_path, "csv",
                                                         self.generator_rows_sql(sql, *args_sql, geom_format="as_wkt"),
                                                         zipped=zipped, cols_csv=cols, tip_cols_csv=tip_cols_csv)
        else:
            file_path_res = file_path if not zipped else file_path_zip

        return file_path_res

    @print_to_log_exception()
    def create_geojsons_tab_or_view(self, nom_tab_or_view, dir='.', file_name_prefix=None, by_geom=False,
                                    dir_topojson=None, overwrite=True, cols=None,
                                    filter_sql=None, *args_sql):
        """

        Args:
            nom_tab_or_view (str): Nombre tabla (vigente o versionada) para entidad GIS
            dir (str="."):
            file_name_prefix (str=None): (opcional) prefijo del fichero
            by_geom (bool=False): (Opcional) si se querrán los geojsons por geometria. Si no se saca un unico geojson con
                            la columna geometry como una GeometryCollection si la tabla es multigeom
            dir_topojson (str=None): path donde irán las conversiones
            overwrite (bool=True):
            cols (list=None):
            filter_sql (str=None):
            *args_sql: lista de argumentos a pasar al filtro sql

        Returns:
            ok (bool)
        """
        ext = "geo.json"
        sqls = {}
        dd_tab = self.get_dd_table(nom_tab_or_view)
        if not cols:
            cols = dd_tab.cols

        if by_geom:
            c_alfas = [cn for cn in dd_tab.alfas() if cn in cols]
            c_geoms = [cn for cn in dd_tab.geoms() if cn in cols]
            for c_geom in c_geoms:
                sqls[c_geom] = sql_tab(nom_tab_or_view, filter_sql, c_alfas + [c_geom])
        else:
            sqls[None] = sql_tab(nom_tab_or_view, filter_sql, cols)

        if not file_name_prefix:
            file_name_prefix = nom_tab_or_view

        for ng, sql in sqls.items():
            file_name = file_name_prefix
            if ng:
                file_name = "-".join((file_name, ng))

            file_name = ".".join((file_name, ext)).lower()
            file_path = os.path.join(dir, file_name)

            if overwrite or not os.path.exists(file_path):
                file_path = vector_file_from_gen_ora_sql(file_path, "geojson",
                                                         self.generator_rows_sql(sql, *args_sql))

            if by_geom and dir_topojson and file_path:
                tip_geom = getattr(dd_tab, ng).GTYPE
                simplify = True
                if tip_geom.endswith("POINT"):
                    simplify = False

                topojson_utils.geojson_to_topojson(file_path, dir_topojson,
                                                   simplify=simplify,
                                                   overwrite=overwrite)

        return True


if __name__ == '__main__':
    import fire

    sys.exit(fire.Fire())
