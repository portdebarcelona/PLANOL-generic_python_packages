import os
import unittest

from apb_extra_utils.postgres_pckg.psql_alchemy import EngPsqlAlchemy, TYPE_UNKNOWN
from apb_extra_utils.utils_logging import get_base_logger


class TestPsqlAlchemy(unittest.TestCase):
    path_logs = os.path.join(os.path.dirname(__file__), "data")

    def setUp(self) -> None:
        self.user = os.getenv('TEST_USER_PG')
        self.psw = os.getenv('TEST_USER_PG_PASSWORD')
        self.srvr_db = os.getenv('TEST_HOST_PG')
        self.port_db = os.getenv('TEST_PORT_PG', 5432)
        self.db = os.getenv('TEST_DB_PG')
        self.schemas = os.getenv('TEST_SCHEMA_PG', 'gis,qgis')
        self.logger = get_base_logger('TestPsqlAlchemy')
        self.eng = EngPsqlAlchemy.get_cached(user=self.user, psw=self.psw, srvr_db=self.srvr_db, port_db=self.port_db,
                             db=self.db, schemas=self.schemas, a_logger=self.logger)

    def test_connection(self):
        self.logger.debug("Testing connection")
        eng = EngPsqlAlchemy(user=self.user, psw=self.psw, srvr_db=self.srvr_db, port_db=self.port_db,
                             db=self.db, schemas=self.schemas, a_logger=self.logger)
        self.logger.debug(f"Connection by params: {eng}")
        self.assertIsNotNone(eng)
        tab=eng.table('origen_dades_gis',)
        self.logger.debug(f"Table by args: {tab}")
        self.assertIsNotNone(tab)
        self.assertRaises(Warning, lambda: eng.table('adm_catalegs_gis'))
        eng=None
        conn_str=f"postgresql://{self.user}:{self.psw}@{self.srvr_db}:{self.port_db}/{self.db}"
        eng = EngPsqlAlchemy.get_cached(conn_string=conn_str, a_logger=self.logger)
        self.logger.debug(f"Connection by string: {eng}")
        self.assertIsNotNone(eng)
        tab=eng.table('adm_catalegs_gis', 'gis_repo')
        self.logger.debug(f"Table by string: {tab}")
        self.assertIsNotNone(tab)

    def test_tables_and_views(self):
        self.logger.debug("Testing tables and views")
        eng = EngPsqlAlchemy.get_cached(user=self.user, psw=self.psw, srvr_db=self.srvr_db, port_db=self.port_db,
                             db=self.db, schemas=self.schemas, a_logger=self.logger)
        tables = eng.tables(schema=self.schemas.split(',')[-1])
        views = eng.views()
        self.logger.debug(f"Tables: {tables}")
        self.assertIsNotNone(tables)
        self.logger.debug(f"Views: {views}")
        self.assertIsNotNone(views)

    def test_columns_table(self):
        self.logger.debug("Testing columns_table for gis_repo.edificacio")
        eng = self.eng
        cols = eng.columns_table('edificacio', schema='gis_repo')
        geom_cols = eng.geoms_table('edificacio', schema='gis_repo')
        self.logger.debug(f"Columns edificacio: {cols}")
        self.logger.debug(f"Geometry columns edificacio: {geom_cols}")

        self.assertIsNotNone(cols)
        self.assertIsInstance(cols, dict)
        self.assertGreater(len(cols), 0)
        self.assertIsInstance(geom_cols, dict)
        self.assertGreater(len(geom_cols), 0)
        for geom_col, geom_info in geom_cols.items():
            self.assertIn(geom_col, cols)
            self.assertIsInstance(geom_info, dict)
            self.assertEqual(cols[geom_col], geom_info['type'])
            self.assertEqual(geom_info['base_type'], 'geometry')
            self.assertNotEqual(geom_info['type'], TYPE_UNKNOWN)
            self.assertNotEqual(geom_info['geometry_type'], TYPE_UNKNOWN)
            self.assertIn('geometry', geom_info['type'].lower())
            self.assertIsInstance(geom_info['srid'], int)


if __name__ == '__main__':
    unittest.main()
