app_name = "asset_customizations"
app_title = "asset_modification"
app_publisher = "manoj"
app_description = "asset_modification"
app_email = "manoj@8848digital.com"
app_license = "MIT"


from erpnext.assets.report.fixed_asset_register import fixed_asset_register
from asset_customizations.asset_modification.customizations.report.fixed_asset_registry import get_data, get_columns
fixed_asset_register.get_columns = get_columns
fixed_asset_register.get_data = get_data

after_migrate = "asset_customizations.migrate.after_migrate"

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Purchase Receipt":"asset_customizations.asset_modification.customizations.buying_controller.doc_events.buying_controller_override.CustomPurchaseReceipt",
    "Asset":"asset_customizations.asset_modification.customizations.asset.asset_override.CustomAsset",
    "Accounting Dimension":"asset_customizations.asset_modification.customizations.accounting_dimension.accounting_dimension_override.CustomAccountingDimension",
    "Asset Movement":"asset_customizations.asset_modification.customizations.asset_movement.doc_events.asset_movement_override.CustomAssetMovement",
    "Asset Depreciation Schedule":"asset_customizations.asset_modification.customizations.asset_depreciation_schedule.doc_event.asset_depreciation_schedule_override.CustomAssetDepreciationSchedule",
	"Asset Value Adjustment": "asset_customizations.asset_modification.customizations.asset_value_adjustment.asset_value_adjustment_override.CustomAssetValueAdjustment",
	"Asset Capitalization": "asset_customizations.asset_modification.customizations.asset_capitalization.doc_events.asset_capitalization_target_account.CustomAssetCapitalization",
    "Asset Repair": "asset_customizations.asset_modification.customizations.asset_repair.doc_events.asset_repair.AssetRepairMaster"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Asset Movement": {
		"validate": "asset_customizations.asset_modification.customizations.asset_movement.asset_movement.validate",
		"before_cancel": "asset_customizations.asset_modification.customizations.asset_movement.asset_movement.before_cancel",
		"on_cancel": "asset_customizations.asset_modification.customizations.asset_movement.asset_movement.on_cancel",
	},
	"Journal Entry": {
		"on_cancel": "asset_customizations.asset_modification.customizations.journal_entry.journal_entry.on_cancel",
	},
    "Asset Repair": {
		"before_save": "asset_customizations.asset_modification.customizations.asset_repair.doc_events.asset_repair.before_save",
        "on_submit": "asset_customizations.asset_modification.customizations.asset_repair.doc_events.asset_repair.on_submit",
	}
}


# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
"erpnext.assets.doctype.asset.asset.make_asset_movement" : "asset_customizations.asset_modification.customizations.asset.asset_override.make_asset_movement",
"erpnext.assets.doctype.asset.depreciation.make_depreciation_entry" : "asset_customizations.asset_modification.customizations.asset.depreciation_override.make_depreciation_entry",
"erpnext.assets.doctype.asset.depreciation.scrap_asset" : "asset_customizations.asset_modification.customizations.asset.depreciation_override.scrap_asset"
}

doctype_js = {"Asset" : "asset_modification/customizations/asset/asset.js",
            "Asset Value Adjustment": "asset_modification/customizations/asset_value_adjustment/asset_value_adjustment_override.js",
            "Asset Movement": "asset_modification/customizations/asset_movement/doc_events/asset_movement_override.js"
            }


fixtures = [
    # {"dt": "Custom Field", "filters": [
    #     [
    #         "module", "=", "asset_modification"
    #     ]
    # ]},

    {"dt": "Property Setter", "filters": [
        [
            "module", "=", "asset_modification"
        ]
    ]}
]

accounting_dimension_doctypes_for_asset = [
	"GL Entry",
	"Payment Ledger Entry",
	"Sales Invoice",
	"Purchase Invoice",
	"Payment Entry",
	"Asset",
	"Stock Entry",
	"Budget",
	"Delivery Note",
	"Sales Invoice Item",
	"Purchase Invoice Item",
	"Purchase Order Item",
	"Sales Order Item",
	"Journal Entry Account",
	"Material Request Item",
	"Delivery Note Item",
	"Purchase Receipt Item",
	"Stock Entry Detail",
	"Payment Entry Deduction",
	"Sales Taxes and Charges",
	"Purchase Taxes and Charges",
	"Shipping Rule",
	"Landed Cost Item",
	"Asset Value Adjustment",
	"Asset Repair",
	"Asset Capitalization",
	"Loyalty Program",
	"Stock Reconciliation",
	"POS Profile",
	"Opening Invoice Creation Tool",
	"Opening Invoice Creation Tool Item",
	"Subscription",
	"Subscription Plan",
	"POS Invoice",
	"POS Invoice Item",
	"Purchase Order",
	"Purchase Receipt",
	"Sales Order",
	"Subcontracting Order",
	"Subcontracting Order Item",
	"Subcontracting Receipt",
	"Subcontracting Receipt Item",
	"Account Closing Balance",
	"Supplier Quotation",
	"Supplier Quotation Item",
	"Payment Reconciliation",
	"Payment Reconciliation Allocation",
	"Payment Request",
 	"Asset Movement Item",
  	"Asset Depreciation Schedule"
]
