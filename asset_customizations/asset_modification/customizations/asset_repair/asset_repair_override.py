import frappe
from frappe import _
from erpnext.assets.doctype.asset_repair.asset_repair import AssetRepair
from frappe.utils import get_link_to_form
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity


class CustomAssetRepair(AssetRepair):
    def before_submit(self):
        self.check_repair_status()

        self.asset_doc.flags.increase_in_asset_value_due_to_repair = False

        if self.get("stock_consumption") or self.get("capitalize_repair_cost"):
            self.asset_doc.flags.increase_in_asset_value_due_to_repair = True

            self.increase_asset_value()

            if self.capitalize_repair_cost:
                self.asset_doc.total_asset_cost += self.repair_cost
                self.asset_doc.additional_asset_cost += self.repair_cost

            if self.get("stock_consumption"):
                self.check_for_stock_items_and_warehouse()
                self.decrease_stock_quantity()
            if self.get("capitalize_repair_cost"):
                if self.asset_doc.calculate_depreciation and self.increase_in_asset_life:
                    self.modify_depreciation_schedule()

                notes = _(
                    "This schedule was created when Asset {0} was repaired through Asset Repair {1}."
                ).format(
                    get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
                    get_link_to_form(self.doctype, self.name),
                )
                self.asset_doc.flags.ignore_validate_update_after_submit = True
                self.asset_doc.save()

                add_asset_activity(
                    self.asset,
                    _("Asset updated after completion of Asset Repair {0}").format(
                        get_link_to_form("Asset Repair", self.name)
                    ),
                )

    def before_cancel(self):
        self.asset_doc = frappe.get_doc("Asset", self.asset)

        self.asset_doc.flags.increase_in_asset_value_due_to_repair = False

        if self.get("stock_consumption") or self.get("capitalize_repair_cost"):
            self.asset_doc.flags.increase_in_asset_value_due_to_repair = True

            self.decrease_asset_value()

            if self.capitalize_repair_cost:
                self.asset_doc.total_asset_cost -= self.repair_cost
                self.asset_doc.additional_asset_cost -= self.repair_cost

            if self.get("capitalize_repair_cost"):
                self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")
                if self.asset_doc.calculate_depreciation and self.increase_in_asset_life:
                    self.revert_depreciation_schedule_on_cancellation()

                notes = _(
                    "This schedule was created when Asset {0}'s Asset Repair {1} was cancelled."
                ).format(
                    get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
                    get_link_to_form(self.doctype, self.name),
                )
                self.asset_doc.flags.ignore_validate_update_after_submit = True
                self.asset_doc.save()

                add_asset_activity(
                    self.asset,
                    _("Asset updated after cancellation of Asset Repair {0}").format(
                        get_link_to_form("Asset Repair", self.name)
                    ),
                )