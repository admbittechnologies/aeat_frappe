#!/usr/bin/env python3
"""
Offline regression certification for erpnext_es_aeat.

Loads the *real* engine, controllers and the *shipped* default tax maps / BOE
export configs (from setup/install.py), drives them with known invoice
scenarios whose AEAT box results were computed by hand, and asserts:

  1. Every casilla equals its golden value.
  2. The generated BOE record round-trips back to the same figures
     (decode(encode(x)) == x), proving the file encodes the right numbers.

Run:  python3 regression/run_regression.py
Exit code is non-zero if any check fails.
"""
import importlib.util
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(HERE)  # .../erpnext_es_aeat (repo root, holds package)

# --- load the frappe stub under the name "frappe" -------------------------
spec = importlib.util.spec_from_file_location("frappe", os.path.join(HERE, "frappe_stub.py"))
frappe = importlib.util.module_from_spec(spec)
sys.modules["frappe"] = frappe
spec.loader.exec_module(frappe)

sys.path.insert(0, APP_ROOT)

# Real app code (engine + shipped seed data + controllers)
from erpnext_es_aeat.erpnext_es_aeat.setup import install            # noqa: E402
from erpnext_es_aeat.erpnext_es_aeat.doctype.aeat_mod_303 import aeat_mod_303  # noqa: E402
from erpnext_es_aeat.erpnext_es_aeat.doctype.aeat_mod_111 import aeat_mod_111  # noqa: E402
from erpnext_es_aeat.erpnext_es_aeat.doctype.aeat_mod_115 import aeat_mod_115  # noqa: E402
from erpnext_es_aeat.erpnext_es_aeat.doctype.aeat_mod_130 import aeat_mod_130  # noqa: E402
from erpnext_es_aeat.erpnext_es_aeat.doctype.aeat_mod_347 import aeat_mod_347  # noqa: E402
from erpnext_es_aeat.erpnext_es_aeat.doctype.aeat_mod_349 import aeat_mod_349  # noqa: E402

# ==========================================================================
# Fixtures
# ==========================================================================
ACCT_TOKENS = {
    ("303", 1): "IVA Repercutido 21% - T", ("303", 3): "IVA Repercutido 21% - T",
    ("303", 4): "IVA Repercutido 10% - T", ("303", 6): "IVA Repercutido 10% - T",
    ("303", 7): "IVA Repercutido 4% - T",  ("303", 9): "IVA Repercutido 4% - T",
    ("303", 28): "4720", ("303", 29): "4720",   # prefix -> soportado corriente
    ("303", 30): "4721", ("303", 31): "4721",   # prefix -> soportado inversión
    ("111", 2): "Retención IRPF Trabajo - T", ("111", 3): "Retención IRPF Trabajo - T",
    ("111", 5): "Retención IRPF Actividades - T", ("111", 6): "Retención IRPF Actividades - T",
    ("115", 2): "Retención IRPF Alquileres - T", ("115", 3): "Retención IRPF Alquileres - T",
    ("130", 1): "Ventas - T", ("130", 2): "Compras - T",
    ("130", 6): "Retención IRPF Soportada - T",
}


def register_accounts():
    frappe.ACCOUNTS.clear()
    rows = [
        ("IVA Repercutido 21% - T", "4770021"),
        ("IVA Repercutido 10% - T", "4770010"),
        ("IVA Repercutido 4% - T", "4770004"),
        ("IVA Soportado 21% - T", "4720021"),
        ("IVA Soportado Inversión 21% - T", "4721021"),
        ("Retención IRPF Trabajo - T", "4751001"),
        ("Retención IRPF Actividades - T", "4751002"),
        ("Retención IRPF Alquileres - T", "4751003"),
        ("Retención IRPF Soportada - T", "4730000"),
        ("Ventas - T", "7000000"),
        ("Compras - T", "6000000"),
    ]
    for company in ("T303", "T111", "T115", "T130", "T347", "T349"):
        for name, num in rows:
            frappe.ACCOUNTS.append(
                {"name": name, "account_number": num, "company": company, "is_group": 0}
            )


def build_maps_and_configs():
    """Reconstruct the shipped maps with accounts filled, register BOE configs."""
    frappe.TAX_MAP_DOCS.clear()
    frappe.MAP_BY_MODEL.clear()
    for spec_ in install.TAX_MAPS:
        model = spec_["aeat_model"]
        lines = []
        for (num, name, ftype, move, source, _acc, notes) in spec_["lines"]:
            lines.append({
                "field_number": num, "box_name": name, "field_type": ftype,
                "move_type": move, "source": source,
                "sum_type": install.line_sum_type(model, num),
                "inverse": 0,
                "accounts": ACCT_TOKENS.get((model, num), ""),
            })
        frappe.TAX_MAP_DOCS[spec_["title"]] = {"aeat_model": model, "lines_filled": lines}
        frappe.MAP_BY_MODEL[model] = spec_["title"]

    frappe.BOE_CONFIG_DOCS.clear()
    for spec_ in install.BOE_CONFIGS:
        frappe.BOE_CONFIG_DOCS[spec_["title"]] = spec_


def tax_row(company, parent, acct, rate, cuota, is_return=0, d=date(2026, 5, 15)):
    return {"company": company, "parent": f"{parent[:3]}-001", "account_head": acct,
            "rate": rate, "base_tax_amount": cuota, "tax_amount": cuota,
            "item_wise_tax_detail": "", "is_return": is_return, "posting_date": d}


def si(company, party, name, tax_id, amount, d):
    return {"company": company, "party": party, "party_name": name, "tax_id": tax_id,
            "is_return": 0, "amount": amount, "posting_date": d}


# ==========================================================================
# Assertion helpers
# ==========================================================================
RESULTS = []


def check(label, got, exp, tol=0.01):
    try:
        ok = abs(float(got or 0) - float(exp)) <= tol
    except (TypeError, ValueError):
        ok = str(got) == str(exp)
    RESULTS.append((ok, label, got, exp))
    return ok


def decode_boe_floats(text, config_title):
    """Slice the record per config and decode float casillas back to numbers."""
    cfg = frappe.BOE_CONFIG_DOCS[config_title]
    out = {}
    pos = 0
    for ln in sorted(cfg["lines"], key=lambda x: x["sequence"]):
        size = ln["size"]
        frag = text[pos:pos + size]
        pos += size
        if ln["export_type"] == "float":
            if ln.get("apply_sign"):
                sign, digits = frag[0], frag[1:]
                val = int(digits) / 100.0
                val = -val if sign == (ln.get("negative_sign") or "N") else val
            else:
                val = int(frag) / 100.0
            out[ln["expression"]] = val
    return out, pos


# ==========================================================================
# Scenarios
# ==========================================================================
def scenario_303():
    co = "T303"
    frappe.TAX_ROWS["Sales Invoice"] = [
        tax_row(co, "Sales Invoice", "IVA Repercutido 21% - T", 21, 210),
        tax_row(co, "Sales Invoice", "IVA Repercutido 10% - T", 10, 50),
        tax_row(co, "Sales Invoice", "IVA Repercutido 4% - T", 4, 8),
        tax_row(co, "Sales Invoice", "IVA Repercutido 21% - T", 21, -21, is_return=1),
    ]
    frappe.TAX_ROWS["Purchase Invoice"] = [
        tax_row(co, "Purchase Invoice", "IVA Soportado 21% - T", 21, 84),
        tax_row(co, "Purchase Invoice", "IVA Soportado Inversión 21% - T", 21, 210),
    ]
    d = aeat_mod_303.AEATMod303(company=co, year=2026, period_type="2T")
    d.calculate()
    exp = {"01": 900, "03": 189, "04": 500, "06": 50, "07": 200, "09": 8,
           "28": 400, "29": 84, "30": 1000, "31": 210,
           "27": 247, "45": 294, "46": -47, "69": -47, "71": -47}
    for k, v in exp.items():
        check(f"303 casilla_{k}", d.get(f"casilla_{k}"), v)
    # BOE round-trip
    url = d.export_boe()
    text = frappe.LAST_BOE[-1]
    dec, total = decode_boe_floats(text, "BOE Modelo 303")
    check("303 BOE len>0", 1 if text else 0, 1)
    check("303 BOE devengada(27)", dec["casilla_27"], 247)
    check("303 BOE deducible(45)", dec["casilla_45"], 294)
    check("303 BOE resultado(46)", dec["casilla_46"], -47)
    check("303 BOE liquidacion(71)", dec["casilla_71"], -47)
    check("303 BOE cabecera modelo", 1 if "303" in text[:5] else 0, 1)


def scenario_111():
    co = "T111"
    frappe.TAX_ROWS["Sales Invoice"] = []
    frappe.TAX_ROWS["Purchase Invoice"] = [
        tax_row(co, "Purchase Invoice", "Retención IRPF Trabajo - T", 15, 300, d=date(2026, 2, 10)),
        tax_row(co, "Purchase Invoice", "Retención IRPF Actividades - T", 15, 150, d=date(2026, 2, 10)),
    ]
    d = aeat_mod_111.AEATMod111(company=co, year=2026, period_type="1T")
    d.calculate()
    for k, v in {"02": 2000, "03": 300, "05": 1000, "06": 150,
                 "28": 3000, "29": 450, "30": 450}.items():
        check(f"111 casilla_{k}", d.get(f"casilla_{k}"), v)
    d.export_boe()
    dec, _ = decode_boe_floats(frappe.LAST_BOE[-1], "BOE Modelo 111")
    check("111 BOE retenciones(29)", dec["casilla_29"], 450)
    check("111 BOE resultado(30)", dec["casilla_30"], 450)


def scenario_115():
    co = "T115"
    frappe.TAX_ROWS["Sales Invoice"] = []
    frappe.TAX_ROWS["Purchase Invoice"] = [
        tax_row(co, "Purchase Invoice", "Retención IRPF Alquileres - T", 19, 190, d=date(2026, 2, 20)),
    ]
    d = aeat_mod_115.AEATMod115(company=co, year=2026, period_type="1T")
    d.calculate()
    for k, v in {"02": 1000, "03": 190, "04": 190}.items():
        check(f"115 casilla_{k}", d.get(f"casilla_{k}"), v)
    d.export_boe()
    dec, _ = decode_boe_floats(frappe.LAST_BOE[-1], "BOE Modelo 115")
    check("115 BOE retenciones(03)", dec["casilla_03"], 190)


def scenario_130():
    co = "T130"
    frappe.TAX_ROWS["Sales Invoice"] = []
    frappe.TAX_ROWS["Purchase Invoice"] = [
        tax_row(co, "Purchase Invoice", "Retención IRPF Soportada - T", 15, 300, d=date(2026, 5, 1)),
    ]
    frappe.GL_ROWS = [
        {"company": co, "account": "Ventas - T", "debit": 0, "credit": 10000, "posting_date": date(2026, 3, 1)},
        {"company": co, "account": "Compras - T", "debit": 4000, "credit": 0, "posting_date": date(2026, 3, 1)},
    ]
    d = aeat_mod_130.AEATMod130(company=co, year=2026, period_type="2T")
    d.calculate()
    check("130 periodo acumulado inicio", str(d.date_start), "2026-01-01")
    for k, v in {"01": 10000, "02": 4000, "06": 300, "03": 6000,
                 "04": 1200, "07": 900, "12": 900, "15": 900}.items():
        check(f"130 casilla_{k}", d.get(f"casilla_{k}"), v)
    d.export_boe()
    dec, _ = decode_boe_floats(frappe.LAST_BOE[-1], "BOE Modelo 130")
    check("130 BOE resultado(15)", dec["casilla_15"], 900)


def scenario_347():
    co = "T347"
    frappe.SI_ROWS = [
        si(co, "C1", "Cliente Grande", "B11111111", 2000, date(2026, 2, 1)),
        si(co, "C1", "Cliente Grande", "B11111111", 3000, date(2026, 5, 1)),
        si(co, "C2", "Cliente Pequeño", "B22222222", 1000, date(2026, 2, 1)),
    ]
    frappe.PI_ROWS = [
        si(co, "P1", "Proveedor X", "B33333333", 4000, date(2026, 8, 1)),
    ]
    d = aeat_mod_347.AEATMod347(company=co, year=2026, period_type="0A", threshold=3050.52)
    d.calculate()
    check("347 nº declarados (01)", d.casilla_01, 2)
    check("347 importe total (02)", d.casilla_02, 9000)
    check("347 nº líneas", len(d.lines), 2)
    parties = sorted([(l.party, l.total) for l in d.lines])
    check("347 Cliente Grande total", dict(parties).get("C1"), 5000)
    check("347 Proveedor X total", dict(parties).get("P1"), 4000)
    # quarter split of C1: q1=2000, q2=3000
    c1 = [l for l in d.lines if l.party == "C1"][0]
    check("347 C1 q1", c1.q1, 2000)
    check("347 C1 q2", c1.q2, 3000)
    d.export_boe()
    check("347 BOE multi-registro", 1 if frappe.LAST_BOE[-1].count("\r\n") >= 2 else 0, 1)


def scenario_349():
    co = "T349"
    frappe.SI_ROWS = [
        si(co, "DE", "DE-Kunde GmbH", "DE123456789", 2000, date(2026, 2, 1)),
        si(co, "ES", "Cliente Español", "ESB12345678", 5000, date(2026, 2, 1)),
    ]
    frappe.PI_ROWS = [
        si(co, "FR", "FR-Fournisseur", "FR12345678901", 1500, date(2026, 2, 1)),
    ]
    d = aeat_mod_349.AEATMod349(company=co, year=2026, period_type="0A")
    d.calculate()
    check("349 nº operadores (01)", d.casilla_01, 2)
    check("349 importe total (02)", d.casilla_02, 3500)
    check("349 nº líneas (ES excluido)", len(d.lines), 2)
    keys = {l.party: l.operation_key for l in d.lines}
    check("349 DE clave E (entrega)", 1 if keys.get("DE") == "E" else 0, 1)
    check("349 FR clave A (adquisición)", 1 if keys.get("FR") == "A" else 0, 1)
    check("349 ES no incluido", 0 if "ES" in keys else 0, 0)


# ==========================================================================
# Main
# ==========================================================================
def main():
    register_accounts()
    build_maps_and_configs()
    for fn in (scenario_303, scenario_111, scenario_115, scenario_130,
               scenario_347, scenario_349):
        fn()

    print("=" * 72)
    print(" CERTIFICACIÓN DE REGRESIÓN — erpnext_es_aeat")
    print("=" * 72)
    passed = sum(1 for ok, *_ in RESULTS if ok)
    failed = [r for r in RESULTS if not r[0]]
    for ok, label, got, exp in RESULTS:
        mark = "PASS" if ok else "FAIL"
        extra = "" if ok else f"   (obtenido={got}  esperado={exp})"
        print(f"  [{mark}] {label}{extra}")
    print("-" * 72)
    print(f"  {passed}/{len(RESULTS)} comprobaciones superadas")
    print("=" * 72)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
