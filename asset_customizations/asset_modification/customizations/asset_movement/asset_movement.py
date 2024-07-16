import frappe
from frappe.utils.data import date_diff, getdate


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


def update_depreciation_schedule(asset_name, asset_depriciation_schedule_name, transaction_date):
	transaction_date = getdate(transaction_date)
	asset_available_for_use_date = frappe.db.get_value("Asset", asset_name, "available_for_use_date")

	asset_depr_schedule_list = frappe.db.get_all(
		"Depreciation Schedule", 
		filters={"parent": asset_depriciation_schedule_name}, 
		fields=["schedule_date", "name", "depreciation_amount", "accumulated_depreciation_amount", "journal_entry"], 
		order_by="schedule_date"
	)

	previous_schedule = None
	next_schedule = None

	for schedule in asset_depr_schedule_list:
		if transaction_date == schedule["schedule_date"]:
			return
		if schedule["schedule_date"] < transaction_date:
			previous_schedule = schedule
		elif schedule["schedule_date"] > transaction_date:
			next_schedule = schedule
			break
	
	set_depreciation_schedule(previous_schedule, next_schedule, 
                              asset_available_for_use_date, transaction_date,
                              asset_depriciation_schedule_name)


def set_depreciation_schedule(
    previous_schedule,
    next_schedule,
    asset_available_for_use_date,
    transaction_date,
    asset_depriciation_schedule_name
    ):

	if not previous_schedule and next_schedule:
		date_diff_between_schedule = date_diff(next_schedule["schedule_date"], asset_available_for_use_date)
		date_difference = date_diff(transaction_date, asset_available_for_use_date)
		
		dep_amount_for_today = (next_schedule["depreciation_amount"] / date_diff_between_schedule) * date_difference
		dep_amount_for_next_schedule = next_schedule["depreciation_amount"] - dep_amount_for_today
				
		accumulated_depreciation_amount = dep_amount_for_today   

	elif previous_schedule and next_schedule:
		date_diff_between_schedule = date_diff(next_schedule["schedule_date"], previous_schedule["schedule_date"])
		date_difference = date_diff(transaction_date, previous_schedule["schedule_date"])
		
		dep_amount_for_today = next_schedule["depreciation_amount"] / date_diff_between_schedule * date_difference
		dep_amount_for_next_schedule = next_schedule["depreciation_amount"] - dep_amount_for_today
				
		accumulated_depreciation_amount = previous_schedule["accumulated_depreciation_amount"]+dep_amount_for_today
	
	else:
		return

	asset_depreciation_schedule = frappe.get_doc("Asset Depreciation Schedule", asset_depriciation_schedule_name)
	asset_depreciation_schedule.append("depreciation_schedule",{
		"schedule_date": transaction_date,
		"depreciation_amount": dep_amount_for_today,
		"accumulated_depreciation_amount": accumulated_depreciation_amount
	})
	asset_depreciation_schedule.save()

	frappe.db.set_value("Depreciation Schedule", next_schedule["name"],
						"depreciation_amount", dep_amount_for_next_schedule)
	
	updated_asset_depr_schedule_list = frappe.db.get_all(
		"Depreciation Schedule", 
		filters={"parent": asset_depriciation_schedule_name}, 
		fields=["schedule_date", "name"], 
		order_by="schedule_date"
	)
	
	for idx, schedule in enumerate(updated_asset_depr_schedule_list):
		frappe.db.set_value("Depreciation Schedule", schedule["name"], "idx", idx + 1)


def on_cancel_reverse_depreciation_schedule(self):
	asset_depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", {"asset": self.assets[0].asset})
 
	transaction_date = getdate(self.transaction_date)
 
	if not frappe.db.exists("Depreciation Schedule", 
                         {"parent": asset_depr_schedule_doc.name,
                          "schedule_date": transaction_date}):
		return

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
        asset_movement_items = frappe.db.get_all("Asset Movement Item",
                                                 filters={"asset": asset_name},
                                                 fields=["parent as name"])
        asset_movement_name_list = list(set(item['name'] for item in asset_movement_items))
        
        if asset_movement_name_list:
            asset_movement_values = frappe.db.get_all("Asset Movement",
                                                      filters={"name": ["in", asset_movement_name_list],
                                                               "docstatus": 1},
                                                      fields=["name", "creation"])
            
            if asset_movement_values:
                asset_movement_values.sort(key=lambda x: x['creation'], reverse=True)
                most_recent_record = asset_movement_values[0]

                if self.name != most_recent_record['name']:
                    frappe.throw("You can only cancel the most recent record.")


@frappe.whitelist()
def create_journal_entry(**kwargs):
	asset_name_list = frappe.db.get_all("Asset Movement Item", 
                                     filters={"parent": kwargs.get("name")},
                                     pluck="asset")
	transaction_date = getdate(kwargs.get("transaction_date"))
	fieldnames = frappe.get_list("Accounting Dimension", pluck="fieldname")
 
	for asset_name in asset_name_list:
		asset_values = frappe.db.get_value("Asset", {"name": asset_name}, "*")

		asset_category_value = frappe.db.get_value("Asset Category Account", 
												{"parent": asset_values.asset_category,
												"company_name": asset_values.company},
												["fixed_asset_account", "accumulated_depreciation_account"],
            									as_dict=True)

		asset_depr_schedule = frappe.db.get_all("Asset Depreciation Schedule",
                                          		{"asset":asset_name}, pluck="name")
  
		old_dimension_value = {}
		new_dimension_value = {}
  
		asset_movement_child_data = frappe.db.get_value("Asset Movement Item",
                                                  {"parent": kwargs.get("name"), "asset":asset_name},
                                                  "*", as_dict= True)
  
		for fieldname in fieldnames:
			old_dimension_value[fieldname] = asset_movement_child_data.get("from_"+fieldname)
			new_dimension_value[fieldname] = asset_movement_child_data.get("target_"+fieldname)
  
		for schedule in asset_depr_schedule:
			accumulated_depreciation_amount = frappe.db.get_value("Depreciation Schedule",
                       			{"parent": schedule, "schedule_date": transaction_date},
                          		"accumulated_depreciation_amount")

			company = asset_values.company
			posting_date = transaction_date

			row1 = {
				"account" : asset_category_value.fixed_asset_account,
				"debit_in_account_currency": asset_values.total_asset_cost,
				"cost_center": asset_movement_child_data.target_cost_center
			}
			row1.update(new_dimension_value)
			row2 = {
				"account" : asset_category_value.fixed_asset_account,
				"credit_in_account_currency": asset_values.total_asset_cost,
				"cost_center": asset_movement_child_data.from_cost_center
			}
			row2.update(old_dimension_value)
   
			row3 = {
				"account" : asset_category_value.accumulated_depreciation_account,
				"debit_in_account_currency" : accumulated_depreciation_amount,
				"cost_center": asset_movement_child_data.from_cost_center
			}
			row3.update(old_dimension_value)
			row4 = {
				"account" : asset_category_value.accumulated_depreciation_account,
				"credit_in_account_currency": accumulated_depreciation_amount,
				"cost_center": asset_movement_child_data.target_cost_center
			}
			row4.update(new_dimension_value)

			doc = frappe.get_doc({
				'doctype': 'Journal Entry',
				"voucher_type": "Journal Entry",
				"posting_date": posting_date,
				"company": company,
				"remark": f"Asset Movement Entry against {kwargs.get('name')}"
			})
			doc.append("accounts", row1)
			doc.append("accounts", row2)
			doc.append("accounts", row3)
			doc.append("accounts", row4)
			doc.save()
			doc.submit()
	return doc.name


@frappe.whitelist()
def make_delivery_note(**kwargs):
	transaction_date = getdate(kwargs.get("transaction_date"))
	asset_movement_item_list = frappe.db.get_all("Asset Movement Item", 
                                              {"parent":kwargs.get("name")},
                                              ["*"])
	
	fieldnames = frappe.get_list("Accounting Dimension", pluck="fieldname")
	delivery_note_item_rows = []
	for item in asset_movement_item_list:
		asset_item_code = frappe.db.get_value("Asset", item.asset, ["item_code", "asset_quantity"])
  
		asset_schedule = frappe.db.get_all("Asset Depreciation Schedule", {"asset":item.asset})

		for schedule in asset_schedule:
			accumulated_depreciation_amount = frappe.db.get_all("Depreciation Schedule",
                                                filters = {"parent": schedule,
                                                           "schedule_date": transaction_date},
                                                pluck = "accumulated_depreciation_amount")
			old_dimension_value = {}
			old_dimension_value["item_code"] = asset_item_code[0]
			old_dimension_value["rate"] = accumulated_depreciation_amount[0]
			old_dimension_value["qty"] = asset_item_code[1]
			for fieldname in fieldnames:
				old_dimension_value[fieldname] = item.get("from_"+fieldname)
			delivery_note_item_rows.append(old_dimension_value)
	return delivery_note_item_rows
