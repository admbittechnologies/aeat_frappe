import requests
import json

BASE_URL = "https://spainaeat.frappe.cloud"
HEADERS = {
    "Authorization": "token 086f3c5a6fd9892:09545c84d43374f",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Check current date on server
resp = requests.get(f"{BASE_URL}/api/method/frappe.utils.nowdate", headers=HEADERS, timeout=30)
print("Server date:", resp.status_code, resp.text)

# Check fiscal years
resp2 = requests.get(f"{BASE_URL}/api/resource/Fiscal Year?fields=[\"name\",\"year_start_date\",\"year_end_date\"]&limit_page_length=100", headers=HEADERS, timeout=30)
print("Fiscal Years:", resp2.status_code, json.dumps(resp2.json(), indent=2))
