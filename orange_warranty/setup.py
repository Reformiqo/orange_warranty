import frappe


def after_install():
	create_custom_roles()
	create_custom_fields()


def create_custom_roles():
	for role_name in ["RMA Manager", "RMA Director"]:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(ignore_permissions=True)


def create_custom_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	custom_fields = {
		"Serial No": [
			{
				"fieldname": "custom_warranty_type",
				"fieldtype": "Select",
				"label": "Warranty Type",
				"options": "Parent Company (Hanglory)\nOrange Warranty",
				"insert_after": "warranty_expiry_date",
				"module": "Orange Warranty",
			},
			{
				"fieldname": "custom_warranty_registration",
				"fieldtype": "Link",
				"label": "Warranty Registration",
				"options": "Warranty Registration",
				"read_only": 1,
				"insert_after": "custom_warranty_type",
				"module": "Orange Warranty",
			},
		],
		"Delivery Note": [
			{
				"fieldname": "custom_is_foc",
				"fieldtype": "Check",
				"label": "Is FOC Replacement",
				"default": "0",
				"insert_after": "is_return",
				"module": "Orange Warranty",
			},
			{
				"fieldname": "custom_rma_reference",
				"fieldtype": "Link",
				"label": "RMA Reference",
				"options": "RMA Request",
				"insert_after": "custom_is_foc",
				"module": "Orange Warranty",
			},
			{
				"fieldname": "custom_warranty_type",
				"fieldtype": "Select",
				"label": "Warranty Type",
				"options": "Parent Company (Hanglory)\nOrange Warranty",
				"depends_on": "eval:doc.custom_is_foc==1",
				"insert_after": "custom_rma_reference",
				"module": "Orange Warranty",
			},
		],
		"Stock Entry": [
			{
				"fieldname": "custom_rma_reference",
				"fieldtype": "Link",
				"label": "RMA Reference",
				"options": "RMA Request",
				"insert_after": "stock_entry_type",
				"module": "Orange Warranty",
			},
			{
				"fieldname": "custom_rma_purpose",
				"fieldtype": "Select",
				"label": "RMA Purpose",
				"options": "Faulty Inward\nSend to Manufacturer",
				"depends_on": "custom_rma_reference",
				"insert_after": "custom_rma_reference",
				"module": "Orange Warranty",
			},
		],
		"Purchase Receipt": [
			{
				"fieldname": "custom_rma_reference",
				"fieldtype": "Link",
				"label": "RMA Reference",
				"options": "RMA Request",
				"insert_after": "supplier",
				"module": "Orange Warranty",
			},
		],
		"Item": [
			{
				"fieldname": "custom_warranty_months",
				"fieldtype": "Int",
				"label": "Default Warranty Months",
				"non_negative": 1,
				"insert_after": "warranty_period",
				"module": "Orange Warranty",
			},
		],
		"Payment Schedule": [
			{
				"fieldname": "custom_payment_type",
				"fieldtype": "Select",
				"label": "Payment Type",
				"options": "\nAdvance\nDelivery\nEMI",
				"insert_after": "description",
				"in_list_view": 1,
				"module": "Orange Warranty",
			},
		],
	}

	create_custom_fields(custom_fields, update=True)
