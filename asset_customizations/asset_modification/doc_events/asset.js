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
            let date_to_send = values.scrap_date;
            let today_date = frappe.datetime.get_today();
            let scrap_date = new Date(date_to_send);

            if (new Date(date_to_send) > new Date(today_date)) {
                frappe.throw(__("Future Date Is Not Allowed"));
            }
            d.hide();
            frappe.confirm(__("Do you really want to scrap this asset?"), function () {
                frappe.call({
                    args: {
                        asset_name: frm.doc.name,
                        scrap_date: date_to_send
                    },
                    method: "asset_customizations.asset_modification.doc_events.asset_depreciation.scrap_asset_modified",
                    callback: function (r) {
                        cur_frm.reload_doc();
                    },
                });
            });
        }
    });
    d.show();
};

