# Copyright (c) 2024, manoj and Contributors
# See license.txt

import json
import frappe
from frappe.tests.utils import FrappeTestCase
import frappe.utils


class TestAssetComponentCapitalization(FrappeTestCase):
	def test_gl_entry(self):
		asset_component = create_asset_component_capitalization()
		expected_gle = [{"account": "_Test Fixed Asset - _TC", "debit": 100000.0, "credit": 0.0},
        {"account": "CWIP Account - _TC", "debit": 0.0, "credit": 100000.0}]

		self.assertGLEntries(asset_component, expected_gle)


	def assertGLEntries(self, asset_component, expected_gl_entries):
		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": asset_component.name, "is_cancelled": 0},
			fields=["account", "debit", "credit"],
		)
		out_str = json.dumps(sorted(gl_entries, key=json.dumps))
		expected_out_str = json.dumps(sorted(expected_gl_entries, key=json.dumps))
		self.assertEqual(out_str, expected_out_str)


def create_asset_component_capitalization():
	asset = create_asset()
	asset_component = frappe.get_doc({
			"doctype": "Asset Component Capitalization",
			"company": asset.company,
			"parent_asset": asset.custom_parent_asset,
			"posting_date": frappe.utils.today(),
		})
	if asset.custom_parent_asset:
		asset_component.append(
      		"component_asset",
			{
				"asset": asset.name,
				"asset_name": asset.asset_name,
				"gross_amount": asset.gross_purchase_amount
			})
	asset_component.insert(ignore_if_duplicate=True)
	asset_component.submit()
	
	frappe.db.commit()
	return asset_component
 

def create_asset(**args):
	args = frappe._dict(args)

	create_asset_data()
	parent_asset_name = create_parent_asset()

	asset = frappe.get_doc(
		{
			"doctype": "Asset",
			"asset_name": args.asset_name or "Macbook Pro 1",
			"asset_category": args.asset_category or "Computers",
			"item_code": args.item_code or "Macbook Pro",
			"company": args.company or "_Test Company",
			"purchase_date": args.purchase_date or "2015-01-01",
			"calculate_depreciation": args.calculate_depreciation or 0,
			"opening_accumulated_depreciation": args.opening_accumulated_depreciation or 0,
			"opening_number_of_booked_depreciations": args.opening_number_of_booked_depreciations or 0,
			"gross_purchase_amount": args.gross_purchase_amount or 100000,
			"purchase_amount": args.purchase_amount or 100000,
			"maintenance_required": args.maintenance_required or 0,
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"available_for_use_date": args.available_for_use_date or "2020-06-06",
			"location": args.location or "Test Location",
			"asset_owner": args.asset_owner or "Company",
			"is_existing_asset": args.is_existing_asset or 1,
			"is_composite_asset": args.is_composite_asset or 0,
			"asset_quantity": args.get("asset_quantity") or 1,
			"depr_entry_posting_status": args.depr_entry_posting_status or "",
			"custom_component_asset": 1,
			"custom_parent_asset": parent_asset_name,
		}
	)
	if asset.calculate_depreciation:
		asset.append(
			"finance_books",
			{
				"finance_book": args.finance_book,
				"depreciation_method": args.depreciation_method or "Straight Line",
				"frequency_of_depreciation": args.frequency_of_depreciation or 12,
				"total_number_of_depreciations": args.total_number_of_depreciations or 5,
				"expected_value_after_useful_life": args.expected_value_after_useful_life or 0,
				"depreciation_start_date": args.depreciation_start_date,
				"daily_prorata_based": args.daily_prorata_based or 0,
				"shift_based": args.shift_based or 0,
				"rate_of_depreciation": args.rate_of_depreciation or 0,
			},
		)

	asset.insert(ignore_if_duplicate=True)
	asset.submit()
	return asset


def create_asset_data():
	if not frappe.db.exists("Company", "_Test Company"):
		set_depreciation_settings_in_company(company=None)
  
	if not frappe.db.exists("Asset Category", "Computers"):
		create_asset_category()

	if not frappe.db.exists("Item", "Macbook Pro"):
		create_fixed_asset_item()

	if not frappe.db.exists("Location", "Test Location"):
		frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert()

	if not frappe.db.exists("Finance Book", "Test Finance Book 1"):
		frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "Test Finance Book 1"}).insert()

	if not frappe.db.exists("Finance Book", "Test Finance Book 2"):
		frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "Test Finance Book 2"}).insert()

	if not frappe.db.exists("Finance Book", "Test Finance Book 3"):
		frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "Test Finance Book 3"}).insert()


def set_depreciation_settings_in_company(company=None):
	if not company:
		company = "_Test Company"
	company = frappe.get_doc("Company", company)
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - " + company.abbr
	company.depreciation_expense_account = "_Test Depreciations - " + company.abbr
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - " + company.abbr
	company.depreciation_cost_center = "Main - " + company.abbr
	company.save()

	# Enable booking asset depreciation entry automatically
	frappe.db.set_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically", 1)


def create_asset_category():
	asset_category = frappe.new_doc("Asset Category")
	asset_category.asset_category_name = "Computers"
	asset_category.total_number_of_depreciations = 3
	asset_category.frequency_of_depreciation = 3
	asset_category.enable_cwip_accounting = 1
	asset_category.append(
		"accounts",
		{
			"company_name": "_Test Company",
			"fixed_asset_account": "_Test Fixed Asset - _TC",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC",
			"capital_work_in_progress_account": "CWIP Account - _TC",
		},
	)
	asset_category.append(
		"accounts",
		{
			"company_name": "_Test Company with perpetual inventory",
			"fixed_asset_account": "_Test Fixed Asset - TCP1",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - TCP1",
			"depreciation_expense_account": "_Test Depreciations - TCP1",
		},
	)

	asset_category.insert()
 
 
def create_fixed_asset_item(item_code=None, auto_create_assets=1, is_grouped_asset=0):
	meta = frappe.get_meta("Asset")
	naming_series = meta.get_field("naming_series").options.splitlines()[0] or "ACC-ASS-.YYYY.-"
	try:
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code or "Macbook Pro",
				"item_name": "Macbook Pro",
				"description": "Macbook Pro Retina Display",
				"asset_category": "Computers",
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": auto_create_assets,
				"is_grouped_asset": is_grouped_asset,
				"asset_naming_series": naming_series,
			}
		)
		item.insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass
	return item


def create_parent_asset(): 
	parent_asset = frappe.get_doc(
		{
			"doctype": "Parent Asset",
			"company": "_Test Company",
			"item_code": "Macbook Pro",
			"asset_category": "Computers",
		}
	)

	parent_asset.insert(ignore_if_duplicate=True)
	parent_asset.submit()

	return parent_asset.name
