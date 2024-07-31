import frappe
from frappe.model.document import Document
from erpnext.accounts.utils import get_fiscal_year


class AssetComponentCapitalization(Document):
	def on_submit(self):
		self.create_gl_entry()


	def create_gl_entry(self):
		posting_date = self.posting_date
		current_fiscal_year = get_fiscal_year(posting_date, as_dict=True)
		current_fiscal_year = current_fiscal_year.get("name")

		components = []
		for row in self.component_asset:
			account_credit_entries ={}
			asset_category = frappe.db.get_value("Asset",
												row.asset,
												["asset_category","gross_purchase_amount"],
												as_dict=True)
			cwip_account = frappe.db.get_value("Asset Category Account",
							{"parent":asset_category["asset_category"], "company_name":self.company},
							"capital_work_in_progress_account")

			account_credit_entries["account"] = cwip_account
			account_credit_entries["credit_in_account_currency"] = asset_category["gross_purchase_amount"]
			if components:
				for component in components:
					if account_credit_entries["account"] == component["account"]:
						component["credit_in_account_currency"] += account_credit_entries["credit_in_account_currency"]
			else:
				components.append(account_credit_entries)
				

		asset_category_name = frappe.db.get_value("Parent Asset", self.parent_asset, "asset_category")
		fixed_account = frappe.db.get_value("Asset Category Account",
						{"parent":asset_category_name, "company_name":self.company},
						"fixed_asset_account")

		account_debit_entries ={}
		account_debit_entries["account"] = fixed_account
		total_debit_in_account_currency = 0
		all_accounts = []

		for component in components:
			component["against"] = fixed_account
			total_debit_in_account_currency += component["credit_in_account_currency"]
			all_accounts.append(component["account"])
		account_debit_entries["debit_in_account_currency"] = total_debit_in_account_currency
		account_debit_entries["against"] = ', '.join(all_accounts)
		components.append(account_debit_entries)

		for component in components:
			debit = component.get("debit_in_account_currency") if component.get("debit_in_account_currency") else 0
			credit = component.get("credit_in_account_currency") if component.get("credit_in_account_currency") else 0
			doc = frappe.get_doc({
				'doctype': 'GL Entry',
				"posting_date": posting_date,
				'account': component["account"],
				# 'cost_center': "Main - AD",
				'debit': debit,
				'credit': credit,
				'debit_in_account_currency': debit,
				'credit_in_account_currency': credit,
				'against': component["against"],
				"voucher_type": self.doctype,
				"voucher_subtype": self.doctype,
				"voucher_no": self.name,
				"fiscal_year": current_fiscal_year,
				"company": self.company,
				"debit_in_transaction_currency": debit,
				"credit_in_transaction_currency": credit,
				# "state": "27-Maharashtra",
				# "remark": f"Asset Movement Entry against {asset_movemet_name}"
			})
			doc.save()
		return doc.name


@frappe.whitelist()
def fetch_asset(parent_asset):
    asset_list = frappe.db.get_all("Asset",
                                   filters={"custom_parent_asset":parent_asset},
                                   fields=["name", "asset_name", "gross_purchase_amount"])
    return asset_list


@frappe.whitelist()
def parent_asset_filters(doctype, txt, searchfield, start, page_len, filters):
    asset_component_list = frappe.db.sql("""SELECT pa.name
										FROM `tabParent Asset` as pa
										Left JOIN `tabAsset Component Capitalization` as acc
											ON pa.name = acc.parent_asset
										WHERE pa.name NOT IN (SELECT acc.parent_asset FROM `tabAsset Component Capitalization` as acc)""")
    return asset_component_list
    