from asset_customizations.asset_modification.customizations.utils.utils import get_asset_depr_schedule_list, update_asset_depr_schedule_index
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
			if schedule["schedule_date"] >= transaction_date:
				next_schedule = schedule
				break
		if next_schedule:
			if next_schedule["journal_entry"]:
				frappe.throw("Depreciation Entry of Transaction Date is already made")


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


def on_cancel_reverse_depreciation_schedule(self):
    asset_name_list = frappe.db.get_all("Asset Movement Item", {"parent": self.name}, pluck="asset")
    transaction_date = getdate(self.transaction_date)
    for asset in asset_name_list:
        asset_depr_schedule_list = frappe.db.get_list("Asset Depreciation Schedule", 
                                                      {"asset": asset}, pluck="name")
        for asset_depr_schedule in asset_depr_schedule_list:
            if not frappe.db.exists("Depreciation Schedule",
                                    {"parent": asset_depr_schedule, "schedule_date": transaction_date}):
                break
            
            depreciation_entry = get_depreciation_entry(asset_depr_schedule, transaction_date)
            if not depreciation_entry:
                break
            try:
                cancel_journal_entry(depreciation_entry["journal_entry"])
                reverse_depreciation_entry(asset_depr_schedule, depreciation_entry, transaction_date)
            except Exception as e:
                frappe.throw(str(e))


def get_depreciation_entry(schedule_name, transaction_date):
    return frappe.db.get_value(
        "Depreciation Schedule",
        {"parent": schedule_name, "schedule_date": transaction_date},
        ["name", "parent", "schedule_date", "depreciation_amount", "accumulated_depreciation_amount", "journal_entry"],
        as_dict=True
    )


def cancel_journal_entry(journal_entry_name):
    if journal_entry_name:
        journal_entry_doc = frappe.get_doc("Journal Entry", journal_entry_name)
        if journal_entry_doc.docstatus == 1:
            journal_entry_doc.cancel()
                
                
def reverse_depreciation_entry(asset_depr_schedule_name, depreciation_entry, transaction_date):
    asset_depr_schedule_list = get_asset_depr_schedule_list(asset_depr_schedule_name)
    previous_schedule, next_schedule = previous_and_next_schedules(asset_depr_schedule_list, transaction_date)
    frappe.get_doc("Depreciation Schedule", depreciation_entry["name"]).cancel()
    frappe.db.delete("Depreciation Schedule", depreciation_entry["name"])
    
    set_depr_schedule_value(previous_schedule, next_schedule, depreciation_entry)
    update_asset_depr_schedule_index(asset_depr_schedule_name)


def previous_and_next_schedules(schedule_list, transaction_date):
    previous_schedule = None
    next_schedule = None
    for schedule in schedule_list:

        if schedule["schedule_date"] < transaction_date:
            previous_schedule = schedule
        elif schedule["schedule_date"] > transaction_date:
            next_schedule = schedule
            break
    return previous_schedule, next_schedule


def set_depr_schedule_value(previous_schedule, next_schedule, depreciation_entry):
    if not previous_schedule and next_schedule:
        frappe.db.set_value("Depreciation Schedule", next_schedule["name"], "depreciation_amount", 
                            next_schedule["depreciation_amount"] + depreciation_entry["depreciation_amount"])
    elif previous_schedule and next_schedule:
        new_dep_amount = next_schedule["depreciation_amount"] + depreciation_entry["depreciation_amount"]
        frappe.db.set_value("Depreciation Schedule", next_schedule["name"], "depreciation_amount", new_dep_amount)
        
        accumulated_depreciation_amount = (
            previous_schedule["accumulated_depreciation_amount"] + next_schedule["depreciation_amount"]+
											depreciation_entry["depreciation_amount"]
        )
        frappe.db.set_value("Depreciation Schedule", next_schedule["name"], "accumulated_depreciation_amount", accumulated_depreciation_amount)


@frappe.whitelist()
def create_journal_entry(**kwargs):
    asset_movemet_name = kwargs.get("name")
    company = kwargs.get("company")
    
    transaction_date = getdate(kwargs.get("transaction_date"))

    asset_name_list = frappe.db.get_all("Asset Movement Item", 
                                        filters={"parent": asset_movemet_name},
                                        pluck="asset")
    fieldnames = frappe.get_list("Accounting Dimension", pluck="fieldname")
    child_rows = []
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
                                                    {"parent": asset_movemet_name, "asset":asset_name},
                                                    "*", as_dict= True)

        for fieldname in fieldnames:
            old_dimension_value[fieldname] = asset_movement_child_data.get("from_"+fieldname)
            new_dimension_value[fieldname] = asset_movement_child_data.get("target_"+fieldname)

        if asset_values.calculate_depreciation:
            for schedule in asset_depr_schedule:
                accumulated_depreciation_amount = frappe.db.get_value("Depreciation Schedule",
                                    {"parent": schedule, "schedule_date": transaction_date},
                                    "accumulated_depreciation_amount")

                dep_row =  set_value_in_journal_entry(asset_values,
                                                    asset_category_value,
                                                    asset_movement_child_data,
                                                    new_dimension_value,
                                                    old_dimension_value,
                                                    accumulated_depreciation_amount,
                                                    )
                child_rows+=dep_row
        else:
            no_dep_row = set_value_in_journal_entry(asset_values,
                                                asset_category_value,
                                                asset_movement_child_data,
                                                new_dimension_value,
                                                old_dimension_value,
                                                None,
                                                )
            child_rows += no_dep_row
    # frappe.throw(str(child_rows))
    doc = frappe.get_doc({
        'doctype': 'Journal Entry',
        "voucher_type": "Journal Entry",
        "posting_date": transaction_date,
        "company": company,
        "accounts":child_rows,
        "remark": f"Asset Movement Entry against {asset_movemet_name}"
    })
    doc.save()
    doc.submit()
    
    return doc.name


def set_value_in_journal_entry(asset_values,
                               asset_category_value,
                               asset_movement_child_data,
                               new_dimension_value,
                               old_dimension_value,
                               accumulated_depreciation_amount,
                            ):
    

    reference = {"reference_type": "Asset",
                "reference_name": asset_movement_child_data.asset}
    if accumulated_depreciation_amount:
        row1 = {
            "account" : asset_category_value.fixed_asset_account,
            "debit_in_account_currency": asset_values.total_asset_cost,
            "cost_center": asset_movement_child_data.target_cost_center
        }
        row1.update(reference)
        row1.update(new_dimension_value)
        row2 = {
            "account" : asset_category_value.fixed_asset_account,
            "credit_in_account_currency": asset_values.total_asset_cost,
            "cost_center": asset_movement_child_data.from_cost_center
        }
        row2.update(reference)
        row2.update(old_dimension_value)

        row3 = {
            "account" : asset_category_value.accumulated_depreciation_account,
            "debit_in_account_currency" : accumulated_depreciation_amount,
            "cost_center": asset_movement_child_data.from_cost_center
        }
        row3.update(reference)
        row3.update(old_dimension_value)
        row4 = {
            "account" : asset_category_value.accumulated_depreciation_account,
            "credit_in_account_currency": accumulated_depreciation_amount,
            "cost_center": asset_movement_child_data.target_cost_center
        }
        row4.update(reference)
        row4.update(new_dimension_value)
        rows = [row1, row2, row3, row4]
    else:
        row1 = {
            "account" : asset_category_value.fixed_asset_account,
            "debit_in_account_currency": asset_values.total_asset_cost,
            "cost_center": asset_movement_child_data.target_cost_center
        }
        row1.update(reference)
        row1.update(new_dimension_value)
        row2 = {
            "account" : asset_category_value.fixed_asset_account,
            "credit_in_account_currency": asset_values.total_asset_cost,
            "cost_center": asset_movement_child_data.from_cost_center
        }
        row2.update(reference)
        row2.update(old_dimension_value)
        rows = [row1, row2]

    return rows


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
