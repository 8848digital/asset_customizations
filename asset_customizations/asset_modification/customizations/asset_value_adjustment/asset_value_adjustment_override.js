// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.off("Asset Value Adjustment", "setup");                     
frappe.ui.form.on("Asset Value Adjustment", {
	new_asset_value: function (frm) {
		frm.set_query("custom_difference_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				},
			};
		});
	},

	setup: function (frm) {
		// frm.add_fetch("company", "cost_center", "cost_center");
		frm.set_query("cost_center", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});
		frm.set_query("asset", function () {
			return {
				filters: {
					calculate_depreciation: 1,
					docstatus: 1,
				},
			};
		});
	},

	asset: function (frm) {
		if (frm.doc.asset) {
			frm.call({
				method: "asset_customizations.asset_modification.customizations.asset_value_adjustment.asset_value_adjustment_override.value_of_accounting_dimension",
				args: {
					asset_name: frm.doc.asset,
				},
				// callback: function (r) {
				// 	console.log(r.message)
				// 	// if (r.message) {
				// 	// 	frm.set_value("current_asset_value", r.message);
				// 	// }
				// },
			});
		}
	},
});
