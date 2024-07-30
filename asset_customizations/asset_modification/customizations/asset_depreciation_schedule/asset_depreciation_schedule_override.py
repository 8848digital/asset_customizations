import frappe
from frappe import _

from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import AssetDepreciationSchedule


class CustomAssetDepreciationSchedule(AssetDepreciationSchedule):
    def set_draft_asset_depr_schedule_details(self, asset_doc, row):
        fields = frappe.get_list("Accounting Dimension", pluck="fieldname")
        
        self.asset = asset_doc.name
        self.finance_book = row.finance_book
        self.finance_book_id = row.idx
        self.opening_accumulated_depreciation = asset_doc.opening_accumulated_depreciation or 0
        self.opening_number_of_booked_depreciations = asset_doc.opening_number_of_booked_depreciations or 0
        self.gross_purchase_amount = asset_doc.gross_purchase_amount
        self.depreciation_method = row.depreciation_method
        self.total_number_of_depreciations = row.total_number_of_depreciations
        self.frequency_of_depreciation = row.frequency_of_depreciation
        self.rate_of_depreciation = row.rate_of_depreciation
        self.expected_value_after_useful_life = row.expected_value_after_useful_life
        self.daily_prorata_based = row.daily_prorata_based
        self.shift_based = row.shift_based
        self.status = "Draft"
        self.custom_cost_center = asset_doc.cost_center
        
        # Setting dynamic fields
        for field in fields:
            setattr(self, field, getattr(asset_doc, field, None))
