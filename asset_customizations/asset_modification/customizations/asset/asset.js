frappe.provide("erpnext.asset");

frappe.ui.form.on("Asset", {
    refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			if (in_list(["Submitted", "Partially Depreciated", "Fully Depreciated"], frm.doc.status)) {
				frm.add_custom_button(
					__("Scrap Asset"),
					function () {
						erpnext.asset.scrap_asset(frm);
					},
					__("Manage")
				);
            }
        }
	},
});

erpnext.asset.scrap_asset = function (frm) {
    var d = new frappe.ui.Dialog({
        title: 'Enter Date',
        fields: [
            {
                label: __("Select the date"),
                fieldname: "scrap_date",
                fieldtype: "Date",
                reqd: 1
            }
        ],
        size: 'small',
        primary_action_label: 'Submit',
        primary_action(values) {     
            frappe.call({
                args: {
                    "asset_name":frm.doc.name,
                    "scrap_date": values.scrap_date,
                    "purchase_date": frm.doc.purchase_date
                },
                method: "asset_customizations.asset_modification.customizations.asset.asset.asset_scrap_date_validation",
                callback: function(r) {
                    cur_frm.reload_doc();
                    d.hide();
                }
            })
        }
    });
    d.show();
};
