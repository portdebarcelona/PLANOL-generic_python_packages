import datetime
import unittest
import os
from functools import partial
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from geopandas import GeoDataFrame

from apb_extra_utils.misc import unzip
from apb_extra_utils.utils_logging import get_base_logger
from apb_pandas_utils import df_memory_usage
from apb_pandas_utils.geopandas_utils import (
    gdf_to_geojson,
    gdf_from_df,
    gdf_to_df,
    df_to_crs,
    gdf_from_url,
    gdf_from_pg_table,
)

RESOURCES_DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))),
    'resources', 'data')


class GeopandasUtilsTestCase(unittest.TestCase):
    unzip(os.path.join(RESOURCES_DATA_DIR, 'edificacio.zip'))
    csv_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio', 'edificacio.csv')
    geojson_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio-perimetre_base.geo.json')
    url_base = 'https://gisplanoldev.portdebarcelona.cat'
    logger = get_base_logger()

    def setUp(self):
        self.gdf_json = gpd.read_file(self.geojson_path, engine='pyogrio')
        self.df_csv = pd.read_csv(self.csv_path)
        self.user = os.getenv('TEST_USER_PG')
        self.psw = os.getenv('TEST_USER_PG_PASSWORD')
        self.srvr_db = os.getenv('TEST_HOST_PG')
        self.port_db = os.getenv('TEST_PORT_PG', 5432)
        self.db = os.getenv('TEST_DB_PG')
        self.schemas = os.getenv('TEST_SCHEMA_PG', 'gis,qgis')

    def test_gdf_to_geojson(self):
        self.logger.info('Converting GeoDataFrame to geojson')
        dict_geo = gdf_to_geojson(
            self.gdf_json,
            'Test geojson',
            with_crs=True,
            show_bbox=True,
            drop_id=False)
        self.logger.info(f'Geojson: {dict_geo}')

    def test_gdf_from_df(self):
        self.logger.info('Converting DataFrame to GeoDataFrame')
        gdf = gdf_from_df(self.df_csv, geom_col='PERIMETRE_BASE', crs='EPSG:4326',
                          cols_geom=['PERIMETRE_SUPERIOR', 'PUNT_BASE', 'DENOMINACIO'])
        gdf_epsg25831 = df_to_crs(gdf, 'EPSG:25831')
        self.logger.info(f'GeoDataFrame: {gdf_epsg25831.shape} | Memory: {df_memory_usage(gdf_epsg25831):.2f} MB')

        self.logger.info('Converting DataFrame with Index to GeoDataFrame')
        df_csv_idx = self.df_csv.copy().set_index('APB_ID')
        gdf = gdf_from_df(df_csv_idx, geom_col='PERIMETRE_BASE', crs='EPSG:4326',
                          cols_geom=['PERIMETRE_SUPERIOR', 'PUNT_BASE', 'DENOMINACIO'])
        self.logger.info(
            f'GeoDataFrame: {gdf.shape} with index {gdf.index.name} | Memory: {df_memory_usage(gdf_epsg25831):.2f} MB')

    def test_gdf_to_dataframe(self):
        self.logger.info('Converting GeoDataFrame to DataFrame as WKT')
        gdf_csv = gdf_from_df(self.df_csv, geom_col='PUNT_BASE', crs='EPSG:4326',
                              cols_geom=['PERIMETRE_SUPERIOR', 'PUNT_BASE', 'DENOMINACIO', 'PERIMETRE_BASE'])
        df = gdf_to_df(gdf_csv)
        self.logger.info(
            f'DF from CSV: {self.df_csv.shape} <> DF from GDF: {df.shape} | Memory: {df_memory_usage(df):.2f} MB')

        self.logger.info('Converting GeoDataFrame to DataFrame as WKB')
        df_wkb = gdf_to_df(gdf_csv, as_wkb=True)
        self.logger.info(f'DF from GDF with WKB: {df_wkb.shape} | Memory: {df_memory_usage(df_wkb):.2f} MB')

    def test_gdf_from_url_repo_gis(self):
        self.logger.info('Loading GeoDataFrame & Dataframes from URL Repo GIS')
        resp_auth = requests.post(
            f'{self.url_base}/repo_gis_pg/auth/acces-token',
            json=dict(
                username=os.getenv('DJANGO_API_USER'),
                key=os.getenv('DJANGO_API_KEY')
            )
        )
        headers = {'Authorization': f'Bearer {resp_auth.json().get("access")}'}
        url_geojson = f'{self.url_base}/repo_gis_pg/api_models_dades/edificacio-perimetre_base/'
        gdf_url = gdf_from_url(url_geojson, crs_api='EPSG:25831', headers=headers, add_goto_url=True)
        self.logger.info(f'GeoDataFrame from URL: {gdf_url.shape} | Memory: {df_memory_usage(gdf_url):.2f} MB')

        url_json = f'{self.url_base}/repo_gis_pg/api_administracio/origen_dades_gis/'
        df_url = gdf_from_url(url_json, headers=headers)
        self.logger.info(f'DataFrame from URL: {df_url.shape} | Memory: {df_memory_usage(df_url):.2f} MB')


    def test_gdf_from_url_escales(self):
        self.logger.info('Loading GeoDataFrame from URL Escales')
        resp_auth = requests.post(
            f'{self.url_base}/adm_escales/auth/acces-token',
            json=dict(
                username=os.getenv('DJANGO_API_USER'),
                key=os.getenv('DJANGO_API_KEY')
            )
        )
        headers = {'Authorization': f'Bearer {resp_auth.json().get("access")}'}
        url_geojson = f'{self.url_base}/adm_escales/api/track-ship-position/'
        api_params = dict(start=datetime.datetime.now().strftime('%Y-%m-%d'), limit=100)
        gdf_url: GeoDataFrame = gdf_from_url(url_geojson, api_params=api_params, crs_api='EPSG:4326', headers=headers,
                                             add_goto_url=True)
        self.logger.info(f'GeoDataFrame from URL: {gdf_url.shape} | Memory: {df_memory_usage(gdf_url):.2f} MB')
        gdf_url.to_file(filename=Path(RESOURCES_DATA_DIR) / 'track-ship-position.geojson', driver='GeoJSON')

    def test_gdf_from_pg_table(self):
        self.logger.info('Loading GeoDataFrame from PostgreSQL table edificacio')
        required = [self.user, self.psw, self.srvr_db, self.db]
        if any(v in (None, '') for v in required):
            self.skipTest('Faltan variables de entorno TEST_* para test PostgreSQL')

        schemas = self.schemas
        if 'gis_repo' not in [s.strip() for s in schemas.split(',') if s.strip()]:
            schemas = f"{schemas},gis_repo"

        call_gdf = partial(
            gdf_from_pg_table,
            user=self.user,
            psw=self.psw,
            srvr_db=self.srvr_db,
            port_db=self.port_db,
            db=self.db,
            schemas=schemas,
        )

        table = 'edificacio'
        self.assertRaises(ValueError, call_gdf,
                          table=table,
                          geom_col='non_existent_geom_col')

        gdf_pg = call_gdf(table=table)
        self.logger.info(f"GeoDataFrame from PG table '{table}': {gdf_pg.shape} | "
                         f"Memory: {df_memory_usage(gdf_pg):.2f} MB")
        self.logger.info(f"Active geometry column: {gdf_pg.geometry.name}")

        self.assertIsNotNone(gdf_pg)
        self.assertIsInstance(gdf_pg, GeoDataFrame)
        self.assertGreater(len(gdf_pg.columns), 0)
        self.assertIsNotNone(gdf_pg.geometry.name)
        self.assertIn(gdf_pg.geometry.name, gdf_pg.columns)
        self.assertEqual(gdf_pg.crs.to_string(), "EPSG:25831")

        table = 'edificacio-perimetre_base'
        gdf_pg = call_gdf(
            table=table,
            geom_col='PERIMETRE_BASE',
            filter_sql='"US_EDIFICACIO_ID" = 4',
            crs_gdf="EPSG:4326",
            add_goto_url=True,
        )
        self.logger.info(f"GeoDataFrame from PG table '{table}': {gdf_pg.shape} | "
                         f"Memory: {df_memory_usage(gdf_pg):.2f} MB")
        self.logger.info(f"Active geometry column: {gdf_pg.geometry.name}")

        self.assertIsNotNone(gdf_pg)
        self.assertIsInstance(gdf_pg, GeoDataFrame)
        self.assertIn('goto_url', gdf_pg.columns)
        self.assertIsNotNone(gdf_pg.geometry.name)
        self.assertIn(gdf_pg.geometry.name, gdf_pg.columns)
        self.assertEqual(gdf_pg.crs.to_string(), "EPSG:4326")


if __name__ == '__main__':
    unittest.main()
