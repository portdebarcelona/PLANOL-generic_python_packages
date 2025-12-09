# Guía Rápida de Migración a GDAL 3.10

## 🚀 Inicio Rápido

### Paso 1: Actualizar el Entorno Conda

```bash
# Actualizar el entorno desde environment.yml
conda env update -f environment.yml --prune

# O crear un nuevo entorno
conda env create -f environment.yml
conda activate python_packages
```

### Paso 2: Verificar la Instalación de GDAL

```bash
python -c "from osgeo import gdal; print(f'GDAL Version: {gdal.__version__}')"
```

Debería mostrar: `GDAL Version: 3.10.x`

### Paso 3: Ejecutar Pruebas de Compatibilidad

```bash
python test_gdal_compatibility.py
```

Si todas las pruebas pasan, la migración fue exitosa.

### Paso 4: Ejecutar Tests Unitarios

```bash
# Instalar dependencias de prueba
pip install pytest

# Ejecutar tests
pytest apb_extra_osgeo_utils_pckg/tests/test_osgeo_utils.py -v
```

## 🔧 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'osgeo'"

**Solución:**
```bash
conda install -c conda-forge gdal=3.10
```

### Error: "GetMetadata_Dict not found"

**Solución:** Este es el comportamiento esperado en GDAL 3.10. El código ya incluye compatibilidad con `GetMetadata()`.

### Error: "Feature.items().items() - object is not iterable"

**Solución:** Este error ha sido corregido en el código. Asegúrate de tener la última versión.

## 📋 Cambios Principales

### 1. Driver Metadata
**Antes (GDAL 3.8):**
```python
metadata = driver.GetMetadata_Dict()
```

**Ahora (GDAL 3.10):**
```python
metadata = driver.GetMetadata()  # Retorna dict directamente
```

**Código Compatible:**
```python
if hasattr(driver, "GetMetadata_Dict"):
    metadata = driver.GetMetadata_Dict()
else:
    metadata = driver.GetMetadata()
```

### 2. Feature.items()
**Antes (GDAL 3.8):**
```python
for key, val in feature.items().items():
    print(key, val)
```

**Ahora (GDAL 3.10):**
```python
feat_items = feature.items()
if isinstance(feat_items, dict):
    for key, val in feat_items.items():
        print(key, val)
else:
    for key, val in feat_items:
        print(key, val)
```

### 3. Driver Validation
**Ahora se valida:**
```python
driver = ogr.GetDriverByName('GeoJSON')
if driver is None:
    raise ValueError("Driver not available")
```

## 🐳 Docker

Si usas Docker:

```bash
# Reconstruir la imagen
docker-compose build --no-cache

# Verificar versión GDAL en el contenedor
docker-compose run --rm app python -c "from osgeo import gdal; print(gdal.__version__)"
```

## 📦 Instalación de Desarrollo

Para desarrollo local:

```bash
# Navegar al directorio del paquete
cd apb_extra_osgeo_utils_pckg

# Instalar en modo desarrollo
pip install -e .
```

## ✅ Checklist de Migración

- [ ] Actualizar environment.yml con GDAL 3.10
- [ ] Reconstruir entorno Conda
- [ ] Verificar versión de GDAL instalada
- [ ] Ejecutar test_gdal_compatibility.py
- [ ] Ejecutar tests unitarios
- [ ] Probar con datos de producción
- [ ] Actualizar documentación del proyecto
- [ ] Actualizar CI/CD pipelines

## 📞 Soporte

Si encuentras problemas:

1. Revisa [GDAL_3.10_MIGRATION_NOTES.md](GDAL_3.10_MIGRATION_NOTES.md)
2. Ejecuta `test_gdal_compatibility.py` para diagnóstico
3. Verifica los logs de error completos
4. Consulta la [documentación oficial de GDAL](https://gdal.org/api/python.html)

## 🔗 Referencias

- [GDAL 3.10 Release Notes](https://gdal.org/download.html)
- [Python GDAL/OGR Cookbook](https://pcjericks.github.io/py-gdalogr-cookbook/)
- [GDAL Migration Guide](https://github.com/OSGeo/gdal/blob/master/MIGRATION_GUIDE.TXT)

---
**Última actualización:** 2025-11-29

