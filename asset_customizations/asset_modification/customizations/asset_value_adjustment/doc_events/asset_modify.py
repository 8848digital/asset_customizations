import frappe
from erpnext.assets.doctype.asset.asset import Asset
def on_submit(self):
    if "asset_customizations" in frappe.get_installed_apps():
        self.validate_in_use_date()
        self.set_status()
        self.make_asset_movement()
        self.reload()
    else:
        on_submit(self)
