import frappe
from frappe.model.document import Document
from erpnext.accounts.utils import get_fiscal_year


class AssetComponentCapitalization(Document):
	def on_submit(self):
		self.validate_asset_is_capitalized_or_draft()
		self.create_gl_entry(cancelled=False)
		self.on_submit_update_asset_is_capitalized()


	def before_cancel(self):
		self.create_gl_entry(cancelled=True)
		self.on_cancel_update_asset_is_capitalized()


	def create_gl_entry(self,cancelled):
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
			gl_data = {
				'doctype': 'GL Entry',
				"posting_date": posting_date,
				'account': component["account"],
				# 'cost_center': "Main - AD",
				'against': component["against"],
				"voucher_type": self.doctype,
				"voucher_subtype": self.doctype,
				"voucher_no": self.name,
				"fiscal_year": current_fiscal_year,
				"company": self.company,
				'debit': debit,
				'credit': credit,
				'debit_in_account_currency': debit,
				'credit_in_account_currency': credit,
				"debit_in_transaction_currency": debit,
				"credit_in_transaction_currency": credit,
				# "state": "27-Maharashtra",
				# "remark": f"Asset Movement Entry against {asset_movemet_name}"
			}
			if cancelled:
				gl_data.update({'debit': credit,
								'credit': debit,
								'debit_in_account_currency': credit,
								'credit_in_account_currency': debit,
								"debit_in_transaction_currency": credit,
								"credit_in_transaction_currency": debit,})
			doc = frappe.get_doc(gl_data)
			doc.save()
		return doc.name


	def validate_asset_is_capitalized_or_draft(self):
		asset_not_submitted_list = []
		for component in self.component_asset:
			if not frappe.db.get_value("Asset", component.asset, "docstatus"):
				asset_not_submitted_list.append(component.asset)
		
		if asset_not_submitted_list:
			asset_links = [f'<a href="/app/asset/{asset}" target="_blank">{asset}</a>' for asset in asset_not_submitted_list]
			error_message = "The following assets are not submitted: " + ", ".join(asset_links)
			frappe.throw(error_message)
		
		return asset_not_submitted_list

	
	def on_submit_update_asset_is_capitalized(self):
		if self.component_asset:
			for asset in self.component_asset:
				frappe.db.set_value("Asset", asset.asset, "is_capitalized", 1)


	def on_cancel_update_asset_is_capitalized(self):
		if self.component_asset:
			for asset in self.component_asset:
				frappe.db.set_value("Asset", asset.asset, "is_capitalized", 0)
    
    
@frappe.whitelist()
def fetch_asset(parent_asset):
    asset_list = frappe.db.get_all("Asset",
                                   filters={"custom_parent_asset":parent_asset,
                                            "is_capitalized": 0},
                                   fields=["name", "asset_name", "gross_purchase_amount"])
    return asset_list


@frappe.whitelist()
def parent_asset_filters(doctype, txt, searchfield, start, page_len, filters):
    asset_component_list = frappe.db.sql(
			"""
				SELECT a.custom_parent_asset
				FROM `tabAsset` as a
				WHERE a.is_capitalized = 0
					AND a.custom_parent_asset IS NOT NULL
					AND a.name NOT IN (SELECT ca.asset
									FROM `tabComponent Asset` as ca
									JOIN `tabAsset Component Capitalization` as acc ON acc.name = ca.parent
									WHERE acc.docstatus != 2)
						
				GROUP BY a.custom_parent_asset
			"""
        )
    return asset_component_list
    