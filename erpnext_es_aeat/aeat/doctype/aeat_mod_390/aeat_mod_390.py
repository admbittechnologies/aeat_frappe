# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later

import frappe
from frappe.utils import flt

from erpnext_es_aeat.aeat.report_base import AEATReportMixin
from erpnext_es_aeat.aeat import boe


class AEATMod390(AEATReportMixin, frappe.model.document.Document):
    aeat_model_code = "390"
    boe_config_name = "BOE Modelo 390"

    def extra_calculation(self):
        pass

    @frappe.whitelist()
    def export_boe(self):
        if not self.boe_config_name:
            frappe.throw("El modelo 390 no tiene export BOE configurado.")

        nif = frappe.db.get_value("Company", self.company, "tax_id") or ""
        nombre = self.company or ""
        ejercicio = str(self.year or "")

        # Get config data lines only (seq >= 100)
        config = frappe.get_doc("AEAT BOE Export Config", self.boe_config_name)
        data_lines = [l for l in config.lines if (l.sequence or 0) >= 100]
        data_content = boe.generate_from_lines(data_lines, self) if data_lines else ""

        # --- PAGE 0: Registro de identificación (346 chars) ---
        page0 = (
            "1" + "390" + ejercicio.rjust(4, "0")
            + nif.ljust(9)[:9] + nombre.ljust(40)[:40]
            + "T" + " ".ljust(9) + " ".ljust(40)
            + "1".rjust(9, "0") + nif.ljust(9)[:9]
            + nombre.ljust(40)[:40] + "O"
            + " ".ljust(234)
        )
        page0 = page0.ljust(346)[:346]

        # --- PAGE 1: Datos principales (1187 chars) ---
        # data_content already includes: tipo 2 + modelo + ejercicio + NIF + nombre + periodo + casillas
        page1 = data_content.ljust(1187)[:1187]

        # --- PAGE 2-8: Continuación y datos adicionales ---
        page2 = data_content.ljust(1806)[:1806]
        page3 = ("2" + "390" + ejercicio.rjust(4, "0") + nif.ljust(9)[:9] + " ".ljust(1828))[:1840]
        page4 = ("2" + "390" + ejercicio.rjust(4, "0") + " ".ljust(848))[:854]
        page5 = ("2" + "390" + ejercicio.rjust(4, "0") + " ".ljust(1512))[:1519]
        page6 = ("2" + "390" + ejercicio.rjust(4, "0") + " ".ljust(821))[:828]
        page7 = ("2" + "390" + ejercicio.rjust(4, "0") + " ".ljust(769))[:776]
        page8 = ("2" + "390" + ejercicio.rjust(4, "0") + " ".ljust(1085))[:1092]

        pages = [
            ("00000", page0, 346),
            ("01000", page1, 1187),
            ("02000", page2, 1806),
            ("03000", page3, 1840),
            ("04000", page4, 854),
            ("05000", page5, 1519),
            ("06000", page6, 828),
            ("07000", page7, 776),
            ("08000", page8, 1092),
        ]

        lines = []
        for code, content, expected_len in pages:
            content = content.ljust(expected_len)[:expected_len]
            tag = f"T{self.aeat_model_code}{code}"
            lines.append(f"<{tag}>{content}</{tag}>")

        text = "\n".join(lines)

        filename = f"{self.aeat_model_code}_{self.year}_{self.period_type}.txt"
        f = boe.attach_boe_file(self, text, filename)
        frappe.msgprint(f"Fichero BOE generado: {filename}", indicator="green")
        return f.file_url
