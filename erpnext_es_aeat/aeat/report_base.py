# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
"""Shared base for AEAT model report controllers (303, 111, 115, 130, ...).

Frappe has no abstract DocType inheritance like Odoo, so we share behaviour via
a plain Python mixin that each model's ``Document`` subclass inherits, alongside
a common ``AEAT Tax Map`` engine. This mirrors OCA's ``l10n.es.aeat.report``.
"""

from __future__ import annotations

import calendar
from datetime import date

import frappe
from frappe.utils import flt, getdate

from erpnext_es_aeat.aeat import boe, tax_engine

PERIOD_MONTHS = {
    "01": 1, "02": 2, "03": 3, "04": 4, "05": 5, "06": 6,
    "07": 7, "08": 8, "09": 9, "10": 10, "11": 11, "12": 12,
}
PERIOD_QUARTERS = {"1T": (1, 3), "2T": (4, 6), "3T": (7, 9), "4T": (10, 12)}


class AEATReportMixin:
    """Behaviour shared by all modelo controllers.

    Subclasses must define:
      * ``aeat_model_code``  e.g. "303"
      * ``boe_config_name``  name of the AEAT BOE Export Config (or None)
    and may override:
      * ``assign_boxes(boxes)`` to copy BoxResults into named casilla fields
      * ``extra_calculation()`` for model-specific arithmetic (resultados, etc.)
    """

    aeat_model_code: str = ""
    boe_config_name: str | None = None

    # -- period -----------------------------------------------------------
    def compute_period(self):
        """Set ``date_start`` / ``date_end`` from ``year`` + ``period_type``."""
        if not self.year:
            frappe.throw("El campo 'Año' es obligatorio para calcular el período.")
        year = int(self.year)
        pt = self.period_type
        if not pt:
            frappe.throw("El campo 'Periodo' es obligatorio para calcular el período.")
        if pt == "0A":
            self.date_start = date(year, 1, 1)
            self.date_end = date(year, 12, 31)
        elif pt in PERIOD_QUARTERS:
            m0, m1 = PERIOD_QUARTERS[pt]
            self.date_start = date(year, m0, 1)
            self.date_end = date(year, m1, calendar.monthrange(year, m1)[1])
        elif pt in PERIOD_MONTHS:
            m = PERIOD_MONTHS[pt]
            self.date_start = date(year, m, 1)
            self.date_end = date(year, m, calendar.monthrange(year, m)[1])
        else:
            frappe.throw(f"Periodo no válido: {pt}")

    # -- tax map ----------------------------------------------------------
    def get_tax_map(self):
        """Return the AEAT Tax Map for this model + company (with default fallback)."""
        filters = {"aeat_model": self.aeat_model_code, "company": self.company}
        name = frappe.db.get_value("AEAT Tax Map", filters)
        if not name:
            name = frappe.db.get_value(
                "AEAT Tax Map", {"aeat_model": self.aeat_model_code, "is_default": 1}
            )
        if not name:
            frappe.throw(
                f"No hay un Mapa de impuestos AEAT para el modelo {self.aeat_model_code}. "
                "Crea uno o ejecuta el seeding por defecto."
            )
        return frappe.get_doc("AEAT Tax Map", name)

    def map_lines_as_dicts(self):
        tax_map = self.get_tax_map()
        # Each line already carries its ``accounts`` Small Text field, so a
        # plain as_dict() is enough for the engine.
        return [line.as_dict() for line in tax_map.lines]

    # -- orchestration ----------------------------------------------------
    @frappe.whitelist()
    def calculate(self):
        """Compute every casilla and persist the document."""
        self.compute_period()
        boxes = tax_engine.compute_boxes(
            self.company, self.date_start, self.date_end, self.map_lines_as_dicts()
        )
        self.assign_boxes(boxes)
        self.extra_calculation()
        self.calculation_state = "Calculated"
        self.save()
        frappe.msgprint("Cálculo completado.", indicator="green")
        return True

    def assign_boxes(self, boxes):
        """Fill every ``casilla_NN`` field that exists on the doc + JSON snapshot.

        For each box, the non-zero figure (base or cuota) is written, since a
        given casilla is mapped either as a base or as a cuota. Computed totals
        and resultados are filled afterwards by :meth:`extra_calculation`.
        """
        snapshot = {}
        for fn, b in boxes.items():
            snapshot[str(fn)] = {"name": b.name, "base": flt(b.base), "cuota": flt(b.cuota)}
            field = f"casilla_{fn:02d}"
            if self.meta.has_field(field):
                val = b.base if abs(flt(b.base)) > 0 else b.cuota
                self.set(field, flt(val))
        self.boxes_json = frappe.as_json(snapshot)
        self._boxes = boxes  # kept for extra_calculation

    def extra_calculation(self):  # override
        pass

    # -- BOE --------------------------------------------------------------
    @frappe.whitelist()
    def export_boe(self):
        if not self.boe_config_name:
            frappe.throw(f"El modelo {self.aeat_model_code} no tiene export BOE configurado.")
        text = boe.generate(self, self.boe_config_name)
        filename = f"{self.aeat_model_code}_{self.year}_{self.period_type}.txt"
        f = boe.attach_boe_file(self, text, filename)
        frappe.msgprint(f"Fichero BOE generado: {filename}", indicator="green")
        return f.file_url

    # -- helpers for subclasses ------------------------------------------
    def box(self, boxes, field_number, which="cuota"):
        b = boxes.get(int(field_number))
        if not b:
            return 0.0
        return flt(b.base if which == "base" else b.cuota)
