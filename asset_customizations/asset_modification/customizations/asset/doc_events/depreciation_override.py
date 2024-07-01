# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Max, Min
from frappe.utils import (
    add_months,
    cint,
    flt,
    get_last_day,
    get_link_to_form,
    getdate,
    is_last_day_of_the_month,
    nowdate,
    today,
)
from frappe.utils.user import get_users_with_role

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_checks_for_pl_and_bs_accounts,
)
from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
    get_asset_depr_schedule_doc,
    get_asset_depr_schedule_name,
    get_temp_asset_depr_schedule_doc,
    make_new_active_asset_depr_schedules_and_cancel_current_ones,
)
from erpnext.assets.doctype.asset.depreciation import get_credit_and_debit_accounts_for_asset_category_and_company,_make_journal_entry_for_depreciation

@frappe.whitelist()
def make_depreciation_entry(
    asset_depr_schedule_name,
    date=None,
    sch_start_idx=None,
    sch_end_idx=None,
    credit_and_debit_accounts=None,
    depreciation_cost_center_and_depreciation_series=None,
    accounting_dimensions=None,
    **kwargs
):
    frappe.has_permission("Journal Entry", throw=True)
    
    if not date:
        date = today()

    asset_depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", asset_depr_schedule_name)

    asset = frappe.get_doc("Asset", asset_depr_schedule_doc.asset)

    if credit_and_debit_accounts:
        credit_account, debit_account = credit_and_debit_accounts
    else:
        credit_account, debit_account = get_credit_and_debit_accounts_for_asset_category_and_company(
            asset.asset_category, asset.company
        )

    if depreciation_cost_center_and_depreciation_series:
        depreciation_cost_center, depreciation_series = depreciation_cost_center_and_depreciation_series
    else:
        depreciation_cost_center, depreciation_series = frappe.get_cached_value(
            "Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
        )

    depreciation_cost_center = asset.cost_center or depreciation_cost_center

    if not accounting_dimensions:
        accounting_dimensions = get_checks_for_pl_and_bs_accounts()

    depreciation_posting_error = None

    for d in asset_depr_schedule_doc.get("depreciation_schedule")[
        sch_start_idx or 0 : sch_end_idx or len(asset_depr_schedule_doc.get("depreciation_schedule"))
    ]:
        try:
            _make_journal_entry_for_depreciation(
                asset_depr_schedule_doc,
                asset,
                date,
                d,
                sch_start_idx,
                sch_end_idx,
                depreciation_cost_center,
                depreciation_series,
                credit_account,
                debit_account,
                accounting_dimensions,
                **kwargs
            )
        except Exception as e:
            depreciation_posting_error = e

    asset.set_status()

    if not depreciation_posting_error:
        asset.db_set("depr_entry_posting_status", "Successful")
        return asset_depr_schedule_doc

    raise depreciation_posting_error


def _make_journal_entry_for_depreciation(
    asset_depr_schedule_doc,
    asset,
    date,
    depr_schedule,
    sch_start_idx,
    sch_end_idx,
    depreciation_cost_center,
    depreciation_series,
    credit_account,
    debit_account,
    accounting_dimensions,
    **kwargs
):
    if not (sch_start_idx and sch_end_idx) and not (
        not depr_schedule.journal_entry and getdate(depr_schedule.schedule_date) <= getdate(date)
    ):
        return

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Depreciation Entry"
    je.naming_series = depreciation_series
    je.posting_date = depr_schedule.schedule_date
    je.company = asset.company
    je.finance_book = asset_depr_schedule_doc.finance_book
    je.remark = f"Depreciation Entry against {asset.name} worth {depr_schedule.depreciation_amount}"

    fields = frappe.get_list("Accounting Dimension", pluck="name")
    additional_fields = {}
    for i in fields:
        field_name = i.lower().replace(' ', '_')
        field_data = frappe.db.get_value("Asset Depreciation Schedule", asset_depr_schedule_doc.name, field_name)
        additional_fields[field_name] = field_data
  
    credit_entry = {
        "account": credit_account,
        "credit_in_account_currency": depr_schedule.depreciation_amount,
        "reference_type": "Asset",
        "reference_name": asset.name,
        "cost_center": depreciation_cost_center,
    }
    credit_entry.update(additional_fields)

    debit_entry = {
        "account": debit_account,
        "debit_in_account_currency": depr_schedule.depreciation_amount,
        "reference_type": "Asset",
        "reference_name": asset.name,
        "cost_center": depreciation_cost_center,
    }
    debit_entry.update(additional_fields)

    for dimension in accounting_dimensions:
        if asset.get(dimension["fieldname"]) or dimension.get("mandatory_for_bs"):
            credit_entry.update(
                {
                    dimension["fieldname"]: asset.get(dimension["fieldname"])
                    or dimension.get("default_dimension")
                }
            )

        if asset.get(dimension["fieldname"]) or dimension.get("mandatory_for_pl"):
            debit_entry.update(
                {
                    dimension["fieldname"]: asset.get(dimension["fieldname"])
                    or dimension.get("default_dimension")
                }
            )

    je.append("accounts", credit_entry)
    je.append("accounts", debit_entry)

    je.flags.ignore_permissions = True
    je.flags.planned_depr_entry = True
    je.save()

    depr_schedule.db_set("journal_entry", je.name)

    if not je.meta.get_workflow():
        je.submit()
        idx = cint(asset_depr_schedule_doc.finance_book_id)
        row = asset.get("finance_books")[idx - 1]
        row.value_after_depreciation -= depr_schedule.depreciation_amount
        row.db_update()


def get_depreciation_accounts(asset_category, company):
    fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None

    accounts = frappe.db.get_value(
        "Asset Category Account",
        filters={"parent": asset_category, "company_name": company},
        fieldname=[
            "fixed_asset_account",
            "accumulated_depreciation_account",
            "depreciation_expense_account",
        ],
        as_dict=1,
    )

    if accounts:
        fixed_asset_account = accounts.fixed_asset_account
        accumulated_depreciation_account = accounts.accumulated_depreciation_account
        depreciation_expense_account = accounts.depreciation_expense_account

    if not accumulated_depreciation_account or not depreciation_expense_account:
        accounts = frappe.get_cached_value(
            "Company", company, ["accumulated_depreciation_account", "depreciation_expense_account"]
        )

        if not accumulated_depreciation_account:
            accumulated_depreciation_account = accounts[0]
        if not depreciation_expense_account:
            depreciation_expense_account = accounts[1]

    if not fixed_asset_account or not accumulated_depreciation_account or not depreciation_expense_account:
        frappe.throw(
            _("Please set Depreciation related Accounts in Asset Category {0} or Company {1}").format(
                asset_category, company
            )
        )

    return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account
