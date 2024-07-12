import frappe
from frappe import _
import erpnext

from erpnext.assets.doctype.asset.depreciation import (
	depreciate_asset,
	get_gl_entries_on_asset_disposal,
	get_profit_gl_entries,
	get_disposal_account_and_cost_center
	)
from erpnext.assets.doctype.asset_capitalization.asset_capitalization import AssetCapitalization
from frappe.utils import flt,getdate,get_link_to_form

# Overriding Asset Capitalization Doctype to change the Credit Account in Assets Table
# def get_gl_entries_for_consumed_asset_items(
# 		self, gl_entries, target_account, target_against, precision
# 	):
# 	if "asset_customizations" in frappe.get_installed_apps():
# 		# Consumed Assets
# 		for item in self.asset_items:
# 			asset = frappe.get_doc("Asset", item.asset)

# 			if asset.calculate_depreciation:
# 				depreciate_asset(asset, self.posting_date)
# 				asset.reload()

# 			fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(
# 				asset,
# 				item.asset_value,
# 				item.get("finance_book") or self.get("finance_book"),
# 				self.get("doctype"),
# 				self.get("name"),
# 				self.get("posting_date"),
# 			)

# 			asset.db_set("disposal_date", self.posting_date)

# 			self.set_consumed_asset_status(asset)

# 			for gle in fixed_asset_gl_entries:
# 				gle["against"] = target_account
# 				gl_entries.append(self.get_gl_dict(gle, item=item))
# 				target_against.add(gle["account"])
# 	else:
# 		AssetCapitalization.get_gl_entries_for_consumed_asset_items(self, gl_entries, target_account, target_against, precision)


class CustomAssetCapitalization(AssetCapitalization):
	# Overriding Asset Capitalization Doctype to change the Credit Account in Assets Table
	def get_gl_entries_for_consumed_asset_items(
			self, gl_entries, target_account, target_against, precision
		):
		print("OVERRIDE")
		if "asset_customizations" in frappe.get_installed_apps():
			# Consumed Assets
			for item in self.asset_items:
				asset = frappe.get_doc("Asset", item.asset)

				if asset.calculate_depreciation:
					notes = _(
						"This schedule was created when Asset {0} was consumed through Asset Capitalization {1}."
					).format(
						get_link_to_form(asset.doctype, asset.name),
						get_link_to_form(self.doctype, self.get("name")),
					)
					depreciate_asset(asset, self.posting_date, notes)
					asset.reload()

				fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(
					asset,
					item.asset_value,
					item.get("finance_book") or self.get("finance_book"),
					self.get("doctype"),
					self.get("name"),
					self.get("posting_date"),
				)

				asset.db_set("disposal_date", self.posting_date)

				self.set_consumed_asset_status(asset)

				for gle in fixed_asset_gl_entries:
					gle["against"] = target_account
					gl_entries.append(self.get_gl_dict(gle, item=item))
					target_against.add(gle["account"])
		else:
			AssetCapitalization.get_gl_entries_for_consumed_asset_items(self, gl_entries, target_account, target_against, precision)



def get_gl_entries_on_asset_disposal(
	asset, selling_amount=0, finance_book=None, voucher_type=None, voucher_no=None, date=None
):
	if not date:
		date = getdate()

	(
		fixed_asset_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_account,
		accumulated_depr_amount,
		disposal_account,
		value_after_depreciation,
	) = get_asset_details(asset, finance_book)

	gl_entries = [
		asset.get_gl_dict(
			{
				"account": fixed_asset_account,
				"credit_in_account_currency": asset.gross_purchase_amount,
				"credit": asset.gross_purchase_amount,
				"cost_center": depreciation_cost_center,
				"posting_date": date,
			},
			item=asset,
		),
	]

	if accumulated_depr_amount:
		gl_entries.append(
			asset.get_gl_dict(
				{
					"account": accumulated_depr_account,
					"debit_in_account_currency": accumulated_depr_amount,
					"debit": accumulated_depr_amount,
					"cost_center": depreciation_cost_center,
					"posting_date": date,
				},
				item=asset,
			),
		)

	profit_amount = flt(selling_amount) - flt(value_after_depreciation)
	if profit_amount:
		get_profit_gl_entries(
			asset, profit_amount, gl_entries, disposal_account, depreciation_cost_center, date
		)

	if voucher_type and voucher_no:
		for entry in gl_entries:
			entry["voucher_type"] = voucher_type
			entry["voucher_no"] = voucher_no

	return gl_entries

def get_asset_details(asset, finance_book=None):
	fixed_asset_account, accumulated_depr_account, _ = get_depreciation_accounts(
		asset.asset_category, asset.company
	)
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(asset.company)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	value_after_depreciation = asset.get_value_after_depreciation(finance_book)

	accumulated_depr_amount = flt(asset.gross_purchase_amount) - flt(value_after_depreciation)

	return (
		fixed_asset_account,
		asset,
		depreciation_cost_center,
		accumulated_depr_account,
		accumulated_depr_amount,
		disposal_account,
		value_after_depreciation,
	)

# Function to change the credit account
def get_depreciation_accounts(asset_category, company):
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None

	accounts = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset_category, "company_name": company},
		fieldname=[
			"capital_work_in_progress_account",
			"accumulated_depreciation_account",
			"depreciation_expense_account",
		],
		as_dict=1,
	)

	if accounts:
		fixed_asset_account = accounts.capital_work_in_progress_account
		accumulated_depreciation_account = accounts.accumulated_depreciation_account
		depreciation_expense_account = accounts.depreciation_expense_account

	if not accumulated_depreciation_account or not depreciation_expense_account:
		accounts = frappe.get_cached_value(
			"Company", company, ["accumulated_depreciation_account", "depreciation_expense_account"]
		)

		if not accumulated_depreciation_account:
			accumulated_depreciation_account = accounts[0]
		if not depreciation_expense_account:
			depreciation_expense_account = accounts[1]

	if not fixed_asset_account or not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(
			_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}").format(
				asset_category, company
			)
		)

	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account
