import os
import unittest

import pandas as pd

from apb_extra_utils.misc import unzip
from apb_extra_utils.utils_logging import get_base_logger
from apb_pandas_utils import df_memory_usage, optimize_df, df_filtered_by_prop

RESOURCES_DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))),
    'resources', 'data')


class PandasUtilsTestCase(unittest.TestCase):
    unzip(os.path.join(RESOURCES_DATA_DIR, 'edificacio.zip'))
    csv_path = os.path.join(RESOURCES_DATA_DIR, 'edificacio', 'edificacio.csv')
    logger = get_base_logger()

    def setUp(self):
        self.df_csv = pd.read_csv(self.csv_path)
        self.df_csv.set_index('APB_ID', inplace=True)

    def test_optimize_df(self):
        self.logger.info('Optimize DataFrame')
        self.logger.info(f'DF before: {self.df_csv.shape} | Memory: {df_memory_usage(self.df_csv):.2f} MB')
        df_opt = optimize_df(self.df_csv)
        cols_categ = df_opt.select_dtypes(include=['category']).columns.tolist()
        self.logger.info(f'Columns: {cols_categ}')
        self.logger.info(f'DF after: {df_opt.shape} | Memory: {df_memory_usage(df_opt):.2f} MB')

    def test_filtered_by_prop(self):
        self.logger.info('Filter DataFrame by properties')
        df_csv = self.df_csv
        filter_props = {
            '>=NUMERO_PLANTES': 1,
            'SEQENTITAT': [250494, 250488, 250829],
            'TIPUS_EDIFICACIO': ['Edificació secundària o auxiliar', 'Edifici principal'],
        }
        df_filtered = df_filtered_by_prop(df_csv, filter_props)
        self.logger.info(f'DF filtered without categories: {df_filtered.shape} | '
                         f'Memory: {df_memory_usage(df_filtered):.2f} MB')

        df_cat = optimize_df(df_csv)
        df_filtered_cat = df_filtered_by_prop(df_cat, filter_props)
        self.logger.info(f'DF filtered with categories: {df_filtered_cat.shape} | '
                         f'Memory: {df_memory_usage(df_filtered_cat):.2f} MB')
        self.assertEqual(df_filtered_cat.shape[0], 3)

        # EAM - Test para comprobar que rango de valores (NUMERO_PLANTES) NOO filtra correctamente!!!
        filter_props['<=NUMERO_PLANTES'] = 2
        df_filtered_cat = df_filtered_by_prop(df_cat, filter_props)
        self.assertEqual(df_filtered_cat.shape[0], 3)


if __name__ == '__main__':
    unittest.main()
