import requests
import json

BASE = "https://spainaeat.frappe.cloud"
HEADERS = {
    "Authorization": "token 086f3c5a6fd9892:09545c84d43374f",
    "Content-Type": "application/json"
}

# Get the full doc first
r = requests.get(f"{BASE}/api/resource/AEAT Mod 303/M303-2026-0003", headers=HEADERS)
doc = r.json()["data"]

# Build minimal doc with only required fields for run_doc_method
minimal = {
    "doctype": "AEAT Mod 303",
    "name": doc["name"],
    "modified": doc["modified"],
    "docstatus": doc["docstatus"],
    "year": doc["year"],
    "period_type": doc["period_type"],
    "company": doc["company"],
}

payload = {
    "docs": json.dumps(minimal),
    "method": "calculate",
    "args": None
}

r2 = requests.post(f"{BASE}/api/method/frappe.handler.run_doc_method", headers=HEADERS, json=payload)
print("Status:", r2.status_code)
result = r2.json()
if "docs" in result:
    d = result["docs"][0]
    print("Calculation state:", d.get("calculation_state"))
    for k in sorted(d.keys()):
        if k.startswith("casilla_"):
            print(f"{k}: {d[k]}")
else:
    print(json.dumps(result, indent=2, ensure_ascii=False))
