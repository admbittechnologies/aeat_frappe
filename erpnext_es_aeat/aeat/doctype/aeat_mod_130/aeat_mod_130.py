# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
from frappe.utils import flt
from erpnext_es_aeat.erpnext_es_aeat.aeat.report_base import AEATReportMixin
from frappe.model.document import Document


class AEATMod130(AEATReportMixin, Document):
    aeat_model_code = "130"
    boe_config_name = "BOE Modelo 130"

    def compute_period(self):
        # 130 es acumulado desde el 1 de enero hasta fin de trimestre
        super().compute_period()
        from datetime import date
        self.date_start = date(int(self.year), 1, 1)

    def extra_calculation(self):
        c = lambda n: flt(self.get(f"casilla_{n}"))
        self.casilla_03 = c("01") - c("02")            # rendimiento neto
        self.casilla_04 = max(self.casilla_03, 0) * 0.20  # 20%
        self.casilla_07 = self.casilla_04 - c("05") - c("06")
        self.casilla_12 = max(self.casilla_07, 0)
        self.casilla_15 = self.casilla_12 - c("14")
