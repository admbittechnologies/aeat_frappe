import requests
import json
from datetime import datetime, timedelta

BASE_URL = "https://spainaeat.frappe.cloud"
HEADERS = {
    "Authorization": "token 086f3c5a6fd9892:09545c84d43374f",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Use future dates to avoid "Due Date cannot be before Posting / Supplier Invoice Date"
future_posting = (datetime.today() + timedelta(days=5)).strftime("%Y-%m-%d")
future_due = (datetime.today() + timedelta(days=35)).strftime("%Y-%m-%d")

invoices = [
    {
        "title": "Modelo 111 - profesionales",
        "data": {
            "doctype": "Purchase Invoice",
            "company": "BIT Technologies Iberica SL",
            "supplier": "Proveedor X SA",
            "posting_date": future_posting,
            "due_date": future_due,
            "items": [
                {
                    "item_name": "Servicios profesionales",
                    "qty": 1,
                    "rate": 5000,
                    "expense_account": "5111 - Cost of Goods Sold - BTIB"
                }
            ],
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": "4751 - Retenciones IRPF 4751 - BTIB",
                    "rate": -15,
                    "description": "IRPF 15%",
                    "cost_center": "Main - BTIB"
                }
            ]
        }
    },
    {
        "title": "Modelo 111 - actividades",
        "data": {
            "doctype": "Purchase Invoice",
            "company": "BIT Technologies Iberica SL",
            "supplier": "Proveedor Y SL",
            "posting_date": future_posting,
            "due_date": future_due,
            "items": [
                {
                    "item_name": "Consultoria actividades",
                    "qty": 1,
                    "rate": 3000,
                    "expense_account": "5111 - Cost of Goods Sold - BTIB"
                }
            ],
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": "4751 - Retenciones IRPF 4751 - BTIB",
                    "rate": -15,
                    "description": "IRPF 15%",
                    "cost_center": "Main - BTIB"
                }
            ]
        }
    },
    {
        "title": "Modelo 115 - alquileres",
        "data": {
            "doctype": "Purchase Invoice",
            "company": "BIT Technologies Iberica SL",
            "supplier": "Proveedor Z",
            "posting_date": future_posting,
            "due_date": future_due,
            "items": [
                {
                    "item_name": "Alquiler oficina",
                    "qty": 1,
                    "rate": 2000,
                    "expense_account": "5111 - Cost of Goods Sold - BTIB"
                }
            ],
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": "4751 - Retenciones IRPF 4751 - BTIB",
                    "rate": -15,
                    "description": "IRPF 15%",
                    "cost_center": "Main - BTIB"
                }
            ]
        }
    }
]

results = []

for inv in invoices:
    print(f"\n=== Creating {inv['title']} ===")
    
    # 1. POST to create
    create_url = f"{BASE_URL}/api/resource/Purchase Invoice"
    resp = requests.post(create_url, headers=HEADERS, json={"data": inv["data"]})
    print(f"POST status: {resp.status_code}")
    
    if resp.status_code not in (200, 201):
        print(f"CREATE FAILED: {resp.text}")
        results.append({"title": inv["title"], "error": f"CREATE {resp.status_code}: {resp.text}"})
        continue
    
    created = resp.json().get("data", {})
    name = created.get("name")
    print(f"Created name: {name}")
    
    # 2. PUT to submit (docstatus = 1)
    submit_url = f"{BASE_URL}/api/resource/Purchase Invoice/{name}"
    submit_resp = requests.put(submit_url, headers=HEADERS, json={"data": {"docstatus": 1}})
    print(f"PUT status: {submit_resp.status_code}")
    
    if submit_resp.status_code not in (200, 202):
        print(f"SUBMIT FAILED: {submit_resp.text}")
        results.append({
            "title": inv["title"],
            "name": name,
            "error": f"SUBMIT {submit_resp.status_code}: {submit_resp.text}"
        })
        continue
    
    submitted = submit_resp.json().get("data", {})
    
    # 3. GET full doc for totals
    get_resp = requests.get(f"{BASE_URL}/api/resource/Purchase Invoice/{name}", headers=HEADERS)
    full_doc = get_resp.json().get("data", {}) if get_resp.status_code == 200 else {}
    
    result = {
        "title": inv["title"],
        "name": name,
        "status": "Submitted",
        "grand_total": full_doc.get("grand_total"),
        "total_taxes_and_charges": full_doc.get("total_taxes_and_charges"),
        "net_total": full_doc.get("net_total"),
        "docstatus": full_doc.get("docstatus")
    }
    results.append(result)
    print(f"Result: {json.dumps(result, indent=2)}")

print("\n\n========== FINAL SUMMARY ==========")
for r in results:
    print(json.dumps(r, indent=2))
