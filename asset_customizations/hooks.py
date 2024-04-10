app_name = "asset_customizations"
app_title = "asset_modification"
app_publisher = "manoj"
app_description = "asset_modification"
app_email = "manoj@8848digital.com"
app_license = "MIT"

# include js, css files in header of desk.html
# app_include_css = "/assets/asset_customizations/css/asset_customizations.css"
# app_include_js = "/assets/asset_customizations/js/asset_customizations.js"

# include js, css files in header of web template
# web_include_css = "/assets/asset_customizations/css/asset_customizations.css"
# web_include_js = "/assets/asset_customizations/js/asset_customizations.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "asset_customizations/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "asset_customizations.utils.jinja_methods",
# 	"filters": "asset_customizations.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "asset_customizations.install.before_install"
# after_install = "asset_customizations.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "asset_customizations.uninstall.before_uninstall"
# after_uninstall = "asset_customizations.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "asset_customizations.utils.before_app_install"
# after_app_install = "asset_customizations.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "asset_customizations.utils.before_app_uninstall"
# after_app_uninstall = "asset_customizations.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "asset_customizations.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"asset_customizations.tasks.all"
# 	],
# 	"daily": [
# 		"asset_customizations.tasks.daily"
# 	],
# 	"hourly": [
# 		"asset_customizations.tasks.hourly"
# 	],
# 	"weekly": [
# 		"asset_customizations.tasks.weekly"
# 	],
# 	"monthly": [
# 		"asset_customizations.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "asset_customizations.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "asset_customizations.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "asset_customizations.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["asset_customizations.utils.before_request"]
# after_request = ["asset_customizations.utils.after_request"]

# Job Events
# ----------
# before_job = ["asset_customizations.utils.before_job"]
# after_job = ["asset_customizations.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"asset_customizations.auth.validate"
# ]

doctype_js = {
	"Asset": "asset_modification/customizations/doc_events/asset.js",
	"Asset Value Adjustment": "public/js/asset_value_adjustment_override.js",
}

from erpnext.assets.doctype.asset.asset import Asset

from asset_customizations.asset_modification.customizations.asset_value_adjustment.doc_events.asset_modify import (
	on_submit,
)

Asset.on_submit = on_submit

# Overriding Asset Capitalization Doctype to change the Credit Account in Assets Table
from erpnext.assets.doctype.asset_capitalization.asset_capitalization import AssetCapitalization

from asset_customizations.asset_modification.customizations.asset_capitalization.doc_events.asset_capitalization_target_account import (
	get_gl_entries_for_consumed_asset_items,
)

AssetCapitalization.get_gl_entries_for_consumed_asset_items = (
	get_gl_entries_for_consumed_asset_items
)

from erpnext.assets.doctype.asset_value_adjustment.asset_value_adjustment import (
	AssetValueAdjustment,
)

from asset_customizations.asset_modification.customizations.asset_value_adjustment.doc_events.asset_value_adjustment_override import (
	make_depreciation_entry_override,
	set_difference_amount_override,
)

AssetValueAdjustment.set_difference_amount = set_difference_amount_override
AssetValueAdjustment.make_depreciation_entry = make_depreciation_entry_override

fixtures = [{"dt": "Custom Field", "filters": [["module", "=", "asset_modification"]]}]
