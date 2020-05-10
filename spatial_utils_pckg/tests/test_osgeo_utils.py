import unittest
from spatial_utils import osgeo_utils
import os

path_project = '/project'
path_data = os.path.join(path_project, 'resources/data')


class TestOsgeoUtils(unittest.TestCase):
    ds_gpkg, overwrite = osgeo_utils.datasource_gdal_vector_file(
        'GPKG', 'edificacio', path_data)

    def test_open_ds_gpkg(self):
        self.assertIsNotNone(self.ds_gpkg)

    def test_layer_gpkg(self):
        lyr = self.ds_gpkg.GetLayerByName('edificacio-perimetre_base')
        self.assertIsNotNone(lyr)

    def test_layer_geojson(self):
        ds, ovrwrt = osgeo_utils.datasource_gdal_vector_file(
            'GeoJSON', 'edificacio-perimetre_base.geo', path_data)
        lyr = ds.GetLayer(0)
        self.assertIsNotNone(lyr)

    def test_copy_layer(self):
        ds_dest, ovrwrt = osgeo_utils.datasource_gdal_vector_file(
            'CSV', 'edificacio-perimetre_superior', path_data, create=True
        )
        lyr_orig = self.ds_gpkg.GetLayerByName('edificacio-perimetre_superior')
        lyr_dest = osgeo_utils.copy_layer_gdal_to_ds_gdal(lyr_orig, ds_dest)
        self.assertIsNotNone(lyr_dest)
        self.assertEqual(lyr_orig.GetFeatureCount(), lyr_dest.GetFeatureCount())

    def test_postgis_conn(self):
        ds = osgeo_utils.ds_postgis(
            dbname='GIS', host='db_pg_pyckg', port=5432, user='eam', password='eam123')
        self.assertIsNotNone(ds)

    def test_add_layer_to_postgis(self):
        lyr_orig = self.ds_gpkg.GetLayerByName('edificacio-perimetre_superior')
        ds = osgeo_utils.ds_postgis(
            dbname='GIS', host='db_pg_pyckg', port=5432, user='eam', password='eam123')
        lyr_dest = osgeo_utils.add_layer_gdal_to_ds_gdal(
            ds, lyr_orig, nom_layer='edificacio', nom_geom='perimetre_superior')
        self.assertIsNotNone(lyr_dest)
        self.assertEqual(lyr_orig.GetFeatureCount(), lyr_dest.GetFeatureCount())


if __name__ == '__main__':
    unittest.main()
