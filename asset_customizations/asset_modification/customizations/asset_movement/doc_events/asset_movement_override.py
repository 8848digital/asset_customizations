import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form

from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_movement.asset_movement import AssetMovement

class CustomAssetMovement(AssetMovement):
	def set_latest_location_and_custodian_in_asset(self):
		fields = frappe.get_list("Accounting Dimension", pluck="name")
		transformed_fields = [f"target_{field.lower().replace(' ', '_')}" for field in fields]
		
		# Create dynamic field mapping
		field_mapping = {tf: tf.split('_', 1)[1] for tf in transformed_fields}
		
		current_values = {field: "" for field in transformed_fields}  # Initialize all fields with empty values
		cond = "1=1"

		for d in self.assets:
			args = {"asset": d.asset, "company": self.company}

			# Fetch latest movement entry for the asset
			latest_movement_entry = frappe.db.sql(
				f"""
				SELECT asm_item.target_location, asm_item.to_employee, asm_item.custom_target_cost_center, {', '.join(transformed_fields)}
				FROM `tabAsset Movement Item` asm_item, `tabAsset Movement` asm
				WHERE
					asm_item.parent = asm.name and
					asm_item.asset = %(asset)s and
					asm.company = %(company)s and
					asm.docstatus = 1 and {cond}
				ORDER BY
					asm.transaction_date DESC LIMIT 1
				""",
				args,
			)

			if latest_movement_entry:
				current_location = latest_movement_entry[0][0]
				current_employee = latest_movement_entry[0][1]
				custom_target_cost_center = latest_movement_entry[0][2]
				
				# Update current_values dictionary with transformed field values
				for idx, field in enumerate(transformed_fields):
					original_field = field_mapping[field]
					current_values[original_field] = latest_movement_entry[0][3 + idx]

			else:
				# If no latest movement entry found, set to empty string or appropriate default values
				current_location = ""
				current_employee = ""
				custom_target_cost_center = ""
				for original_field in field_mapping.values():
					current_values[original_field] = ""

			# Set values in Asset document
			frappe.db.set_value("Asset", d.asset, "location", current_location, update_modified=False)
			frappe.db.set_value("Asset", d.asset, "custodian", current_employee, update_modified=False)
			frappe.db.set_value("Asset", d.asset, "cost_center", custom_target_cost_center, update_modified=False)

			# Set values for original fields based on mappings
			for original_field in field_mapping.values():
				frappe.db.set_value("Asset", d.asset, original_field, current_values[original_field], update_modified=False)

			# Add activity based on the updated values
			if current_location and current_employee:
				add_asset_activity(
					d.asset,
					_("Asset received at Location {0} and issued to Employee {1}").format(
						get_link_to_form("Location", current_location),
						get_link_to_form("Employee", current_employee),
					),
				)
			elif current_location:
				add_asset_activity(
					d.asset,
					_("Asset transferred to Location {0}").format(
						get_link_to_form("Location", current_location)
					),
				)
			elif current_employee:
				add_asset_activity(
					d.asset,
					_("Asset issued to Employee {0}").format(get_link_to_form("Employee", current_employee)),
				)
