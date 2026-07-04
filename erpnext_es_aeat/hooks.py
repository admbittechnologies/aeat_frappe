"""Frappe hooks for erpnext_es_aeat."""

app_name = "erpnext_es_aeat"
app_title = "ERPNext ES AEAT"
app_publisher = "BIT Technologies GmbH"
app_description = (
    "Modelos tributarios españoles (AEAT) para ERPNext: 303, 111, 115, 130, "
    "390, 347 y 349, con motor de mapeo casilla↔cuenta y generación de fichero BOE."
)
app_email = "info@bit-technologies.eu"
app_license = "AGPL-3.0-or-later"
required_apps = ["erpnext"]

# ------------------------------------------------------------------
# Seeding of default tax maps and BOE export configs after install
# ------------------------------------------------------------------
after_install = "erpnext_es_aeat.setup.install.after_install"
after_migrate = "erpnext_es_aeat.setup.install.after_migrate"

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
fixtures = [
    {
        "doctype": "AEAT Tax Map",
        "filters": [["is_default", "=", 1]],
    },
    {
        "doctype": "AEAT BOE Export Config",
        "filters": [["is_default", "=", 1]],
    },
]

doc_events = {}
