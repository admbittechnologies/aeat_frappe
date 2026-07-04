# Certificación de regresión — erpnext_es_aeat

**Resultado: 58 / 58 comprobaciones superadas** (`python3 regression/run_regression.py`).

Esta certificación ejercita el **código real** (motor `tax_engine`, escritor
`boe`, base `report_base`, controladores de los 7 modelos) y los **mapas de
casillas y configuraciones BOE que se instalan por defecto** (`setup/install.py`),
alimentándolos con escenarios de facturas cuyos resultados se han calculado a
mano. Para cada modelo se verifica (1) que cada casilla coincide con su valor
esperado y (2) que el fichero BOE generado **vuelve a decodificarse** a esas
mismas cifras (prueba round-trip: `decode(encode(x)) == x`).

## Alcance de lo que se certifica aquí

* Agregación correcta de facturas por cuenta contable (ventas + compras), con
  filtrado por empresa, periodo (`posting_date`) y tipo de operación.
* Derivación de base imponible desde la cuota (`cuota / tipo × 100`).
* Tratamiento de **rectificativas/abonos** (`is_return = 1`, signo negativo).
* Resolución de cuentas por **nombre exacto** y por **número PGC / prefijo**.
* Aritmética propia de cada liquidación (totales, resultados, 20 % del 130…).
* **Periodo acumulado** del modelo 130 (desde 1 de enero).
* **Umbral 3.050,52 €** y desglose trimestral del 347.
* **Detección intracomunitaria** del 349 por prefijo de NIF-IVA (UE ≠ ES) y
  asignación de clave (E entregas / A adquisiciones).
* Codificación BOE de ancho fijo: relleno, alineación, decimales implícitos y
  **signo** (carácter `N` para negativos), con validación por round-trip.

## Escenarios y valores esperados

### Modelo 303 — 2T 2026
Ventas: 1.000 @21 %, 500 @10 %, 200 @4 %, y un abono −100 @21 %.
Compras: 400 @21 % corriente, 1.000 @21 % inversión.

| Casilla | Concepto | Esperado |
|--------:|----------|---------:|
| 01 / 03 | Base / cuota 21 % | 900 / 189 |
| 04 / 06 | Base / cuota 10 % | 500 / 50 |
| 07 / 09 | Base / cuota 4 % | 200 / 8 |
| 28 / 29 | Soportado corriente | 400 / 84 |
| 30 / 31 | Soportado inversión | 1.000 / 210 |
| 27 | IVA devengado | 247 |
| 45 | IVA deducible | 294 |
| 46 / 69 / 71 | Resultado | **−47** |

Registro BOE generado (78 car.):

```
<30320262T0000000000002470000000000000029400N0000000000004700N0000000000004700
```

Decodificado: cuota devengada 247,00 · deducible 294,00 · resultado −47,00 ·
liquidación −47,00. ✔

### Modelo 111 — 1T 2026
Retenciones: trabajo base 2.000 / 300; actividades base 1.000 / 150.
Esperado: 02=2.000, 03=300, 05=1.000, 06=150, 28=3.000, 29=450, 30=450. ✔

### Modelo 115 — 1T 2026
Alquileres base 1.000, retención 190. Esperado: 02=1.000, 03=190, 04=190. ✔

### Modelo 130 — 2T 2026 (acumulado)
Ingresos 10.000, gastos 4.000, retenciones 300. Periodo 01-ene → 30-jun.
Esperado: 01=10.000, 02=4.000, 03=6.000, 04=1.200 (20 %), 06=300, 07=900,
12=900, 15=900. ✔

### Modelo 347 — ejercicio 2026
C. Grande 5.000 (q1 2.000, q2 3.000), C. Pequeño 1.000 (< umbral → excluido),
Proveedor X 4.000 (q3). Esperado: 2 declarados, total 9.000, desglose
trimestral correcto, fichero multi-registro. ✔

### Modelo 349 — ejercicio 2026
Cliente DE 2.000 (clave E), Cliente ES 5.000 (excluido), Proveedor FR 1.500
(clave A). Esperado: 2 operadores, total 3.500, ES no incluido. ✔

## Cómo reproducirlo

```bash
python3 regression/run_regression.py     # offline, sin bench (lo aquí certificado)
```

## Validación en vivo (en tu bench, tras instalar)

El runner offline certifica la **lógica fiscal y el formato**. Para cerrar el
círculo en una instancia ERPNext real:

1. `bench get-app erpnext_es_aeat …` → `install-app` → `migrate`.
2. Configura los *templates* de impuestos por tipo y las *Tax Withholding
   Category*, y rellena las cuentas en cada `AEAT Tax Map`.
3. Emite 2–3 facturas de prueba con cifras conocidas (p.ej. las del escenario
   303 de arriba), pulsa **Calcular** y compara las casillas con la tabla.
4. Pulsa **Generar fichero BOE** y verifica el registro.

## Límites honestos de esta certificación

* Se certifica el **cálculo y la codificación**, no que los DocType JSON
  carguen en una versión concreta de Frappe (eso requiere un bench vivo; la
  sintaxis JSON/Python sí está validada: 39 `.py` + 13 `.json` sin errores).
* Las casillas cubiertas son el **subconjunto representativo** documentado en el
  README, no el total de cada modelo.
* Los diseños BOE son **parciales** (cabecera + casillas principales); complétalos
  contra el diseño de registro oficial del ejercicio antes de presentar.
