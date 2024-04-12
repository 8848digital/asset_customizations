app_name = "asset_customizations"
app_title = "asset_modification"
app_publisher = "manoj"
app_description = "asset_modification"
app_email = "manoj@8848digital.com"
app_license = "MIT"


doctype_js = {
	"Asset": "asset_modification/customizations/asset_value_adjustment/doc_events/asset.js",
	"Asset Value Adjustment": "public/js/asset_value_adjustment_override.js",
}

from erpnext.assets.doctype.asset.asset import Asset

from asset_customizations.asset_modification.customizations.asset_value_adjustment.doc_events.asset_modify import (
	on_submit,
)

Asset.on_submit = on_submit

# Overriding Asset Capitalization Doctype to change the Credit Account in Assets Table
from erpnext.assets.doctype.asset import depreciation

from asset_customizations.asset_modification.customizations.asset_capitalization.doc_events.asset_capitalization_target_account import (
	get_depreciation_accounts,
)

depreciation.get_depreciation_accounts = get_depreciation_accounts

# from erpnext.assets.doctype.asset_value_adjustment.asset_value_adjustment import (
# 	AssetValueAdjustment,
# )

# from asset_customizations.asset_modification.customizations.asset_value_adjustment.doc_events.asset_value_adjustment_override import (
# 	make_depreciation_entry_custom,
# 	set_difference_amount_custom,
# )

# AssetValueAdjustment.set_difference_amount = set_difference_amount_custom
# AssetValueAdjustment.make_depreciation_entry = make_depreciation_entry_custom

fixtures = [{"dt": "Custom Field", "filters": [["module", "=", "asset_modification"]]}]

override_doctype_class = {
	"Asset Value Adjustment": "asset_customizations.asset_modification.customizations.asset_value_adjustment.doc_events.asset_value_adjustment_override.CustomAssetValueAdjustment"
}
