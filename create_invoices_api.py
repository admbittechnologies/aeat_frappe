import requests
import json

BASE_URL = "https://spainaeat.frappe.cloud"
HEADERS = {
    "Authorization": "token 086f3c5a6fd9892:09545c84d43374f",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
COMPANY = "BIT Technologies Iberica SL"

sales_invoices = [
    {
        "customer": "Cliente A SA",
        "posting_date": "2025-01-15",
        "due_date": "2025-02-15",
        "items": [{"item_name": "Servicios consultoria", "qty": 1, "rate": 10000, "income_account": "4110 - Sales - BTIB"}],
        "taxes": [{"charge_type": "On Net Total", "account_head": "4770 - IVA Repercutido 21% - BTIB", "rate": 21, "description": "IVA 21%", "tax_amount": 2100, "total": 12100}]
    },
    {
        "customer": "Cliente B SL",
        "posting_date": "2025-01-20",
        "due_date": "2025-02-20",
        "items": [{"item_name": "Desarrollo software", "qty": 1, "rate": 15000, "income_account": "4110 - Sales - BTIB"}],
        "taxes": [{"charge_type": "On Net Total", "account_head": "4770 - IVA Repercutido 21% - BTIB", "rate": 21, "description": "IVA 21%", "tax_amount": 3150, "total": 18150}]
    },
    {
        "customer": "Cliente Particular",
        "posting_date": "2025-02-10",
        "due_date": "2025-03-10",
        "items": [{"item_name": "Mantenimiento", "qty": 1, "rate": 5000, "income_account": "4110 - Sales - BTIB"}],
        "taxes": [{"charge_type": "On Net Total", "account_head": "4770 - IVA Repercutido 21% - BTIB", "rate": 21, "description": "IVA 21%", "tax_amount": 1050, "total": 6050}]
    }
]

purchase_invoices = [
    {
        "supplier": "Proveedor X SA",
        "posting_date": "2025-01-15",
        "due_date": "2025-02-15",
        "items": [{"item_name": "Material oficina", "qty": 1, "rate": 2000, "expense_account": "5111 - Cost of Goods Sold - BTIB"}],
        "taxes": [{"charge_type": "On Net Total", "account_head": "4720 - IVA Soportado 21% - BTIB", "rate": 21, "description": "IVA 21%", "tax_amount": 420, "total": 2420}]
    },
    {
        "supplier": "Proveedor Y SL",
        "posting_date": "2025-01-25",
        "due_date": "2025-02-25",
        "items": [{"item_name": "Servicios hosting", "qty": 1, "rate": 3000, "expense_account": "5111 - Cost of Goods Sold - BTIB"}],
        "taxes": [{"charge_type": "On Net Total", "account_head": "4720 - IVA Soportado 21% - BTIB", "rate": 21, "description": "IVA 21%", "tax_amount": 630, "total": 3630}]
    },
    {
        "supplier": "Proveedor Z",
        "posting_date": "2025-02-05",
        "due_date": "2025-03-05",
        "items": [{"item_name": "Licencias software", "qty": 1, "rate": 4000, "expense_account": "5111 - Cost of Goods Sold - BTIB"}],
        "taxes": [{"charge_type": "On Net Total", "account_head": "4720 - IVA Soportado 21% - BTIB", "rate": 21, "description": "IVA 21%", "tax_amount": 840, "total": 4840}]
    }
]

results = []

def create_and_submit(doctype, data, name_field):
    # Use frappe.client.insert which handles doc creation properly
    url = f"{BASE_URL}/api/method/frappe.client.insert"
    doc = {
        "doctype": doctype,
        "company": COMPANY,
        "currency": "EUR",
        "conversion_rate": 1,
        "plc_conversion_rate": 1,
        "set_posting_time": 1,
    }
    doc.update(data)
    
    print(f"\nCreating {doctype} for {data[name_field]}...")
    resp = requests.post(url, headers=HEADERS, json={"doc": doc}, timeout=60)
    print(f"  POST status: {resp.status_code}")
    
    if resp.status_code not in (200, 201):
        print(f"  POST error: {resp.text}")
        results.append({
            "doctype": doctype,
            "name": None,
            "status": "create_failed",
            "error": resp.text,
            "grand_total": None
        })
        return
    
    result = resp.json()
    if result.get("message"):
        created = result["message"]
    else:
        created = result.get("data", {})
    
    invoice_name = created.get("name")
    print(f"  Created: {invoice_name}")
    
    # Submit via frappe.client.submit (or save with docstatus=1)
    # First try frappe.client.submit
    submit_url = f"{BASE_URL}/api/method/frappe.client.submit"
    submit_resp = requests.post(submit_url, headers=HEADERS, json={"doc": created}, timeout=60)
    print(f"  Submit status: {submit_resp.status_code}")
    
    if submit_resp.status_code not in (200, 201):
        print(f"  Submit error: {submit_resp.text}")
        # Try alternative: fetch and save with docstatus=1
        fetch_url = f"{BASE_URL}/api/method/frappe.client.get"
        fetch_resp = requests.get(fetch_url, headers=HEADERS, params={"doctype": doctype, "name": invoice_name}, timeout=60)
        if fetch_resp.status_code == 200:
            fetched_doc = fetch_resp.json().get("message", {})
            fetched_doc["docstatus"] = 1
            save_url = f"{BASE_URL}/api/method/frappe.client.save"
            save_resp = requests.post(save_url, headers=HEADERS, json={"doc": fetched_doc}, timeout=60)
            print(f"  Save status: {save_resp.status_code}")
            if save_resp.status_code not in (200, 201):
                print(f"  Save error: {save_resp.text}")
                results.append({
                    "doctype": doctype,
                    "name": invoice_name,
                    "status": "submit_failed",
                    "error": save_resp.text,
                    "grand_total": created.get("grand_total")
                })
                return
            submitted = save_resp.json().get("message", {})
        else:
            results.append({
                "doctype": doctype,
                "name": invoice_name,
                "status": "submit_failed",
                "error": submit_resp.text,
                "grand_total": created.get("grand_total")
            })
            return
    else:
        submitted = submit_resp.json().get("message", {})
    
    grand_total = submitted.get("grand_total") or created.get("grand_total")
    print(f"  Submitted. Grand Total: {grand_total}")
    results.append({
        "doctype": doctype,
        "name": invoice_name,
        "status": "success",
        "error": None,
        "grand_total": grand_total
    })

for inv in sales_invoices:
    create_and_submit("Sales Invoice", inv, "customer")

for inv in purchase_invoices:
    create_and_submit("Purchase Invoice", inv, "supplier")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
for r in results:
    status_icon = "OK" if r["status"] == "success" else "FAIL"
    print(f"[{status_icon}] {r['doctype']}: {r['name']} | Grand Total: {r['grand_total']} | Status: {r['status']}")
    if r["error"]:
        print(f"       Error: {r['error'][:300]}")

with open("invoice_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\nResults saved to invoice_results.json")
