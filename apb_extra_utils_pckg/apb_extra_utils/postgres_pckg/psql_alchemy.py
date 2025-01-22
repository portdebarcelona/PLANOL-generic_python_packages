#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 31/03/2019
#  Copyright (c)
from apb_extra_utils.utils_logging import get_file_logger
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import create_engine
from sqlalchemy import MetaData, Table, text
from collections import namedtuple


class EngPsqlAlchemy(object):
    """
    Clase que gestiona conexion sqlalchemy a Postgres
    """
    __slots__ = 'nom_con_db', 'eng_db', 'psw_con_db', 'logger', 'session_db'

    def __init__(self, user, psw, srvr_db='localhost', port_db=5432, db='postgres', a_logger=None):
        """
        Retorna engine para database postgres. Si no se informa ningun argumento retorna el cacheado

        Args:
            user (str):
            psw (str):
            srvr_db (str=None):
            port_db (int=None):
            db (str=None):

        Returns:
            sqlalchemy.engine.base.Engine
        """
        nom_con = f"{user.upper()}@{db.upper()}"
        self.nom_con_db = nom_con

        self.logger = a_logger

        self.__set_logger()
        self.__set_conexion(user, psw, srvr_db, port_db, db)

    def __set_logger(self):
        """
        Asigna el LOGGER po defecto si este no se ha informado al inicializar el gestor

        Returns:
        """
        if self.logger is None:
            self.logger = get_file_logger(f'{self.__class__.__name__}({self.nom_con_db})')

    def __set_conexion(self, user, psw, srvr_db, port_db, db):
        """
        Crea engine para database postgres con sqlalchemy

        Args:
            user (str):
            psw (str):
            srvr_db (str):
            port_db (int):
            db (str):
        """
        str_conn = f'postgresql://{user}:{psw}@{srvr_db}:{port_db}/{db}'
        eng_db = create_engine(str_conn)

        eng_db.connect()

        self.eng_db = eng_db
        # self.eng_db.logger = self.logger
        self._set_session()
        self.psw_con_db = psw

    def _set_session(self, eng_db=None):
        """
        Configura session para controlar workflow de transacciones (commit, rollback, close...)

        Args:
            eng_db:
        """
        Session = sessionmaker()
        Session.configure(bind=eng_db if eng_db else self.eng_db)
        self.session_db = Session()

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

    def table(self, nom_tab, schema=None):
        """
        Retorna acceso a tabla sobre engine DB (

        Args:
            nom_tab (str):
            schema (str=None):

        Returns:

        """
        if not self.eng_db.has_table(nom_tab, schema):
            raise Warning(f"No existe la tabla '{nom_tab}' "
                          f"{'para el esquema {} '.format(schema) if schema else ''}"
                          f"sobre el user@database '{self.nom_con_db}'")

        meta = MetaData()

        extra_args = {}
        if schema:
            extra_args['schema'] = schema

        a_tab = Table(nom_tab, meta, autoload=True, autoload_with=self.eng_db, **extra_args)

        self.session_db.bind_table(a_tab, self.eng_db)

        return a_tab

    def rows_table(self, nom_tab, sql_query=None, **table_args):
        """
        Itera sobre los registros de la tabla

        Args:
            nom_tab (str):
            sql_query (str=None):
            **table_args: argumentos de la funcion table()

        Yields:
            namedtuple
        """
        tab = self.table(nom_tab, **table_args)

        query = tab.select(text(sql_query) if sql_query else None)

        res = self.session_db.execute(query)

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
        tab = self.table(nom_tab, **table_args)
        query = tab.insert(values=row_values).returning(*tab.columns)

        res = self.session_db.execute(query)

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
        tab = self.table(tab, **table_args)
        query = tab.update().where(text(sql_query)).values(values).returning(*tab.columns)

        res = self.session_db.execute(query)

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
        tab = self.table(nom_tab, **table_args)
        query = tab.delete()

        if sql_query:
            query = query.where(text(sql_query))

        res = self.session_db.execute(query)

        return res


if __name__ == '__main__':
    from fire import Fire

    Fire()