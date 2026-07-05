# Guia de Instalacion - ERPNext ES AEAT

## Requisitos

- ERPNext v15+ (Frappe v15+)
- Python 3.10+
- MariaDB 10.6+ / PostgreSQL 13+

## Instalacion paso a paso

### 1. Clonar el repositorio

```bash
cd /home/bench/frappe-bench/apps
git clone https://github.com/bit-technologies/erpnext_es_aeat.git
# O copiar desde una carpeta local:
# cp -r /ruta/a/erpnext_es_aeat .
```

### 2. Instalar la aplicacion

```bash
cd /home/bench/frappe-bench

# Instalar dependencias
pip install -e apps/erpnext_es_aeat

# Instalar en el sitio
bench --site [tu-sitio] install-app erpnext_es_aeat

# Ejemplo:
bench --site erp.local install-app erpnext_es_aeat
```

### 3. Crear los Fiscal Years necesarios

```bash
# Crear desde la interfaz web:
# Contabilidad > Configuracion > Fiscal Year > Nuevo
# O ejecutar desde bench console:

bench --site [tu-sitio] console
```

```python
import frappe
for year in range(2024, 2031):
    if not frappe.db.exists("Fiscal Year", str(year)):
        fy = frappe.get_doc({
            "doctype": "Fiscal Year",
            "year": str(year),
            "year_start_date": f"{year}-01-01",
            "year_end_date": f"{year}-12-31",
        })
        fy.save()
frappe.db.commit()
```

### 4. Configurar la Empresa

**Obligatorio:** La empresa debe tener el NIF configurado.

```
Configuracion > Empresa > [Tu Empresa]
```

| Campo | Valor | Ejemplo |
|-------|-------|---------|
| Nombre | Nombre fiscal | Mi Empresa SL |
| NIF / Tax ID | CIF/NIF completo | B12345678 |

### 5. Configurar cuentas contables (PGC)

Las cuentas del Plan General Contable deben estar creadas. Las minimas requeridas son:

| Codigo | Nombre | Tipo |
|--------|--------|------|
| 430 | Clientes (Deudores) | Receivable |
| 400 | Proveedores (Acreedores) | Payable |
| 4770 | Hacienda Publica. IVA Repercutido | Tax |
| 4720 | Hacienda Publica. IVA Soportado | Tax |

### 6. Crear Item Tax Templates

```python
# Desde bench console:
import frappe

company = "[TU EMPRESA]"

for title, rate, account in [
    ("IVA 21% Ventas", 21, "4770 - IVA Repercutido 21%"),
    ("IVA 10% Ventas", 10, "4770 - IVA Repercutido 10%"),
    ("IVA 4% Ventas", 4, "4770 - IVA Repercutido 4%"),
    ("IVA 0% EU Ventas", 0, "4770 - IVA Repercutido 0%"),
    ("IVA 21% Compras", 21, "4720 - IVA Soportado 21%"),
    ("IVA 10% Compras", 10, "4720 - IVA Soportado 10%"),
]:
    if not frappe.db.exists("Item Tax Template", f"{title} - {company[:3].upper()}"):
        doc = frappe.get_doc({
            "doctype": "Item Tax Template",
            "title": title,
            "company": company,
            "taxes": [{"tax_type": account, "tax_rate": rate}]
        })
        doc.save()

frappe.db.commit()
```

### 7. Asignar Item Tax Templates a productos

```python
import frappe

for item_code, template_title in [
    ("[ITEM-CODE-1]", "IVA 21% Ventas - [ABREV]"),
    ("[ITEM-CODE-2]", "IVA 10% Ventas - [ABREV]"),
]:
    item = frappe.get_doc("Item", item_code)
    item.taxes = []
    item.append("taxes", {"item_tax_template": template_title, "tax_category": ""})
    item.save()

frappe.db.commit()
```

### 8. Importar mapeo PGC predefinido (opcional pero recomendado)

```bash
bench --site [tu-sitio] execute erpnext_es_aeat.setup.install.setup_tax_maps
```

O importar desde el JSON incluido:

```bash
bench --site [tu-sitio] console < scripts/import_pgc_mapping.py
```

### 9. Reiniciar el servidor

```bash
bench restart
# O si usas supervisor:
supervisorctl restart all
```

### 10. Verificar la instalacion

```bash
bench --site [tu-sitio] console
```

```python
import frappe

# Verificar DocTypes
doctypes = ["AEAT Mod 303", "AEAT Mod 390", "AEAT Mod 111", "AEAT Mod 115",
            "AEAT Mod 130", "AEAT Mod 347", "AEAT Mod 349", "AEAT Tax Map",
            "AEAT BOE Export Config"]
for dt in doctypes:
    meta = frappe.get_meta(dt)
    print(f"{dt}: {len(meta.fields)} fields")

# Verificar workspace
ws = frappe.db.exists("Workspace", "AEAT Espana")
print(f"\nWorkspace AEAT Espana: {'OK' if ws else 'FALTA'}")
```

---

## Estructura de la aplicacion

```
erpnext_es_aeat/
  hooks.py              # Hooks de Frappe
  pyproject.toml        # Dependencias Python
  README.md
  erpnext_es_aeat/
    aeat/
      boe.py            # Generador de ficheros BOE
      report_base.py    # Clase base para modelos
      tax_engine.py     # Motor de calculo de IVA
      __init__.py
    doctype/
      aeat_mod_111/     # Modelo 111 - Retenciones IRPF
      aeat_mod_115/     # Modelo 115 - Retenciones alquileres
      aeat_mod_130/     # Modelo 130 - IRPF Estimacion Directa
      aeat_mod_303/     # Modelo 303 - IVA trimestral
      aeat_mod_347/     # Modelo 347 - Operaciones +3.000
      aeat_mod_349/     # Modelo 349 - Intracomunitarias
      aeat_mod_390/     # Modelo 390 - Resumen Anual IVA
      aeat_tax_map/     # Mapeo de impuestos
      aeat_boe_export_config/   # Configuracion BOE
      aeat_boe_export_config_line/
    setup/
      install.py        # Setup inicial
    workspace/
      aeat/             # Workspace AEAT
```

## Desinstalacion

```bash
bench --site [tu-sitio] uninstall-app erpnext_es_aeat
bench remove-app erpnext_es_aeat
```
