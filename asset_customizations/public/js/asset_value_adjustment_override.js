// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Value Adjustment", {
	new_asset_value: function (frm) {
		frm.set_query("custom_difference_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});
	},
});
