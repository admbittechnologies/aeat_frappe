# Guia de Configuracion - ERPNext ES AEAT

## Tabla de contenidos

1. [Configuracion inicial](#configuracion-inicial)
2. [AEAT Tax Map](#aeat-tax-map)
3. [Mapeo PGC predefinido](#mapeo-pgc-predefinido)
4. [Configuracion BOE](#configuracion-boe)
5. [Flujo de trabajo](#flujo-de-trabajo)
6. [Resolucion de problemas](#resolucion-de-problemas)

---

## Configuracion inicial

### 1.1 Configurar la empresa

**Pantalla:** Configuracion > Empresa > [Tu Empresa]

```
- NIF / Tax ID: B12345678 (tu CIF/NIF real)
- Nombre fiscal: Mi Empresa SL (nombre completo para el modelo)
```

### 1.2 Verificar cuentas contables

El modulo usa las siguientes cuentas estandar del PGC:

| Cuenta | Descripcion | Uso |
|--------|-------------|-----|
| 430000 | Deudores por ventas | Clientes (IVA devengado) |
| 400000 | Acreedores por compras | Proveedores (IVA deducible) |
| 477100 | IVA Repercutido 21% | Ventas IVA 21% |
| 477110 | IVA Repercutido 10% | Ventas IVA 10% |
| 477120 | IVA Repercutido 4% | Ventas IVA 4% |
| 472100 | IVA Soportado 21% | Compras IVA 21% |
| 472110 | IVA Soportado 10% | Compras IVA 10% |
| 472120 | IVA Soportado 4% | Compras IVA 4% |

### 1.3 Crear plantillas de impuestos

**Pantalla:** Contabilidad > Plantilla de impuestos > Nuevo

Crear las siguientes plantillas:

**Ventas:**
- IVA 21% - Ventas
- IVA 10% - Ventas
- IVA 4% - Ventas
- IVA 0% - Ventas Intracomunitarias
- IVA 0% - Servicios UE

**Compras:**
- IVA 21% - Compras
- IVA 10% - Compras
- IVA 4% - Compras
- IVA 0% - Adquisicion Intracomunitaria Bienes
- IVA 0% - Adquisicion Intracomunitaria Servicios

### 1.4 Crear Item Tax Templates

**Pantalla:** Stock > Item Tax Template > Nuevo

Asignar a cada producto/servicio el template correspondiente segun el tipo de IVA.

---

## AEAT Tax Map

El Tax Map relaciona las cuentas de impuestos del ERPNext con las casillas del modelo AEAT.

### Estructura de una linea de Tax Map

| Campo | Descripcion | Ejemplo |
|-------|-------------|---------|
| field_number | Numero de casilla AEAT | 1, 3, 4, 6... |
| box_name | Nombre descriptivo | "Base 21% regimen general" |
| source | Fuente (tax/gl) | tax |
| field_type | Tipo (base/cuota) | base |
| sum_type | Suma (sale/purchase/both) | both |
| move_type | Tipo de movimiento | all |
| accounts | Cuentas contables | 477100 - IVA Repercutido 21% |

### Tax Map para Modelo 303 (estandar)

| Casilla | Nombre | Tipo | Cuentas (ventas) | Cuentas (compras) |
|---------|--------|------|-----------------|-------------------|
| 01 | Base 21% regimen general | base | 477100 | 472100 |
| 03 | Cuota 21% regimen general | cuota | 477100 | 472100 |
| 04 | Base 10% regimen reducido | base | 477110 | 472110 |
| 06 | Cuota 10% regimen reducido | cuota | 477110 | 472110 |
| 07 | Base 4% superreducido | base | 477120 | 472120 |
| 09 | Cuota 4% superreducido | cuota | 477120 | 472120 |
| 14 | Base adq. intracom. bienes | base | 477130 | 472130 |
| 15 | Cuota adq. intracom. bienes | cuota | 477130 | 472130 |
| 28 | Base IVA soportado interiores | base | - | 472100, 472110 |
| 29 | Cuota IVA soportado interiores | cuota | - | 472100, 472110 |

---

## Mapeo PGC predefinido

El archivo `scripts/import_pgc_mapping.py` importa un mapeo completo segun el Plan General Contable espanol.

Para importar:

```bash
bench --site [tu-sitio] execute erpnext_es_aeat.setup.install.after_install
```

Esto crea automaticamente:
- Tax Maps para los modelos 303, 390, 347, 349
- BOE Export Configs para todos los modelos
- Item Tax Templates estandar

---

## Configuracion BOE

### Formato de ficheros por modelo

| Modelo | Formato AEAT | Caracteristicas |
|--------|-------------|-----------------|
| 111 | Libre | Texto plano continuo |
| 115 | Libre | Texto plano continuo |
| 130 | Libre | Texto plano continuo |
| 303 | Multi-pagina | `<T303xxxxx>...contenido...</T303xxxxx>` |
| 347 | Registro fijo | 500 caracteres por linea (tipo 1 + tipo 2) |
| 349 | Registro fijo | 500 caracteres por linea (tipo 1 + tipo 2) |
| 390 | Multi-pagina | `<T390xxxxx>...contenido...</T390xxxxx>` |

### Convenciones numericas

- Importes monetarios: multiplicados por 100 (sin decimales)
- Negativos: prefijo "N" (ej: -781.00 -> N78100)
- Codificacion: Latin-1 (ISO-8859-1)
- Separador de lineas: `\r\n` (CRLF) para 347/349, `\n` para 303/390

---

## Flujo de trabajo

### Modelo 303 (IVA trimestral)

```
1. AEAT Espana > Modelo 303 > Nuevo
2. Seleccionar: Empresa, Ejercicio (desplegable), Periodo (1T/2T/3T/4T)
3. Guardar
4. Click "Calcular" -> sistema lee facturas y rellena casillas
5. Verificar casillas calculadas
6. Click "Export BOE" -> genera .txt descargable
7. Subir a agenciatributaria.gob.es
```

### Modelo 390 (Resumen Anual)

```
1. AEAT Espana > Modelo 390 > Nuevo
2. Ejercicio completo (0A)
3. Calcular -> resume los 4 trimestres
4. Export BOE
```

### Modelo 347 (Operaciones +3.000 EUR)

```
1. AEAT Espana > Modelo 347 > Nuevo
2. Ejercicio completo (0A)
3. Umbral: 3050.52 (por defecto)
4. Calcular -> agrupa por tercero
5. Verificar lineas de detalle
6. Export BOE
```

### Modelo 349 (Intracomunitarias)

```
1. AEAT Espana > Modelo 349 > Nuevo
2. Trimestre (1T/2T/3T/4T)
3. Calcular -> busca NIF de paises EU
4. Export BOE
```

---

## Resolucion de problemas

### "First non keyword argument must be a string or dict"

**Causa:** El JavaScript usa `frm.call()` que lee del cache local.

**Fix:** Usar `frappe.call()` con `docs: frm.doc` explicitamente.

### "AttributeError: 'AEATModXXX' object has no attribute 'casilla_XX'"

**Causa:** El codigo referencia casillas que no existen en el DocType.

**Fix:** Usar `getattr(self, f"casilla_{n:02d}", 0)` en `extra_calculation()`.

### "all casillas zero" despues de Calcular

**Causas posibles:**
1. No hay facturas en el periodo seleccionado
2. Los items no tienen Item Tax Template asignado
3. No existe Tax Map configurado para la empresa
4. Las facturas no estan en estado "Submitted" (docstatus=1)

### Fichero BOE no descarga como .txt

**Causa:** Nginx no configura Content-Disposition: attachment para .txt

**Fix:** Anadir en `/etc/nginx/conf.d/frappe-bench.conf`:

```nginx
location ~* ^/(private/)?files/.*\.txt$ {
    add_header Content-Disposition "attachment";
}
```

### "Date is not in any active Fiscal Year"

**Causa:** No existe el Fiscal Year para el periodo de las facturas.

**Fix:** Crear el Fiscal Year en Contabilidad > Configuracion > Fiscal Year.
