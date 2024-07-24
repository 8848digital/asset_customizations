import frappe
from datetime import datetime
from frappe import _
from erpnext.assets.doctype.asset_repair.asset_repair import AssetRepair
from frappe.utils import get_link_to_form
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity

def before_save(self, method=None):
    repair_cost_value = 0
    for data in self.purchase_invoice_data:
        repair_cost_value += data.repair_cost
    
    self.repair_cost = repair_cost_value

def on_submit(self, method=None):
    details = []
    debit_value = 0

    for account in self.purchase_invoice_data:
        account_data = {}
        purchase_invoice_data = frappe.get_doc("Purchase Invoice", account.purchase_invoice)
        for item in purchase_invoice_data.items:
            account_data["account"] = item.get("expense_account")
            account_data["debit_in_account_currency"] = 0
            account_data["credit_in_account_currency"] = purchase_invoice_data.total
        debit_value += purchase_invoice_data.total
        details.append(account_data)

    query = get_fixed_asset_account(self)

    for item in query:
        fixed_asset_account = item.fixed_asset_account
    
    account_debit_data = {"account" : fixed_asset_account, "debit_in_account_currency" : debit_value, "credit_in_account_currency" : 0}
    details.append(account_debit_data)

    account_details = get_unique_accounts(details)
    if self.capitalize_repair_cost == 1:
        create_gl_entry(self, account_details)


def get_fixed_asset_account(self):
    asset = frappe.qb.DocType('Asset')
    asset_cat = frappe.qb.DocType('Asset Category')
    asset_cat_acc = frappe.qb.DocType('Asset Category Account')

    query = frappe.qb.from_(asset)\
            .left_join(asset_cat).on(asset_cat.name == asset.asset_category)\
            .left_join(asset_cat_acc).on(asset_cat_acc.parent == asset_cat.name)\
            .select(asset_cat_acc.fixed_asset_account)\
            .where(asset.name == self.asset).run(as_dict=True)
    return query


def get_unique_accounts(pi_data):
    result = []
    account_details = []
    for item in pi_data:
        if item["account"] not in account_details:
            account_details.append(item["account"])
            
    for detail in account_details:
        account_data = {}
        debit_in_account_currency = 0
        credit_in_account_currency = 0
        
        for entry in pi_data:
            if entry["account"] == detail:
                debit_in_account_currency += entry["debit_in_account_currency"]
                credit_in_account_currency += entry["credit_in_account_currency"]
        account_data["account"] = detail
        account_data["debit_in_account_currency"] = debit_in_account_currency
        account_data["credit_in_account_currency"] = credit_in_account_currency
        result.append(account_data) 
    return result

def create_journal_entry(self, account_details):
    journal_entry_doc = frappe.new_doc("Journal Entry")
    journal_entry_doc.voucher_type = "Journal Entry"
    journal_entry_doc.posting_date = datetime.now().date()
    journal_entry_doc.company = self.company
    for record in account_details:
        journal_entry_doc.append(
            "accounts",
            {
                "account": record["account"],
                "debit_in_account_currency": record["debit_in_account_currency"],
                "credit_in_account_currency": record["credit_in_account_currency"],
            },
        )
    journal_entry_doc.save(ignore_permissions=True)
    
    
def create_gl_entry(self, account_details):
    account_against = {}

    for entry in account_details:
        if entry['credit_in_account_currency'] > 0:
            credit_account = entry['account']
            for counterpart in account_details:
                if counterpart['debit_in_account_currency'] > 0:
                    debit_account = counterpart['account']
                    account_against[credit_account] = debit_account
                    account_against[debit_account] = credit_account


    for entry in account_details:
        ge = frappe.new_doc("GL Entry")
        ge.account = entry["account"]
        ge.debit = entry["debit_in_account_currency"]
        ge.credit = entry["credit_in_account_currency"]
        ge.debit_in_account_currency = entry["debit_in_account_currency"]
        ge.credit_in_account_currency = entry["credit_in_account_currency"]
        ge.against = account_against[entry["account"]]
        ge.voucher_type = self.doctype
        ge.voucher_no = self.name
        ge.company = self.company
        ge.debit_in_transaction_currency = entry["debit_in_account_currency"]
        ge.credit_in_transaction_currency = entry["credit_in_account_currency"]
        ge.posting_date = datetime.now().date()
        ge.cost_center = self.cost_center

        fiscal_year = frappe.qb.DocType('Fiscal Year')
        fiscal_year_query = frappe.qb.from_(fiscal_year)\
                            .select(fiscal_year.name)\
                            .where((fiscal_year.year_start_date <= datetime.now().date()) & (fiscal_year.year_end_date >= datetime.now().date())).run(as_dict=True)
        for data in fiscal_year_query:
            fiscal_year_value = data["name"]
        ge.fiscal_year = fiscal_year_value
        ge.save(ignore_permissions=True)

class AssetRepairMaster(AssetRepair):
    def before_submit(self):
        self.check_repair_status()

        self.asset_doc.flags.increase_in_asset_value_due_to_repair = False

        if self.get("stock_consumption") or self.get("capitalize_repair_cost"):
            self.asset_doc.flags.increase_in_asset_value_due_to_repair = True

            self.increase_asset_value()

            if self.capitalize_repair_cost:
                self.asset_doc.total_asset_cost += self.repair_cost
                self.asset_doc.additional_asset_cost += self.repair_cost

            if self.get("stock_consumption"):
                self.check_for_stock_items_and_warehouse()
                self.decrease_stock_quantity()
            if self.get("capitalize_repair_cost"):
                if self.asset_doc.calculate_depreciation and self.increase_in_asset_life:
                    self.modify_depreciation_schedule()

                notes = _(
                    "This schedule was created when Asset {0} was repaired through Asset Repair {1}."
                ).format(
                    get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
                    get_link_to_form(self.doctype, self.name),
                )
                self.asset_doc.flags.ignore_validate_update_after_submit = True
                self.asset_doc.save()

                add_asset_activity(
                    self.asset,
                    _("Asset updated after completion of Asset Repair {0}").format(
                        get_link_to_form("Asset Repair", self.name)
                    ),
                )

    def before_cancel(self):
        self.asset_doc = frappe.get_doc("Asset", self.asset)

        self.asset_doc.flags.increase_in_asset_value_due_to_repair = False

        if self.get("stock_consumption") or self.get("capitalize_repair_cost"):
            self.asset_doc.flags.increase_in_asset_value_due_to_repair = True

            self.decrease_asset_value()

            if self.capitalize_repair_cost:
                self.asset_doc.total_asset_cost -= self.repair_cost
                self.asset_doc.additional_asset_cost -= self.repair_cost

            if self.get("capitalize_repair_cost"):
                self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")
                if self.asset_doc.calculate_depreciation and self.increase_in_asset_life:
                    self.revert_depreciation_schedule_on_cancellation()

                notes = _(
                    "This schedule was created when Asset {0}'s Asset Repair {1} was cancelled."
                ).format(
                    get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
                    get_link_to_form(self.doctype, self.name),
                )
                self.asset_doc.flags.ignore_validate_update_after_submit = True
                self.asset_doc.save()

                add_asset_activity(
                    self.asset,
                    _("Asset updated after cancellation of Asset Repair {0}").format(
                        get_link_to_form("Asset Repair", self.name)
                    ),
                )