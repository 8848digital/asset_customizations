from erpnext.assets.report.fixed_asset_register.fixed_asset_register import (
    get_asset_depreciation_amount_map,
    get_assets_linked_to_fb, get_conditions,
    get_group_by_data,
    get_purchase_invoice_supplier_map,
    get_purchase_receipt_supplier_map
)
import frappe
from frappe import _

def get_data(filters):
	data = []

	conditions = get_conditions(filters)
	pr_supplier_map = get_purchase_receipt_supplier_map()
	pi_supplier_map = get_purchase_invoice_supplier_map()

	assets_linked_to_fb = get_assets_linked_to_fb(filters)

	company_fb = frappe.get_cached_value("Company", filters.company, "default_finance_book")

	if filters.include_default_book_assets and company_fb:
		finance_book = company_fb
	elif filters.finance_book:
		finance_book = filters.finance_book
	else:
		finance_book = None

	depreciation_amount_map = get_asset_depreciation_amount_map(filters, finance_book)

	group_by = frappe.scrub(filters.get("group_by"))

	if group_by in ("asset_category", "location"):
		data = get_group_by_data(group_by, conditions, assets_linked_to_fb, depreciation_amount_map)
		return data

	fields = [
		"custom_parent_asset",
		"name as asset_id",
		"asset_name",
		"status",
		"department",
		"company",
		"cost_center",
		"calculate_depreciation",
		"purchase_receipt",
		"asset_category",
		"purchase_date",
		"gross_purchase_amount",
		"location",
		"available_for_use_date",
		"purchase_invoice",
		"opening_accumulated_depreciation",
	]
	assets_record = frappe.db.get_all("Asset", filters=conditions, fields=fields)

	for asset in assets_record:
		if assets_linked_to_fb and asset.calculate_depreciation and asset.asset_id not in assets_linked_to_fb:
			continue

		depreciation_amount = depreciation_amount_map.get(asset.asset_id) or 0.0
		asset_value = (
			asset.gross_purchase_amount - asset.opening_accumulated_depreciation - depreciation_amount
		)

		row = {
			"custom_parent_asset": asset.custom_parent_asset,
			"asset_id": asset.asset_id,
			"asset_name": asset.asset_name,
			"status": asset.status,
			"department": asset.department,
			"cost_center": asset.cost_center,
			"vendor_name": pr_supplier_map.get(asset.purchase_receipt)
			or pi_supplier_map.get(asset.purchase_invoice),
			"gross_purchase_amount": asset.gross_purchase_amount,
			"opening_accumulated_depreciation": asset.opening_accumulated_depreciation,
			"depreciated_amount": depreciation_amount,
			"available_for_use_date": asset.available_for_use_date,
			"location": asset.location,
			"asset_category": asset.asset_category,
			"purchase_date": asset.purchase_date,
			"asset_value": asset_value,
			"company": asset.company,
		}
		data.append(row)
	
	new_data = []
	child_row= []
	rest_row = []
	unique_custom_parent_assets = {}
	child_by_parent = {}

	for row in data:
		if row["custom_parent_asset"]:
			child_row.append(row)
			custom_parent = row["custom_parent_asset"]
			if custom_parent not in unique_custom_parent_assets:
				unique_custom_parent_assets[custom_parent] = {
					"custom_parent_asset": custom_parent,
					"gross_purchase_amount": 0,
					"asset_value": 0,
					"opening_accumulated_depreciation": 0,
					"depreciated_amount": 0,
				}
			unique_custom_parent_assets[custom_parent]["gross_purchase_amount"] += row["gross_purchase_amount"]
			unique_custom_parent_assets[custom_parent]["asset_value"] += row["asset_value"]
			unique_custom_parent_assets[custom_parent]["opening_accumulated_depreciation"] += row["opening_accumulated_depreciation"]
			unique_custom_parent_assets[custom_parent]["depreciated_amount"] += row["depreciated_amount"]
			if custom_parent not in child_by_parent:
				child_by_parent[custom_parent] = []
			child_by_parent[custom_parent].append(row)
		else:
			rest_row.append(row)

	for parent_asset, parent_data in unique_custom_parent_assets.items():
		new_data.append(parent_data)
		for child_row in child_by_parent[parent_asset]:
			child_row["indent"] = 1
			new_data.append(child_row)
	for rest in rest_row:
		rest["indent"] = 0
		new_data.append(rest)

	return new_data


def get_columns(filters):
	if filters.get("group_by") in ["Asset Category", "Location"]:
		return [
			{
				"label": _("{}").format(filters.get("group_by")),
				"fieldtype": "Link",
				"fieldname": frappe.scrub(filters.get("group_by")),
				"options": filters.get("group_by"),
				"width": 216,
			},
			{
				"label": _("Gross Purchase Amount"),
				"fieldname": "gross_purchase_amount",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"width": 250,
			},
			{
				"label": _("Opening Accumulated Depreciation"),
				"fieldname": "opening_accumulated_depreciation",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"width": 250,
			},
			{
				"label": _("Depreciated Amount"),
				"fieldname": "depreciated_amount",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"width": 250,
			},
			{
				"label": _("Asset Value"),
				"fieldname": "asset_value",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"width": 250,
			},
			{
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
				"width": 120,
			},
		]

	return [
		{
			"label": _("Parent Asset"),
			"fieldtype": "Link",
			"fieldname": "custom_parent_asset",
			"options": "Parent Asset",
			"width": 110,
		},
		{
			"label": _("Asset ID"),
			"fieldtype": "Link",
			"fieldname": "asset_id",
			"options": "Asset",
			"width": 60,
		},
		{"label": _("Asset Name"), "fieldtype": "Data", "fieldname": "asset_name", "width": 140},
		{
			"label": _("Asset Category"),
			"fieldtype": "Link",
			"fieldname": "asset_category",
			"options": "Asset Category",
			"width": 100,
		},
		{"label": _("Status"), "fieldtype": "Data", "fieldname": "status", "width": 80},
		{"label": _("Purchase Date"), "fieldtype": "Date", "fieldname": "purchase_date", "width": 90},
		{
			"label": _("Available For Use Date"),
			"fieldtype": "Date",
			"fieldname": "available_for_use_date",
			"width": 90,
		},
		{
			"label": _("Gross Purchase Amount"),
			"fieldname": "gross_purchase_amount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 100,
		},
		{
			"label": _("Asset Value"),
			"fieldname": "asset_value",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 100,
		},
		{
			"label": _("Opening Accumulated Depreciation"),
			"fieldname": "opening_accumulated_depreciation",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 90,
		},
		{
			"label": _("Depreciated Amount"),
			"fieldname": "depreciated_amount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 100,
		},
		{
			"label": _("Cost Center"),
			"fieldtype": "Link",
			"fieldname": "cost_center",
			"options": "Cost Center",
			"width": 100,
		},
		{
			"label": _("Department"),
			"fieldtype": "Link",
			"fieldname": "department",
			"options": "Department",
			"width": 100,
		},
		{"label": _("Vendor Name"), "fieldtype": "Data", "fieldname": "vendor_name", "width": 100},
		{
			"label": _("Location"),
			"fieldtype": "Link",
			"fieldname": "location",
			"options": "Location",
			"width": 100,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
	]
