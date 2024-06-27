
frappe.ui.form.off("Asset Movement", "set_required_fields");
frappe.ui.form.on("Asset Movement", {
	set_required_fields: (frm, cdt, cdn) => {
		let fieldnames_to_be_altered;
		console.log("innnnnnnnnnnnnnnnn 1")
		if (frm.doc.purpose === "Transfer") {
			fieldnames_to_be_altered = {
				target_location: { read_only: 0, reqd: 1 },
				source_location: { read_only: 1, reqd: 1 },
				from_employee: { read_only: 1, reqd: 0 },
				to_employee: { read_only: 0, reqd: 0 },
			};
		} else if (frm.doc.purpose === "Receipt") {
			fieldnames_to_be_altered = {
				target_location: { read_only: 0, reqd: 1 },
				source_location: { read_only: 1, reqd: 0 },
				from_employee: { read_only: 0, reqd: 0 },
				to_employee: { read_only: 1, reqd: 0 },
			};
		} else if (frm.doc.purpose === "Issue") {
			fieldnames_to_be_altered = {
				target_location: { read_only: 0, reqd: 0 },
				source_location: { read_only: 1, reqd: 0 },
				from_employee: { read_only: 1, reqd: 0 },
				to_employee: { read_only: 0, reqd: 1 },
			};
		}
		if (fieldnames_to_be_altered) {
			console.log("innnnnnnnnnnnnnnnn 2")
			Object.keys(fieldnames_to_be_altered).forEach((fieldname) => {
				let property_to_be_altered = fieldnames_to_be_altered[fieldname];
				Object.keys(property_to_be_altered).forEach((property) => {
					let value = property_to_be_altered[property];
					frm.fields_dict["assets"].grid.update_docfield_property(fieldname, property, value);
				});
			});
			frm.refresh_field("assets");
		}
	},
});

frappe.ui.form.off("Asset Movement Item", "asset");                     
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