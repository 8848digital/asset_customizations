from asset_customizations.asset_modification.customizations.utils.utils import get_asset_depr_schedule_list, update_asset_depr_schedule_index
import frappe
from frappe import _
from frappe.utils import get_link_to_form

from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_movement.asset_movement import AssetMovement
from asset_customizations.asset_modification.customizations.asset.depreciation_override import make_depreciation_entry
from frappe.utils.data import date_diff, getdate


class CustomAssetMovement(AssetMovement):
	def set_latest_location_and_custodian_in_asset(self):
		fields = frappe.get_list("Accounting Dimension", pluck="fieldname")
		transformed_fields = [f"target_{field}" for field in fields]
		field_mapping = {}
		current_values = {}
		for tf in transformed_fields:
			field_mapping[tf] = tf.split('_', 1)[1]
			# if fields:
			# 	current_values[tf] = ""

		current_location, current_employee = "", ""
		custom_target_cost_center = ""
		cond = "1=1"

		for d in self.assets:
			args = {"asset": d.asset, "company": self.company}

			if transformed_fields:
				transformed_fields_str = ", " + ", ".join(transformed_fields)
			else:
				transformed_fields_str = ""

			latest_movement_entry = frappe.db.sql(
				f"""
				SELECT asm_item.target_location, asm_item.to_employee, asm_item.custom_target_cost_center{transformed_fields_str}
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

				for idx, field in enumerate(transformed_fields):
					original_field = field_mapping[field]
					current_values[original_field] = latest_movement_entry[0][3 + idx] if fields else ""

			else:
				for original_field in field_mapping.values():
					current_values[original_field] = ""

			frappe.db.set_value("Asset", d.asset, "location", current_location, update_modified=False)
			frappe.db.set_value("Asset", d.asset, "custodian", current_employee, update_modified=False)
			frappe.db.set_value("Asset", d.asset, "cost_center", custom_target_cost_center, update_modified=False)

			for original_field in field_mapping.values():
				frappe.db.set_value("Asset", d.asset, original_field, current_values[original_field], update_modified=False)
			if self.purpose == "Transfer":
				if len(frappe.db.get_all("Asset Movement Item", {"asset": d.asset})) > 1:
					if frappe.db.exists("Asset Depreciation Schedule", {"asset": d.asset}):
						asset_depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", {"asset":d.asset})
						update_depreciation_schedule(d.asset, asset_depr_schedule_doc.name, self.transaction_date)
						make_depreciation_entry(asset_depr_schedule_doc.name)

						frappe.db.set_value("Asset Depreciation Schedule",
											asset_depr_schedule_doc.name,
											"custom_cost_center",
											custom_target_cost_center,
											update_modified=True)

						for original_field in field_mapping.values():
							frappe.db.set_value("Asset Depreciation Schedule",
												asset_depr_schedule_doc.name,
												original_field,
												current_values[original_field], 
												update_modified=True)

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


	def validate_location(self):
		for d in self.assets:
			if self.purpose in ["Transfer", "Issue"]:
				current_location = frappe.db.get_value("Asset", d.asset, "location")
				if d.source_location:
					if current_location != d.source_location:
						frappe.throw(
							_("Asset {0} does not belongs to the location {1}").format(
								d.asset, d.source_location
							)
						)
				else:
					d.source_location = current_location

			if self.purpose == "Issue":
				if not d.to_employee:
					frappe.throw(_("Employee is required while issuing Asset {0}").format(d.asset))

			if self.purpose == "Transfer":
				if not d.target_location:
					frappe.throw(
						_("Target Location is required while transferring Asset {0}").format(d.asset)
					)
				if d.source_location == d.target_location:
					frappe.throw(_("Source and Target Location cannot be same"))

			if self.purpose == "Receipt":
				if not (d.source_location) and not (d.target_location or d.to_employee):
					frappe.throw(
						_("Target Location or To Employee is required while receiving Asset {0}").format(
							d.asset
						)
					)
				elif d.source_location:
					if d.from_employee and not d.target_location:
						frappe.throw(
							_(
								"Target Location is required while receiving Asset {0} from an employee"
							).format(d.asset)
						)
					elif d.to_employee and d.target_location:
						frappe.throw(
							_(
								"Asset {0} cannot be received at a location and given to an employee in a single movement"
							).format(d.asset)
						)
      

def update_depreciation_schedule(asset_name, asset_depriciation_schedule_name, transaction_date):
    transaction_date = getdate(transaction_date)
    asset_available_for_use_date = frappe.db.get_value("Asset", asset_name, "available_for_use_date")
    asset_depr_schedule_list = get_asset_depr_schedule_list(asset_depriciation_schedule_name)
    
    previous_schedule, next_schedule = find_previous_and_next_schedules(asset_depr_schedule_list,
                                                                        transaction_date)
    
    if not (previous_schedule or next_schedule):
        return
    
    set_depreciation_schedule(
        previous_schedule,
        next_schedule,
        asset_available_for_use_date,
        transaction_date,
        asset_depriciation_schedule_name
    )


def find_previous_and_next_schedules(schedule_list, transaction_date):
    previous_schedule = None
    next_schedule = None
    for schedule in schedule_list:
        if transaction_date == schedule["schedule_date"]:
            return None, None
        if schedule["schedule_date"] < transaction_date:
            previous_schedule = schedule
        elif schedule["schedule_date"] > transaction_date:
            next_schedule = schedule
            break
    return previous_schedule, next_schedule


def set_depreciation_schedule(previous_schedule,
                              next_schedule,
                              asset_available_for_use_date,
                              transaction_date,
                              asset_depriciation_schedule_name):
    dep_amount_for_today, dep_amount_for_next_schedule, accumulated_depreciation_amount = calculate_depreciation_amounts(previous_schedule, next_schedule, asset_available_for_use_date, transaction_date)
    
    if not dep_amount_for_today:
        return
    
    append_depreciation_schedule(asset_depriciation_schedule_name, transaction_date, dep_amount_for_today, accumulated_depreciation_amount)
    
    if next_schedule:
        frappe.db.set_value("Depreciation Schedule", next_schedule["name"], "depreciation_amount", dep_amount_for_next_schedule)
    
    update_asset_depr_schedule_index(asset_depriciation_schedule_name)
    
    
def calculate_depreciation_amounts(previous_schedule, next_schedule, asset_available_for_use_date, transaction_date):
    if not previous_schedule and next_schedule:
        date_diff_between_schedule = date_diff(next_schedule["schedule_date"], asset_available_for_use_date)
        date_difference = date_diff(transaction_date, asset_available_for_use_date)
    elif previous_schedule and next_schedule:
        date_diff_between_schedule = date_diff(next_schedule["schedule_date"], previous_schedule["schedule_date"])
        date_difference = date_diff(transaction_date, previous_schedule["schedule_date"])
    else:
        return None, None, None
    
    dep_amount_for_today = (next_schedule["depreciation_amount"] / date_diff_between_schedule) * date_difference
    dep_amount_for_next_schedule = next_schedule["depreciation_amount"] - dep_amount_for_today
    accumulated_depreciation_amount = previous_schedule["accumulated_depreciation_amount"] + dep_amount_for_today if previous_schedule else dep_amount_for_today
    
    return dep_amount_for_today, dep_amount_for_next_schedule, accumulated_depreciation_amount


def append_depreciation_schedule(asset_depriciation_schedule_name, transaction_date, dep_amount_for_today, accumulated_depreciation_amount):
    asset_depreciation_schedule = frappe.get_doc("Asset Depreciation Schedule", asset_depriciation_schedule_name)
    asset_depreciation_schedule.append("depreciation_schedule", {
        "schedule_date": transaction_date,
        "depreciation_amount": dep_amount_for_today,
        "accumulated_depreciation_amount": accumulated_depreciation_amount
    })
    asset_depreciation_schedule.save()
    
    
def update_next_schedule(schedule_name, dep_amount_for_next_schedule):
    frappe.db.set_value("Depreciation Schedule", schedule_name, "depreciation_amount", dep_amount_for_next_schedule)



