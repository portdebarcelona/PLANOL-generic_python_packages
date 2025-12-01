# ✅ Checklist de Validación Post-Migración GDAL 3.10

## Pre-requisitos
- [ ] Python 3.10 instalado
- [ ] Conda o Miniconda instalado
- [ ] Acceso al repositorio actualizado

## 1. Actualización del Entorno

### Opción A: Actualizar entorno existente
```bash
conda activate python_packages
conda env update -f environment.yml --prune
```
- [ ] Comando ejecutado sin errores
- [ ] No hay conflictos de dependencias

### Opción B: Crear entorno nuevo
```bash
conda env create -f environment.yml
conda activate python_packages
```
- [ ] Entorno creado exitosamente
- [ ] Entorno activado correctamente

## 2. Verificación de Instalación

### Verificar versión de GDAL
```bash
python -c "from osgeo import gdal; print(f'GDAL Version: {gdal.__version__}')"
```
**Resultado esperado:** `GDAL Version: 3.10.x`

- [ ] GDAL 3.10.x instalado correctamente
- [ ] No hay errores de importación

### Verificar módulos GDAL
```bash
python -c "from osgeo import gdal, ogr, osr; print('✓ All GDAL modules imported')"
```
- [ ] Todos los módulos importan correctamente

## 3. Tests de Compatibilidad

### Ejecutar script de compatibilidad
```bash
python test_gdal_compatibility.py
```

Verificar que todos los tests pasen:
- [ ] ✓ GDAL Import
- [ ] ✓ Driver Access
- [ ] ✓ Feature.items()
- [ ] ✓ Spatial Reference
- [ ] ✓ Geometry Operations

**Resultado esperado:** `Results: 5/5 tests passed`

## 4. Tests Unitarios

### Instalar pytest (si no está instalado)
```bash
pip install pytest
```
- [ ] pytest instalado

### Ejecutar tests del paquete principal
```bash
pytest apb_extra_osgeo_utils_pckg/tests/test_osgeo_utils.py -v
```
- [ ] Tests ejecutados
- [ ] Número de tests pasados: _____
- [ ] Número de tests fallidos: _____

### Tests esperados que deben pasar:
- [ ] test_open_ds_gpkg
- [ ] test_layer_gpkg
- [ ] test_layer_geojson
- [ ] test_layer_csv
- [ ] test_copy_layer

## 5. Validación Funcional

### Test 1: Crear GeoJSON
```python
from osgeo import ogr, osr

driver = ogr.GetDriverByName('GeoJSON')
ds = driver.CreateDataSource('/tmp/test.geojson')
srs = osr.SpatialReference()
srs.ImportFromEPSG(4326)
layer = ds.CreateLayer('test', srs, ogr.wkbPoint)
print("✓ GeoJSON creation works")
```
- [ ] Sin errores
- [ ] Archivo creado correctamente

### Test 2: Leer metadata de driver
```python
from osgeo import ogr

driver = ogr.GetDriverByName('GPKG')
metadata = driver.GetMetadata()
print(f"Extensions: {metadata.get('DMD_EXTENSIONS', 'N/A')}")
```
- [ ] Metadata obtenida correctamente
- [ ] Extensions mostradas

### Test 3: Feature.items()
```python
from osgeo import ogr

driver = ogr.GetDriverByName('Memory')
ds = driver.CreateDataSource('test')
layer = ds.CreateLayer('test')
feat = ogr.Feature(layer.GetLayerDefn())
items = feat.items()
print(f"Type: {type(items)}")
```
- [ ] Sin errores
- [ ] Tipo correcto obtenido

## 6. Validación con Datos Reales

### Test con archivo GeoJSON
```bash
python -c "
import apb_extra_osgeo_utils as utils
# Usar tu propio archivo GeoJSON aquí
layer, name, ds = utils.layer_gdal_from_file('ruta/a/tu/archivo.geojson')
print(f'Layer: {name}, Features: {layer.GetFeatureCount()}')
"
```
- [ ] Archivo leído correctamente
- [ ] Features contadas correctamente

### Test con GPKG
```bash
python -c "
import apb_extra_osgeo_utils as utils
ds, created = utils.datasource_gdal_vector_file('GPKG', 'test_gpkg', '/tmp')
print(f'GPKG created: {created}')
"
```
- [ ] GPKG creado/abierto correctamente

## 7. Validación Docker (Opcional)

### Rebuild Docker image
```bash
docker-compose build --no-cache
```
- [ ] Imagen construida sin errores
- [ ] GDAL 3.10 en la imagen

### Verificar GDAL en container
```bash
docker-compose run --rm app python -c "from osgeo import gdal; print(gdal.__version__)"
```
- [ ] GDAL 3.10.x en container

## 8. Validación de Documentación

- [ ] GDAL_3.10_MIGRATION_NOTES.md revisado
- [ ] MIGRATION_QUICKSTART.md revisado
- [ ] README.md actualizado visible
- [ ] Cambios de código comprendidos

## 9. Integración Continua

### Verificar pipelines CI/CD
- [ ] GitHub Actions actualizado (si aplica)
- [ ] Jenkins pipeline actualizado (si aplica)
- [ ] Tests automáticos pasan

## 10. Rollback Plan

### En caso de problemas, rollback a versión anterior:
```bash
# Restaurar environment.yml anterior
git checkout HEAD~1 -- environment.yml environment.docker.yml

# Actualizar entorno
conda env update -f environment.yml --prune
```
- [ ] Procedimiento de rollback documentado
- [ ] Backup del código anterior disponible

## 📊 Resumen de Validación

### Resultados:
- Total checks: _____ / _____
- Estado general: [ ] ✅ Aprobado [ ] ⚠️ Con observaciones [ ] ❌ Fallido

### Observaciones:
```
_____________________________________________
_____________________________________________
_____________________________________________
```

### Problemas Encontrados:
```
_____________________________________________
_____________________________________________
_____________________________________________
```

### Acción Requerida:
- [ ] Ninguna - Todo funcionando correctamente
- [ ] Investigar warnings menores
- [ ] Realizar ajustes adicionales
- [ ] Ejecutar rollback

## 📝 Notas Adicionales

### Performance:
- [ ] Operaciones más rápidas que antes
- [ ] Operaciones igual de rápidas
- [ ] Operaciones más lentas (investigar)

### Compatibilidad:
- [ ] Compatible con todos los archivos existentes
- [ ] Algunos archivos requieren conversión
- [ ] Problemas de compatibilidad (especificar)

### Documentación:
- [ ] Documentación clara y suficiente
- [ ] Necesita más ejemplos
- [ ] Necesita más detalles técnicos

## ✅ Aprobación Final

**Validado por:** _____________________  
**Fecha:** _____________________  
**Firma:** _____________________

**Estado:** 
- [ ] ✅ APROBADO - Listo para producción
- [ ] ⚠️ APROBADO CON OBSERVACIONES
- [ ] ❌ RECHAZADO - Requiere correcciones

---

## 🆘 Soporte

Si algún check falla:
1. Revisar [MIGRATION_QUICKSTART.md](MIGRATION_QUICKSTART.md)
2. Ejecutar `python test_gdal_compatibility.py` para diagnóstico
3. Consultar [GDAL_3.10_MIGRATION_NOTES.md](GDAL_3.10_MIGRATION_NOTES.md)
4. Contactar al equipo de desarrollo

---
**Última actualización:** 2025-11-29

