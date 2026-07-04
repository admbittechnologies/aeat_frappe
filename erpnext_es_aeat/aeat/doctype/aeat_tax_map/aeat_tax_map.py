# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
import frappe
from frappe.model.document import Document


class AEATTaxMap(Document):
    def validate(self):
        seen = set()
        for line in self.lines:
            key = (line.field_number, line.field_type, line.move_type)
            if key in seen:
                frappe.msgprint(
                    f"Casilla {line.field_number} duplicada con el mismo tipo/operación.",
                    indicator="orange",
                )
            seen.add(key)
