"""Minimal in-memory `frappe` stub for offline regression testing.

It emulates ONLY the surface the AEAT engine touches: a SQL router over the
ERPNext tables we query (Sales/Purchase Taxes and Charges, Sales/Purchase
Invoice, GL Entry, Account) plus get_doc for the app's own AEAT Tax Map / BOE
Export Config. Registries below are populated by the test runner.
"""

import json as _json
import sys
import types


# ---------------------------------------------------------------------------
# Registries the runner fills
# ---------------------------------------------------------------------------
TAX_ROWS = {"Sales Invoice": [], "Purchase Invoice": []}
GL_ROWS = []
SI_ROWS = []          # party-level sales invoices
PI_ROWS = []          # party-level purchase invoices
ACCOUNTS = []         # {name, account_number, company, is_group}
MAP_BY_MODEL = {}     # model_code -> map name
TAX_MAP_DOCS = {}     # name -> spec dict (with filled accounts)
BOE_CONFIG_DOCS = {}  # title -> spec dict


class ValidationError(Exception):
    pass


def throw(msg, exc=ValidationError):
    raise (exc if isinstance(exc, type) else ValidationError)(str(msg))


def msgprint(*a, **k):
    pass


def whitelist(*a, **k):
    def deco(fn):
        return fn
    return deco


def as_json(obj):
    return _json.dumps(obj, default=str)


# ---------------------------------------------------------------------------
# Fake documents
# ---------------------------------------------------------------------------
class FakeRow:
    def __init__(self, data):
        self.__dict__["_d"] = dict(data)

    def __getattr__(self, k):
        return self.__dict__["_d"].get(k)

    def __setattr__(self, k, v):
        self.__dict__["_d"][k] = v

    def get(self, k, default=None):
        return self._d.get(k, default)

    def as_dict(self):
        return dict(self._d)


class FakeParent:
    def __init__(self, fields, lines=None):
        self.__dict__.update(fields)
        self.lines = [FakeRow(x) for x in (lines or [])]


def get_doc(doctype, name=None):
    if doctype == "AEAT Tax Map":
        spec = TAX_MAP_DOCS[name]
        return FakeParent({"title": name, "aeat_model": spec["aeat_model"]},
                          spec["lines_filled"])
    if doctype == "AEAT BOE Export Config":
        spec = BOE_CONFIG_DOCS[name]
        return FakeParent({"title": name, "record_length": spec.get("record_length", 0)},
                          spec["lines"])
    if isinstance(doctype, dict) and doctype.get("doctype") == "File":
        # attach_boe_file path -> capture content, return object with insert()
        holder = FakeRow(doctype)
        holder._d["file_url"] = "/private/files/" + doctype.get("file_name", "boe.txt")

        def _insert(ignore_permissions=False):
            LAST_BOE.append(doctype.get("content"))
            return holder
        holder.insert = _insert
        return holder
    raise RuntimeError(f"stub get_doc no soportado: {doctype}")


LAST_BOE = []


# ---------------------------------------------------------------------------
# Fake DB
# ---------------------------------------------------------------------------
class _DB:
    def get_value(self, doctype, filters, fieldname=None):
        if doctype == "AEAT Tax Map":
            return MAP_BY_MODEL.get(filters.get("aeat_model"))
        return None

    def exists(self, doctype, filters=None):
        if doctype == "Account" and isinstance(filters, dict):
            name = filters.get("name")
            return any(a["name"] == name for a in ACCOUNTS)
        return False

    def commit(self):
        pass

    def sql(self, query, params=None, as_dict=False):
        q = " ".join(query.split())
        p = params or {}
        # --- invoice tax rows (sales/purchase) ---
        if "Taxes and Charges" in q:
            parent = p["parent"]
            out = []
            for r in TAX_ROWS[parent]:
                if r["company"] != p["company"]:
                    continue
                if not (p["start"] <= r["posting_date"] <= p["end"]):
                    continue
                if r["account_head"] not in p["accounts"]:
                    continue
                if "inv.is_return = 0" in q and r["is_return"]:
                    continue
                if "inv.is_return = 1" in q and not r["is_return"]:
                    continue
                row = dict(r)
                row["parent"] = r["parent"]
                row["parenttype"] = parent
                out.append(FakeRow(row) if not as_dict else row)
            return [FakeRow(x) if not isinstance(x, FakeRow) else x for x in out]
        # --- GL balance ---
        if "tabGL Entry" in q:
            bal = 0.0
            for r in GL_ROWS:
                if r["company"] != p["company"]:
                    continue
                if not (p["start"] <= r["posting_date"] <= p["end"]):
                    continue
                if r["account"] not in p["accounts"]:
                    continue
                bal += r["debit"] - r["credit"]
            return [FakeRow({"bal": bal})]
        # --- party invoice totals ---
        if "tabSales Invoice" in q:
            return [FakeRow(r) for r in SI_ROWS
                    if r["company"] == p["company"] and p["start"] <= r["posting_date"] <= p["end"]]
        if "tabPurchase Invoice" in q:
            return [FakeRow(r) for r in PI_ROWS
                    if r["company"] == p["company"] and p["start"] <= r["posting_date"] <= p["end"]]
        return []


db = _DB()


def get_all(doctype, filters=None, fields=None, pluck=None, **kw):
    if doctype == "Account":
        company = filters.get("company")
        out = []
        for a in ACCOUNTS:
            if a["company"] != company or a.get("is_group"):
                continue
            num = filters.get("account_number")
            if isinstance(num, list) and num and num[0] == "like":
                pat = num[1].rstrip("%")
                if not str(a.get("account_number", "")).startswith(pat):
                    continue
            elif num is not None and a.get("account_number") != num:
                continue
            out.append(a["name"] if pluck == "name" else a)
        return out
    return []


def new_doc(doctype):
    raise RuntimeError("new_doc no usado en regresión")


# ---------------------------------------------------------------------------
# Wire up submodules so `import frappe.utils` / `frappe.model.document` work
# ---------------------------------------------------------------------------
_utils = types.ModuleType("frappe.utils")


def flt(v, precision=None):
    try:
        return round(float(v or 0), precision) if precision is not None else float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def getdate(v=None):
    return v


_utils.flt = flt
_utils.getdate = getdate

_model = types.ModuleType("frappe.model")
_doc = types.ModuleType("frappe.model.document")


class Document:
    def __init__(self, **kw):
        self.lines = []
        self.doctype = type(self).__name__
        self.name = "TEST-001"
        for k, v in kw.items():
            setattr(self, k, v)

    def get(self, k, default=None):
        return getattr(self, k, default)

    def set(self, k, v):
        setattr(self, k, v)

    def save(self):
        pass

    def append(self, key, value):
        lst = getattr(self, key, None)
        if lst is None:
            lst = []
            setattr(self, key, lst)
        lst.append(FakeRow(value))

    @property
    def meta(self):
        outer = self

        class _M:
            def has_field(self, f):
                # casillas of the model are real fields; allow them
                return True
        return _M()


_doc.Document = Document
_model.document = _doc

_self = sys.modules[__name__]
sys.modules["frappe.utils"] = _utils
sys.modules["frappe.model"] = _model
sys.modules["frappe.model.document"] = _doc
_self.utils = _utils
_self.model = _model
