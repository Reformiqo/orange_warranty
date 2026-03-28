frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		if (frm.doc.docstatus === 2 || frm.is_new()) return;

		frm.add_custom_button(__("Recalculate EMI"), () => show_emi_dialog_po(frm), __("Actions"));
	},

	validate(frm) {
		validate_payment_schedule(frm);
	},
});

function show_emi_dialog_po(frm) {
	// Pre-check: block if any EMI row already has payments
	let paid_row = (frm.doc.payment_schedule || []).find(
		(r) =>
			r.custom_payment_type !== "Advance" &&
			r.custom_payment_type !== "Delivery" &&
			flt(r.paid_amount) > 0
	);
	if (paid_row) {
		frappe.msgprint(
			__("Cannot recalculate: row {0} already has paid amount {1}.", [
				paid_row.idx,
				format_currency(paid_row.paid_amount, frm.doc.currency),
			])
		);
		return;
	}

	// Calculate summary values
	let grand_total = flt(frm.doc.grand_total);
	let protected_amount = 0;
	let protected_portion = 0;

	(frm.doc.payment_schedule || []).forEach((r) => {
		if (r.custom_payment_type === "Advance" || r.custom_payment_type === "Delivery") {
			protected_amount += flt(r.payment_amount);
			protected_portion += flt(r.invoice_portion);
		}
	});

	let outstanding = flt(grand_total - protected_amount, 2);

	if (outstanding <= 0) {
		frappe.msgprint(
			__(
				"No outstanding amount to split into EMIs. Advance + Delivery covers the full Grand Total."
			)
		);
		return;
	}

	let d = new frappe.ui.Dialog({
		title: __("Recalculate EMI"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "summary_html",
				options: `
					<div class="mb-3">
						<p><strong>${__("Grand Total")}:</strong> ${format_currency(grand_total, frm.doc.currency)}</p>
						<p><strong>${__("Advance + Delivery")}:</strong> ${format_currency(
					protected_amount,
					frm.doc.currency
				)} (${flt(protected_portion, 2)}%)</p>
						<p><strong>${__("EMI Split Amount")}:</strong> ${format_currency(
					outstanding,
					frm.doc.currency
				)} (${flt(100 - protected_portion, 2)}%)</p>
					</div>
				`,
			},
			{
				fieldname: "num_emis",
				fieldtype: "Int",
				label: __("Number of EMIs"),
				default: 6,
				reqd: 1,
			},
			{
				fieldname: "start_date",
				fieldtype: "Date",
				label: __("Start Date"),
				default: frappe.datetime.add_months(frappe.datetime.nowdate(), 1),
				reqd: 1,
			},
			{
				fieldname: "day_of_month",
				fieldtype: "Int",
				label: __("Day of Month"),
				default: 10,
				reqd: 1,
				description: __("1-28"),
			},
			{
				fieldname: "cascade_to_pi",
				fieldtype: "Check",
				label: __("Also update linked Purchase Invoices"),
				default: 0,
			},
		],
		primary_action_label: __("Recalculate"),
		primary_action(values) {
			if (values.num_emis < 1) {
				frappe.msgprint(__("Number of EMIs must be at least 1."));
				return;
			}
			if (values.day_of_month < 1 || values.day_of_month > 28) {
				frappe.msgprint(__("Day of month must be between 1 and 28."));
				return;
			}

			let emi_amount = flt(outstanding / values.num_emis, 2);
			let msg = __(
				"This will replace all EMI rows with {0} installments of approx. {1} starting {2}.",
				[values.num_emis, format_currency(emi_amount, frm.doc.currency), values.start_date]
			);
			if (values.cascade_to_pi) {
				msg += "<br><br>" + __("This will also update linked Purchase Invoices.");
			}

			frappe.confirm(msg, () => {
				frappe
					.xcall("orange_warranty.api_emi.recalculate_emi", {
						doctype: "Purchase Order",
						docname: frm.doc.name,
						num_emis: values.num_emis,
						start_date: values.start_date,
						day_of_month: values.day_of_month,
						cascade_to_pi: values.cascade_to_pi ? 1 : 0,
					})
					.then((r) => {
						d.hide();
						frappe.show_alert(
							{
								message: __("EMI schedule updated: {0} installments of {1}", [
									r.num_emis,
									format_currency(r.emi_base_amount, frm.doc.currency),
								]),
								indicator: "green",
							},
							5
						);
						if (r.cascaded_invoices && r.cascaded_invoices.length) {
							frappe.show_alert(
								{
									message: __("Updated {0} linked Purchase Invoice(s).", [
										r.cascaded_invoices.length,
									]),
									indicator: "blue",
								},
								5
							);
						}
						if (r.skipped_invoices && r.skipped_invoices.length) {
							frappe.msgprint(
								__("Skipped {0} Purchase Invoice(s): {1}", [
									r.skipped_invoices.length,
									r.skipped_invoices.join(", "),
								])
							);
						}
						if (
							values.cascade_to_pi &&
							!(r.cascaded_invoices && r.cascaded_invoices.length) &&
							!(r.skipped_invoices && r.skipped_invoices.length)
						) {
							frappe.show_alert(
								{
									message: __("No linked Purchase Invoices found to update."),
									indicator: "orange",
								},
								5
							);
						}
						frm.reload_doc();
					});
			});
		},
	});

	d.show();
}

function validate_payment_schedule(frm) {
	let rows = frm.doc.payment_schedule || [];
	if (!rows.length) return;

	let total_portion = 0;
	let total_amount = 0;

	rows.forEach((r) => {
		total_portion += flt(r.invoice_portion);
		total_amount += flt(r.payment_amount);
	});

	if (Math.abs(total_portion - 100) > 0.01) {
		frappe.msgprint(
			__("Payment Schedule portions sum to {0}%, expected 100%.", [flt(total_portion, 3)])
		);
		frappe.validated = false;
	}

	if (Math.abs(total_amount - flt(frm.doc.grand_total)) > 1) {
		frappe.msgprint(
			__("Payment Schedule amounts sum to {0}, expected {1}.", [
				format_currency(total_amount, frm.doc.currency),
				format_currency(frm.doc.grand_total, frm.doc.currency),
			])
		);
		frappe.validated = false;
	}
}
