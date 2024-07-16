import frappe
from frappe import ValidationError, _, msgprint
from frappe.contacts.doctype.address.address import render_address
from frappe.utils import cint, flt, getdate
from frappe.utils.data import nowtime

from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget
from erpnext.accounts.party import get_party_details
from erpnext.buying.utils import update_last_purchase_rate, validate_for_items
from erpnext.controllers.sales_and_purchase_return import get_rate_for_return
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import get_incoming_rate
from erpnext.controllers.buying_controller import get_asset_item_details
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt

class CustomPurchaseReceipt(PurchaseReceipt):
    def auto_make_assets(self, asset_items):
        if self.is_internal_supplier == 1:
            return
        
        items_data = get_asset_item_details(asset_items)
        messages = []
        
        # Get list of fields from Accounting Dimension
        fields = frappe.get_list("Accounting Dimension", pluck="name")
        
        # Transform field names to lowercase with underscores
        transformed_fields = {field: field.lower().replace(' ', '_') for field in fields}

        for d in self.items:
            data = {}
            data["cost_center"] = d.cost_center
            for original_field, transformed_field in transformed_fields.items():
                if hasattr(d, transformed_field):
                    data[transformed_field] = getattr(d, transformed_field)

            if d.is_fixed_asset:
                item_data = items_data.get(d.item_code)

                if item_data.get("auto_create_assets"):
                    # If asset has to be auto created
                    # Check for asset naming series
                    if item_data.get("asset_naming_series"):
                        created_assets = []
                        if item_data.get("is_grouped_asset"):
                            asset = self.make_asset(d, is_grouped_asset=True, **data)
                            created_assets.append(asset)
                        else:
                            for _qty in range(cint(d.qty)):
                                asset = self.make_asset(d, **data)
                                created_assets.append(asset)

                        if len(created_assets) > 5:
                            # Don't show asset form links if more than 5 assets are created
                            messages.append(
                                _("{} Assets created for {}").format(
                                    len(created_assets), frappe.bold(d.item_code)
                                )
                            )
                        else:
                            assets_link = list(
                                map(lambda d: frappe.utils.get_link_to_form("Asset", d), created_assets)
                            )
                            assets_link = frappe.bold(",".join(assets_link))

                            is_plural = "s" if len(created_assets) != 1 else ""
                            messages.append(
                                _("Asset{} {assets_link} created for {}").format(
                                    is_plural, frappe.bold(d.item_code), assets_link=assets_link
                                )
                            )
                    else:
                        frappe.throw(
                            _(
                                "Row {}: Asset Naming Series is mandatory for the auto creation for item {}"
                            ).format(d.idx, frappe.bold(d.item_code))
                        )
                else:
                    messages.append(
                        _("Assets not created for {0}. You will have to create asset manually.").format(
                            frappe.bold(d.item_code)
                        )
                    )

        for message in messages:
            frappe.msgprint(message, title="Success", indicator="green")

    def make_asset(self, row, is_grouped_asset=False, **kwargs):
        if not row.asset_location:
            frappe.throw(_("Row {0}: Enter location for the asset item {1}").format(row.idx, row.item_code))

        item_data = frappe.db.get_value(
            "Item", row.item_code, ["asset_naming_series", "asset_category"], as_dict=1
        )
        asset_quantity = row.qty if is_grouped_asset else 1
        purchase_amount = flt(row.valuation_rate) * asset_quantity

        asset_data = {
            "doctype": "Asset",
            "item_code": row.item_code,
            "asset_name": row.item_name,
            "naming_series": item_data.get("asset_naming_series") or "AST",
            "asset_category": item_data.get("asset_category"),
            "location": row.asset_location,
            "company": self.company,
            "supplier": self.supplier,
            "purchase_date": self.posting_date,
            "calculate_depreciation": 0,
            "purchase_amount": purchase_amount,
            "gross_purchase_amount": purchase_amount,
            "asset_quantity": asset_quantity,
            "purchase_receipt": self.name if self.doctype == "Purchase Receipt" else None,
            "purchase_invoice": self.name if self.doctype == "Purchase Invoice" else None,
            "cost_center": kwargs.get("cost_center") or None  # Assign cost_center from kwargs
        }

        # Add additional dynamic fields
        asset_data.update(kwargs)

        asset = frappe.get_doc(asset_data)

        asset.flags.ignore_validate = True
        asset.flags.ignore_mandatory = True
        asset.set_missing_values()
        asset.insert()

        return asset.name
