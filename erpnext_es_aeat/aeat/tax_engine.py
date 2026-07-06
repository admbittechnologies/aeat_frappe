# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
"""
AEAT calculation engine for ERPNext.

This module translates the OCA `l10n_es_aeat` "tax map" idea to the ERPNext
data model. In ERPNext, Spanish VAT is modelled with *Sales/Purchase Taxes and
Charges Templates* (one **account head** per rate, e.g. "IVA Repercutido 21%")
and IRPF withholdings with *Tax Withholding Category* (which also posts to a
dedicated account). Therefore the natural aggregation key here is the **GL
account**, not an Odoo-style global ``account.tax`` object.

A box (``casilla``) is defined by an :class:`AEAT Tax Map Line` and resolved by
:func:`compute_boxes` into a base imponible and a cuota.

Assumptions (documented and valid for the "standard" setup: per-rate templates
+ Tax Withholding Category):
  * One tax *account head* corresponds to a single VAT/IRPF rate. The taxable
    base of a tax row is therefore derived as ``cuota / rate * 100``.
  * Only submitted (``docstatus = 1``) invoices are considered.
  * ``posting_date`` determines the period (devengo por fecha de factura).
  * ``is_return = 1`` marks a refund/abono (rectificativa).

For exento (rate = 0) boxes, the cuota/rate derivation is not possible; such
boxes must be mapped with ``field_type = "base"`` against a *base account*
(a non-tax account that collects the exempt net), or filled manually. See
README → "Casillas exentas".
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field

import frappe
from frappe.utils import flt

# Map line "move_type" values
MOVE_ALL = "all"
MOVE_REGULAR = "regular"
MOVE_REFUND = "refund"

# Map line "field_type" values
FIELD_BASE = "base"
FIELD_AMOUNT = "amount"  # cuota
FIELD_BOTH = "both"


@dataclass
class BoxResult:
    """Aggregated result for a single casilla (field_number)."""

    field_number: int
    name: str = ""
    base: float = 0.0
    cuota: float = 0.0
    # Audit trail: list of (voucher_type, voucher_no, account, base, cuota)
    detail: list = field(default_factory=list)

    def add(self, base, cuota, ref=None):
        self.base = flt(self.base) + flt(base)
        self.cuota = flt(self.cuota) + flt(cuota)
        if ref:
            self.detail.append(ref)


# ----------------------------------------------------------------------------
# Low-level data access
# ----------------------------------------------------------------------------
def _tax_rows(company, date_start, date_end, accounts, move_type=MOVE_ALL):
    """Return invoice tax rows (sales + purchase) hitting ``accounts``.

    Each returned dict carries: ``parenttype``, ``parent``, ``account_head``,
    ``rate``, ``base_tax_amount`` (company-currency cuota), ``is_return`` and
    ``item_wise_tax_detail``.
    """
    if not accounts:
        return []
    accounts = list(accounts)

    return_filter = ""
    if move_type == MOVE_REGULAR:
        return_filter = "AND inv.is_return = 0"
    elif move_type == MOVE_REFUND:
        return_filter = "AND inv.is_return = 1"

    rows = []
    for child, parent in (
        ("Sales Taxes and Charges", "Sales Invoice"),
        ("Purchase Taxes and Charges", "Purchase Invoice"),
    ):
        data = frappe.db.sql(
            f"""
            SELECT  t.parent              AS parent,
                    %(parent)s            AS parenttype,
                    t.account_head        AS account_head,
                    t.rate                AS rate,
                    t.base_tax_amount     AS base_tax_amount,
                    t.tax_amount          AS tax_amount,
                    t.item_wise_tax_detail AS item_wise_tax_detail,
                    inv.is_return         AS is_return,
                    inv.posting_date      AS posting_date
            FROM `tab{child}` t
            INNER JOIN `tab{parent}` inv ON inv.name = t.parent
            WHERE inv.docstatus = 1
              AND inv.company = %(company)s
              AND inv.posting_date BETWEEN %(start)s AND %(end)s
              AND t.account_head IN %(accounts)s
              {return_filter}
            """,
            {
                "parent": parent,
                "company": company,
                "start": date_start,
                "end": date_end,
                "accounts": tuple(accounts),
            },
            as_dict=True,
        )
        rows.extend(data)
    return rows


def gl_account_balance(company, accounts, date_start, date_end, signed="net"):
    """Net movement (debit - credit) of ``accounts`` within the period.

    Used for account-based boxes (e.g. modelo 130 ingresos/gastos) where the
    figure is a plain GL balance rather than a VAT row.
    """
    if not accounts:
        return 0.0
    res = frappe.db.sql(
        """
        SELECT COALESCE(SUM(debit - credit), 0) AS bal
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND is_cancelled = 0
          AND posting_date BETWEEN %(start)s AND %(end)s
          AND account IN %(accounts)s
        """,
        {
            "company": company,
            "start": date_start,
            "end": date_end,
            "accounts": tuple(accounts),
        },
        as_dict=True,
    )
    bal = flt(res[0].bal) if res else 0.0
    if signed == "credit":
        return -bal
    return bal


# ----------------------------------------------------------------------------
# Box computation
# ----------------------------------------------------------------------------
def _derive_base(rate, cuota):
    """Derive taxable base from rate and cuota. rate is a percentage."""
    rate = flt(rate)
    if not rate:
        return 0.0
    return flt(cuota) / rate * 100.0


def _line_accounts(line):
    """Return the set of account names referenced by a map line.

    ``accounts`` may be a Small Text (one account per line, or comma separated)
    or a list of dicts/objects with an ``account`` attribute.
    """
    raw = line.get("accounts")
    accounts = set()
    if not raw:
        return accounts
    if isinstance(raw, str):
        for token in raw.replace(",", "\n").splitlines():
            token = token.strip()
            if token:
                accounts.add(token)
    else:
        for acc in raw:
            name = acc.get("account") if isinstance(acc, dict) else getattr(acc, "account", None)
            if name:
                accounts.add(name)
    return accounts


def _resolve_accounts(company, tokens):
    """Map tokens (account names or PGC numbers/prefixes) to real account names.

    A token matches if (a) it is an existing account name, or (b) it is an
    ``account_number`` (exact) of an account in the company, or (c) accounts
    whose ``account_number`` starts with the token (prefix), enabling mappings
    like "477" -> all 477x IVA repercutido subaccounts.
    """
    names = set()
    for tok in tokens:
        if frappe.db.exists("Account", {"name": tok, "company": company}):
            names.add(tok)
            continue
        exact = frappe.get_all(
            "Account",
            filters={"company": company, "account_number": tok, "is_group": 0},
            pluck="name",
        )
        if exact:
            names.update(exact)
            continue
        like = frappe.get_all(
            "Account",
            filters={"company": company, "account_number": ["like", f"{tok}%"], "is_group": 0},
            pluck="name",
        )
        names.update(like)
    return names


def compute_boxes(company, date_start, date_end, lines):
    """Compute every casilla defined by ``lines`` for the given period.

    ``lines`` is an iterable of dicts/Documents with at least:
        field_number, box_name, field_type, sum_type, move_type, inverse,
        source ("tax" | "gl"), and an ``accounts`` text field.

    Returns ``{field_number: BoxResult}``.
    """
    results: dict[int, BoxResult] = {}

    for line in lines:
        fn = int(line.get("field_number"))
        res = results.setdefault(fn, BoxResult(field_number=fn, name=line.get("box_name") or ""))
        raw_accounts = _line_accounts(line)
        accounts = _resolve_accounts(company, raw_accounts)
        sign = -1.0 if line.get("inverse") else 1.0
        move_type = line.get("move_type") or MOVE_ALL
        field_type = line.get("field_type") or FIELD_AMOUNT
        source = line.get("source") or "tax"

        # DEBUG logging
        frappe.log_error(
            f"AEAT DEBUG compute_boxes: fn={fn}, raw_accounts={raw_accounts}, "
            f"resolved_accounts={accounts}, source={source}, field_type={field_type}, "
            f"move_type={move_type}, date_start={date_start}, date_end={date_end}"
        )

        if source == "gl":
            # Plain GL balance (e.g. modelo 130 ingresos/gastos groups)
            signed = "credit" if (line.get("sum_type") == "credit") else "net"
            bal = gl_account_balance(company, accounts, date_start, date_end, signed)
            res.add(base=sign * bal, cuota=0.0,
                    ref=("GL", ",".join(sorted(accounts)), sign * bal, 0.0))
            continue

        tax_rows = _tax_rows(company, date_start, date_end, accounts, move_type)
        frappe.log_error(
            f"AEAT DEBUG tax_rows: fn={fn}, found={len(tax_rows)} rows, accounts={accounts}"
        )
        for row in tax_rows:
            cuota = flt(row.base_tax_amount)
            base = _derive_base(row.rate, cuota)
            frappe.log_error(
                f"AEAT DEBUG row: parent={row.parent}, account_head={row.account_head}, "
                f"rate={row.rate}, cuota={cuota}, base={base}"
            )
            # Refund rows carry the natural sign already (negative tax_amount on
            # returns), so we only apply the configured inversion.
            add_base = sign * base if field_type in (FIELD_BASE, FIELD_BOTH) else 0.0
            add_cuota = sign * cuota if field_type in (FIELD_AMOUNT, FIELD_BOTH) else 0.0
            res.add(
                base=add_base,
                cuota=add_cuota,
                ref=(row.parenttype, row.parent, row.account_head, add_base, add_cuota),
            )

    return results


# ----------------------------------------------------------------------------
# Party-level aggregation (modelos 347 / 349)
# ----------------------------------------------------------------------------
def party_invoice_totals(company, date_start, date_end, party_type, accounts=None):
    """Aggregate invoice totals per party (customer/supplier) for a period.

    Returns a list of dicts: party, party_name, tax_id, total, q1..q4 (when
    spanning a full year these split by natural quarter).
    """
    if party_type == "Customer":
        parent = "Sales Invoice"
        party_field = "customer"
        name_field = "customer_name"
    else:
        parent = "Purchase Invoice"
        party_field = "supplier"
        name_field = "supplier_name"

    rows = frappe.db.sql(
        f"""
        SELECT  inv.{party_field}      AS party,
                inv.{name_field}       AS party_name,
                inv.tax_id             AS tax_id,
                inv.posting_date       AS posting_date,
                inv.is_return          AS is_return,
                inv.base_grand_total   AS amount
        FROM `tab{parent}` inv
        WHERE inv.docstatus = 1
          AND inv.company = %(company)s
          AND inv.posting_date BETWEEN %(start)s AND %(end)s
        """,
        {"company": company, "start": date_start, "end": date_end},
        as_dict=True,
    )

    agg: dict[str, dict] = {}
    for r in rows:
        key = r.party
        a = agg.setdefault(
            key,
            {
                "party": r.party,
                "party_name": r.party_name,
                "tax_id": r.tax_id,
                "total": 0.0,
                "q1": 0.0,
                "q2": 0.0,
                "q3": 0.0,
                "q4": 0.0,
            },
        )
        amount = flt(r.amount) * (-1 if r.is_return else 1)
        a["total"] += amount
        q = (r.posting_date.month - 1) // 3 + 1
        a[f"q{q}"] += amount
    return list(agg.values())
