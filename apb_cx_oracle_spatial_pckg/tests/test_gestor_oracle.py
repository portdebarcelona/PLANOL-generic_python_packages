import os
import unittest

import cx_Oracle
from apb_cx_oracle_spatial.gestor_oracle import gestor_oracle
import apb_extra_osgeo_utils

path_project = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path_data = os.path.join(path_project, 'resources/data')


class MyTestCase(unittest.TestCase):
    """
    To run the tests over the db Oracle, run with system privileges  init_test_db.sql in the same folder as this file
    """
    dsn_ora = cx_Oracle.makedsn(host=os.getenv("HOST_DB_ORA", "db_ora_pyckg"),
                                port=os.getenv('PORT_DB_ORA', 1521), sid='xe')
    cache_gest = None

    @property
    def gest_ora(self):
        if not self.cache_gest:
            self.cache_gest = gestor_oracle("GIS", "GIS123", self.dsn_ora)
        return self.cache_gest

    def test_connect_oracle(self):
        self.assertIsNotNone(self.gest_ora)

    def test_call_func(self):
        ret = self.gest_ora.callfunc_sql('SDO_UTIL.FROM_WKTGEOMETRY',
                                         self.gest_ora.con_db.gettype("MDSYS.SDO_GEOMETRY"),
                                         'POINT (2.180045275 41.372005989)')
        self.assertIsNotNone(ret)

    def test_transactions_ora(self):
        g = self.gest_ora
        ds_csv, ovrwrt = apb_extra_osgeo_utils.datasource_gdal_vector_file(
            'CSV', 'edificacio.zip', path_data, create=False, from_zip=True)
        lyr_orig = ds_csv.GetLayer(0)
        geoms_lyr_orig = [*map(lambda fn: fn.replace('geom_', ''),
                               apb_extra_osgeo_utils.geoms_layer_gdal(lyr_orig))]
        pk_ora = g.get_primary_key_table('edificacio')
        for vals, wkt in ((nt, g.ExportToIsoWkt() if g else None) for f, g, nt in
                          apb_extra_osgeo_utils.feats_layer_gdal(lyr_orig, 'punt_base')):
            alfa_vals = {k: val for k, val in vals._asdict().items()
                         if k.upper() not in geoms_lyr_orig}
            key_vals = {k: val for k, val in alfa_vals.items() if k in pk_ora}
            r_tab = g.row_table_at('edificacio', *key_vals.values())
            if r_tab:
                g.update_row_tab('edificacio', key_vals, alfa_vals)
            else:
                g.insert_row_tab('edificacio', alfa_vals)

        g.con_db.commit()
        cont_ora = g.row_sql('select count(*) as cont from edificacio').CONT
        self.assertEqual(lyr_orig.GetFeatureCount(), cont_ora)


if __name__ == '__main__':
    unittest.main()
