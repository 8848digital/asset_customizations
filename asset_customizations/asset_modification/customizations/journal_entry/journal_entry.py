import frappe

def on_cancel(self, method=None):
    unlink_je_in_asset_movement_on_cancel(self)


def unlink_je_in_asset_movement_on_cancel(self):
    asset_movement_name = frappe.db.get_value("Asset Movement", {"custom_journal_entry": self.name}, "name")
    frappe.db.set_value("Asset Movement",asset_movement_name,"custom_journal_entry", None)
    