import unittest
import os
from logging import DEBUG
from pathlib import Path

from oracledb import makedsn
from shapely.geometry.point import Point

from apb_cx_oracle_spatial.gestor_oracle import gestor_oracle, iter_execute_fetch_sql, execute_fetch_sql
from apb_extra_utils.utils_logging import get_base_logger


class APBOracleCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dsn_ora = makedsn(host=os.getenv("HOST_DB_ORA"),
                               port=os.getenv('PORT_DB_ORA', 1521), sid=os.getenv('SID_DB_ORA', 'xe'))
        self.gest_ora = g = gestor_oracle(
            os.getenv("USER_DB_ORA"), os.getenv("PASSWORD_DB_ORA"), self.dsn_ora,
            a_logger=get_base_logger('test_oracle_spatial', DEBUG),
            schema_ora=os.getenv("SCHEMA_ORA"),
        )
        self.table_to_test = os.getenv('TABLE_TO_TEST', 'ARBRE')

    def test_connect_gisdata(self):
        self.assertIsNotNone(self.gest_ora)

    def test_call_func(self):
        ret = self.gest_ora.callfunc_sql('SDO_UTIL.FROM_WKTGEOMETRY',
                                         self.gest_ora.con_db.gettype("MDSYS.SDO_GEOMETRY"),
                                         'POINT (2.180045275 41.372005989)')
        self.assertIsNotNone(ret)

    def test_create_geojsons_tab_or_view(self):
        geojson = self.gest_ora.create_geojsons_tab_or_view(
            'edificacio', by_geom='PERIMETRE_BASE',
            dir=Path(os.path.dirname(os.path.abspath(__file__))) / 'data' / 'results', )

    def test_row_table_at(self):
        row = self.gest_ora.row_table_at(self.table_to_test, 5971638)
        self.assertIsNotNone(row)
        self.assertEqual(row.APB_ID, 5971638)

    def test_iter_fetch_sql(self):
        num_rows = self.gest_ora.row_sql(f'select count(*) as count from {self.table_to_test}')[0]
        count = 0
        for row in iter_execute_fetch_sql(
                self.gest_ora.con_db,
                f'SELECT * FROM {self.table_to_test}',
                logger=self.gest_ora.logger,
                prefetchrows=0,
                arraysize=5000):
            count += 1
        self.assertEqual(count, num_rows)

    def test_execute_fetch_sql(self):
        row = execute_fetch_sql(self.gest_ora.con_db, 'select * from ARBRE where APB_ID=:1', 5971638, geom_format='as_shapely')
        self.assertEqual(row.APB_ID, 5971638)
        self.assertIsInstance(row.PUNT_BASE, Point)

    def test_update_row_tab(self):
        row = self.gest_ora.row_table_at(self.table_to_test, 5971638)
        row_updated = self.gest_ora.update_row_tab(self.table_to_test, {'APB_ID': 5971638}, row._asdict())
        self.assertEqual(row_updated.PUNT_BASE, row.PUNT_BASE)


if __name__ == '__main__':
    unittest.main()
