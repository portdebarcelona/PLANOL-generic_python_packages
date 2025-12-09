#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar la compatibilidad con GDAL 3.10
"""
import sys

def test_gdal_import():
    """Test basic GDAL imports"""
    try:
        from osgeo import gdal, ogr, osr
        print(f"✓ GDAL imported successfully")
        print(f"  Version: {gdal.__version__}")
        return True
    except ImportError as e:
        print(f"✗ Failed to import GDAL: {e}")
        return False

def test_driver_access():
    """Test driver access with new API"""
    try:
        from osgeo import ogr

        # Test GetDriverByName
        driver = ogr.GetDriverByName('GeoJSON')
        if driver is None:
            print("✗ Failed to get GeoJSON driver")
            return False

        print(f"✓ Driver access working")

        # Test GetMetadata
        metadata = driver.GetMetadata()
        if metadata:
            print(f"✓ GetMetadata() working: {type(metadata)}")
            exts = metadata.get('DMD_EXTENSIONS', '')
            print(f"  Extensions: {exts}")

        # Test GetMetadata_Dict if available
        if hasattr(driver, 'GetMetadata_Dict'):
            metadata_dict = driver.GetMetadata_Dict()
            print(f"✓ GetMetadata_Dict() available: {type(metadata_dict)}")
        else:
            print(f"ℹ GetMetadata_Dict() not available (expected in GDAL 3.10+)")

        return True
    except Exception as e:
        print(f"✗ Driver access failed: {e}")
        return False

def test_feature_items():
    """Test Feature.items() behavior"""
    try:
        from osgeo import ogr, osr

        # Create in-memory dataset
        driver = ogr.GetDriverByName('Memory')
        ds = driver.CreateDataSource('test')

        # Create layer
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        layer = ds.CreateLayer('test_layer', srs, ogr.wkbPoint)

        # Add field
        field_def = ogr.FieldDefn('test_field', ogr.OFTString)
        layer.CreateField(field_def)

        # Create feature
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('test_field', 'test_value')

        # Test items()
        items = feature.items()
        print(f"✓ Feature.items() returns: {type(items)}")

        # Check if it's a dict
        if isinstance(items, dict):
            print(f"✓ Feature.items() returns dict directly")
            for key, val in items.items():
                print(f"  {key}: {val}")
        else:
            print(f"✓ Feature.items() returns iterable")
            for key, val in items:
                print(f"  {key}: {val}")

        return True
    except Exception as e:
        print(f"✗ Feature.items() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_spatial_reference():
    """Test SpatialReference and axis mapping"""
    try:
        from osgeo import osr

        srs = osr.SpatialReference()
        ret = srs.ImportFromEPSG(4326)

        if ret != 0:
            print(f"✗ Failed to import EPSG:4326")
            return False

        print(f"✓ SpatialReference EPSG import working")

        # Test OAMS_TRADITIONAL_GIS_ORDER
        try:
            from osgeo.osr import OAMS_TRADITIONAL_GIS_ORDER
            srs.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER)
            print(f"✓ OAMS_TRADITIONAL_GIS_ORDER available")
        except ImportError:
            print(f"ℹ OAMS_TRADITIONAL_GIS_ORDER not available")

        return True
    except Exception as e:
        print(f"✗ SpatialReference test failed: {e}")
        return False

def test_geometry_operations():
    """Test basic geometry operations"""
    try:
        from osgeo import ogr

        # Create geometry from WKT
        wkt = "POINT (1 1)"
        geom = ogr.CreateGeometryFromWkt(wkt)

        if geom is None:
            print(f"✗ Failed to create geometry from WKT")
            return False

        print(f"✓ Geometry creation working")

        # Test ExportToIsoWkt
        iso_wkt = geom.ExportToIsoWkt()
        print(f"✓ ExportToIsoWkt working: {iso_wkt}")

        # Test geometry type
        gtype = geom.GetGeometryType()
        print(f"✓ GetGeometryType: {gtype}")

        return True
    except Exception as e:
        print(f"✗ Geometry operations failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("GDAL 3.10 Compatibility Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("GDAL Import", test_gdal_import),
        ("Driver Access", test_driver_access),
        ("Feature.items()", test_feature_items),
        ("Spatial Reference", test_spatial_reference),
        ("Geometry Operations", test_geometry_operations),
    ]

    results = []
    for name, test_func in tests:
        print(f"\nTest: {name}")
        print("-" * 40)
        result = test_func()
        results.append((name, result))
        print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! GDAL 3.10 compatibility confirmed.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

