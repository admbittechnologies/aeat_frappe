# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
import frappe
from frappe.utils import flt
from frappe.model.document import Document

from erpnext_es_aeat.aeat.report_base import AEATReportMixin
from erpnext_es_aeat.aeat import tax_engine, boe

# EU VAT prefixes excluding Spain (ES). Used to detect intracommunity ops via
# the invoice tax_id / VAT number prefix.
EU_PREFIXES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "SE",
}


def _eu_party(tax_id):
    if not tax_id:
        return False
    prefix = tax_id.strip()[:2].upper()
    return prefix in EU_PREFIXES


class AEATMod349(AEATReportMixin, Document):
    aeat_model_code = "349"
    boe_config_name = "BOE Modelo 349 Header"
    boe_line_config_name = "BOE Modelo 349 Line"

    @frappe.whitelist()
    def calculate(self):
        self.compute_period()
        self.set("lines", [])
        rows = []
        rows += [(r, "Customer", "E") for r in tax_engine.party_invoice_totals(
            self.company, self.date_start, self.date_end, "Customer")]
        rows += [(r, "Supplier", "A") for r in tax_engine.party_invoice_totals(
            self.company, self.date_start, self.date_end, "Supplier")]

        total = 0.0
        count = 0
        for r, ptype, key in rows:
            if not _eu_party(r["tax_id"]):
                continue
            if abs(flt(r["total"])) < 0.01:
                continue
            count += 1
            total += flt(r["total"])
            self.append("lines", {
                "party_type": ptype,
                "party": r["party"],
                "party_name": r["party_name"],
                "vat": r["tax_id"],
                "operation_key": key,
                "amount": flt(r["total"]),
            })
        self.casilla_01 = count
        self.casilla_02 = total
        self.boxes_json = frappe.as_json({"operadores": count, "total": total})
        self.calculation_state = "Calculated"
        self.save()
        frappe.msgprint(f"349 calculado: {count} operadores, {total:.2f} EUR", indicator="green")
        return True

    @frappe.whitelist()
    def export_boe(self):
        parts = [boe.generate(self, self.boe_config_name).ljust(500)[:500]]
        for line in self.lines:
            parts.append(boe.generate(self, self.boe_line_config_name, context=line.as_dict()).ljust(500)[:500])
        text = "\r\n".join(parts) + "\r\n"
        f = boe.attach_boe_file(self, text, f"349_{self.year}_{self.period_type}.txt")
        frappe.msgprint("Fichero 349 generado.", indicator="green")
        return f.file_url

