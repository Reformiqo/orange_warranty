app_name = "orange_warranty"
app_title = "Orange Warranty"
app_publisher = "Orange O Tech"
app_description = "Product Warranty and RMA Management"
app_email = "info@erpera.io"
app_license = "mit"

doctype_js = {
	"Sales Order": "public/js/sales_order.js",
	"Purchase Order": "public/js/purchase_order.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
}

doc_events = {
	"Delivery Note": {
		"validate": "orange_warranty.events.delivery_note.validate_foc"
	}
}

scheduler_events = {
	"daily_long": [
		"orange_warranty.tasks.daily_warranty_update"
	]
}

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Orange Warranty"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Orange Warranty"]]},
	{"dt": "Role", "filters": [["name", "in", ["RMA Manager", "RMA Director"]]]},
	{"dt": "Workflow", "filters": [["document_type", "=", "RMA Request"]]},
	{"dt": "Notification", "filters": [["module", "=", "Orange Warranty"]]},
]

after_install = "orange_warranty.setup.after_install"
