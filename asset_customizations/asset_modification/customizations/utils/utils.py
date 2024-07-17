import frappe


def get_asset_depr_schedule_list(asset_depriciation_schedule_name):
    return frappe.db.get_all(
        "Depreciation Schedule",
        filters={"parent": asset_depriciation_schedule_name},
        fields=["schedule_date", "name", "depreciation_amount", "accumulated_depreciation_amount", "journal_entry"],
        order_by="schedule_date"
    )


def update_asset_depr_schedule_index(asset_depriciation_schedule_name):
    updated_asset_depr_schedule_list = get_asset_depr_schedule_list(asset_depriciation_schedule_name)
    for idx, schedule in enumerate(updated_asset_depr_schedule_list):
        frappe.db.set_value("Depreciation Schedule", schedule["name"], "idx", idx + 1)