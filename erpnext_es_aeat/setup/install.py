# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
"""Seed default AEAT tax maps and BOE export configs (idempotent)."""

import frappe


# ---------------------------------------------------------------------------
# Default tax maps. Accounts are left blank on purpose: account names are
# company-specific. Fill the "Cuentas contables" of each line with your real
# account heads (or PGC numbers like 477 / 472, resolved automatically).
# ---------------------------------------------------------------------------
TAX_MAPS = [
    {
        "title": "Modelo 303 (por defecto)",
        "aeat_model": "303",
        "is_default": 1,
        "lines": [
            # casilla, descripción, field_type, move_type, source, accounts, notes
            (1, "Base devengada 21%", "base", "all", "tax", "", "Cuenta IVA repercutido 21% (p.ej. 477x)"),
            (3, "Cuota devengada 21%", "amount", "all", "tax", "", "Cuenta IVA repercutido 21%"),
            (4, "Base devengada 10%", "base", "all", "tax", "", "Cuenta IVA repercutido 10%"),
            (6, "Cuota devengada 10%", "amount", "all", "tax", "", "Cuenta IVA repercutido 10%"),
            (7, "Base devengada 4%", "base", "all", "tax", "", "Cuenta IVA repercutido 4%"),
            (9, "Cuota devengada 4%", "amount", "all", "tax", "", "Cuenta IVA repercutido 4%"),
            (28, "Base IVA soportado corriente", "base", "all", "tax", "", "Cuentas IVA soportado op. corrientes (472x)"),
            (29, "Cuota IVA soportado corriente", "amount", "all", "tax", "", "Cuentas IVA soportado op. corrientes"),
            (30, "Base IVA soportado inversión", "base", "all", "tax", "", "Cuentas IVA soportado bienes de inversión"),
            (31, "Cuota IVA soportado inversión", "amount", "all", "tax", "", "Cuentas IVA soportado bienes de inversión"),
        ],
    },
    {
        "title": "Modelo 111 (por defecto)",
        "aeat_model": "111",
        "is_default": 1,
        "lines": [
            (2, "Base retenciones trabajo", "base", "all", "tax", "", "Cuenta retención IRPF nóminas (4751 trabajo)"),
            (3, "Retenciones trabajo", "amount", "all", "tax", "", "Cuenta retención IRPF nóminas"),
            (5, "Base retenciones actividades", "base", "all", "tax", "", "Cuenta retención IRPF profesionales (4751 actividades)"),
            (6, "Retenciones actividades", "amount", "all", "tax", "", "Cuenta retención IRPF profesionales"),
        ],
    },
    {
        "title": "Modelo 115 (por defecto)",
        "aeat_model": "115",
        "is_default": 1,
        "lines": [
            (2, "Base retenciones alquileres", "base", "all", "tax", "", "Cuenta retención IRPF alquileres (4751 alquileres)"),
            (3, "Retenciones alquileres", "amount", "all", "tax", "", "Cuenta retención IRPF alquileres"),
        ],
    },
    {
        "title": "Modelo 130 (por defecto)",
        "aeat_model": "130",
        "is_default": 1,
        "lines": [
            (1, "Ingresos computables", "base", "all", "gl", "", "Cuentas de ventas/ingresos (grupo 7)"),
            (2, "Gastos deducibles", "base", "all", "gl", "", "Cuentas de gastos (grupo 6)"),
            (6, "Retenciones soportadas", "amount", "all", "tax", "", "Cuenta retenciones IRPF soportadas a cuenta"),
        ],
    },
]


def line_sum_type(model, field_number):
    """Default sign treatment per (model, casilla).

    Modelo 130 casilla 01 (ingresos) lives on credit-balance accounts (grupo 7),
    so it must take the credit side to come out positive. Everything else nets.
    """
    if model == "130" and field_number == 1:
        return "credit"
    return "both"


def _ensure_tax_map(spec):
    if frappe.db.exists("AEAT Tax Map", spec["title"]):
        return
    doc = frappe.new_doc("AEAT Tax Map")
    doc.title = spec["title"]
    doc.aeat_model = spec["aeat_model"]
    doc.is_default = spec["is_default"]
    for (num, name, ftype, move, source, accounts, notes) in spec["lines"]:
        doc.append("lines", {
            "field_number": num, "box_name": name, "field_type": ftype,
            "move_type": move, "source": source,
            "sum_type": line_sum_type(spec["aeat_model"], num),
            "accounts": accounts, "notes": notes,
        })
    doc.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Default BOE export configs. These are FUNCTIONAL but PARTIAL: they encode the
# presenter/exercise/period header and the headline casillas so the export runs
# end to end. Complete each layout against the official "diseño de registro" of
# the relevant ejercicio before presenting to the AEAT. record_length=0 disables
# strict length validation until you finish the layout.
# ---------------------------------------------------------------------------
def _line(seq, label, etype, size, expr="", **kw):
    d = {"sequence": seq, "label": label, "export_type": etype, "size": size,
         "expression": expr}
    d.update(kw)
    return d


BOE_CONFIGS = [
    {
        "title": "BOE Modelo 303",
        "aeat_model": "303",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="<"),
            _line(20, "Modelo", "fixed", 3, fixed_value="303"),
            _line(30, "Ejercicio", "integer", 4, "year"),
            _line(40, "Periodo", "alphanumeric", 2, "period_type"),
            _line(50, "Cuota devengada (27)", "float", 17, "casilla_27", apply_sign=1),
            _line(60, "Cuota deducible (45)", "float", 17, "casilla_45", apply_sign=1),
            _line(70, "Resultado régimen general (46)", "float", 17, "casilla_46", apply_sign=1),
            _line(80, "Resultado liquidación (71)", "float", 17, "casilla_71", apply_sign=1),
        ],
    },
    {
        "title": "BOE Modelo 111",
        "aeat_model": "111",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="<"),
            _line(20, "Modelo", "fixed", 3, fixed_value="111"),
            _line(30, "Ejercicio", "integer", 4, "year"),
            _line(40, "Periodo", "alphanumeric", 2, "period_type"),
            _line(50, "Total bases (28)", "float", 17, "casilla_28", apply_sign=1),
            _line(60, "Total retenciones (29)", "float", 17, "casilla_29", apply_sign=1),
            _line(70, "Resultado (30)", "float", 17, "casilla_30", apply_sign=1),
        ],
    },
    {
        "title": "BOE Modelo 115",
        "aeat_model": "115",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="<"),
            _line(20, "Modelo", "fixed", 3, fixed_value="115"),
            _line(30, "Ejercicio", "integer", 4, "year"),
            _line(40, "Periodo", "alphanumeric", 2, "period_type"),
            _line(50, "Base (02)", "float", 17, "casilla_02", apply_sign=1),
            _line(60, "Retenciones (03)", "float", 17, "casilla_03", apply_sign=1),
            _line(70, "Resultado (04)", "float", 17, "casilla_04", apply_sign=1),
        ],
    },
    {
        "title": "BOE Modelo 130",
        "aeat_model": "130",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="<"),
            _line(20, "Modelo", "fixed", 3, fixed_value="130"),
            _line(30, "Ejercicio", "integer", 4, "year"),
            _line(40, "Periodo", "alphanumeric", 2, "period_type"),
            _line(50, "Rendimiento neto (03)", "float", 17, "casilla_03", apply_sign=1),
            _line(60, "Pago fraccionado (12)", "float", 17, "casilla_12", apply_sign=1),
            _line(70, "Resultado (15)", "float", 17, "casilla_15", apply_sign=1),
        ],
    },
    {
        "title": "BOE Modelo 390",
        "aeat_model": "390",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="<"),
            _line(20, "Modelo", "fixed", 3, fixed_value="390"),
            _line(30, "Ejercicio", "integer", 4, "year"),
            _line(50, "Cuota devengada (34)", "float", 17, "casilla_34", apply_sign=1),
            _line(60, "Cuota deducible (42)", "float", 17, "casilla_42", apply_sign=1),
            _line(70, "Resultado (65)", "float", 17, "casilla_65", apply_sign=1),
        ],
    },
    # --- 347: header + per-declarado line ---
    {
        "title": "BOE Modelo 347 Header",
        "aeat_model": "347",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="1"),
            _line(20, "Modelo", "fixed", 3, fixed_value="347"),
            _line(30, "Ejercicio", "integer", 4, "year"),
            _line(40, "Nº declarados", "integer", 9, "casilla_01"),
            _line(50, "Importe total", "float", 16, "casilla_02", apply_sign=1),
        ],
    },
    {
        "title": "BOE Modelo 347 Line",
        "aeat_model": "347",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="2"),
            _line(20, "Modelo", "fixed", 3, fixed_value="347"),
            _line(30, "Ejercicio", "integer", 4, "=ctx.get('parent') and doc.year or doc.year"),
            _line(40, "NIF declarado", "alphanumeric", 9, "=ctx.get('tax_id') or ''"),
            _line(50, "Nombre declarado", "alphanumeric", 40, "=ctx.get('party_name') or ''"),
            _line(60, "Clave", "alphanumeric", 1, "=ctx.get('operation_key') or ''"),
            _line(70, "Importe anual", "float", 16, "=flt(ctx.get('total'))", apply_sign=1),
            _line(80, "1T", "float", 16, "=flt(ctx.get('q1'))", apply_sign=1),
            _line(90, "2T", "float", 16, "=flt(ctx.get('q2'))", apply_sign=1),
            _line(100, "3T", "float", 16, "=flt(ctx.get('q3'))", apply_sign=1),
            _line(110, "4T", "float", 16, "=flt(ctx.get('q4'))", apply_sign=1),
        ],
    },
    # --- 349: header + per-operator line ---
    {
        "title": "BOE Modelo 349 Header",
        "aeat_model": "349",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="1"),
            _line(20, "Modelo", "fixed", 3, fixed_value="349"),
            _line(30, "Ejercicio", "integer", 4, "year"),
            _line(40, "Periodo", "alphanumeric", 2, "period_type"),
            _line(50, "Nº operadores", "integer", 9, "casilla_01"),
            _line(60, "Importe total", "float", 16, "casilla_02", apply_sign=1),
        ],
    },
    {
        "title": "BOE Modelo 349 Line",
        "aeat_model": "349",
        "is_default": 1,
        "record_length": 0,
        "lines": [
            _line(10, "Tipo registro", "fixed", 1, fixed_value="2"),
            _line(20, "Modelo", "fixed", 3, fixed_value="349"),
            _line(30, "NIF-IVA operador", "alphanumeric", 17, "=ctx.get('vat') or ''"),
            _line(40, "Nombre", "alphanumeric", 40, "=ctx.get('party_name') or ''"),
            _line(50, "Clave", "alphanumeric", 1, "=ctx.get('operation_key') or ''"),
            _line(60, "Importe", "float", 16, "=flt(ctx.get('amount'))", apply_sign=1),
        ],
    },
]


def _ensure_boe_config(spec):
    if frappe.db.exists("AEAT BOE Export Config", spec["title"]):
        return
    doc = frappe.new_doc("AEAT BOE Export Config")
    doc.title = spec["title"]
    doc.aeat_model = spec["aeat_model"]
    doc.is_default = spec["is_default"]
    doc.record_length = spec["record_length"]
    for line in spec["lines"]:
        doc.append("lines", line)
    doc.insert(ignore_permissions=True)


def seed():
    for spec in TAX_MAPS:
        _ensure_tax_map(spec)
    for spec in BOE_CONFIGS:
        _ensure_boe_config(spec)
    frappe.db.commit()


def after_install():
    # Fix DocTypes that may have been created with wrong module in previous
    # failed installations. Frappe does not re-sync the module field on reinstall.
    try:
        _fix_doctype_modules()
    except Exception:
        frappe.log_error("erpnext_es_aeat: _fix_doctype_modules failed during after_install")

    try:
        _ensure_workspace()
    except Exception:
        frappe.log_error("erpnext_es_aeat: _ensure_workspace failed during after_install")

    try:
        seed()
    except Exception:
        frappe.log_error("erpnext_es_aeat: seed failed during after_install")
        raise


def _ensure_workspace():
    """Create the AEAT workspace if it doesn't exist."""
    workspace_name = "AEAT Espana"
    if frappe.db.exists("Workspace", workspace_name):
        return

    workspace = frappe.new_doc("Workspace")
    workspace.name = workspace_name
    workspace.label = workspace_name
    workspace.title = workspace_name
    workspace.icon = "file"
    workspace.module = "aeat"
    workspace.public = 1
    workspace.sequence_id = 99.0
    workspace.is_hidden = 0
    workspace.hide_custom = 0
    workspace.content = '[{"id": "b00aeat", "type": "header", "data": {"text": "<span class=\\"h4\\"><b>Modelos tributarios AEAT</b></span>", "col": 12}}, {"id": "b01aeat", "type": "shortcut", "data": {"shortcut_name": "Modelo 303", "col": 3}}, {"id": "b02aeat", "type": "shortcut", "data": {"shortcut_name": "Modelo 111", "col": 3}}, {"id": "b03aeat", "type": "shortcut", "data": {"shortcut_name": "Modelo 115", "col": 3}}, {"id": "b04aeat", "type": "shortcut", "data": {"shortcut_name": "Modelo 130", "col": 3}}, {"id": "b05aeat", "type": "shortcut", "data": {"shortcut_name": "Modelo 390", "col": 3}}, {"id": "b06aeat", "type": "shortcut", "data": {"shortcut_name": "Modelo 347", "col": 3}}, {"id": "b07aeat", "type": "shortcut", "data": {"shortcut_name": "Modelo 349", "col": 3}}, {"id": "b08aeat", "type": "header", "data": {"text": "<span class=\\"h4\\"><b>Accesos</b></span>", "col": 12}}, {"id": "b09aeat", "type": "card", "data": {"card_name": "Liquidaciones", "col": 4}}, {"id": "b10aeat", "type": "card", "data": {"card_name": "Resumen anual", "col": 4}}, {"id": "b11aeat", "type": "card", "data": {"card_name": "Informativas", "col": 4}}, {"id": "b12aeat", "type": "card", "data": {"card_name": "Configuración", "col": 4}}]'

    # Shortcuts
    shortcuts = [
        ("Modelo 303", "AEAT Mod 303", "Blue"),
        ("Modelo 111", "AEAT Mod 111", "Cyan"),
        ("Modelo 115", "AEAT Mod 115", "Green"),
        ("Modelo 130", "AEAT Mod 130", "Orange"),
        ("Modelo 390", "AEAT Mod 390", "Pink"),
        ("Modelo 347", "AEAT Mod 347", "Purple"),
        ("Modelo 349", "AEAT Mod 349", "Yellow"),
    ]
    for label, link_to, color in shortcuts:
        workspace.append("shortcuts", {
            "label": label,
            "link_to": link_to,
            "type": "DocType",
            "doc_view": "List",
            "color": color,
        })

    # Links - Card Breaks and Links
    links = [
        ("Card Break", "Liquidaciones", None, None),
        ("Link", "Modelo 303 · IVA", "AEAT Mod 303", "DocType"),
        ("Link", "Modelo 111 · Retenciones trabajo/actividades", "AEAT Mod 111", "DocType"),
        ("Link", "Modelo 115 · Retenciones alquileres", "AEAT Mod 115", "DocType"),
        ("Link", "Modelo 130 · Pago fraccionado", "AEAT Mod 130", "DocType"),
        ("Card Break", "Resumen anual", None, None),
        ("Link", "Modelo 390 · Resumen anual IVA", "AEAT Mod 390", "DocType"),
        ("Card Break", "Informativas", None, None),
        ("Link", "Modelo 347 · Operaciones con terceros", "AEAT Mod 347", "DocType"),
        ("Link", "Modelo 349 · Operaciones intracomunitarias", "AEAT Mod 349", "DocType"),
        ("Card Break", "Configuración", None, None),
        ("Link", "Mapa de impuestos (casilla → cuentas)", "AEAT Tax Map", "DocType"),
        ("Link", "Configuración de fichero BOE", "AEAT BOE Export Config", "DocType"),
    ]
    for link_type, label, link_to, link_type_val in links:
        if link_type == "Card Break":
            workspace.append("links", {
                "type": "Card Break",
                "label": label,
                "link_count": 0,
                "hidden": 0,
                "is_query_report": 0,
                "onboard": 0,
            })
        else:
            workspace.append("links", {
                "type": "Link",
                "label": label,
                "link_to": link_to,
                "link_type": link_type_val,
                "hidden": 0,
                "is_query_report": 0,
                "onboard": 0,
                "dependencies": "",
            })

    workspace.insert(ignore_permissions=True)
    frappe.db.commit()


def _fix_doctype_modules():
    """Ensure our DocTypes point to the correct module, not Core.

    On a reinstall after a previous failed installation, DocTypes may exist in
    the DB with module='Core' (Frappe's fallback). We try to reload each
    DocType from its JSON on disk so Frappe re-syncs module and controller.
    If reload_doc fails (e.g. DB not fully ready), we fall back to a direct
    SQL update and log the error so the install can continue.
    """
    doctypes = [
        "AEAT Tax Map",
        "AEAT Tax Map Line",
        "AEAT BOE Export Config",
        "AEAT BOE Export Config Line",
        "AEAT Mod 111",
        "AEAT Mod 115",
        "AEAT Mod 130",
        "AEAT Mod 303",
        "AEAT Mod 347",
        "AEAT Mod 347 Line",
        "AEAT Mod 349",
        "AEAT Mod 349 Line",
        "AEAT Mod 390",
    ]
    for dt in doctypes:
        if not frappe.db.exists("DocType", dt):
            continue
        try:
            # Reload from JSON on disk — this re-syncs module, fields, permissions
            frappe.reload_doc("aeat", "doctype", frappe.scrub(dt), force=True)
            # Clear per-doctype cache (clear_cache expects a string, not a list)
            frappe.clear_cache(doctype=dt)
        except Exception:
            # If reload_doc fails (e.g. during a fresh install where the DocType
            # table is not yet fully synced), fall back to a direct SQL update
            # so the module field is at least correct in the DB.
            frappe.log_error(f"erpnext_es_aeat: reload_doc failed for {dt}; falling back to SQL update")
            try:
                frappe.db.sql(
                    "UPDATE `tabDocType` SET module = %s WHERE name = %s",
                    ("aeat", dt),
                )
            except Exception:
                frappe.log_error(f"erpnext_es_aeat: SQL fallback also failed for {dt}")

    # Clear the global controller cache so get_controller() picks up the new module
    if hasattr(frappe.local, "site_controllers"):
        try:
            frappe.local.site_controllers.clear()
        except Exception:
            pass


def after_migrate():
    seed()
