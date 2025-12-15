import os
import unittest

import duckdb
import pandas as pd

from apb_duckdb_utils import get_duckdb_connection, import_csv_to_duckdb, list_tables_duckdb, \
    import_gdal_file_to_duckdb, \
    rename_cols_on_sql, set_types_geom_to_cols_wkt_on_sql, exclude_cols_on_sql, exists_table_duckdb, \
    quote_name_duckdb, import_dataframe_to_duckdb, import_parquet_to_duckdb, set_secret_s3_storage, exists_secret
from apb_extra_utils.misc import unzip
from apb_pandas_utils.geopandas_utils import gdf_from_df, df_geometry_columns

RESOURCES_DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))),
    'resources', 'data')
TEST_DB_PATH = os.path.join(RESOURCES_DATA_DIR, 'test.db')


class UtilsDuckDBTestCase(unittest.TestCase):
    unzip(os.path.join(RESOURCES_DATA_DIR, 'edificacio.zip'))
    csv_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio', 'edificacio.csv')
    geojson_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio-perimetre_base.geo.json')
    geoparquet_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio.geoparquet')

    def setUp(self):
        pass

    def test_get_connect(self):
        conn = get_duckdb_connection()
        dck_rel = conn.sql("SELECT 'HEY'")
        self.assertTrue('HEY' == dck_rel.to_df().iat[0, 0])

    def test_list_tables(self):
        conn = get_duckdb_connection(no_cached=True)
        conn.execute("CREATE TABLE IF NOT EXISTS test AS SELECT 'HEY'")
        list_tables = list_tables_duckdb(conn_db=conn, schemas=('main',))
        self.assertIn('test', list_tables)
        conn.execute("CREATE SCHEMA IF NOT EXISTS test_schema")
        conn.execute("CREATE TABLE IF NOT EXISTS test_schema.test AS SELECT 'HEY'")
        list_tables = list_tables_duckdb(conn_db=conn, schemas=('test_schema',))
        self.assertIn('test_schema.test', list_tables)
        list_tables = list_tables_duckdb(conn_db=conn)
        self.assertEqual(len(list_tables), 2)

    def test_get_connect_database(self):
        conn = get_duckdb_connection(no_cached=True)
        conn.execute(f"CREATE TABLE IF NOT EXISTS {quote_name_duckdb('test prueba')} AS SELECT 'HEY'")
        self.assertTrue(exists_table_duckdb('test prueba', conn_db=conn))
        row = conn.execute(f"FROM {quote_name_duckdb('test prueba')}").fetchone()
        self.assertTrue('HEY' == row[0])
        conn.execute("CREATE SCHEMA IF NOT EXISTS test_schema")
        t_name = quote_name_duckdb('test_schema.\"test prueba2\"')
        conn.execute(f"CREATE TABLE IF NOT EXISTS {t_name} AS SELECT 'HEY'")
        self.assertEqual(len(list_tables_duckdb(conn, ('test_schema',))), 1)
        self.assertTrue(exists_table_duckdb("test_schema.\"test prueba2\"", conn_db=conn))
        self.assertTrue(exists_table_duckdb("test_schema.test prueba2", conn_db=conn))

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

    def test_rename_cols_on_sql(self):
        conn = get_duckdb_connection(TEST_DB_PATH, as_current=True)
        sql_tab = conn.sql("SELECT 'HEY' as old_name")
        sql_tab = rename_cols_on_sql({'old_name': 'new_name'}, sql_tab)
        self.assertIn('new_name', sql_tab.columns)

    def test_import_csv(self):
        conn = get_duckdb_connection(TEST_DB_PATH, as_current=True)

        sql_tab = import_csv_to_duckdb(self.csv_path, 'edificacio_test', conn_db=conn, overwrite=True)
        row = sql_tab.fetchone()
        self.assertIsNotNone(row)
        n_cols_ant = len(sql_tab.columns)
        sql_tab = exclude_cols_on_sql(['DENOMINACIO'], sql_tab)
        self.assertEqual(n_cols_ant - 1, len(sql_tab.columns))
        try:
            sql_tab = import_csv_to_duckdb(self.csv_path, 'edificacio_test', conn_db=conn, overwrite=False)
        except duckdb.Error as e:
            sql_tab = None

        self.assertIsNone(sql_tab)

    def test_import_csv_with_geoms(self):
        conn = get_duckdb_connection(extensions=['spatial'], no_cached=True)
        sql = import_csv_to_duckdb(self.csv_path, 'edificacio',
                                   cols_wkt=['PERIMETRE_SUPERIOR', 'PERIMETRE_BASE', 'PUNT_BASE', 'DENOMINACIO'],
                                   as_view=True, conn_db=conn, overwrite=True)
        conn.sql("drop view edificacio")
        sql = import_csv_to_duckdb(self.csv_path, 'edificacio',
                                   cols_wkt=['PERIMETRE_SUPERIOR', 'PERIMETRE_BASE', 'PUNT_BASE', 'DENOMINACIO'],
                                   conn_db=conn, overwrite=True)
        row = sql.select('ST_AsText(ST_Centroid(perimetre_base)) as centroid').fetchone()
        self.assertTrue(str(row[0]).startswith('POINT'))

    def test_import_gdal_file_csv(self):
        sql = import_gdal_file_to_duckdb(self.csv_path, 'edificacio_gdal_csv', gdal_open_options=[
            'GEOM_POSSIBLE_NAMES=PERIMETRE_SUPERIOR,PERIMETRE_BASE,PUNT_BASE,DENOMINACIO'
        ], as_view=True, overwrite=True)
        row = sql.select('ST_AsText(ST_Centroid(geom_PERIMETRE_BASE)) as centroid').fetchone()
        self.assertTrue(str(row[0]).startswith('POINT'))

    def test_import_gdal_file_geojson(self):
        sql = import_gdal_file_to_duckdb(self.geojson_path, gdal_open_options=[], cols_alias={'geom': 'PERIMETRE BASE'})
        sql = sql.select('*, ST_AsText(ST_Centroid("PERIMETRE BASE")) AS centroid')
        sql = set_types_geom_to_cols_wkt_on_sql(
            ['centroid'],
            sql
        )
        geom_type = sql.select('ST_GeometryType(centroid)').fetchone()[0]
        self.assertTrue(geom_type == 'POINT')

    def test_import_dataframes(self):
        df = pd.read_csv(self.csv_path)
        sql = import_dataframe_to_duckdb(df, 'df',
                                         cols_wkt=['PERIMETRE_SUPERIOR', 'PERIMETRE_BASE', 'PUNT_BASE', 'DENOMINACIO'])
        row = sql.select('ST_AsText(ST_Centroid(PERIMETRE_BASE)) as centroid').fetchone()
        print(sql.columns)
        self.assertTrue(str(row[0]).startswith('POINT'))

        gdf = gdf_from_df(df, 'PERIMETRE_BASE', 'EPSG:4326',
                          ['PERIMETRE_SUPERIOR', 'PERIMETRE_BASE', 'PUNT_BASE', 'DENOMINACIO'])
        sql = import_dataframe_to_duckdb(gdf, 'gdf')
        row = sql.select('ST_AsText(ST_Centroid(PERIMETRE_BASE)) as centroid').fetchone()
        print(sql.columns)
        self.assertTrue(str(row[0]).startswith('POINT'))

    def test_import_geoparquet(self):
        df = pd.read_csv(self.csv_path)
        gdf = gdf_from_df(df, 'PERIMETRE_BASE', 'EPSG:4326',
                          ['PERIMETRE_SUPERIOR', 'PERIMETRE_BASE', 'PUNT_BASE', 'DENOMINACIO'])
        gdf.to_parquet(self.geoparquet_path)
        sql = import_parquet_to_duckdb(self.geoparquet_path, 'v_geoparquet',
                                       cols_geom=df_geometry_columns(gdf), as_view=True)
        row = sql.select('ST_AsText(ST_Centroid(PERIMETRE_BASE)) as centroid').fetchone()
        self.assertTrue(str(row[0]).startswith('POINT'))

        duckdb_parquet_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio_duckdb.geoparquet')
        sql.write_parquet(duckdb_parquet_path)
        sql = import_parquet_to_duckdb(duckdb_parquet_path, 'v_geoparquet_duckdb', as_view=True)
        row = sql.select('ST_AsText(ST_Centroid(PERIMETRE_BASE)) as centroid').fetchone()
        self.assertTrue(str(row[0]).startswith('POINT'))

    def test_connect_to_s3(self):
        conn = get_duckdb_connection(as_current=True, extensions=['spatial', 'httpfs'], )
        ok = set_secret_s3_storage(conn, endpoint=os.getenv('S3_ENDPOINT'), access_key_id=os.getenv('S3_ACCESS_KEY'),
                                   secret_access_key=os.getenv('S3_SECRET_KEY'), url_style=os.getenv('S3_URL_STYLE'),
                                   use_ssl=eval(os.getenv('S3_USE_SSL')), region=os.getenv('S3_REGION'),
                                   secret_name=(secret_name := os.getenv('S3_SECRET_NAME')))
        self.assertTrue(ok)

        exists = exists_secret(conn, secret_name)
        self.assertTrue(exists)

        df = pd.read_csv(self.csv_path)
        sql = import_dataframe_to_duckdb(df, 'df',
                                         cols_wkt=['PERIMETRE_SUPERIOR', 'PERIMETRE_BASE', 'PUNT_BASE', 'DENOMINACIO'], conn_db=conn)
        path_s3_parquet = 's3://apb-duckdb-utils-test/edificacio_duckdb_utils_test.parquet'
        sql.write_parquet(path_s3_parquet)
        sql_s3 = import_parquet_to_duckdb(path_s3_parquet, 'v_geoparquet_duckdb', as_view=True, conn_db=conn)

        sql_to_check_type_geom = 'ST_AsText(ST_Centroid(PERIMETRE_BASE)) as centroid'
        row = sql_s3.select(sql_to_check_type_geom).fetchone()
        print(row)
        self.assertTrue(str(row[0]).startswith('POINT'))

        sql_s3_via_api = conn.read_parquet(path_s3_parquet)
        row_via_api = sql_s3_via_api.select(sql_to_check_type_geom).fetchone()
        print(f"{row_via_api} == {row}")
        self.assertEqual(row_via_api, row)


if __name__ == '__main__':
    unittest.main()
