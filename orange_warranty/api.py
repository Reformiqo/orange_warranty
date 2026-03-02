import frappe
from frappe import _
from frappe.utils import nowdate, getdate


@frappe.whitelist()
def set_replacement_serial(rma_name, new_serial_number):
	"""Set replacement serial. Validates item match and uniqueness."""
	rma = frappe.get_doc("RMA Request", rma_name)

	if not frappe.db.exists("Serial No", new_serial_number):
		frappe.throw(_("Serial No {0} does not exist.").format(new_serial_number))

	if new_serial_number == rma.serial_number:
		frappe.throw(_("Replacement serial must differ from faulty serial."))

	sn_item = frappe.db.get_value("Serial No", new_serial_number, "item_code")
	if sn_item != rma.item_code:
		frappe.throw(
			_("Serial {0} belongs to item {1}, not {2}.").format(
				new_serial_number, sn_item, rma.item_code
			)
		)

	rma.new_serial_number = new_serial_number
	rma.flags.ignore_validate_update_after_submit = True
	rma.save(ignore_permissions=True)


@frappe.whitelist()
def mark_faulty_received(rma_name, date_of_inward, returnable_to_parent):
	"""Mark faulty received. Triggers auto inward Stock Entry."""
	rma = frappe.get_doc("RMA Request", rma_name)

	if getdate(date_of_inward) > getdate(nowdate()):
		frappe.throw(_("Inward date cannot be in the future."))

	if returnable_to_parent not in ("Yes", "No - Discard"):
		frappe.throw(_("Please specify if part is returnable to parent."))

	rma.date_of_inward = date_of_inward
	rma.faulty_part_received = 1
	rma.returnable_to_parent = returnable_to_parent
	rma.flags.ignore_validate_update_after_submit = True
	rma.save(ignore_permissions=True)


@frappe.whitelist()
def mark_returned_to_parent(rma_name, returned_date, tracking=None):
	"""Mark faulty part returned to manufacturer."""
	rma = frappe.get_doc("RMA Request", rma_name)

	if getdate(returned_date) > getdate(nowdate()):
		frappe.throw(_("Return date cannot be in the future."))

	rma.returned_to_parent_date = returned_date
	rma.parent_return_tracking = tracking or ""
	rma.flags.ignore_validate_update_after_submit = True
	rma.save(ignore_permissions=True)


@frappe.whitelist()
def close_rma(rma_name):
	"""Close RMA. Triggers serial swap on Warranty Registration."""
	rma = frappe.get_doc("RMA Request", rma_name)

	if rma.rma_status not in ("Faulty Received", "Returned to Parent", "Discarded"):
		frappe.throw(
			_("RMA can only be closed from Faulty Received, Returned, or Discarded status.")
		)

	rma.rma_status = "Closed"
	rma.flags.ignore_validate_update_after_submit = True
	rma.save(ignore_permissions=True)
