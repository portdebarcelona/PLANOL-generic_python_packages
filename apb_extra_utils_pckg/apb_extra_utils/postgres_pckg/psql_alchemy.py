#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 31/03/2019
#  Copyright (c)
from __future__ import annotations
import re
from threading import Lock

from apb_extra_utils.utils_logging import get_base_logger
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import make_url, URL
from sqlalchemy import MetaData, Table, text, Engine, inspect
from collections import namedtuple

TYPE_UNKNOWN = 'UNKNOWN'
PG_DRIVER = 'postgresql+psycopg2'

# Intenta importar soporte para tipos geométricos PostGIS
try:
    import geoalchemy2  # noqa: F401

    HAS_GEOALCHEMY2 = True
except ImportError:
    HAS_GEOALCHEMY2 = False


def url_pg_string_connection(user='', psw='', host='localhost', port=5432, db='postgres', url_conn_string=None,
                             schemas='') -> URL:
    """
    Retorna una URL pg_connection parseada.
    Se pueden informar los parámetros uno a uno o directamente con la cadena de conexión completa (conn_string).
    En este ultimo caso se ignoran los parámetros individuales excepto el 'schemas'  que se añade a la cadena de conexión si no estuviera

    Args:
        user (str): usuario
        psw (str): password
        host (str): host
        port (int): port
        db (str): database
        url_conn_string (str | URL): connection string or sqlalchemy URL
        schemas (str): schemas separados por comas

    Returns:
        URL
    """
    if url_conn_string:
        url = make_url(url_conn_string)
    else:
        url = URL.create(
            drivername=PG_DRIVER,
            username=user or '', password=psw or '',
            host=host or '', port=port, database=db or '',
        )

    if schemas:
        normalized_schemas = ','.join([s.strip() for s in str(schemas).split(',') if s.strip()])
        if normalized_schemas:
            url = url.update_query_dict(dict(options=f"-csearch_path={normalized_schemas}"))

    return url


class EngPsqlAlchemy(object):
    """
    Clase que gestiona conexion sqlalchemy a Postgres
    """
    __slots__ = 'url_con_db', 'eng_db', 'logger', 'session_db', 'schemas'
    _CACHE = {}
    _CACHE_LOCK = Lock()

    @classmethod
    def get_cached(cls, user=None, psw=None,
                   srvr_db='localhost', port_db=5432,
                   db='postgres', schemas=None,
                   a_logger=None, url_conn_string=None, force_new=False):
        """
        Recupera una instancia cacheada por conexión o crea una nueva si no existe.

        La clave de caché se basa en user/host/port/db/schemas (o conn_string).
        Antes de devolver una instancia cacheada, valida y recupera su session si es necesario.
        """
        cache_key = url_pg_string_connection(user=user, psw=psw, host=srvr_db, port=port_db, db=db,
                                             url_conn_string=url_conn_string, schemas=schemas)

        with cls._CACHE_LOCK:
            if force_new:
                cls._CACHE.pop(cache_key, None)

            inst = cls._CACHE.get(cache_key)
            if inst is None:
                inst = cls(user=user, psw=psw, srvr_db=srvr_db, port_db=port_db, db=db,
                           schemas=schemas, a_logger=a_logger, url_conn_string=url_conn_string)
                cls._CACHE[cache_key] = inst
            else:
                inst.ensure_session()

            return inst

    def __init__(self, user=None, psw=None, srvr_db='localhost', port_db=5432, db='postgres', schemas=None,
                 a_logger=None, url_conn_string=None):
        """
        Retorna engine para database postgres. Si no se informa ningun argumento retorna el cacheado

        Args:
            user (str=None):
            psw (str=None):
            srvr_db (str=None):
            port_db (int=None):
            db (str=None):
            schemas (str=None): schemas separated by comma
            a_logger (logging.Logger=None):
            url_conn_string (str|URL=None): connection string or sqlalchemy URL

        Returns:
            sqlalchemy.engine.base.Engine
        """
        if (user is None or psw is None) and url_conn_string is None:
            raise ValueError("Debe informar user y psw, o alternativamente conn_string")

        self.url_con_db = url_pg_string_connection(user=user, psw=psw, host=srvr_db, port=port_db, db=db,
                                                   url_conn_string=url_conn_string, schemas=schemas)

        if schemas:
            self.schemas = [s.strip() for s in str(schemas).split(',') if s.strip()]

        self.logger = a_logger
        self.__set_logger()

        self.logger.debug(f"Initializing EngPsqlAlchemy '{self.url_con_db}'")

        extra_args = {}
        if HAS_GEOALCHEMY2:
            extra_args['plugins'] = ['geoalchemy2']

        eng_db: Engine = create_engine(
            self.url_con_db,
            **extra_args
        )

        eng_db.connect()

        self.eng_db = eng_db
        # self.eng_db.logger = self.logger
        self._set_session()

    @classmethod
    def from_url_conn_string(cls, url_conn_string, a_logger=None):
        """
        Constructor alternativo a partir de cadena de conexion.

        Args:
            url_conn_string (str | URL):
            a_logger (logging.Logger=None):

        Returns:
            EngPsqlAlchemy
        """
        return cls(url_conn_string=url_conn_string, a_logger=a_logger)

    def __set_logger(self):
        """
        Asigna el LOGGER po defecto si este no se ha informado al inicializar el gestor

        Returns:
        """
        if self.logger is None:
            self.logger = get_base_logger(f'{self.__class__.__name__}({self.url_con_db})')

    def _set_session(self, eng_db=None):
        """
        Configura session para controlar workflow de transacciones (commit, rollback, close...)

        Args:
            eng_db:
        """
        session = sessionmaker()
        session.configure(bind=eng_db if eng_db else self.eng_db)
        self.session_db = session()

    def is_session_alive(self):
        """Valida si la session actual responde correctamente con un ping simple."""
        if not getattr(self, 'session_db', None):
            return False

        try:
            self.session_db.execute(text('SELECT 1'))
            return True
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Session no disponible, se intentará recuperar: {exc}")
            return False

    def recover_session(self, dispose_engine=False):
        """Recrea la sesión, opcionalmente reciclando el pool del engine."""
        try:
            if getattr(self, 'session_db', None):
                self.session_db.close()
        except Exception:
            pass

        if dispose_engine and getattr(self, 'eng_db', None):
            self.eng_db.dispose()

        self._set_session()
        return self.session_db

    def ensure_session(self):
        """Garantiza que la session está operativa; si no, la recupera."""
        if self.is_session_alive():
            return self.session_db

        self.recover_session(dispose_engine=False)
        if self.is_session_alive():
            return self.session_db

        # Último intento reciclando conexiones del pool.
        self.recover_session(dispose_engine=True)
        return self.session_db

    def __del__(self):
        """
        Cierra la conexion al matar la instancia
        """
        try:
            if hasattr(self, 'session_db'):
                self.session_db.close()
            if hasattr(self, "con_db"):
                self.eng_db = None
        except:
            pass

    def commit(self):
        """
        Hace commit sobre la sesion actual
        """
        if self.session_db:
            self.session_db.commit()

    def rollback(self):
        """
        Hace rollback sobre la sesion actual
        """
        if self.session_db:
            self.session_db.rollback()

    def iter_rows_result(self, query_res, nom_row=None):
        """
        Itera las filas del resultado como namedtuple con las claves de los campos seleccionados

        Args:
            query_res (sqlalchemy.engine.result.ResultProxy)
            nom_row (str=None): nombre de la clase namedtuple si aplica

        Yields:
            namedtuple o tuple
        """
        row_dd = None
        if query_res.keys():
            row_dd = namedtuple(nom_row if nom_row else 'row_result',
                                [n_col.replace(" ", "_") for n_col in query_res.keys()])

        for row in query_res:
            yield row_dd(*row) if row_dd else row

    def table_view(self, nom_tab_view, schema=None):
        """
        Retorna acceso a tabla sobre engine DB (

        Args:
            nom_tab_view (str):
            schema (str=None):

        Returns:

        """
        schema = self.check_exists_table_view(nom_tab_view, schema=schema)

        meta = MetaData()

        extra_args = {}
        if schema:
            extra_args['schema'] = schema

        a_tab = Table(nom_tab_view, meta, autoload_with=self.eng_db, **extra_args)

        return a_tab

    def tables_views(self, schema=None, only_tables=False) -> dict[str, list[str]]:
        """
        Lista las tablas/views disponibles para la conexion actual.

        Args:
            only_tables:
            schema (str=None): esquema a consultar; si es None, usa el search_path/por defecto.

        Returns:
            dict[str, list[str]]: diccionario con las tablas/views disponibles por esquema
        """
        inspector = inspect(self.eng_db)
        if not schema:
            schemas = inspector.get_schema_names()
        else:
            schemas = [schema]

        tables_views = {}
        for schema in schemas:
            tabs_schema = sorted(inspector.get_table_names(schema=schema))
            if not only_tables:
                tabs_schema.extend(sorted(inspector.get_view_names(schema=schema)))
            if not tabs_schema:
                continue
            tables_views[schema] = tabs_schema

        return tables_views

    def columns_table_view(self, nom_tab, schema=None):
        """
        Retorna columnas y tipos de una tabla o vista.

        Args:
            nom_tab (str): nombre de tabla o vista.
            schema (str=None): esquema a consultar.

        Returns:
            dict[str, str]: diccionario indexado por nombre de columna con el tipo.
        """
        schema = self.check_exists_table_view(nom_tab, schema=schema)

        # noinspection SqlResolve,SqlNoDataSourceInspection
        # language=PostgreSQL
        sql_query = text("""
                         SELECT a.attname                                       AS column_name,
                                pg_catalog.format_type(a.atttypid, a.atttypmod) AS column_type
                         FROM pg_catalog.pg_attribute a
                                  INNER JOIN pg_catalog.pg_class c
                                             ON c.oid = a.attrelid
                                  INNER JOIN pg_catalog.pg_namespace n
                                             ON n.oid = c.relnamespace
                         WHERE a.attnum > 0
                           AND NOT a.attisdropped
                           AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
                           AND c.relname = :table_name
                           AND (
                             (:schema IS NOT NULL AND n.nspname = :schema)
                                 OR (:schema IS NULL AND pg_catalog.pg_table_is_visible(c.oid))
                             )
                         ORDER BY a.attnum
                         """)

        res = self.ensure_session().execute(sql_query, {
            'table_name': nom_tab,
            'schema': schema,
        })

        cols = {}
        for row in res:
            cols[row.column_name] = row.column_type.replace('public.', '') if row.column_type else TYPE_UNKNOWN

        return cols

    def check_exists_table_view(self, nom_tab_or_view, schema=None) -> str:
        """
        Valida que exista una tabla o vista para la conexión actual y devuelve su esquema

        Args:
            nom_tab_or_view (str): nombre de tabla o vista.
            schema (str=None): esquema a consultar.

        Returns:
            str: schema de la tabla o vista.
        """
        schema_tab_view = None
        for sch, tabs_views in self.tables_views(schema=schema).items():
            if nom_tab_or_view in tabs_views:
                schema_tab_view = sch
                break

        if not schema_tab_view:
            raise ValueError(f"No existe la tabla/vista '{nom_tab_or_view}' "
                             f"{'para el esquema {} '.format(schema) if schema else ''}"
                             f"sobre la conexión '{self.url_con_db}'")

        return schema_tab_view

    def geoms_table_view(self, nom_tab, schema=None):
        """
        Retorna columnas geométricas/geográficas de una tabla o vista con metadatos detallados.

        Args:
            nom_tab (str): nombre de tabla o vista.
            schema (str=None): esquema a consultar

        Returns:
            dict[str, dict]: diccionario indexado por nombre de columna con metadatos geométricos.
        """
        schema = self.check_exists_table_view(nom_tab, schema=schema)

        # noinspection SqlResolve,SqlNoDataSourceInspection
        # language=PostgreSQL
        sql_query = text("""
                         SELECT a.attname                                                               AS column_name,
                                REPLACE(pg_catalog.format_type(a.atttypid, a.atttypmod), 'public.', '') AS column_type,
                                t.typname                                                               AS base_type
                         FROM pg_catalog.pg_attribute a
                                  INNER JOIN pg_catalog.pg_class c
                                             ON c.oid = a.attrelid
                                  INNER JOIN pg_catalog.pg_namespace n
                                             ON n.oid = c.relnamespace
                                  INNER JOIN pg_catalog.pg_type t
                                             ON t.oid = a.atttypid
                         WHERE a.attnum > 0
                           AND NOT a.attisdropped
                           AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
                           AND c.relname = :table_name
                           AND t.typname IN ('geometry', 'geography')
                           AND (
                             (:schema IS NOT NULL AND n.nspname = :schema)
                                 OR (:schema IS NULL AND pg_catalog.pg_table_is_visible(c.oid))
                             )
                         ORDER BY a.attnum
                         """)

        res = self.ensure_session().execute(sql_query, {
            'table_name': nom_tab,
            'schema': schema,
        })

        geoms = {}
        for row in res:
            type_str, base_type, geometry_type, srid = self.__parse_spatial_type(
                row.column_type,
                base_type_hint=row.base_type,
            )
            geoms[row.column_name] = {
                'type': type_str,
                'base_type': base_type,
                'geometry_type': geometry_type,
                'srid': srid,
            }

        return geoms

    @staticmethod
    def __parse_spatial_type(type_str, base_type_hint=None):
        """Parsea tipos espaciales tipo geometry(Point,25831) sin depender de funciones PostGIS."""
        if not type_str and not base_type_hint:
            return TYPE_UNKNOWN, TYPE_UNKNOWN, TYPE_UNKNOWN, None

        clean_type = (type_str or '').replace('public.', '').strip() or TYPE_UNKNOWN
        base_type = (base_type_hint or clean_type.split('(', 1)[0]).strip().lower()
        geometry_type = TYPE_UNKNOWN
        srid = None

        # Ejemplos esperados: geometry(Point,25831), geography(MultiPolygon,4326), geometry
        m = re.match(r'^(geometry|geography)\(([^,()]+)(?:\s*,\s*(\d+))?\)$', clean_type, flags=re.IGNORECASE)
        if m:
            base_type = m.group(1).lower()
            geometry_type = m.group(2)
            srid = int(m.group(3)) if m.group(3) else None
        elif clean_type.lower() in ('geometry', 'geography'):
            base_type = clean_type.lower()

        if base_type not in ('geometry', 'geography'):
            base_type = TYPE_UNKNOWN

        return clean_type, base_type, geometry_type, srid

    def rows_table_view(self, nom_tab, sql_query=None, **table_args):
        """
        Itera sobre los registros de la tabla

        Args:
            nom_tab (str):
            sql_query (str=None):
            **table_args: argumentos de la funcion table()

        Yields:
            namedtuple
        """
        tab = self.table_view(nom_tab, **table_args)

        query = tab.select()
        if sql_query:
            query = query.where(text(sql_query))

        res = self.ensure_session().execute(query)

        for row in self.iter_rows_result(res, tab.name):
            yield row

    def insert_rows_table(self, nom_tab, row_values, **table_args):
        """
        Inserta los registros en la tabla

        Args:
            nom_tab (str):
            row_values (list): lista de dicts con los valores de los campos a insertar por cada fila
            **table_args: argumentos de la funcion table()

        Returns:
            list: lista de los rows_inserted (namedtuple)
        """
        tab = self.table_view(nom_tab, **table_args)
        query = tab.insert(values=row_values).returning(*tab.columns())

        res = self.ensure_session().execute(query)

        rows_inserted = [*self.iter_rows_result(res, tab.name)]

        return rows_inserted

    def update_rows_table(self, tab, values, sql_query=None, **table_args):
        """
        Actualiza los registros de la tabla que cumplan con where_query (todos por defecto)

        Args:
            tab (str):
            values (dict):
            sql_query (str):
            **table_args: argumentos de la funcion table()

        Returns:
            generator: iterador con la lista de elementos a devolver
        """
        tab = self.table_view(tab, **table_args)
        query = tab.update()
        if sql_query:
            query = query.where(text(sql_query))
        query = query.values(values).returning(*tab.columns())

        res = self.ensure_session().execute(query)

        return res

    def remove_rows_table(self, nom_tab, sql_query=None, **table_args):
        """
        Borra los registros de la tabla que cumplan con where_query (todos por defecto)

        Args:
            nom_tab (str):
            sql_query (str):
            **table_args: argumentos de la funcion table()

        Returns:
            res
        """
        tab = self.table_view(nom_tab, **table_args)
        query = tab.delete()

        if sql_query:
            query = query.where(text(sql_query))

        res = self.ensure_session().execute(query)

        return res


if __name__ == '__main__':
    from fire import Fire

    Fire()
