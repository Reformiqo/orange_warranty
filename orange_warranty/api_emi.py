import frappe
from frappe import _
from frappe.utils import flt, getdate, cint, add_months, get_last_day


ALLOWED_DOCTYPES = ("Purchase Order", "Purchase Invoice")
PROTECTED_TYPES = ("Advance", "Delivery")


@frappe.whitelist()
def recalculate_emi(doctype, docname, num_emis, start_date, day_of_month, cascade_to_pi=0):
	"""Recalculate EMI rows in the payment schedule of a Purchase Order or Purchase Invoice.

	Preserves Advance/Delivery rows and replaces all other rows with N equal monthly EMIs.
	"""
	num_emis = cint(num_emis)
	day_of_month = cint(day_of_month)
	cascade_to_pi = cint(cascade_to_pi)
	start_date = getdate(start_date)

	if doctype not in ALLOWED_DOCTYPES:
		frappe.throw(_("EMI recalculation is only supported for Purchase Order and Purchase Invoice."))
	if num_emis < 1:
		frappe.throw(_("Number of EMIs must be at least 1."))
	if not (1 <= day_of_month <= 28):
		frappe.throw(_("Day of month must be between 1 and 28."))

	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("write")

	result = _apply_emi_schedule(doc, num_emis, start_date, day_of_month)

	cascaded_invoices = []
	skipped_invoices = []

	if doctype == "Purchase Order" and cascade_to_pi:
		cascaded_invoices, skipped_invoices = _cascade_to_purchase_invoices(
			docname, num_emis, start_date, day_of_month
		)

	return {
		"success": True,
		"docname": docname,
		"num_emis": num_emis,
		"outstanding_amount": result["outstanding"],
		"emi_base_amount": result["emi_base_amount"],
		"cascaded_invoices": cascaded_invoices,
		"skipped_invoices": skipped_invoices,
		"total_rows": result["total_rows"],
	}


def _apply_emi_schedule(doc, num_emis, start_date, day_of_month):
	"""Core logic: partition rows, calculate EMIs, rebuild payment schedule."""
	protected_rows = []
	emi_rows = []

	for row in doc.payment_schedule:
		if row.custom_payment_type in PROTECTED_TYPES:
			protected_rows.append(row)
		else:
			emi_rows.append(row)

	# Block if any existing EMI row has been paid
	for row in emi_rows:
		if flt(row.paid_amount) > 0:
			frappe.throw(
				_("Cannot recalculate: row {0} ({1}) already has paid amount {2}.").format(
					row.idx, row.description or "", row.paid_amount
				)
			)

	# Calculate outstanding
	protected_amount = sum(flt(r.payment_amount) for r in protected_rows)
	protected_portion = sum(flt(r.invoice_portion) for r in protected_rows)

	outstanding = flt(flt(doc.grand_total) - protected_amount, 2)
	remaining_portion = flt(100.0 - protected_portion, 3)

	if outstanding <= 0:
		frappe.throw(_("No outstanding amount to split into EMIs. Outstanding: {0}").format(outstanding))

	# Calculate EMI amounts
	emi_base_amount = flt(outstanding / num_emis, 2)
	emi_base_portion = flt(remaining_portion / num_emis, 3)

	conversion_rate = flt(doc.conversion_rate or 1, 9)

	# Generate EMI dates
	emi_dates = _generate_emi_dates(start_date, num_emis, day_of_month)

	# Rebuild payment schedule
	doc.payment_schedule = []

	# Re-add protected rows
	for row in protected_rows:
		doc.append("payment_schedule", {
			"payment_term": row.payment_term,
			"description": row.description,
			"due_date": row.due_date,
			"invoice_portion": row.invoice_portion,
			"payment_amount": row.payment_amount,
			"outstanding": row.outstanding,
			"paid_amount": row.paid_amount,
			"base_payment_amount": row.base_payment_amount,
			"mode_of_payment": row.mode_of_payment,
			"custom_payment_type": row.custom_payment_type,
		})

	# Add new EMI rows
	for i in range(num_emis):
		is_last = i == num_emis - 1

		if is_last:
			amount = flt(outstanding - emi_base_amount * (num_emis - 1), 2)
			portion = flt(remaining_portion - emi_base_portion * (num_emis - 1), 3)
		else:
			amount = emi_base_amount
			portion = emi_base_portion

		doc.append("payment_schedule", {
			"description": "EMI {0} of {1}".format(i + 1, num_emis),
			"due_date": emi_dates[i],
			"invoice_portion": portion,
			"payment_amount": amount,
			"outstanding": amount,
			"paid_amount": 0,
			"base_payment_amount": flt(amount * conversion_rate, 2),
			"custom_payment_type": "EMI",
		})

	doc.flags.ignore_validate_update_after_submit = True
	doc.save()

	return {
		"outstanding": outstanding,
		"emi_base_amount": emi_base_amount,
		"total_rows": len(doc.payment_schedule),
	}


def _generate_emi_dates(start_date, num_emis, day_of_month):
	"""Generate monthly EMI dates, clamping day to month's max day."""
	dates = []
	for i in range(num_emis):
		raw_date = add_months(start_date, i)
		max_day = getdate(get_last_day(raw_date)).day
		clamped_day = min(day_of_month, max_day)
		emi_date = raw_date.replace(day=clamped_day)
		dates.append(emi_date)
	return dates


def _cascade_to_purchase_invoices(po_name, num_emis, start_date, day_of_month):
	"""Apply the same EMI schedule to all linked Purchase Invoices."""
	# Find linked PIs (not cancelled)
	pi_items = frappe.get_all(
		"Purchase Invoice Item",
		filters={"purchase_order": po_name, "docstatus": ["!=", 2]},
		fields=["distinct parent as name"],
	)

	pi_names = [row.name for row in pi_items]
	cascaded = []
	skipped = []

	for pi_name in pi_names:
		pi_doc = frappe.get_doc("Purchase Invoice", pi_name)

		# Check if any non-protected row has payments
		has_paid_emi = False
		for row in pi_doc.payment_schedule:
			if row.custom_payment_type not in PROTECTED_TYPES and flt(row.paid_amount) > 0:
				has_paid_emi = True
				break

		if has_paid_emi:
			skipped.append(pi_name)
			continue

		_apply_emi_schedule(pi_doc, num_emis, start_date, day_of_month)
		cascaded.append(pi_name)

	return cascaded, skipped
