# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
import frappe
from frappe.utils import flt
from frappe.model.document import Document

from erpnext_es_aeat.erpnext_es_aeat.aeat.report_base import AEATReportMixin
from erpnext_es_aeat.erpnext_es_aeat.aeat import tax_engine, boe


class AEATMod347(AEATReportMixin, Document):
    aeat_model_code = "347"
    boe_config_name = "BOE Modelo 347 Header"
    boe_line_config_name = "BOE Modelo 347 Line"

    @frappe.whitelist()
    def calculate(self):
        self.compute_period()
        threshold = flt(self.threshold) or 3050.52
        self.set("lines", [])
        rows = []
        rows += [(r, "Customer", "B") for r in tax_engine.party_invoice_totals(
            self.company, self.date_start, self.date_end, "Customer")]
        rows += [(r, "Supplier", "A") for r in tax_engine.party_invoice_totals(
            self.company, self.date_start, self.date_end, "Supplier")]

        total = 0.0
        count = 0
        for r, ptype, key in rows:
            if abs(flt(r["total"])) < threshold:
                continue
            count += 1
            total += flt(r["total"])
            self.append("lines", {
                "party_type": ptype,
                "party": r["party"],
                "party_name": r["party_name"],
                "tax_id": r["tax_id"],
                "operation_key": key,
                "total": flt(r["total"]),
                "q1": flt(r["q1"]), "q2": flt(r["q2"]),
                "q3": flt(r["q3"]), "q4": flt(r["q4"]),
            })
        self.casilla_01 = count
        self.casilla_02 = total
        self.boxes_json = frappe.as_json({"declarados": count, "total": total})
        self.calculation_state = "Calculated"
        self.save()
        frappe.msgprint(f"347 calculado: {count} declarados, {total:.2f} EUR", indicator="green")
        return True

    @frappe.whitelist()
    def export_boe(self):
        parts = [boe.generate(self, self.boe_config_name).ljust(500)[:500]]
        for line in self.lines:
            parts.append(boe.generate(self, self.boe_line_config_name, context=line.as_dict()).ljust(500)[:500])
        text = "\r\n".join(parts) + "\r\n"
        f = boe.attach_boe_file(self, text, f"347_{self.year}.txt")
        frappe.msgprint("Fichero 347 generado.", indicator="green")
        return f.file_url

