import unittest

import cx_Oracle
from cx_oracle_spatial.gestor_oracle import gestor_oracle


class MyTestCase(unittest.TestCase):
    def test_connect_oracle(self):
        dsn_ora = cx_Oracle.makedsn(host="db_ora_pyckg", port=1521, sid='xe')
        g = gestor_oracle("GIS", "GIS123", dsn_ora)
        self.assertIsNotNone(g)


if __name__ == '__main__':
    unittest.main()
