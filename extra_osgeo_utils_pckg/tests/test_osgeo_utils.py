import unittest
from functools import reduce

import extra_osgeo_utils
import os

PASSWORD_DB_POSTGRES = 'eam123'
USER_DB_POSTGRES = 'eam'

path_project = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path_data = os.path.join(path_project, 'resources/data')


class TestOsgeoUtils(unittest.TestCase):
    ds_gpkg, overwrite = extra_osgeo_utils.datasource_gdal_vector_file(
        'GPKG', 'edificacio', path_data)

    def setUp(self) -> None:
        self.host_pg = os.getenv('HOST_POSTGRES', 'db_pg_pyckg')
        self.port_pg = int(os.getenv('PORT_POSTGRES', 5432))

    def test_open_ds_gpkg(self):
        self.assertIsNotNone(self.ds_gpkg)

    def test_layer_gpkg(self):
        lyr = self.ds_gpkg.GetLayerByName('edificacio-perimetre_base')
        self.assertIsNotNone(lyr)

    def test_layer_geojson(self):
        ds, ovrwrt = extra_osgeo_utils.datasource_gdal_vector_file(
            'GeoJSON', 'edificacio-perimetre_base.geo', path_data)
        lyr = ds.GetLayer(0)
        self.assertIsNotNone(lyr)

    def test_layer_csv(self):
        ds, ovrwrt = extra_osgeo_utils.datasource_gdal_vector_file(
            'CSV', 'edificacio.zip', path_data, create=False, from_zip=True)
        lyr = ds.GetLayer(0)
        self.assertIsNotNone(lyr)

    def test_copy_layer(self):
        ds_dest, ovrwrt = extra_osgeo_utils.datasource_gdal_vector_file(
            'CSV', 'edificacio-perimetre_superior', path_data, create=True)
        lyr_orig = self.ds_gpkg.GetLayerByName('edificacio-perimetre_superior')
        lyr_dest = extra_osgeo_utils.copy_layer_gdal_to_ds_gdal(lyr_orig, ds_dest)
        self.assertIsNotNone(lyr_dest)
        self.assertEqual(lyr_orig.GetFeatureCount(), lyr_dest.GetFeatureCount())

    def test_postgis_conn(self):
        ds = extra_osgeo_utils.ds_postgis(dbname='GIS', host=self.host_pg, port=self.port_pg, user=USER_DB_POSTGRES,
                                          password=PASSWORD_DB_POSTGRES)
        self.assertIsNotNone(ds)

    def test_add_layer_mono_geom_to_postgis(self):
        lyr_orig = self.ds_gpkg.GetLayerByName('edificacio-perimetre_superior')
        ds = extra_osgeo_utils.ds_postgis(dbname='GIS', host=self.host_pg, port=self.port_pg, user=USER_DB_POSTGRES,
                                          password=PASSWORD_DB_POSTGRES)
        lyrs_dest = extra_osgeo_utils.add_layer_gdal_to_ds_gdal(
            ds, lyr_orig, nom_layer='edificacio', nom_geom='perimetre_superior', overwrite='OVERWRITE=YES')
        self.assertIsNotNone(lyrs_dest)
        self.assertEqual(lyr_orig.GetFeatureCount(),
                         reduce(sum, [lyr_dest.GetFeatureCount() for lyr_dest in lyrs_dest]))

    def test_add_layer_multi_geom_to_postgis(self):
        ds_csv, ovrwrt = extra_osgeo_utils.datasource_gdal_vector_file(
            'CSV', 'edificacio.zip', path_data, create=False, from_zip=True)
        lyr_orig = ds_csv.GetLayer(0)

        ds = extra_osgeo_utils.ds_postgis(dbname='GIS', host=self.host_pg, port=self.port_pg, user=USER_DB_POSTGRES,
                                          password=PASSWORD_DB_POSTGRES)
        lyrs_dest = extra_osgeo_utils.add_layer_gdal_to_ds_gdal(
            ds, lyr_orig, nom_layer='edificacio', multi_geom=True,
            overwrite='OVERWRITE=YES', promote_to_multi='PROMOTE_TO_MULTI=YES')
        self.assertIsNotNone(lyrs_dest)
        self.assertEqual(lyr_orig.GetFeatureCount(),
                         reduce(sum, [lyr_dest.GetFeatureCount() for lyr_dest in lyrs_dest]))

    def test_add_layer_multi_geom_to_gpkg(self):
        ds_csv, ovrwrt = extra_osgeo_utils.datasource_gdal_vector_file(
            'CSV', 'edificacio.zip', path_data, create=False, from_zip=True)
        lyr_orig = ds_csv.GetLayer(0)

        lyrs_dest = extra_osgeo_utils.add_layer_gdal_to_ds_gdal(
            self.ds_gpkg, lyr_orig, overwrite='OVERWRITE=YES', promote_to_multi='PROMOTE_TO_MULTI=YES')
        self.assertIsNotNone(lyrs_dest)
        self.assertEqual(4, len(lyrs_dest))

    def test_create_mono_geom_from_csv(self):
        layer_gdal, nom_layer_gdal, ds_gdal = extra_osgeo_utils.layer_gdal_from_file(
            os.path.join(path_data, 'edificacio.zip'), 'CSV', default_order_long_lat=False)
        for nom_geom in extra_osgeo_utils.geoms_layer_gdal(layer_gdal):
            fix_nom_geom = extra_osgeo_utils.fix_suffix_geom_name_layer_gdal(nom_geom, layer_gdal)
            ds_gdal_geojson, overwrited = extra_osgeo_utils.datasource_gdal_vector_file(
                'GEOJSON',
                "{}-{}".format(nom_layer_gdal, fix_nom_geom.lower()),
                path_data,
                create=True)
            extra_osgeo_utils.add_layer_gdal_to_ds_gdal(ds_gdal_geojson, layer_gdal, lite=True, srs_epsg_code=4326,
                                                  nom_geom=nom_geom)


if __name__ == '__main__':
    unittest.main()
