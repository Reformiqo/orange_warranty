import json

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate


@frappe.whitelist()
def set_replacement_serial(rma_name, new_serial_number):
	"""Set replacement serial. Validates item match and uniqueness."""
	rma = frappe.get_doc("RMA Request", rma_name)
	rma.check_permission("write")

	if not frappe.db.exists("Serial No", new_serial_number):
		frappe.throw(_("Serial No {0} does not exist.").format(new_serial_number))

	if new_serial_number == rma.serial_number:
		frappe.throw(_("Replacement serial must differ from faulty serial."))

	sn_item = frappe.db.get_value("Serial No", new_serial_number, "item_code")
	if sn_item != rma.item_code:
		frappe.throw(
			_("Serial {0} belongs to item {1}, not {2}.").format(new_serial_number, sn_item, rma.item_code)
		)

	# Validate serial is in stock (active)
	sn_status = frappe.db.get_value("Serial No", new_serial_number, "status")
	if sn_status != "Active":
		frappe.throw(
			_("Serial {0} is not Active (current status: {1}).").format(new_serial_number, sn_status)
		)

	rma.new_serial_number = new_serial_number
	rma.flags.ignore_validate_update_after_submit = True
	rma.save()


@frappe.whitelist()
def mark_faulty_received(rma_name, date_of_inward, returnable_to_parent):
	"""Mark faulty received. Triggers auto inward Stock Entry."""
	rma = frappe.get_doc("RMA Request", rma_name)
	rma.check_permission("write")

	if getdate(date_of_inward) > getdate(nowdate()):
		frappe.throw(_("Inward date cannot be in the future."))

	if returnable_to_parent not in ("Yes", "No - Discard"):
		frappe.throw(_("Please specify if part is returnable to parent."))

	rma.date_of_inward = date_of_inward
	rma.faulty_part_received = 1
	rma.returnable_to_parent = returnable_to_parent
	rma.flags.ignore_validate_update_after_submit = True
	rma.save()


@frappe.whitelist()
def mark_returned_to_parent(rma_name, returned_date, tracking=None):
	"""Mark faulty part returned to manufacturer."""
	rma = frappe.get_doc("RMA Request", rma_name)
	rma.check_permission("write")

	if getdate(returned_date) > getdate(nowdate()):
		frappe.throw(_("Return date cannot be in the future."))

	rma.returned_to_parent_date = returned_date
	rma.parent_return_tracking = tracking or ""
	rma.flags.ignore_validate_update_after_submit = True
	rma.save()


@frappe.whitelist()
def close_rma(rma_name):
	"""Close RMA. Triggers serial swap on Warranty Registration."""
	rma = frappe.get_doc("RMA Request", rma_name)
	rma.check_permission("write")

	if rma.rma_status not in ("Faulty Received", "Returned to Parent", "Discarded"):
		frappe.throw(_("RMA can only be closed from Faulty Received, Returned, or Discarded status."))

	rma.rma_status = "Closed"
	rma.flags.ignore_validate_update_after_submit = True
	rma.save()


@frappe.whitelist()
def get_credit_summary(customer, companies):
	"""Get credit summary data for a customer across selected companies."""
	if isinstance(companies, str):
		companies = json.loads(companies)

	if not companies:
		return {
			"outstanding_amount": 0,
			"overdue_30_days": 0,
			"credit_limit": 0,
			"payment_terms": "",
		}

	total_outstanding = 0
	total_overdue_30 = 0
	total_credit_limit = 0
	payment_terms_list = []

	for company in companies:
		# Outstanding amount from GL Entry
		outstanding = frappe.db.sql(
			"""
			SELECT IFNULL(SUM(debit) - SUM(credit), 0)
			FROM `tabGL Entry`
			WHERE party_type = 'Customer'
			AND party = %s
			AND company = %s
			AND is_cancelled = 0
			""",
			(customer, company),
		)
		total_outstanding += flt(outstanding[0][0]) if outstanding else 0

		# Overdue 0-30 days: sum outstanding per voucher where due_date is
		# within the last 30 days (overdue but not older than 30 days)
		today = nowdate()
		overdue_30 = frappe.db.sql(
			"""
			SELECT IFNULL(SUM(outstanding), 0) FROM (
				SELECT
					ple.against_voucher_no,
					SUM(ple.amount) as outstanding
				FROM `tabPayment Ledger Entry` ple
				WHERE ple.party_type = 'Customer'
				AND ple.party = %s
				AND ple.company = %s
				AND ple.delinked = 0
				GROUP BY ple.against_voucher_no
				HAVING outstanding > 0
				AND MIN(ple.due_date) < %s
				AND MIN(ple.due_date) >= %s
			) t
			""",
			(customer, company, today, add_days(today, -30)),
		)
		total_overdue_30 += flt(overdue_30[0][0]) if overdue_30 else 0

		# Credit limit from Customer Credit Limit child table
		credit_limit = frappe.db.get_value(
			"Customer Credit Limit",
			{"parent": customer, "parenttype": "Customer", "company": company},
			"credit_limit",
		)
		total_credit_limit += flt(credit_limit)

		# Payment terms from Customer
		payment_terms = frappe.db.get_value("Customer", customer, "payment_terms")
		if payment_terms and payment_terms not in payment_terms_list:
			payment_terms_list.append(payment_terms)

	return {
		"outstanding_amount": total_outstanding,
		"overdue_30_days": total_overdue_30,
		"credit_limit": total_credit_limit,
		"payment_terms": ", ".join(payment_terms_list),
	}


@frappe.whitelist()
def get_company_list():
	"""Get list of companies the user has access to."""
	return frappe.get_all("Company", pluck="name", order_by="name")
