#   coding=utf-8
#  #
#   Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#   File: sdo_geom.py
#   Created: 05/04/2020, 17:47
#   Last modified: 10/11/2019, 11:24
#   Copyright (c) 2020
import json
import re
import sys

import cx_Oracle
from math import atan2, degrees
from osgeo import ogr
from shapely.geometry import shape

from extra_utils.misc import rounded_float
import osgeo_utils
from spatial_utils import shapely_utils


class sdo_geom(object):
    """
    Clase que instanciará objectos MDSYS.SDO_GEOMETRY devueltos por cx_Oracle añadiendo funcionalidad para convertir a
    distintos formatos geométricos. Se representará como una geometria geojson a partir de interfaz _geo_interface_
    """
    __slots__ = ["__SDO_GTYPE",
                 "__SDO_SRID",
                 "__SDO_POINT",
                 "__SDO_ELEM_INFO",
                 "__SDO_ORDINATES",
                 "__SDO_DIM",
                 "__SDO_LRS",
                 "__DD_SDO_GTYPE",
                 "__type_geojson",
                 "__idxs_elems_geom",
                 "__con_db",
                 "__ora_sdo_geometry",
                 "__shapely_obj",
                 "__ogr_geom",
                 "__cache_transformed_geoms",
                 "__cache_formatted_geoms"]

    __ora_dd_gtypes = {0: "UNKNOWN_GEOMETRY",
                       1: "POINT",
                       2: "LINE",  # "CURVE",
                       3: "POLYGON",  # "SURFACE",
                       4: "COLLECTION",
                       5: "MULTIPOINT",
                       6: "MULTILINE",  # "MULTICURVE",
                       7: "MULTIPOLYGON",  # "MULTISURFACE",
                       8: "SOLID",
                       9: "MULTISOLID"}

    __ora_gtypes_geojson_types = {1: "Point",
                                  5: "MultiPoint",
                                  2: "LineString",
                                  6: "MultiLineString",
                                  3: "Polygon",
                                  7: "MultiPolygon",
                                  4: "GeometryCollection"}

    def __init__(self, cx_ora_sdo_geom, con_ora_db):
        """
        Genera instancia para geometria Oracle MDSYS.SDO_GEOMETRY

        Args:
            cx_ora_sdo_geom: valor MDSYS.SDO_GEOMETRY a partir de cx_Oracle
            con_ora_db: conexion Oracle cx_Oracle.Connection
        """
        self.__SDO_GTYPE = int(cx_ora_sdo_geom.SDO_GTYPE)
        self.__SDO_SRID = int(cx_ora_sdo_geom.SDO_SRID)

        sdo_point_orig = cx_ora_sdo_geom.SDO_POINT
        a_sdo_point = None
        l_elem_info = None
        l_ordinates = None
        if sdo_point_orig:
            a_sdo_point = sdo_point_orig.copy()
        else:
            l_elem_info = cx_ora_sdo_geom.SDO_ELEM_INFO.aslist()
            l_ordinates = cx_ora_sdo_geom.SDO_ORDINATES.aslist()

        self.__SDO_POINT = a_sdo_point
        self.__SDO_ELEM_INFO = l_elem_info
        self.__SDO_ORDINATES = l_ordinates

        self.__con_db = con_ora_db

        self.__idxs_elems_geom = []

        self._parse_oracle_params()

        self.__ora_sdo_geometry = None
        self.__shapely_obj = None
        self.__ogr_geom = None
        self.__cache_transformed_geoms = {}
        self.__cache_formatted_geoms = {}

    def _gen_elems_info(self):
        """
        Itera sobre los elementos SDO_ELEM_INFO de la MDSYS.SDO_GEOMETRY
        Returns:
            tuple de integers
        """
        if not self.__SDO_ELEM_INFO:
            return

        prev_elem_info = None
        len_elem_info = 3
        for id_elem in range(0, len(self.__SDO_ELEM_INFO), len_elem_info):
            elem_info = self.__SDO_ELEM_INFO[id_elem: id_elem + len_elem_info]

            if prev_elem_info:
                yield (int(prev_elem_info[1]), int(prev_elem_info[2]),
                       (int(prev_elem_info[0] - 1), int(elem_info[0] - 1)))

            prev_elem_info = elem_info

        yield int(prev_elem_info[1]), int(prev_elem_info[2]), (int(prev_elem_info[0] - 1), None)

    def _parse_oracle_params(self):
        """
        Descompone geometría a partir especificación Oracle Spatial para MDSYS.SDO_GEOMETRY e inicializa atributos
        de self
        """
        m_sdo_gtype = re.match("(\d{1})(\d{1})(\d{2})", str(self.__SDO_GTYPE))
        self.__SDO_DIM = int(m_sdo_gtype.group(1))
        self.__SDO_LRS = int(m_sdo_gtype.group(2))
        self.__DD_SDO_GTYPE = int(m_sdo_gtype.group(3))

        # Un punto puede venir informado en SDO_POINT y no debería venir informado SDO_ORDINATES ni SDO_ELEM_INFO
        if self.__SDO_POINT:
            self.__type_geojson = self.__ora_gtypes_geojson_types.get(1)
        else:
            if self.__SDO_DIM not in [2, 3]:
                print("!AVISO! - Geometria no parseable a formato GEOJSON por NO ser de SDO_DIM 2D o 3D")
                return

            # Solo se interpretarán los SDO_ETYPE simples segun tabla en siguiente link
            # https://docs.oracle.com/cd/B28359_01/appdev.111/b28400/sdo_objrelschema.htm#BGHDGCCE
            sdo_etypes_simples = [1, 2, 1003, 2003]

            num_elems = 0
            for SDO_ETYPE, SDO_INTERPRETATION, IDXS_SDO_ORDS in self._gen_elems_info():
                if SDO_ETYPE not in sdo_etypes_simples:
                    print("!AVISO! - Geometria con elementos no parseables a formato GEOJSON "
                          "por no ser de tipo SDO_ETYPE 1,2,1003,2003")
                    continue

                list_idxs = None
                if self.__DD_SDO_GTYPE in [1, 5]:  # POINT o MULTIPOINT
                    # Angulo del Punto Orientado se añade al ultimo punto
                    if SDO_ETYPE == 1 and SDO_INTERPRETATION == 0:
                        self.__idxs_elems_geom[-1] += IDXS_SDO_ORDS
                    else:
                        list_idxs = self.__idxs_elems_geom
                        num_elems += 1

                elif self.__DD_SDO_GTYPE in [2, 6]:  # LINE o MULTILINE
                    list_idxs = self.__idxs_elems_geom
                    num_elems += 1

                elif self.__DD_SDO_GTYPE in [3, 7]:  # POLYGON o MULTIPOLYGON
                    list_idxs = self.__idxs_elems_geom
                    m_tip_pol = re.match("(\d{1})(\d*)", str(SDO_ETYPE))  # Si primer digito 1=EXTERIOR si 2=INTERIOR
                    TIP_POL = int(m_tip_pol.group(1))
                    if TIP_POL == 1:
                        num_elems += 1

                    IDXS_SDO_ORDS += (TIP_POL,)

                # Guardamos en el ultimo elemento de la terna de indices para cada elemento su SDO_INTERPRETATION
                IDXS_SDO_ORDS += (SDO_INTERPRETATION,)

                if list_idxs is not None:
                    list_idxs.append(IDXS_SDO_ORDS)

            if num_elems:
                self.__type_geojson = self.__ora_gtypes_geojson_types.get(self.__DD_SDO_GTYPE)
                if num_elems == 1 and self.__DD_SDO_GTYPE > 4:
                    self.__type_geojson = re.sub("Multi", "", self.__type_geojson, 0, re.IGNORECASE)

    def _sdo_ordinates_as_coords(self, idx_ini=0, idx_fi=None):
        """
        Itera sobre las coordenadas (SDO_ORDINATES) de la geometria Oracle MDSYS.SDO_GEOMETRY
        Args:
            idx_ini:
            idx_fi:

        Returns:
            tuple con las coordenadas
        """
        if self.__SDO_POINT:
            coords_geojson = (self.__SDO_POINT.X, self.__SDO_POINT.Y)
            if self.__SDO_POINT.Z:
                coords_geojson += (self.__SDO_POINT.Z,)

            yield coords_geojson

        elif self.__SDO_ORDINATES:
            if not idx_fi:
                idx_fi = len(self.__SDO_ORDINATES)

            for el_dim in range(idx_ini, idx_fi, self.__SDO_DIM):
                yield tuple(self.__SDO_ORDINATES[el_dim:el_dim + self.__SDO_DIM])

    def _list_sdo_ordinates_as_coords(self, idx_ini=None, idx_fi=None):
        """
        Devuelve lista de coordenadas redondeadas a 9 decimales por defecto
        Args:
            idx_ini:
            idx_fi:

        Returns:
            [tuple de coords]
        """
        return [tuple(rounded_float(v) for v in c) for c in self._sdo_ordinates_as_coords(idx_ini, idx_fi)]

    def coords_elems_geom(self, grup_holes=True):
        """
        Devuelve las coordenadas agrupadas por listas para cada sub-elemento (poligono, agujero) que compone la geom
        Args:
            grup_holes: Por defecto agrupa los agujeros en una lista

        Returns:
            list
        """
        coords_elems = []
        if re.match(r'.*Polygon', self.__type_geojson, re.IGNORECASE):
            pols = None
            holes = None
            for elems_geom in self.iter_elems_geom():
                crds = elems_geom[1]
                if elems_geom[0] == "Polygon":
                    pols = []
                    holes = None
                    coords_elems.append(pols)
                    pols.append(crds)
                else:
                    if not grup_holes:
                        holes = pols
                    elif not holes:
                        holes = []
                        pols.append(holes)
                    holes.append(crds)

            if len(coords_elems) == 1:
                coords_elems = coords_elems[0]
        elif re.match(r'Multi.*', self.__type_geojson, re.IGNORECASE):
            for elems_geom in self.iter_elems_geom():
                coords_elems.append(elems_geom[1])
        else:
            for elems_geom in self.iter_elems_geom():
                for c in elems_geom[1]:
                    coords_elems.append(c)

        return coords_elems

    def angle_points(self):
        """
        Si el tipus de geometria es 'Point' retorna llista d'angles en graus (decimal degrees) respectius
        a la llista de coordenades o si només és un Point directament el float amb el angle en graus

        Returns:
            list ó float
        """
        if re.match(r'.*Point', self.__type_geojson, re.IGNORECASE):
            if re.match(r'Multi.*', self.__type_geojson, re.IGNORECASE):
                angles_pts = []
                for elems_geom in self.iter_elems_geom():
                    angles_pts.append(degrees(elems_geom[2]))
                return angles_pts
            else:
                return degrees(next(self.iter_elems_geom())[2])

    @property
    def simple_tip_geom_geojson(self):
        """
        Devuelve el tipo de geometria simple al que pertence SELF
        Returns:
            Point, LineString, Polygon
        """
        return re.sub("Multi", "", self.__type_geojson, 0, re.IGNORECASE)

    def iter_elems_geom(self):
        """
        Retorna segun el tipo de geometria tuples identificando cada elemento que conforma la geometria:
          Tipo Point      -> ("Point", [x,y], angle_radians))
          Tipo LineString -> ("LineString", [[x1,y1], [x2,y2], ...]])
          Tipo Polygon    -> ("Polygon", [[x1,y1], [x2,y2],...]])
                             ("Hole", [[x1,y1], [x2,y2],...]])
          Tipo MultiPoint -> Varios tuples de tipo Point
          Tipo MultiLineString -> Varios tuples de tipo LineString
          Tipo MultiPolygon -> Varios tuples de tipo Polygon

        Returns:
            tuples (tip_geom, list_coords) para cada elementos que conforma la geometria
        """
        simple_type = self.simple_tip_geom_geojson
        if simple_type == "Point" and not self.__idxs_elems_geom:
            yield simple_type, next(self._sdo_ordinates_as_coords()), 0
        else:
            for idxs in self.__idxs_elems_geom:
                list_coords = self._list_sdo_ordinates_as_coords(idxs[0], idxs[1])
                if simple_type == "Point":
                    angle = 0
                    if len(idxs) == 5:  # Punto orientado
                        dx_dy = self._list_sdo_ordinates_as_coords(idxs[-2], idxs[-1])[0]
                        if dx_dy[0] != 0:
                            angle = atan2(dx_dy[1], dx_dy[0])

                    yield simple_type, list_coords[0], angle

                elif simple_type == "Polygon":
                    tip_pol = simple_type
                    if idxs[2] == 2:
                        tip_pol = "Hole"

                    # Cuando es tipo poligono y solo vienen 2 pares de coordenadas se revisa su SDO_INTERPRETATION
                    a_sdo_interpretation = idxs[-1]
                    if len(list_coords) == 2 and a_sdo_interpretation == 3:
                        # Será un MBR o optimized rectangle conformado por la esq. inf-izq y la sup-der
                        # Siguiendo la especificacion de GEOJSON se ordenan las coordenadas en el sentido
                        # antihorario siendo la primera y la ultima coordenada las mismas
                        list_coords.insert(1, (list_coords[-1][0], list_coords[0][1]))
                        list_coords.append((list_coords[0][0], list_coords[-1][1]))
                        list_coords.append((list_coords[0][0], list_coords[0][1]))

                    yield tip_pol, list_coords
                else:
                    yield simple_type, list_coords

    def __repr__(self):
        """
        Devuelve string que define la geometria cuando se representa como STRING
        Returns:
            str
        """
        l_coords = [",".join(map(lambda x: '{0:.9g}'.format(x), c))
                    for c in self._sdo_ordinates_as_coords(idx_fi=self.__SDO_DIM)]
        if self.__DD_SDO_GTYPE not in [1, 5] or len(self.__idxs_elems_geom) > 1:
            l_coords.append("...")
        l_txt = [self.__ora_dd_gtypes[self.__DD_SDO_GTYPE],
                 "(SRID=", str(self.__SDO_SRID),
                 ",COORDS=", ",".join(l_coords), ")"]

        return "".join(l_txt)

    def __eq__(self, other):
        """
        Funcion igualdad para cuando se compare con el operador '==' con otro objecto

        Args:
            other: otro objecto de la clase sdo_geom

        Returns:
            bool
        """

        if isinstance(other, self.__class__):
            return self.__SDO_GTYPE == other.__SDO_GTYPE and \
                   self.__SDO_SRID == other.__SDO_SRID and \
                   self.__SDO_POINT == other.__SDO_POINT and \
                   self.__SDO_ELEM_INFO == other.__SDO_ELEM_INFO and \
                   self.__SDO_ORDINATES == other.__SDO_ORDINATES
        else:
            return False

    def __ne__(self, other):
        """
        Funcion NO igual para cuando se compare con el operador '!=' con otro objecto

        Args:
            other: otro objecto de la clase sdo_geom

        Returns:
            bool
        """
        return not self.__eq__(other)

    @property
    def tip_geom(self):
        """
        Devuelve tipo de geometria:
            "UNKNOWN_GEOMETRY",
            "POINT",
            "LINE",
            "POLYGON",
            "COLLECTION",
            "MULTIPOINT",
            "MULTILINE",
            "MULTIPOLYGON",
            "SOLID",
            "MULTISOLID"

        Returns:
             tip_geom
        """
        return self.__ora_dd_gtypes[self.__DD_SDO_GTYPE]

    def as_ora_sdo_geometry(self):
        """
        Devuelve self como un oracle sdo_geometry

        Returns:
            cx_Oracle type object MDSYS.SDO_GEOMETRY
        """
        if not self.__ora_sdo_geometry:
            ora_sdo_geom_type = self.__con_db.gettype("MDSYS.SDO_GEOMETRY")
            ora_sdo_geom = ora_sdo_geom_type.newobject()
            ora_sdo_geom.SDO_GTYPE = self.__SDO_GTYPE
            ora_sdo_geom.SDO_SRID = self.__SDO_SRID

            if self.__SDO_POINT:
                ora_sdo_geom.SDO_POINT = self.__SDO_POINT
            else:
                elementInfoTypeObj = self.__con_db.gettype("MDSYS.SDO_ELEM_INFO_ARRAY")
                ordinateTypeObj = self.__con_db.gettype("MDSYS.SDO_ORDINATE_ARRAY")
                ora_sdo_geom.SDO_ELEM_INFO = elementInfoTypeObj.newobject()
                ora_sdo_geom.SDO_ELEM_INFO.extend(self.__SDO_ELEM_INFO)
                ora_sdo_geom.SDO_ORDINATES = ordinateTypeObj.newobject()
                ora_sdo_geom.SDO_ORDINATES.extend(self.__SDO_ORDINATES)

            self.__ora_sdo_geometry = ora_sdo_geom

        return self.__ora_sdo_geometry

    def as_shapely(self):
        """
        Retorna self como una geom del modulo shapely

        Returns:
            clase geometria del modulo shapely
        """
        if not self.__shapely_obj and self.__type_geojson:
            shp_geom = shape(self.__geo_interface__)
            if self.__SDO_SRID != 4326:
                shp_geom = shapely_utils.transform_shapely_geom(shp_geom, 4326, self.__SDO_SRID)
            self.__shapely_obj = shp_geom

        return self.__shapely_obj

    def as_wkt(self):
        """
        Retorna geom en formato WKT

        Returns:
            str
        """
        ogr_geom = self.as_ogr_geom()
        if ogr_geom:
            return ogr_geom.ExportToWkt()

    def as_wkb(self):
        """
        Retorna geom en formato WKB

        Returns:
            b(str): binary string
        """
        ogr_geom = self.as_ogr_geom()
        if ogr_geom:
            return ogr_geom.ExportToWkb()

    def as_ogr_geom(self):
        """
        Retorna la geometria como instancia de geometria de la libreria ogr

        Returns:
            osgeo.ogr.Geometry
        """
        if not self.__ogr_geom and self.__type_geojson:
            self.__ogr_geom = ogr.CreateGeometryFromJson(self.as_geojson())

        return self.__ogr_geom

    def as_gml(self):
        """
        Retorna geom en format GML

        Returns:
            str en formato GML
        """
        ogr_g = self.as_ogr_geom()
        if ogr_g:
            return ogr_g.ExportToGML()

    def as_kml(self):
        """
        Retorna geom en format KML

        Returns:
            str en formato KML
        """
        ogr_g = self.as_ogr_geom()
        if ogr_g:
            return ogr_g.ExportToKML()

    def as_geojson(self):
        """
        Retorna geom en format GeoJson

        Returns:
            str en formato GeoJson
        """
        return json.dumps(self.__geo_interface__)

    @property
    def __geo_interface__(self):
        """
        Python protocol for geospatial data (GeoJson always in EPSG4326 lat-long)

        Returns:
            dict que representa geom en formato GeoJson
        """
        geom_geojson = {
            "type": self.__type_geojson,
            "coordinates": self.transform_to_srid(4326).coords_elems_geom(grup_holes=False)
        }

        return geom_geojson

    def transform_to_srid(self, srid):
        """
        Retorna la geometría transformada al SRID de Oracle dado (suele ser codigo numérico EPSG)

        Args:
            srid: codigo epsg

        Returns:
            sdo_geom transformada al SRID
        """
        from cx_oracle_spatial import gestor_oracle

        if int(srid) == int(self.__SDO_SRID):
            return self

        geom_trans = self.__cache_transformed_geoms.get(srid)
        if not geom_trans:
            nom_col = "GEOM"

            try:
                sql = "select sdo_cs.transform(:1, :2) as {nom_col} from dual".format(nom_col=nom_col)
                row_ret = gestor_oracle.execute_fetch_sql(
                    self.__con_db,
                    sql,
                    self.as_ora_sdo_geometry(),
                    srid,
                    output_handler=get_output_handler(self.__con_db))

                geom_trans = getattr(row_ret, nom_col)
                self._set_transformed_geom(srid, geom_trans)
                # Se guarda en la nueva sdo_geom creada SELF
                geom_trans._set_transformed_geom(self.__SDO_SRID, self)
            except:
                raise Exception(
                    "!ERROR en metodo sdo_geom.transform_to_srid() para geometria {}!".format(
                        self))

        return geom_trans

    def _set_transformed_geom(self, srid, a_sdo_geom):
        """
        Cachea sobre self las transformaciones a distintos SRID

        Args:
            srid:
            a_sdo_geom:
        """
        if self != a_sdo_geom:
            self.__cache_transformed_geoms[srid] = a_sdo_geom

    def convert_to(self, a_format, srid=None):
        """
        Retorna la geometría en los formatos WKT, KML o GML (disponibles en Oracle) o JSON/GEOJSON
        (son el mismo) y en el sistema de coordenadas especificado

        Args:
            a_format:
            srid:

        Returns:
            object o str con el formato especificado
        """
        formats = {"JSON": "ExportToJson",
                   "GEOJSON": "ExportToJson",
                   "WKT": "ExportToWkt",
                   "WKB": "ExportToWkb",
                   "GML": "ExportToGml",
                   "XML": "ExportToGml",
                   "KML": "ExportToKml"}

        a_format = a_format.upper()
        geom_formatted = self.__cache_formatted_geoms.get((a_format, srid))
        if not geom_formatted:
            a_ogr_geom = self.as_ogr_geom()
            if srid and srid != self.__SDO_SRID:
                a_ogr_geom = osgeo_utils.transform_ogr_geom(a_ogr_geom, self.__SDO_SRID, srid)

            if a_format in formats:
                geom_formatted = getattr(a_ogr_geom,
                                         formats[a_format])()
            else:
                raise Exception("!ERROR! - Formato '" + a_format +
                                "' no disponible para sdo_geom.convert_to()")

            if geom_formatted:
                self.__cache_formatted_geoms[(a_format, srid)] = geom_formatted

        return geom_formatted


# Handler de Input y Output para los cursores de cx_Oracle para devolver las geometrías como instancias de la SDO_GEOM
def get_build_sdo_geom(con_db=None, func_format_geom=None):
    """
    Retorna la funcion decorada que devolverá el objeto SDO_GEOM y si viene
    la llamada a partir de una ROW de una tabla o vista entonces también
    llegará informada la conexión cx_oracle (CON_DB) y el tipo de class_tip_geom que
    que está asociado a la columna de la geometría (TIP_GEOM)

    Args:
        con_db:
        func_format_geom:

    Returns:
        sdo_geom ó formato retorno de la funcion func_format_geom
    """

    def build_sdo_geom(cx_oracle_obj):
        if cx_oracle_obj:
            try:
                a_geom = sdo_geom(cx_oracle_obj, con_db)
                if func_format_geom:
                    a_geom = getattr(a_geom, func_format_geom)()

                return a_geom
            except Exception:
                return cx_oracle_obj

    return build_sdo_geom


def get_output_handler(con_db, func_format_geom=None):
    """
    Retorna el handler para tratar geometrías oracle Sdo_geometry y convertirlas a SDO_GEOM.
    Se podrá indicar como dicccionario de nombres columna: class_tip_geom el tipo en concreto que tendrá asociado
    cada nueva SDO_GEOM creada

    Args:
        con_db:
        func_format_geom: nombre funcion conversion sobre SDO_GEOM a otro formato de geometria

    Returns:
        output_type_handler configurado dependiendo de valor
    """

    def output_type_handler(cursor, name_field, defaultType, length, precision, scale):
        if defaultType in [cx_Oracle.Object, cx_Oracle.OBJECT]:
            return cursor.var(defaultType, arraysize=cursor.arraysize,
                              outconverter=get_build_sdo_geom(con_db, func_format_geom),
                              typename="MDSYS.SDO_GEOMETRY")

        elif defaultType in [cx_Oracle.STRING, cx_Oracle.FIXED_CHAR] and sys.version_info[0] < 3:
            return cursor.var(defaultType, arraysize=cursor.arraysize,
                              outconverter=lambda val_campo: val_campo.decode(con_db.encoding).encode('UTF-8'))

    return output_type_handler


def sdo_geom_in_converter(a_sdo_geom):
    """
    Devuelve cx_Oracle.Object SDO_GEOMETRY a partir de SDO_GEOM

    Args:
        a_sdo_geom: instancia clase sdo_geom

    Returns:
        cx_Oracle.SDO_GEOMETRY
    """
    try:
        return a_sdo_geom.as_ora_sdo_geometry()
    except Exception:
        print("!ERROR en cx_oracle_spatial.get_sdo_geom_in_converter() al convertir clase sdo_geom a "
              "cx_Oracle.Object!")
        return None


def get_sdo_input_handler():
    """
    Devuelve funcion para tratar los SDO_GEOM en transacciones sql como MDSYS.SDO_GEOMETRY

    Returns:
        input_type_handler configurado para convertir las sdo_geom a MDSYS.SDO_GEOMETRY
    """

    def sdo_input_handler(cursor, value, num_elems):
        if isinstance(value, sdo_geom):
            return cursor.var(cx_Oracle.OBJECT, arraysize=num_elems,
                              inconverter=sdo_geom_in_converter,
                              typename="MDSYS.SDO_GEOMETRY")

    return sdo_input_handler
