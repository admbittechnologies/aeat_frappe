# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
from frappe.utils import flt
from erpnext_es_aeat.erpnext_es_aeat.aeat.report_base import AEATReportMixin
from frappe.model.document import Document


class AEATMod115(AEATReportMixin, Document):
    aeat_model_code = "115"
    boe_config_name = "BOE Modelo 115"

    def extra_calculation(self):
        self.casilla_04 = flt(self.get("casilla_03"))
