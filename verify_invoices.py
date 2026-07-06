import requests
import json

BASE_URL = "https://spainaeat.frappe.cloud"
HEADERS = {
    "Authorization": "token 086f3c5a6fd9892:09545c84d43374f",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

invoices = [
    ("Sales Invoice", "ACC-SINV-2026-00011"),
    ("Sales Invoice", "ACC-SINV-2026-00012"),
    ("Sales Invoice", "ACC-SINV-2026-00013"),
    ("Purchase Invoice", "ACC-PINV-2026-00010"),
    ("Purchase Invoice", "ACC-PINV-2026-00011"),
    ("Purchase Invoice", "ACC-PINV-2026-00012"),
]

print("Verification of created invoices:")
print("="*70)

for doctype, name in invoices:
    url = f"{BASE_URL}/api/resource/{doctype}/{name}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 200:
        doc = resp.json().get("data", {})
        print(f"\n{doctype}: {name}")
        print(f"  Customer/Supplier: {doc.get('customer') or doc.get('supplier')}")
        print(f"  Posting Date: {doc.get('posting_date')}")
        print(f"  Due Date: {doc.get('due_date')}")
        print(f"  Grand Total: {doc.get('grand_total')}")
        print(f"  DocStatus: {doc.get('docstatus')}")
        print(f"  Status: {doc.get('status')}")
    else:
        print(f"\n{doctype}: {name} - FAILED to fetch (status {resp.status_code})")
