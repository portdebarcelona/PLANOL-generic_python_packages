import unittest
import os
from duckdb_utils import get_duckdb_connection, import_csv_to_duckdb, list_tables_duckdb
from extra_utils.misc import unzip

RESOURCES_DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))),
    'resources', 'data')
TEST_DB_PATH = os.path.join(RESOURCES_DATA_DIR, 'test.db')


class UtilsDuckDBTestCase(unittest.TestCase):
    def test_get_connect(self):
        conn = get_duckdb_connection()
        dck_rel = conn.sql("SELECT 'HEY'")
        self.assertTrue('HEY' == dck_rel.to_df().iat[0, 0])

    def test_get_connect_database(self):
        conn = get_duckdb_connection(TEST_DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS test AS SELECT 'HEY'")
        row = conn.execute("SELECT * FROM test").fetchone()
        self.assertTrue('HEY' == row[0])

    def test_get_connect_database_as_current(self):
        conn = get_duckdb_connection(TEST_DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS test AS SELECT 'HEY'")
        # Not set as current then return memory db
        conn = get_duckdb_connection()
        list_tables = list_tables_duckdb(conn_db=conn)
        self.assertNotIn('test', list_tables)
        conn = get_duckdb_connection(TEST_DB_PATH, as_current=True)
        # Set as current then return test.db
        conn = get_duckdb_connection()
        row = conn.sql("SELECT * FROM test").fetchone()
        self.assertTrue('HEY' == row[0])

    def test_import_csv(self):
        conn = get_duckdb_connection(TEST_DB_PATH, as_current=True)
        unzip(os.path.join(RESOURCES_DATA_DIR, 'edificacio.zip'))
        import_csv_to_duckdb(os.path.join(RESOURCES_DATA_DIR, 'edificacio', 'edificacio.csv'), conn_db=conn,
                             overwrite=True)
        row = conn.execute("SELECT * FROM edificacio").fetchone()
        self.assertIsNotNone(row)
        conn.execute("DROP TABLE IF EXISTS edificacio")
        import_csv_to_duckdb(os.path.join(RESOURCES_DATA_DIR, 'edificacio', 'edificacio.csv'),
                             table_name='edificacio_test', conn_db=conn, overwrite=True)
        row = conn.execute("SELECT * FROM edificacio_test").fetchone()
        self.assertIsNotNone(row)

    def test_import_csv_with_geoms(self):
        conn = get_duckdb_connection(extensions=['spatial'])
        unzip(os.path.join(RESOURCES_DATA_DIR, 'edificacio.zip'))
        import_csv_to_duckdb(
            os.path.join(RESOURCES_DATA_DIR, 'edificacio', 'edificacio.csv'),
            cols_geom=['PERIMETRE_SUPERIOR', 'PERIMETRE_BASE', 'PUNT_BASE', 'DENOMINACIO'],
            conn_db=conn,
            overwrite=True)
        row = conn.execute("SELECT * FROM edificacio").fetchone()
        self.assertIsNotNone(row)


if __name__ == '__main__':
    unittest.main()
