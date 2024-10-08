
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts

def set_difference_amount_custom(self):
    self.difference_amount = flt(self.new_asset_value - self.current_asset_value)


def make_depreciation_entry_custom(self):
    asset = frappe.get_doc("Asset", self.asset)
    (
        fixed_asset_account,
        accumulated_depreciation_account,
        _,
    ) = get_depreciation_accounts(asset.asset_category, asset.company)

    depreciation_cost_center, depreciation_series = frappe.get_cached_value(
        "Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
    )

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Depreciation Entry"
    je.naming_series = depreciation_series
    je.posting_date = self.date
    je.company = self.company
    je.remark = "Depreciation Entry against {0} worth {1}".format(self.asset, self.difference_amount)
    je.finance_book = self.finance_book

    if self.difference_amount<0:
        difference_amount  = -(self.difference_amount)
        credit_entry = {
            "account": fixed_asset_account,
            "credit_in_account_currency": difference_amount,
            "cost_center": depreciation_cost_center or self.cost_center,
            "reference_type": "Asset",
            "reference_name": asset.name,
        }

        debit_entry = {
            "account": self.custom_difference_account,
            "debit_in_account_currency": difference_amount,
            "cost_center": depreciation_cost_center or self.cost_center,
            "reference_type": "Asset",
            "reference_name": asset.name,
        }

    elif self.difference_amount>0:
        difference_amount  = self.difference_amount
        credit_entry = {
            "account": self.custom_difference_account,
            "credit_in_account_currency": difference_amount,
            "cost_center": depreciation_cost_center or self.cost_center,
            "reference_type": "Asset",
            "reference_name": asset.name,
        }

        debit_entry = {
            "account": fixed_asset_account,
            "debit_in_account_currency": difference_amount,
            "cost_center": depreciation_cost_center or self.cost_center,
            "reference_type": "Asset",
            "reference_name": asset.name,
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

    je.append("accounts", credit_entry)
    je.append("accounts", debit_entry)

    je.flags.ignore_permissions = True
    je.submit()

    self.db_set("journal_entry", je.name)
