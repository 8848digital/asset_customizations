import frappe
from frappe import _
from frappe.utils import (
	get_datetime,
	getdate,
)
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	convert_draft_asset_depr_schedules_into_active,
)
 
from erpnext.assets.doctype.asset.asset import Asset

class CustomAsset(Asset):
    def on_submit(self):
        self.validate_in_use_date()
        self.make_asset_movement()
        if self.calculate_depreciation and not self.split_from:
            convert_draft_asset_depr_schedules_into_active(self)
        self.set_status()
        add_asset_activity(self.name, _("Asset submitted"))


    def make_asset_movement(self):
        reference_doctype = "Purchase Receipt" if self.purchase_receipt else "Purchase Invoice"
        reference_docname = self.purchase_receipt or self.purchase_invoice
        transaction_date = getdate(self.purchase_date)
        if reference_docname:
            posting_date, posting_time = frappe.db.get_value(
                reference_doctype, reference_docname, ["posting_date", "posting_time"]
            )
            transaction_date = get_datetime(f"{posting_date} {posting_time}")

        fields = frappe.get_list("Accounting Dimension", pluck="fieldname")
        transformed_fields = [f"target_{field}" for field in fields]

        assets = [{
            "asset": self.name,
            "asset_name": self.asset_name,
            "target_location": self.location,
            "to_employee": self.custodian,
            "custom_target_cost_center": self.cost_center
        }]

        for field in transformed_fields:
            original_fieldname = field.replace("target_", "")
            assets[0][field] = getattr(self, original_fieldname, None)

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


@frappe.whitelist()
def make_asset_movement(assets, purpose=None):
    import json

    if isinstance(assets, str):
        assets = json.loads(assets)

    if len(assets) == 0:
        frappe.throw(_("At least one asset has to be selected."))

    asset_movement = frappe.new_doc("Asset Movement")
    asset_movement.quantity = len(assets)
    for asset in assets:
        asset = frappe.get_doc("Asset", asset.get("name"))
        asset_movement.company = asset.get("company")
        
        fields = frappe.get_list("Accounting Dimension", pluck="fieldname")
        transformed_fields = [f"from_{field}" for field in fields]
        
        asset_dict = {
            "asset": asset.get("name"),
            "source_location": asset.get("location"),
            "from_employee": asset.get("custodian"),
            "custom_from_cost_center": asset.get("cost_center")
        }
        
        for field in transformed_fields:
            original_fieldname = field.replace("from_", "")
            asset_dict[field] = asset.get(original_fieldname, None)
        
        asset_movement.append("assets", asset_dict)
        
    if asset_movement.get("assets"):
        return asset_movement.as_dict()