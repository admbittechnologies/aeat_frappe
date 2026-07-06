#!/usr/bin/env python3
"""Create fake Sales and Purchase Invoices in ERPNext via API."""
import json
import sys
import urllib.request
import urllib.error

BASE_URL = "https://spainaeat.frappe.cloud"
API_KEY = "086f3c5a6fd9892"
API_SECRET = "09545c84d43374f"
COMPANY = "BIT Technologies Iberica SL"


def api_call(method, data=None, http_method="POST"):
    url = f"{BASE_URL}/api/method/{method}"
    req = urllib.request.Request(url, method=http_method)
    req.add_header("Authorization", f"token {API_KEY}:{API_SECRET}")
    req.add_header("Content-Type", "application/json")
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err = json.loads(body)
        except Exception:
            err = body
        return {"error": True, "status": e.code, "body": err}


def create_sales_invoice(customer, posting_date, due_date, item_name, rate):
    doc = {
        "doctype": "Sales Invoice",
        "company": COMPANY,
        "customer": customer,
        "posting_date": posting_date,
        "due_date": due_date,
        "set_posting_time": 1,
        "items": [
            {
                "item_name": item_name,
                "qty": 1,
                "rate": rate,
                "income_account": "4110 - Sales - BTIB",
            }
        ],
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "4770 - IVA Repercutido 21% - BTIB",
                "rate": 21,
                "description": "IVA 21%",
            }
        ],
    }
    return api_call("frappe.client.insert", {"doc": doc})


def create_purchase_invoice(supplier, posting_date, due_date, item_name, rate):
    doc = {
        "doctype": "Purchase Invoice",
        "company": COMPANY,
        "supplier": supplier,
        "posting_date": posting_date,
        "due_date": due_date,
        "set_posting_time": 1,
        "items": [
            {
                "item_name": item_name,
                "qty": 1,
                "rate": rate,
                "expense_account": "5111 - Cost of Goods Sold - BTIB",
            }
        ],
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "4720 - IVA Soportado 21% - BTIB",
                "rate": 21,
                "description": "IVA 21%",
            }
        ],
    }
    return api_call("frappe.client.insert", {"doc": doc})


def submit_doc(doctype, name):
    # Re-fetch the doc first to avoid timestamp mismatch
    fetched = api_call("frappe.client.get", {"doctype": doctype, "name": name})
    if fetched.get("error"):
        return fetched
    doc = fetched["message"]
    doc["docstatus"] = 1
    return api_call("frappe.client.save", {"doc": doc})


sales_invoices = [
    ("Cliente A SA", "2026-01-15", "2026-02-15", "Servicios consultoria", 10000),
    ("Cliente B SL", "2026-01-20", "2026-02-20", "Desarrollo software", 15000),
    ("Cliente Particular", "2026-02-10", "2026-03-10", "Mantenimiento", 5000),
]

purchase_invoices = [
    ("Proveedor X SA", "2026-01-15", "2026-02-15", "Material oficina", 2000),
    ("Proveedor Y SL", "2026-01-25", "2026-02-25", "Servicios hosting", 3000),
    ("Proveedor Z", "2026-02-05", "2026-03-05", "Licencias software", 4000),
]


def main():
    results = []

    # Create Sales Invoices
    for customer, posting_date, due_date, item_name, rate in sales_invoices:
        print(f"\n>>> Creating Sales Invoice for {customer} ...")
        resp = create_sales_invoice(customer, posting_date, due_date, item_name, rate)
        if resp.get("error"):
            print(f"ERROR creating Sales Invoice for {customer}:")
            print(json.dumps(resp, indent=2, ensure_ascii=False))
            results.append({"type": "Sales Invoice", "customer": customer, "status": "error", "detail": resp})
            continue
        name = resp["message"]["name"]
        print(f"Created: {name}")
        print(f">>> Submitting {name} ...")
        sub = submit_doc("Sales Invoice", name)
        if sub.get("error"):
            print(f"ERROR submitting {name}:")
            print(json.dumps(sub, indent=2, ensure_ascii=False))
            results.append({"type": "Sales Invoice", "name": name, "status": "submit_error", "detail": sub})
        else:
            print(f"Submitted: {name}")
            results.append({"type": "Sales Invoice", "name": name, "status": "submitted"})

    # Create Purchase Invoices
    for supplier, posting_date, due_date, item_name, rate in purchase_invoices:
        print(f"\n>>> Creating Purchase Invoice for {supplier} ...")
        resp = create_purchase_invoice(supplier, posting_date, due_date, item_name, rate)
        if resp.get("error"):
            print(f"ERROR creating Purchase Invoice for {supplier}:")
            print(json.dumps(resp, indent=2, ensure_ascii=False))
            results.append({"type": "Purchase Invoice", "supplier": supplier, "status": "error", "detail": resp})
            continue
        name = resp["message"]["name"]
        print(f"Created: {name}")
        print(f">>> Submitting {name} ...")
        sub = submit_doc("Purchase Invoice", name)
        if sub.get("error"):
            print(f"ERROR submitting {name}:")
            print(json.dumps(sub, indent=2, ensure_ascii=False))
            results.append({"type": "Purchase Invoice", "name": name, "status": "submit_error", "detail": sub})
        else:
            print(f"Submitted: {name}")
            results.append({"type": "Purchase Invoice", "name": name, "status": "submitted"})

    print("\n\n=== SUMMARY ===")
    for r in results:
        print(r)

    # Save full results to file
    with open("invoice_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nFull results saved to invoice_results.json")


if __name__ == "__main__":
    main()
