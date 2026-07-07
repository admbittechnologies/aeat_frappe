import requests
import json

BASE = "https://spainaeat.frappe.cloud"
HEADERS = {
    "Authorization": "token 086f3c5a6fd9892:09545c84d43374f",
    "Content-Type": "application/json"
}

# Get the doc
r = requests.get(f"{BASE}/api/resource/AEAT%20Mod%20303/M303-2026-0003", headers=HEADERS)
doc = r.json()["data"]

print("Doc values from DB:")
for k in sorted(doc.keys()):
    if k.startswith("casilla_"):
        print(f"  {k}: {doc[k]}")

# Get the BOE config
r2 = requests.get(f"{BASE}/api/resource/AEAT%20BOE%20Export%20Config/BOE%20Modelo%20303", headers=HEADERS)
config = r2.json()["data"]

print("\nBOE config lines:")
for line in config["lines"]:
    expr = line.get("expression", "")
    if expr and expr.startswith("casilla_"):
        val = doc.get(expr, "NOT_FOUND")
        print(f"  {expr}: {val}")
