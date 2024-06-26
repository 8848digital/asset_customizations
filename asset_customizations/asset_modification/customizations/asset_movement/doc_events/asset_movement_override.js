frappe.ui.form.on("Asset Movement Item", {
	asset: function (frm, cdt, cdn) {
		// Fetch the fields from "Accounting Dimension"
		frappe.db.get_list("Accounting Dimension", {
			fields: ["name"]
		}).then(fields => {
			// Extract and convert field names to the required format
			const field_names = fields.map(field => `from_${field.name.toLowerCase().replace(/ /g, '_')}`);
			
			console.log("Override jssssssssssss");
            console.log("Converted Field Names:", field_names);

			// on manual entry of an asset auto sets their source location / employee
			const asset_name = locals[cdt][cdn].asset;
			console.log("Selected Asset:", asset_name);

			if (asset_name) {
				frappe.db.get_doc("Asset", asset_name)
					.then(asset_doc => {
						if (asset_doc.location) {
							console.log("Setting Source Location:", asset_doc.location);
							frappe.model.set_value(cdt, cdn, "source_location", asset_doc.location);
						}
						if (asset_doc.custodian) {
							frappe.model.set_value(cdt, cdn, "from_employee", asset_doc.custodian);
						}
						if (asset_doc.cost_center) {
							console.log("Setting From Cost Center:", asset_doc.cost_center);
							frappe.model.set_value(cdt, cdn, "custom_from_cost_center", asset_doc.cost_center);
						}

						// Dynamically set other fields
						field_names.forEach(field => {
							const original_field = field.replace("from_", "");
							if (asset_doc[original_field]) {
								console.log(`Setting ${field}:`, asset_doc[original_field]);
								frappe.model.set_value(cdt, cdn, field, asset_doc[original_field]);
							}
						});
					})
					.catch(err => {
						console.log("Error fetching asset:", err);
					});
			}
		}).catch(err => {
			console.log("Error fetching fields:", err);
		});
	},
});