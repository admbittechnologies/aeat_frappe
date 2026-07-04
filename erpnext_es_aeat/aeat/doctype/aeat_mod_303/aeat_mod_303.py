# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later

import frappe
from frappe.utils import flt

from erpnext_es_aeat.erpnext_es_aeat.aeat.report_base import AEATReportMixin
from erpnext_es_aeat.erpnext_es_aeat.aeat import boe


class AEATMod303(AEATReportMixin, frappe.model.document.Document):
    aeat_model_code = "303"
    boe_config_name = "BOE Modelo 303"

    def validate(self):
        self.compute_period()

    def _c(self, num):
        """Return casilla value or 0 if field does not exist."""
        return flt(getattr(self, f"casilla_{num:02d}", 0))

    def extra_calculation(self):
        # IVA Devengado (ventas) - sum all rechargeable VAT quotas
        self.casilla_27 = (
            self._c(3) + self._c(6) + self._c(9)
            + self._c(12) + self._c(15) + self._c(18)
            + self._c(21) + self._c(24) + self._c(26)
        )
        # IVA Deducible (compras)
        self.casilla_44 = (
            self._c(29) + self._c(31) + self._c(33)
            + self._c(35) + self._c(37) + self._c(39)
            + self._c(40) + self._c(41) + self._c(42)
            + self._c(43)
        )
        self.casilla_45 = self._c(27) - self._c(44)
        self.casilla_46 = self._c(45) - self._c(47)
        self.casilla_69 = self._c(46)
        if self._c(69) < 0:
            self.casilla_71 = abs(self._c(69))
        if self._c(69) > 0:
            self.casilla_70 = self._c(69)

    @frappe.whitelist()
    def export_boe(self):
        if not self.boe_config_name:
            frappe.throw("El modelo 303 no tiene export BOE configurado.")

        nif = frappe.db.get_value("Company", self.company, "tax_id") or ""
        nombre = self.company or ""
        ejercicio = str(self.year or "")

        config = frappe.get_doc("AEAT BOE Export Config", self.boe_config_name)
        data_lines = [l for l in config.lines if (l.sequence or 0) >= 100]
        data_content = boe.generate_from_lines(data_lines, self) if data_lines else ""

        # PAGE 0: Identificacion (346 chars)
        page0 = (
            "1" + "303" + ejercicio.rjust(4, "0")
            + nif.ljust(9)[:9] + nombre.ljust(40)[:40]
            + "T" + " ".ljust(9) + " ".ljust(40)
            + "1".rjust(9, "0") + nif.ljust(9)[:9]
            + nombre.ljust(40)[:40] + "O"
            + " ".ljust(234)
        )
        page0 = page0.ljust(346)[:346]

        # PAGE 1-5: data_content already includes tipo 2 header + casillas
        page1 = data_content.ljust(1581)[:1581]
        page2 = data_content.ljust(1900)[:1900]
        page3 = ("2" + "303" + ejercicio.rjust(4, "0") + nif.ljust(9)[:9] + " ".ljust(1003))[:1017]
        page4 = ("2" + "303" + ejercicio.rjust(4, "0") + " ".ljust(391))[:398]
        page5 = ("2" + "303" + ejercicio.rjust(4, "0") + " ".ljust(1521))[:1528]

        pages = [
            ("00000", page0, 346),
            ("01000", page1, 1581),
            ("02000", page2, 1900),
            ("03000", page3, 1017),
            ("04000", page4, 398),
            ("05000", page5, 1528),
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

