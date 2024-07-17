# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Max, Min

from frappe.utils.data import get_link_to_form
from erpnext.assets.doctype.asset.depreciation import *

from erpnext.assets.doctype.asset.depreciation import scrap_asset

@frappe.whitelist()
def scrap_asset_modified(asset_name,scrap_date):
	if "asset_customizations" in frappe.get_installed_apps():
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
	else:
		scrap_asset(asset_name)