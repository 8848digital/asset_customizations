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
    get_first_day,
    get_last_day,
    getdate,
    nowdate,
    today,
)
from frappe.utils.data import get_link_to_form
from frappe.utils.user import get_users_with_role
from erpnext.assets.doctype.asset.depreciation import *
import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_checks_for_pl_and_bs_accounts,
)
from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry


@frappe.whitelist()
def scrap_asset_modified(asset_name,scrap_date):
    asset = frappe.get_doc("Asset", asset_name)
    if asset.docstatus != 1:
        frappe.throw(_("Asset {0} must be submitted").format(asset.name))
    elif asset.status in ("Cancelled", "Sold", "Scrapped", "Capitalized", "Decapitalized"):
        frappe.throw(
            _("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status)
        )
    date = scrap_date

    depreciate_asset(asset, date)
    asset.reload()

    depreciation_series = frappe.get_cached_value(
        "Company", asset.company, "series_for_depreciation_entry"
    )

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.naming_series = depreciation_series
    je.posting_date = date
    je.company = asset.company
    je.remark = "Scrap Entry for asset {0}".format(asset_name)

    for entry in get_gl_entries_on_asset_disposal(asset, date):
        entry.update({"reference_type": "Asset", "reference_name": asset_name})
        je.append("accounts", entry)

    je.flags.ignore_permissions = True
    je.submit()

    frappe.db.set_value("Asset", asset_name, "disposal_date", date)
    frappe.db.set_value("Asset", asset_name, "journal_entry_for_scrap", je.name)
    asset.set_status("Scrapped")

    frappe.msgprint(_("Asset scrapped via Journal Entry {0}").format(je.name))
