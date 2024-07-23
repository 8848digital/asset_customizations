from asset_customizations.asset_modification.customizations.asset_value_adjustment.doc_events.asset_depreciation import scrap_asset_modified
import frappe
from frappe.utils import getdate, today


@frappe.whitelist()
def asset_scrap_date(asset_name, scrap_date, purchase_date):
    scrap_date = getdate(scrap_date)
    today_date = getdate(today())
    purchase_date = getdate(purchase_date)
    
    depriciation_list = frappe.db.get_all("Asset Depreciation Schedule", {"asset": asset_name}, pluck="name")
    for depriciation in depriciation_list:
        asset_depr_schedule_list = frappe.db.get_all(
            "Depreciation Schedule", 
            filters={"parent": depriciation}, 
            fields=["schedule_date", "journal_entry"], 
            order_by="schedule_date"
        )
        
        last_depreciated_row = None
        next_depriciating_row = None
        for schedule in asset_depr_schedule_list:
            if schedule["journal_entry"]:
                last_depreciated_row = schedule
            elif not schedule["journal_entry"]:
                next_depriciating_row = schedule
                break
        print(last_depreciated_row, next_depriciating_row)
        if next_depriciating_row and last_depreciated_row:
            if scrap_date < last_depreciated_row["schedule_date"] and scrap_date > purchase_date:
                frappe.throw("Asset cannot be scrap before the depreciation entry")
            elif (scrap_date <= next_depriciating_row["schedule_date"] and 
                  scrap_date > last_depreciated_row["schedule_date"]):
                scrap_asset_modified(asset_name, scrap_date)
        elif not last_depreciated_row and not next_depriciating_row["journal_entry"]:
            scrap_asset_modified(asset_name, scrap_date)
        
        if scrap_date > today_date:
            frappe.throw("Future Date Is Not Allowed")
            
        elif scrap_date < purchase_date:
            frappe.throw("Scrap Date Cannot Be Before Purchase Date")