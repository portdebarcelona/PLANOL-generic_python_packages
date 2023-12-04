import unittest
from duckdb_utils import get_duckdb_connection


class UtilsDuckDBTestCase(unittest.TestCase):
    def test_get_connect(self):
        conn = get_duckdb_connection()
        dck_rel = conn.sql("SELECT 'HEY'")
        self.assertTrue('HEY' == dck_rel.to_df().iat[0, 0])


if __name__ == '__main__':
    unittest.main()
