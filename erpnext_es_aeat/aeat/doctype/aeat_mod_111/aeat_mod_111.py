# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
from frappe.utils import flt
from erpnext_es_aeat.erpnext_es_aeat.aeat.report_base import AEATReportMixin
from frappe.model.document import Document


class AEATMod111(AEATReportMixin, Document):
    aeat_model_code = "111"
    boe_config_name = "BOE Modelo 111"

    def extra_calculation(self):
        c = lambda n: flt(self.get(f"casilla_{n}"))
        # Total bases y total retenciones (trabajo + actividades)
        self.casilla_28 = c("02") + c("05")
        self.casilla_29 = c("03") + c("06")
        self.casilla_30 = self.casilla_29
