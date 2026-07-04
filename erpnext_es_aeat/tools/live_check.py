# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
"""
Live certification against a REAL ERPNext instance.

Run it inside the bench:

    bench --site <site> execute erpnext_es_aeat.erpnext_es_aeat.tools.live_check.run

It creates a throwaway company + accounts + per-rate tax templates, posts the
"Modelo 303" scenario as real (submitted) Sales/Purchase Invoices, runs the
AEAT Mod 303 calculation and asserts each casilla against the golden values that
the offline regression already certifies. Prints a PASS/FAIL report and raises
on mismatch (so CI / the provisioning script gets a non-zero exit).

NOTE: ERPNext mandatory fields vary slightly by version/region. This is a live
harness meant to be run on a disposable box and iterated: if a field is missing
on your version, the failing step is printed clearly and is a one-line fix.
"""

import frappe
from frappe.utils import flt, nowdate

COMPANY = "AEAT Test SL"
ABBR = "ATST"
CURRENCY = "EUR"
COUNTRY = "Spain"

# Golden values for the LIVE scenario (no credit note, to avoid return_against
# plumbing; still yields a negative result so sign handling is exercised).
EXPECTED = {
    "01": 1000, "03": 210, "04": 500, "06": 50, "07": 200, "09": 8,
    "28": 400, "29": 84, "30": 1000, "31": 210,
    "27": 268, "45": 294, "46": -26, "71": -26,
}


def log(step):
    print(f"  · {step}")


# ---------------------------------------------------------------------------
# Master data helpers (get-or-create)
# ---------------------------------------------------------------------------
def ensure_company():
    if frappe.db.exists("Company", COMPANY):
        return COMPANY
    log(f"creando empresa {COMPANY}")
    frappe.get_doc({
        "doctype": "Company",
        "company_name": COMPANY,
        "abbr": ABBR,
        "default_currency": CURRENCY,
        "country": COUNTRY,
        "create_chart_of_accounts_based_on": "Standard Template",
    }).insert()
    frappe.db.commit()
    return COMPANY


def root_group(root_type):
    """Return a group account of the given root_type to hang children under."""
    name = frappe.db.get_value(
        "Account",
        {"company": COMPANY, "root_type": root_type, "is_group": 1, "parent_account": ["is", "not set"]},
        "name",
    )
    if name:
        return name
    # fallback: any group of that root_type
    return frappe.db.get_value(
        "Account", {"company": COMPANY, "root_type": root_type, "is_group": 1}, "name"
    )


def ensure_account(acc_name, root_type, account_type=None, number=None):
    full = f"{acc_name} - {ABBR}"
    if frappe.db.exists("Account", full):
        return full
    doc = frappe.get_doc({
        "doctype": "Account",
        "account_name": acc_name,
        "company": COMPANY,
        "parent_account": root_group(root_type),
        "root_type": root_type,
        "is_group": 0,
    })
    if account_type:
        doc.account_type = account_type
    if number:
        doc.account_number = number
    doc.insert()
    return doc.name


def ensure_tax_template(kind, title, account_head, rate):
    """kind = 'Sales' | 'Purchase'."""
    doctype = f"{kind} Taxes and Charges Template"
    name = f"{title} - {ABBR}"
    if frappe.db.exists(doctype, name):
        return name
    doc = frappe.get_doc({
        "doctype": doctype,
        "title": title,
        "company": COMPANY,
        "taxes": [{
            "charge_type": "On Net Total",
            "account_head": account_head,
            "rate": rate,
            "description": title,
        }],
    })
    doc.insert()
    return doc.name


def ensure_item():
    code = "AEAT-SVC"
    if frappe.db.exists("Item", code):
        return code
    frappe.get_doc({
        "doctype": "Item",
        "item_code": code,
        "item_name": "Servicio AEAT Test",
        "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups",
        "is_stock_item": 0,
        "is_sales_item": 1,
        "is_purchase_item": 1,
    }).insert()
    return code


def ensure_party(party_type, name, tax_id):
    if party_type == "Customer":
        if not frappe.db.exists("Customer", name):
            frappe.get_doc({"doctype": "Customer", "customer_name": name,
                            "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
                            "territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
                            "tax_id": tax_id}).insert()
    else:
        if not frappe.db.exists("Supplier", name):
            frappe.get_doc({"doctype": "Supplier", "supplier_name": name,
                            "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name"),
                            "tax_id": tax_id}).insert()
    return name


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
def post_sales(customer, item, net, income_account, tax_account, rate):
    inv = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": COMPANY,
        "customer": customer,
        "currency": CURRENCY,
        "conversion_rate": 1,
        "posting_date": "2026-05-15",
        "due_date": "2026-05-15",
        "items": [{"item_code": item, "qty": 1, "rate": net, "income_account": income_account}],
        "taxes": [{"charge_type": "On Net Total", "account_head": tax_account,
                   "rate": rate, "description": f"IVA {rate}%"}],
    })
    inv.insert()
    inv.submit()
    return inv.name


def post_purchase(supplier, item, net, expense_account, tax_account, rate):
    inv = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "company": COMPANY,
        "supplier": supplier,
        "currency": CURRENCY,
        "conversion_rate": 1,
        "posting_date": "2026-05-15",
        "bill_no": f"TEST-{tax_account[:6]}-{int(net)}",
        "items": [{"item_code": item, "qty": 1, "rate": net, "expense_account": expense_account}],
        "taxes": [{"charge_type": "On Net Total", "account_head": tax_account,
                   "rate": rate, "description": f"IVA sop {rate}%",
                   "category": "Total", "add_deduct_tax": "Add"}],
    })
    inv.insert()
    inv.submit()
    return inv.name


def fill_map_accounts(accounts):
    """Point the default 303 map's casillas at the accounts we just created."""
    map_name = frappe.db.get_value("AEAT Tax Map", {"aeat_model": "303", "is_default": 1})
    m = frappe.get_doc("AEAT Tax Map", map_name)
    for line in m.lines:
        acc = accounts.get(line.field_number)
        if acc:
            line.accounts = acc
    m.save()
    frappe.db.commit()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run():
    print("=" * 64)
    print(" LIVE CHECK 303 — erpnext_es_aeat")
    print("=" * 64)

    ensure_company()

    log("cuentas")
    rep21 = ensure_account("IVA Repercutido 21 Test", "Liability", "Tax", "47700021")
    rep10 = ensure_account("IVA Repercutido 10 Test", "Liability", "Tax", "47700010")
    rep04 = ensure_account("IVA Repercutido 4 Test", "Liability", "Tax", "47700004")
    sop21 = ensure_account("IVA Soportado 21 Test", "Asset", "Tax", "47200021")
    sopinv = ensure_account("IVA Soportado Inv 21 Test", "Asset", "Tax", "47210021")
    income = ensure_account("Ventas AEAT Test", "Income", None, "70500000")
    expense = ensure_account("Compras AEAT Test", "Expense", None, "60000000")

    log("templates de impuestos")
    s21 = ensure_tax_template("Sales", "IVA Repercutido 21", rep21, 21)
    s10 = ensure_tax_template("Sales", "IVA Repercutido 10", rep10, 10)
    s04 = ensure_tax_template("Sales", "IVA Repercutido 4", rep04, 4)

    item = ensure_item()
    cust = ensure_party("Customer", "Cliente AEAT Test", "B11111111")
    supp = ensure_party("Supplier", "Proveedor AEAT Test", "B33333333")
    frappe.db.commit()

    log("facturas de venta")
    post_sales(cust, item, 1000, income, rep21, 21)
    post_sales(cust, item, 500, income, rep10, 10)
    post_sales(cust, item, 200, income, rep04, 4)
    log("facturas de compra")
    post_purchase(supp, item, 400, expense, sop21, 21)
    post_purchase(supp, item, 1000, expense, sopinv, 21)
    frappe.db.commit()

    log("ajustando mapa 303 a las cuentas de prueba")
    fill_map_accounts({
        1: rep21, 3: rep21, 4: rep10, 6: rep10, 7: rep04, 9: rep04,
        28: sop21, 29: sop21, 30: sopinv, 31: sopinv,
    })

    log("calculando modelo 303")
    doc = frappe.get_doc({
        "doctype": "AEAT Mod 303", "company": COMPANY, "year": 2026, "period_type": "2T",
    })
    doc.insert()
    doc.calculate()
    doc.reload()

    print("-" * 64)
    failed = []
    for k, exp in EXPECTED.items():
        got = flt(doc.get(f"casilla_{k}"))
        ok = abs(got - exp) <= 0.01
        if not ok:
            failed.append((k, got, exp))
        print(f"  [{'PASS' if ok else 'FAIL'}] casilla_{k}: {got}  (esperado {exp})")

    # BOE round trip
    url = doc.export_boe()
    print(f"  fichero BOE: {url}")

    print("-" * 64)
    if failed:
        print(f"  RESULTADO: FALLO ({len(failed)} casillas)")
        raise frappe.ValidationError(f"Live check 303 falló: {failed}")
    print(f"  RESULTADO: OK — {len(EXPECTED)}/{len(EXPECTED)} casillas correctas")
    print("=" * 64)
