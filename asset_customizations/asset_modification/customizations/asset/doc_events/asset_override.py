import json
import math

import frappe
from frappe import _
from frappe.utils import (
	cint,
	flt,
	get_datetime,
	get_last_day,
	get_link_to_form,
	getdate,
	nowdate,
	today,
)

import erpnext
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.assets.doctype.asset.depreciation import (
	get_comma_separated_links,
	get_depreciation_accounts,
	get_disposal_account_and_cost_center,
)
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	cancel_asset_depr_schedules,
	convert_draft_asset_depr_schedules_into_active,
	get_asset_depr_schedule_doc,
	get_depr_schedule,
	make_draft_asset_depr_schedules,
	make_draft_asset_depr_schedules_if_not_present,
	update_draft_asset_depr_schedules,
)
from erpnext.controllers.accounts_controller import AccountsController
 
from erpnext.assets.doctype.asset.asset import Asset

class CustomAsset(Asset):
    def make_asset_movement(self):
        reference_doctype = "Purchase Receipt" if self.purchase_receipt else "Purchase Invoice"
        reference_docname = self.purchase_receipt or self.purchase_invoice
        transaction_date = getdate(self.purchase_date)
        if reference_docname:
            posting_date, posting_time = frappe.db.get_value(
                reference_doctype, reference_docname, ["posting_date", "posting_time"]
            )
            transaction_date = get_datetime(f"{posting_date} {posting_time}")

        fields = frappe.get_list("Accounting Dimension", pluck="name")
        transformed_fields = [f"from_{field.lower().replace(' ', '_')}" for field in fields]

        # Create dynamic dictionary for assets
        assets_dict = {
            "asset": self.name,
            "asset_name": self.asset_name,
            "target_location": self.location,
            "to_employee": self.custodian,
            "custom_cost_center": self.cost_center
        }

        for field in transformed_fields:
            original_fieldname = field.replace("from_", "")
            assets_dict[field] = getattr(self, original_fieldname, None)

        assets = [assets_dict]

        asset_movement = frappe.get_doc(
            {
                "doctype": "Asset Movement",
                "assets": assets,
                "purpose": "Receipt",
                "company": self.company,
                "transaction_date": transaction_date,
                "reference_doctype": reference_doctype,
                "reference_name": reference_docname,
                "custom_cost_center":self.cost_center
            }
        ).insert()
        asset_movement.submit()