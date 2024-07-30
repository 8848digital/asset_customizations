import json

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
	get_allowed_types_from_settings,
)

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    AccountingDimension,
    get_accounting_dimensions
)

class CustomAccountingDimension(AccountingDimension):
    def after_insert(self):
        if frappe.flags.in_test:
            make_dimension_in_accounting_doctypes(doc=self)
        else:
            frappe.enqueue(
                make_dimension_in_accounting_doctypes, doc=self, queue="long", enqueue_after_commit=True
            )

    def on_trash(self):
        if frappe.flags.in_test:
            delete_accounting_dimension(doc=self)
        else:
            frappe.enqueue(delete_accounting_dimension, doc=self, queue="long", enqueue_after_commit=True)


def make_dimension_in_accounting_doctypes(doc, doclist=None):
    if not doclist:
        doclist = get_doctypes_with_dimensions()

    accounting_dimension_doctypes_asset_movement_item = ["Asset Movement Item"]

    doc_count = len(get_accounting_dimensions())
    count = 0
    repostable_doctypes = get_allowed_types_from_settings()

    for doctype in doclist:
        if (doc_count + 1) % 2 == 0:
            insert_after_field = "dimension_col_break"
        else:
            insert_after_field = "accounting_dimensions_section"

        set_source_dimension = "custom_source_column_break" if (doc_count + 1) % 2 != 0 else "accounting_dimensions_source"
        set_target_dimension = "custom_target_column_break" if (doc_count + 1) % 2 != 0 else "accounting_dimensions_target"
        
        if doctype in accounting_dimension_doctypes_asset_movement_item:
            create_from_and_target_field(doc, set_source_dimension, doctype, repostable_doctypes, set_target_dimension)

        else:
            df = {
                "fieldname": doc.fieldname,
                "label": doc.label,
                "fieldtype": "Link",
                "options": doc.document_type,
                "insert_after": insert_after_field,
                "owner": "Administrator",
                "allow_on_submit": 1 if doctype in repostable_doctypes else 0,
            }

            meta = frappe.get_meta(doctype, cached=False)
            fieldnames = [d.fieldname for d in meta.get("fields")]

            if df["fieldname"] not in fieldnames:
                create_custom_field(doctype, df, ignore_validate=True)

        count += 1
        frappe.publish_progress(count * 100 / len(doclist), title=_("Creating Dimensions..."))
        frappe.clear_cache(doctype=doctype)


def create_from_and_target_field(doc, set_source_dimension, doctype, repostable_doctypes, set_target_dimension):
    from_df = {
        "fieldname": "from_" + doc.fieldname,
        "label": "From " + doc.label,
        "fieldtype": "Link",
        "options": doc.document_type,
        "insert_after": set_source_dimension,
        "owner": "Administrator",
        "allow_on_submit": 1 if doctype in repostable_doctypes else 0,
        "read_only": 1
    }
    target_df = {
        "fieldname": "target_" + doc.fieldname,
        "label": "Target " + doc.label,
        "fieldtype": "Link",
        "options": doc.document_type,
        "insert_after": set_target_dimension,
        "owner": "Administrator",
        "allow_on_submit": 1 if doctype in repostable_doctypes else 0,
    }

    meta = frappe.get_meta(doctype, cached=False)
    fieldnames = [d.fieldname for d in meta.get("fields")]

    if from_df["fieldname"] not in fieldnames:
        create_custom_field(doctype, from_df, ignore_validate=True)

    if target_df["fieldname"] not in fieldnames:
        create_custom_field(doctype, target_df, ignore_validate=True)


def delete_accounting_dimension(doc):
	doclist = get_doctypes_with_dimensions()
	accounting_dimension_doctypes_asset_movement_item = ["Asset Movement Item"]

	for doctype in doclist:
		if doctype in accounting_dimension_doctypes_asset_movement_item:
			# Delete two custom fields for specified doctypes needing duplicates
			frappe.db.sql(
				"""
				DELETE FROM `tabCustom Field`
				WHERE fieldname IN (%s, %s)
				AND dt = %s""",
				("from_" + doc.fieldname, "target_" + doc.fieldname, doctype)
			)

			frappe.db.sql(
				"""
				DELETE FROM `tabProperty Setter`
				WHERE field_name IN (%s, %s)
				AND doc_type = %s""",
				("from_" + doc.fieldname, "target " + doc.fieldname, doctype)
			)
		else:
			# Delete a single custom field for other doctypes
			frappe.db.sql(
				"""
				DELETE FROM `tabCustom Field`
				WHERE fieldname = %s
				AND dt = %s""",
				(doc.fieldname, doctype)
			)

			frappe.db.sql(
				"""
				DELETE FROM `tabProperty Setter`
				WHERE field_name = %s
				AND doc_type = %s""",
				(doc.fieldname, doctype)
			)

	budget_against_property = frappe.get_doc("Property Setter", "Budget-budget_against-options")
	value_list = budget_against_property.value.split("\n")[3:]

	if doc.document_type in value_list:
		value_list.remove(doc.document_type)

	budget_against_property.value = "\nCost Center\nProject\n" + "\n".join(value_list)
	budget_against_property.save()

	for doctype in doclist:
		frappe.clear_cache(doctype=doctype)


def toggle_disabling(doc):
    doc = json.loads(doc)

    if doc.get("disabled"):
        df = {"read_only": 1}
    else:
        df = {"read_only": 0}

    doclist = get_doctypes_with_dimensions()
    accounting_dimension_doctypes_asset_movement_item = ["Asset Movement Item"]

    for doctype in doclist:
        field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": doc.get("fieldname")})
        if field:
            custom_field = frappe.get_doc("Custom Field", field)
            custom_field.update(df)
            custom_field.save()

        if doctype in accounting_dimension_doctypes_asset_movement_item:
            target_field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": "target_" + doc.get("fieldname")})
            from_field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": "from_" + doc.get("fieldname")})
            if target_field:
                custom_field_duplicate = frappe.get_doc("Custom Field", target_field)
                custom_field_duplicate.update(df)
                custom_field_duplicate.save()
            if from_field:
                custom_field_duplicate = frappe.get_doc("Custom Field", from_field)
                custom_field_duplicate.update(df)
                custom_field_duplicate.save()

        frappe.clear_cache(doctype=doctype)


def get_doctypes_with_dimensions():
	return frappe.get_hooks("accounting_dimension_doctypes_for_asset")