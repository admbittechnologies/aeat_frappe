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

# Keep doctype and modified, remove other constant fields
doc.pop("creation", None)
doc.pop("modified_by", None)
doc.pop("owner", None)
doc.pop("idx", None)

# Call calculate via run_doc_method
payload = {
    "docs": json.dumps(doc),
    "method": "calculate",
    "args": None
}

r2 = requests.post(f"{BASE}/api/method/frappe.handler.run_doc_method", headers=HEADERS, json=payload)
print("Status:", r2.status_code)
print(json.dumps(r2.json(), indent=2, ensure_ascii=False))
