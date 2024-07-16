
frappe.ui.form.off("Asset Movement", "set_required_fields");
frappe.ui.form.on("Asset Movement", {
	refresh: function(frm) {
		if (!frm.doc.custom_journal_entry){
			frm.add_custom_button(__("Make Journal Entry"), function(){
				frappe.confirm('Are you sure you want to proceed?',
					() => {
						frappe.call({
							method: "asset_customizations.asset_modification.customizations.asset_movement.asset_movement.create_journal_entry",
							args: {
								"name": frm.doc.name,
								"transaction_date": frm.doc.transaction_date
							},
							callback: function (r) {
								frm.set_value("custom_journal_entry", r.message)
								frm.save("Submit")
							},
						});
					}
				)
			}, __("Create"));
		}
		frm.add_custom_button(__('Make Delivery Note'), function() {
			frappe.confirm('Are you sure you want to proceed?',
				() => {
					frappe.call({
						method: "asset_customizations.asset_modification.customizations.asset_movement.asset_movement.make_delivery_note",
						args: {
							"name": frm.doc.name,
							"transaction_date": frm.doc.transaction_date
						},
						callback: function (r) {
							frappe.model.with_doctype('Delivery Note', function() {
								var doc = frappe.model.get_new_doc('Delivery Note');
								doc.set_warehouse = 'Stores - AD';
								var items = r.message;
								var child = frappe.model.add_child(doc, 'items');

								items.forEach(function(item) {
									for (var key in item) {
										if (item.hasOwnProperty(key)) {
											child[key] = item[key];
										}
									}
								});
								frappe.set_route('Form', 'Delivery Note', doc.name);
							});
						},
					});
				}, () => {
					// action to perform if No is selected
			})
		}, __("Create"));
	},

	set_required_fields: (frm, cdt, cdn) => {
		let fieldnames_to_be_altered;
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