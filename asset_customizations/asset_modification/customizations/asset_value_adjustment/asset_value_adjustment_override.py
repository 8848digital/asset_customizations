
import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts
from erpnext.assets.doctype.asset_value_adjustment.asset_value_adjustment import AssetValueAdjustment


class CustomAssetValueAdjustment(AssetValueAdjustment):
    def set_difference_amount(self):
        if "asset_customizations" in frappe.get_installed_apps():
            self.difference_amount = flt(self.new_asset_value - self.current_asset_value)
            frappe.db.set_value("Asset",self.asset,"value_after_depreciation",self.new_asset_value)
        else:
            AssetValueAdjustment.set_difference_amount(self)

    def make_depreciation_entry(self):
        if "asset_customizations" in frappe.get_installed_apps():
            asset = frappe.get_doc("Asset", self.asset)
            (
                fixed_asset_account,
                accumulated_depreciation_account,
                depreciation_expense_account,
            ) = get_depreciation_accounts(asset.asset_category, asset.company)

            depreciation_cost_center, depreciation_series = frappe.get_cached_value(
                "Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
            )

            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Journal Entry"
            je.naming_series = depreciation_series
            je.posting_date = self.date
            je.company = self.company
            je.remark = f"Revaluation Entry against {self.asset} worth {self.difference_amount}"
            je.finance_book = self.finance_book

            entry_template = {
                "cost_center": self.cost_center or depreciation_cost_center,
                "reference_type": "Asset",
                "reference_name": asset.name,
            }

            if self.difference_amount < 0:
                credit_entry = {
                    "account": fixed_asset_account,
                    "credit_in_account_currency": -self.difference_amount,
                    **entry_template,
                }
                debit_entry = {
                    "account": self.difference_account,
                    "debit_in_account_currency": -self.difference_amount,
                    **entry_template,
                }
            elif self.difference_amount > 0:
                credit_entry = {
                    "account": self.difference_account,
                    "credit_in_account_currency": self.difference_amount,
                    **entry_template,
                }
                debit_entry = {
                    "account": fixed_asset_account,
                    "debit_in_account_currency": self.difference_amount,
                    **entry_template,
                }

            accounting_dimensions = get_checks_for_pl_and_bs_accounts()

            for dimension in accounting_dimensions:
                if dimension.get("mandatory_for_bs"):
                    credit_entry.update(
                        {
                            dimension["fieldname"]: self.get(dimension["fieldname"])
                            or dimension.get("default_dimension")
                        }
                    )

                if dimension.get("mandatory_for_pl"):
                    debit_entry.update(
                        {
                            dimension["fieldname"]: self.get(dimension["fieldname"])
                            or dimension.get("default_dimension")
                        }
                    )

            additional_fields = {}
            fieldnames = frappe.get_list("Accounting Dimension", pluck="fieldname")
            for fieldname in fieldnames:
                field_data = frappe.db.get_value("Asset Value Adjustment", self.name, fieldname)
                additional_fields[fieldname] = field_data

            credit_entry.update(additional_fields)
            debit_entry.update(additional_fields)

            je.append("accounts", credit_entry)
            je.append("accounts", debit_entry)

            je.flags.ignore_permissions = True
            je.submit()

            self.db_set("journal_entry", je.name)
        else:
            AssetValueAdjustment.make_depreciation_entry(self)
            
            
@frappe.whitelist()
def value_of_accounting_dimension(asset_name):
    fields = frappe.get_list("Accounting Dimension", pluck="fieldname")
    acc_dimension_fiels_value = {}
    for field in fields:
        value = frappe.db.get_value("Asset", asset_name, field)
        acc_dimension_fiels_value[field] = value
    acc_dimension_fiels_value["cost_center"] = frappe.db.get_value("Asset", asset_name, "cost_center")
    return acc_dimension_fiels_value