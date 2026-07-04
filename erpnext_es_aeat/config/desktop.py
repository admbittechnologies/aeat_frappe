# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
from frappe import _


def get_data():
    return [
        {
            "module_name": "ERPNext ES AEAT",
            "category": "Modules",
            "label": _("AEAT España"),
            "color": "#c0392b",
            "icon": "octicon octicon-law",
            "type": "module",
            "description": "Modelos tributarios españoles (303, 111, 115, 130, 390, 347, 349).",
        }
    ]
