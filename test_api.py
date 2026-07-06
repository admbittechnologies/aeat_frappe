import requests
import json

BASE_URL = "https://spainaeat.frappe.cloud"
HEADERS = {
    "Authorization": "token 086f3c5a6fd9892:09545c84d43374f",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Check Sales Invoice meta to understand fields
resp = requests.get(f"{BASE_URL}/api/resource/Sales Invoice?limit_page_length=1&fields=[\"name\",\"posting_date\",\"due_date\",\"customer\",\"grand_total\"]", headers=HEADERS, timeout=30)
print("Existing Sales Invoices:", resp.status_code)
if resp.status_code == 200:
    print(json.dumps(resp.json(), indent=2))

# Check Purchase Invoice meta
resp2 = requests.get(f"{BASE_URL}/api/resource/Purchase Invoice?limit_page_length=1&fields=[\"name\",\"posting_date\",\"due_date\",\"supplier\",\"grand_total\"]", headers=HEADERS, timeout=30)
print("\nExisting Purchase Invoices:", resp2.status_code)
if resp2.status_code == 200:
    print(json.dumps(resp2.json(), indent=2))

# Check doctype fields for Sales Invoice
resp3 = requests.get(f"{BASE_URL}/api/method/frappe.desk.form.load.getdoctype?doctype=Sales Invoice", headers=HEADERS, timeout=30)
print("\nSales Invoice doctype:", resp3.status_code)
