import unittest
import os

import geopandas as gpd
import pandas as pd
from apb_extra_utils.misc import unzip
from apb_extra_utils.utils_logging import get_base_logger
from apb_pandas_utils import df_memory_usage
from apb_pandas_utils.geopandas_utils import gdf_to_geojson, gdf_from_df, gdf_to_df, df_to_crs

RESOURCES_DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))),
    'resources', 'data')


class GeopandasUtilsTestCase(unittest.TestCase):
    unzip(os.path.join(RESOURCES_DATA_DIR, 'edificacio.zip'))
    csv_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio', 'edificacio.csv')
    geojson_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio-perimetre_base.geo.json')
    logger = get_base_logger()

    def setUp(self):
        self.gdf_json = gpd.read_file(self.geojson_path, engine='pyogrio')
        self.df_csv = pd.read_csv(self.csv_path)

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
        self.logger.info(f'GeoDataFrame: {gdf.shape} with index {gdf.index.name} | Memory: {df_memory_usage(gdf_epsg25831):.2f} MB')

    def test_gdf_to_dataframe(self):
        self.logger.info('Converting GeoDataFrame to DataFrame as WKT')
        gdf_csv = gdf_from_df(self.df_csv, geom_col='PUNT_BASE', crs='EPSG:4326',
                              cols_geom=['PERIMETRE_SUPERIOR', 'PUNT_BASE', 'DENOMINACIO', 'PERIMETRE_BASE'])
        df = gdf_to_df(gdf_csv)
        self.logger.info(f'DF from CSV: {self.df_csv.shape} <> DF from GDF: {df.shape} | Memory: {df_memory_usage(df):.2f} MB')

        self.logger.info('Converting GeoDataFrame to DataFrame as WKB')
        df_wkb = gdf_to_df(gdf_csv, as_wkb=True)
        self.logger.info(f'DF from GDF with WKB: {df_wkb.shape} | Memory: {df_memory_usage(df_wkb):.2f} MB')


if __name__ == '__main__':
    unittest.main()
