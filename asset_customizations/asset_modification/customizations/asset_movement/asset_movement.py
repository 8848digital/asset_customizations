import frappe
from frappe.utils.data import getdate


def validate(self, method=None):
    validate_dep_schedule(self)


def before_cancel(self, method=None):
    sequence_cancel(self)


def on_cancel(self, method=None):
    on_cancel_reverse_depreciation_schedule(self)


def validate_dep_schedule(self):
	for asset in self.assets:
		if not frappe.db.exists("Asset Depreciation Schedule", {"asset": asset.asset}):
			return

		asset_depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", {"asset": asset.asset})
		transaction_date = getdate(self.transaction_date)

		asset_depr_schedule_list = frappe.db.get_all(
			"Depreciation Schedule", 
			filters={"parent": asset_depr_schedule_doc.name}, 
			fields=["schedule_date", "name", "depreciation_amount", 
           			"accumulated_depreciation_amount", "journal_entry"], 
			order_by="schedule_date"
		)
  
		next_schedule = None
		for schedule in asset_depr_schedule_list:
			if schedule["schedule_date"] > transaction_date:
				next_schedule = schedule
				break
		if next_schedule:
			if next_schedule["journal_entry"]:
				frappe.throw("Depreciation Entry of Transaction Date is already made")


def on_cancel_reverse_depreciation_schedule(self):
	asset_depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", {"asset": self.assets[0].asset})
 
	transaction_date = getdate(self.transaction_date)

	depreciation_entry = frappe.db.get_value(
		"Depreciation Schedule", 
		{"parent": asset_depr_schedule_doc.name, "schedule_date": transaction_date}, 
		["name", "depreciation_amount", "accumulated_depreciation_amount", "journal_entry"], 
		as_dict=True
	)

	if depreciation_entry["journal_entry"]:
		journal_entry_doc = frappe.get_doc("Journal Entry", depreciation_entry["journal_entry"])
		if journal_entry_doc.docstatus == 1:
			journal_entry_doc.cancel()
   
	asset_depr_schedule_list = frappe.db.get_all(
		"Depreciation Schedule", 
		filters={"parent": asset_depr_schedule_doc.name}, 
		fields=["schedule_date", "name", "depreciation_amount",
          		"accumulated_depreciation_amount", "journal_entry"], 
		order_by="schedule_date"
	)

	previous_schedule = None
	next_schedule = None
	for schedule in asset_depr_schedule_list:
		if schedule["schedule_date"] < transaction_date:
			previous_schedule = schedule
		elif schedule["schedule_date"] > transaction_date:
			next_schedule = schedule
			break

	frappe.get_doc("Depreciation Schedule", depreciation_entry["name"]).cancel()
	frappe.delete_doc("Depreciation Schedule", depreciation_entry["name"])

	set_depr_schedule_value(previous_schedule, next_schedule, depreciation_entry)
	update_asset_depr_schedule_index(asset_depr_schedule_doc.name)


def set_depr_schedule_value(previous_schedule, next_schedule, depreciation_entry):
	if not previous_schedule and next_schedule:
		frappe.db.set_value("Depreciation Schedule", next_schedule["name"], "depreciation_amount", 
			next_schedule["depreciation_amount"] + depreciation_entry["depreciation_amount"])

	elif previous_schedule and next_schedule:
		frappe.db.set_value("Depreciation Schedule", next_schedule["name"], "depreciation_amount", 
			next_schedule["depreciation_amount"] + depreciation_entry["depreciation_amount"])
		
		accumulated_depreciation_amount = (previous_schedule["accumulated_depreciation_amount"]+
											next_schedule["depreciation_amount"]+
											depreciation_entry["depreciation_amount"])

		frappe.db.set_value("Depreciation Schedule", next_schedule["name"],
                      		"accumulated_depreciation_amount", accumulated_depreciation_amount)



def update_asset_depr_schedule_index(asset_depreciation_schedule_name):
	updated_asset_depr_schedule_list = frappe.db.get_all(
		"Depreciation Schedule", 
		filters={"parent": asset_depreciation_schedule_name}, 
		fields=["schedule_date", "name"], 
		order_by="schedule_date"
	)

	for idx, schedule in enumerate(updated_asset_depr_schedule_list):
		frappe.db.set_value("Depreciation Schedule", schedule["name"], "idx", idx + 1)


def sequence_cancel(self):
	asset_name_list = frappe.db.get_all("Asset Movement Item", filters={"parent": self.name}, pluck="asset")
	for asset_name in asset_name_list:
		asset_movement_name_list = frappe.db.get_all("Asset Movement Item",
                                               filters={"asset": asset_name},
                                               pluck="parent")
		asset_movement_value_list = []
		for asset_movement_name in asset_movement_name_list:
			asset_movement_value = frappe.db.get_value("Asset Movement", 
                                              {"name": asset_movement_name, "docstatus":1},
                                              ["name", "creation"], as_dict=True)
			if asset_movement_value:
				asset_movement_value_list.append(asset_movement_value)
  
		for i in range(len(asset_movement_value_list)):
			for j in range(i + 1, len(asset_movement_value_list)):
				if asset_movement_value_list[i]['creation'] < asset_movement_value_list[j]['creation']:
					asset_movement_value_list[i], asset_movement_value_list[j] = asset_movement_value_list[j], asset_movement_value_list[i]

		most_recent_record = asset_movement_value_list[0] if asset_movement_value_list else None

		if most_recent_record and self.name != most_recent_record['name']:
			frappe.throw("You can only cancel the most recent record.")