import frappe
from frappe import _
from frappe.utils import (
    cint,
    getdate,
    today,
)

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_checks_for_pl_and_bs_accounts,
)

from erpnext.assets.doctype.asset.depreciation import get_credit_and_debit_accounts_for_asset_category_and_company,_make_journal_entry_for_depreciation
    
from frappe.utils.data import get_link_to_form
from erpnext.assets.doctype.asset.depreciation import *


@frappe.whitelist()
def make_depreciation_entry(
    asset_depr_schedule_name,
    date=None,
    sch_start_idx=None,
    sch_end_idx=None,
    credit_and_debit_accounts=None,
    depreciation_cost_center_and_depreciation_series=None,
    accounting_dimensions=None,
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
                accounting_dimensions
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
    accounting_dimensions
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

    credit_entry = {
        "account": credit_account,
        "credit_in_account_currency": depr_schedule.depreciation_amount,
        "reference_type": "Asset",
        "reference_name": asset.name,
        "cost_center": depreciation_cost_center,
    }

    debit_entry = {
        "account": debit_account,
        "debit_in_account_currency": depr_schedule.depreciation_amount,
        "reference_type": "Asset",
        "reference_name": asset.name,
        "cost_center": depreciation_cost_center,
    }
    
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

    update_dimension_fields(asset_depr_schedule_doc.name, credit_entry, debit_entry)

    je.append("accounts", credit_entry)
    je.append("accounts", debit_entry)

    je.flags.ignore_permissions = True
    je.flags.planned_depr_entry = True
    je.save()

    depr_schedule.db_set("journal_entry", je.name)

    if not je.meta.get_workflow():
        je.submit()
        asset.reload()
        idx = cint(asset_depr_schedule_doc.finance_book_id)
        row = asset.get("finance_books")[idx - 1]
        row.value_after_depreciation -= depr_schedule.depreciation_amount
        row.db_update()


def update_dimension_fields(asset_depr_schedule_doc_name, credit_entry, debit_entry):
    additional_fields = {}
    fieldnames = frappe.get_list("Accounting Dimension", pluck="fieldname")
    for fieldname in fieldnames:
        field_data = frappe.db.get_value("Asset Depreciation Schedule",
                                         asset_depr_schedule_doc_name, fieldname)
        additional_fields[fieldname] = field_data
        
    custom_cost_center = frappe.db.get_value("Asset Depreciation Schedule",
                                         asset_depr_schedule_doc_name, "custom_cost_center")
    additional_fields["cost_center"] = custom_cost_center
    
    credit_entry.update(additional_fields)
    debit_entry.update(additional_fields)
    

@frappe.whitelist()
def scrap_asset(asset_name, scrap_date):
    asset = frappe.get_doc("Asset", asset_name)

    if asset.docstatus != 1:
        frappe.throw(_("Asset {0} must be submitted").format(asset.name))
    elif asset.status in ("Cancelled", "Sold", "Scrapped", "Capitalized", "Decapitalized"):
        frappe.throw(_("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status))

    date = scrap_date

    notes = _("This schedule was created when Asset {0} was scrapped.").format(
        get_link_to_form(asset.doctype, asset.name)
    )

    depreciate_asset(asset, date, notes)
    asset.reload()

    depreciation_series = frappe.get_cached_value("Company", asset.company, "series_for_depreciation_entry")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.naming_series = depreciation_series
    je.posting_date = date
    je.company = asset.company
    je.remark = f"Scrap Entry for asset {asset_name}"

    for entry in get_gl_entries_on_asset_disposal(asset, date):
        entry.update({"reference_type": "Asset", "reference_name": asset_name})
        je.append("accounts", entry)

    je.flags.ignore_permissions = True
    je.submit()

    frappe.db.set_value("Asset", asset_name, "disposal_date", date)
    frappe.db.set_value("Asset", asset_name, "journal_entry_for_scrap", je.name)
    asset.set_status("Scrapped")

    add_asset_activity(asset_name, _("Asset scrapped"))

    frappe.msgprint(_("Asset scrapped via Journal Entry {0}").format(je.name))
