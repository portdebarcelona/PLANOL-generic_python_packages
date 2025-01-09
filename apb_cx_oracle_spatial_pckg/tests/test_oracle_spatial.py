import unittest
import os
from cx_Oracle import makedsn
from apb_cx_oracle_spatial.gestor_oracle import gestor_oracle


class APBOracleCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dsn_ora = makedsn(host=os.getenv("HOST_DB_ORA", "ORANORDPRE.port.apb.es"),
                               port=os.getenv('PORT_DB_ORA', 1521), sid='GISDATAPRE')
        self.cache_gest = g = gestor_oracle("GISHISREP", "GISHISREP", self.dsn_ora)

    def test_connect_gisdata(self):
        self.assertIsNotNone(self.cache_gest)


if __name__ == '__main__':
    unittest.main()
