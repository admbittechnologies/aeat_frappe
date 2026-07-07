# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
"""
Declarative BOE file generator.

Generates AEAT submission files with exact official format:
- Multi-page models (303, 390): <Txxxppppp>...content...</Txxxppppp>
- Fixed-record models (347, 349, 190, etc.): fixed-width records
- Web import models (111, 115, etc.): continuous format
"""

from __future__ import annotations

import frappe
from frappe.utils import flt

ALPHA = "alphanumeric"
INTEGER = "integer"
FLOAT = "float"
BOOLEAN = "boolean"
FIXED = "fixed"
SUBCONFIG = "subconfig"


class BOEError(frappe.ValidationError):
    pass


def _resolve(expression, doc, context=None):
    if not expression:
        return ""
    # Handle doc. prefix
    if expression.startswith("doc."):
        expression = expression[4:]
    # Handle ctx. prefix - resolve against context dict
    if expression.startswith("ctx."):
        expr = expression[4:]  # Remove ctx. prefix
        if expr.startswith("="):
            # ctx.=... -> evaluate with ctx in scope
            safe = {"doc": doc, "flt": flt, "frappe": frappe, "ctx": context or {}}
            try:
                return eval(expr[1:], {"__builtins__": {}}, safe)
            except Exception as exc:
                frappe.throw(f"Error evaluando expresion BOE '{expression}': {exc}", BOEError)
        # ctx.field -> context.get("field")
        ctx = context or {}
        val = ctx
        for part in expr.split("."):
            val = val.get(part) if isinstance(val, dict) else getattr(val, part, None)
            if val is None:
                break
        return val if val is not None else ""
    # Handle =expr (eval)
    if expression.startswith("="):
        safe = {"doc": doc, "flt": flt, "frappe": frappe, "ctx": context or {}}
        try:
            return eval(expression[1:], {"__builtins__": {}}, safe)
        except Exception as exc:
            frappe.throw(f"Error evaluando expresion BOE '{expression}': {exc}", BOEError)
    # Plain field name -> getattr from doc
    val = doc
    for part in expression.split("."):
        val = getattr(val, part, None) if not isinstance(val, dict) else val.get(part)
        if val is None:
            break
    return val if val is not None else ""


def _format_alpha(value, size, alignment="left"):
    text = str(value or "")
    text = text.upper()
    import unicodedata
    text = "".join(c for c in unicodedata.normalize("NFKD", text)
                   if unicodedata.category(c) != "Mn")
    text = text[:size]
    if alignment == "right":
        return text.rjust(size)
    return text.ljust(size)


def _format_integer(value, size, decimal_size=0):
    val = flt(value)
    if decimal_size:
        val = val * (10 ** decimal_size)
    n = int(round(val))
    body = str(abs(n))
    if n < 0:
        return ("N" + body).rjust(size, "0")[:size]
    return body.rjust(size, "0")[:size]


def _format_float(value, size, decimal_size=2, apply_sign=False,
                  positive_sign="0", negative_sign="N"):
    val = flt(value)
    negative = val < 0
    cents = int(round(abs(val) * (10 ** decimal_size)))
    body = str(cents)
    if apply_sign:
        sign_char = negative_sign if negative else positive_sign
        body = body.rjust(size - 1, "0")
        return (sign_char + body)[:size]
    return body.rjust(size, "0")[:size]


def _format_boolean(value, bool_yes="X", bool_no=" "):
    return bool_yes if value else bool_no


def render_line(line, doc, context=None):
    etype = line.get("export_type")
    size = int(line.get("size") or 0)

    # DEBUG logging
    expr = line.get("expression", "")
    if expr and not expr.startswith("="):
        val = getattr(doc, expr, None) if not isinstance(doc, dict) else doc.get(expr)
        frappe.log_error(f"AEAT DEBUG render_line: expr={expr}, val={val}, type={etype}, size={size}")

    if etype == FIXED:
        return _format_alpha(line.get("fixed_value"), size, "left")

    value = _resolve(line.get("expression"), doc, context)
    frappe.log_error(f"AEAT DEBUG _resolve returned: expr={expr}, value={value}, type={type(value)}")

    if etype == ALPHA:
        return _format_alpha(value, size, line.get("alignment") or "left")
    if etype == INTEGER:
        return _format_integer(value, size, int(line.get("decimal_size") or 0))
    if etype == FLOAT:
        return _format_float(
            value, size,
            decimal_size=int(line.get("decimal_size") or 2),
            apply_sign=bool(line.get("apply_sign")),
            positive_sign=line.get("positive_sign") or "0",
            negative_sign=line.get("negative_sign") or "N",
        )
    if etype == BOOLEAN:
        return _format_boolean(value, line.get("bool_yes") or "X", line.get("bool_no") or " ")

    frappe.throw(f"Tipo de exportacion BOE no soportado: {etype}", BOEError)


def generate_from_lines(lines, doc, context=None):
    """Generate text from a list of config lines."""
    parts = []
    for line in sorted(lines, key=lambda l: l.sequence or 0):
        parts.append(render_line(line.as_dict(), doc, context))
    return "".join(parts)


def generate(doc, config_name, context=None):
    """Generate the full BOE text for doc using config_name."""
    config = frappe.get_doc("AEAT BOE Export Config", config_name)
    frappe.log_error(f"AEAT DEBUG generate: config={config_name}, lines={len(config.lines)}")
    for line in config.lines:
        frappe.log_error(f"AEAT DEBUG generate line: seq={line.sequence}, expr={repr(line.expression)}, type={line.export_type}")
    text = generate_from_lines(config.lines, doc, context)

    if config.record_length and config.record_length > 0:
        if len(text) != config.record_length:
            frappe.msgprint(
                f"Aviso: la longitud generada ({len(text)}) no coincide con la "
                f"longitud de registro declarada ({config.record_length}) en "
                f"'{config_name}'. Se ajusta automaticamente.",
                indicator="orange",
            )
        text = text.ljust(config.record_length)[:config.record_length]
    return text


def attach_boe_file(doc, text, filename):
    return frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "is_private": 0,
            "content": text,
        }
    ).insert(ignore_permissions=True)


@frappe.whitelist()
def download_boe(doctype, docname):
    doc = frappe.get_doc(doctype, docname)
    config_name = getattr(doc, "boe_config_name", None)
    if not config_name:
        frappe.throw(f"El modelo no tiene export BOE configurado.")
    text = generate(doc, config_name)
    filename = f"{doc.aeat_model_code}_{doc.year}_{doc.period_type}.txt"
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = text.encode("latin-1", errors="replace")
    frappe.local.response.type = "download"
    frappe.local.response.content_type = "text/plain; charset=latin-1"

