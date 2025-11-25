import unittest
import os
from logging import DEBUG
from pathlib import Path

from oracledb import makedsn
from apb_cx_oracle_spatial.gestor_oracle import gestor_oracle
from apb_extra_utils.utils_logging import get_base_logger


class APBOracleCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dsn_ora = makedsn(host=os.getenv("HOST_DB_ORA"),
                               port=os.getenv('PORT_DB_ORA', 1521), sid=os.getenv('SID_DB_ORA', 'xe'))
        self.gest_ora = g = gestor_oracle(
            os.getenv("USER_DB_ORA"), os.getenv("PASSWORD_DB_ORA"), self.dsn_ora,
        a_logger=get_base_logger('test_oracle_spatial', DEBUG),)

    def test_connect_gisdata(self):
        self.assertIsNotNone(self.gest_ora)

    def test_call_func(self):
        ret = self.gest_ora.callfunc_sql('SDO_UTIL.FROM_WKTGEOMETRY',
                                         self.gest_ora.con_db.gettype("MDSYS.SDO_GEOMETRY"),
                                         'POINT (2.180045275 41.372005989)')
        self.assertIsNotNone(ret)

    def test_create_geojsons_tab_or_view(self):
        geojson = self.gest_ora.create_geojsons_tab_or_view(
            'ARBRE',
            dir=Path(os.path.dirname(os.path.abspath(__file__))) / 'data' / 'results',)


if __name__ == '__main__':
    unittest.main()
