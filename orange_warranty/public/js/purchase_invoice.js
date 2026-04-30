frappe.ui.form.on("Purchase Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 2 || frm.is_new()) return;

		frm.add_custom_button(__("Recalculate EMI"), () => show_emi_dialog_pi(frm), __("Actions"));
	},

	validate(frm) {
		validate_payment_schedule_pi(frm);
	},
});

function show_emi_dialog_pi(frm) {
	// Pre-check: block if any EMI row already has payments
	let paid_row = (frm.doc.payment_schedule || []).find(
		(r) =>
			r.custom_payment_type !== "Advance" &&
			r.custom_payment_type !== "Delivery" &&
			flt(r.paid_amount) > 0,
	);
	if (paid_row) {
		frappe.msgprint(
			__("Cannot recalculate: row {0} already has paid amount {1}.", [
				paid_row.idx,
				format_currency(paid_row.paid_amount, frm.doc.currency),
			]),
		);
		return;
	}

	// Detect untagged rows so we can offer inline tagging in the dialog
	let untagged_rows = (frm.doc.payment_schedule || []).filter((r) => !r.custom_payment_type);

	// Calculate summary values from currently-tagged rows
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

	if (outstanding <= 0 && untagged_rows.length === 0) {
		frappe.msgprint(
			__(
				"No outstanding amount to split into EMIs. Advance + Delivery covers the full Grand Total.",
			),
		);
		return;
	}

	let tagging_html = build_tagging_html_pi(frm, untagged_rows);

	let dialog_fields = [
		{
			fieldtype: "HTML",
			fieldname: "summary_html",
			options: `
				<div class="mb-3">
					<p><strong>${__("Grand Total")}:</strong> ${format_currency(grand_total, frm.doc.currency)}</p>
					<p><strong>${__("Advance + Delivery")}:</strong> ${format_currency(
						protected_amount,
						frm.doc.currency,
					)} (${flt(protected_portion, 2)}%)</p>
				</div>
			`,
		},
	];

	if (tagging_html) {
		dialog_fields.push({
			fieldtype: "HTML",
			fieldname: "tagging_html",
			options: tagging_html,
		});
	}

	dialog_fields.push(
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
	);

	let d = new frappe.ui.Dialog({
		title: __("Recalculate EMI"),
		fields: dialog_fields,
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

			let row_tags = collect_row_tags_pi(d);
			if (untagged_rows.length && Object.keys(row_tags).length !== untagged_rows.length) {
				frappe.msgprint(__("Please assign a Payment Type to every untagged row."));
				return;
			}

			let emi_amount = flt(outstanding / values.num_emis, 2);
			let msg = __(
				"This will replace all EMI rows with {0} installments of approx. {1} starting {2}.",
				[
					values.num_emis,
					format_currency(emi_amount, frm.doc.currency),
					values.start_date,
				],
			);

			frappe.confirm(msg, () => {
				let args = {
					doctype: "Purchase Invoice",
					docname: frm.doc.name,
					num_emis: values.num_emis,
					start_date: values.start_date,
					day_of_month: values.day_of_month,
					cascade_to_pi: 0,
				};
				if (Object.keys(row_tags).length) {
					args.row_tags = JSON.stringify(row_tags);
				}

				frappe.xcall("orange_warranty.api_emi.recalculate_emi", args).then((r) => {
					d.hide();
					frappe.show_alert(
						{
							message: __("EMI schedule updated: {0} installments of {1}", [
								r.num_emis,
								format_currency(r.emi_base_amount, frm.doc.currency),
							]),
							indicator: "green",
						},
						5,
					);
					frm.reload_doc();
				});
			});
		},
	});

	d.show();
	wire_tagging_dialog_pi(d);
}

function build_tagging_html_pi(frm, untagged_rows) {
	if (!untagged_rows.length) return "";

	let rows_html = untagged_rows
		.map((r) => {
			let desc = frappe.utils.escape_html(r.description || r.payment_term || "");
			let amt = format_currency(r.payment_amount, frm.doc.currency);
			let pct = flt(r.invoice_portion, 2);
			return `
				<tr>
					<td style="white-space: nowrap;">#${r.idx}</td>
					<td>${desc}</td>
					<td class="text-right">${pct}%</td>
					<td class="text-right">${amt}</td>
					<td>
						<select class="form-control input-sm emi-row-tag" data-row-name="${frappe.utils.escape_html(
							r.name,
						)}">
							<option value="EMI" selected>${__("EMI")}</option>
							<option value="Advance">${__("Advance")}</option>
							<option value="Delivery">${__("Delivery")}</option>
						</select>
					</td>
				</tr>
			`;
		})
		.join("");

	return `
		<div class="mb-3" style="border:1px solid var(--border-color); padding:10px; border-radius:6px; background: var(--bg-light-gray);">
			<p><strong>${__("Tag {0} untagged row(s)", [untagged_rows.length])}</strong></p>
			<p class="text-muted small">${__(
				"Rows tagged 'EMI' will be replaced. 'Advance' and 'Delivery' rows are preserved.",
			)}</p>
			<table class="table table-condensed" style="margin-bottom: 8px;">
				<thead>
					<tr>
						<th>${__("Row")}</th>
						<th>${__("Description")}</th>
						<th class="text-right">${__("Portion")}</th>
						<th class="text-right">${__("Amount")}</th>
						<th>${__("Payment Type")}</th>
					</tr>
				</thead>
				<tbody>${rows_html}</tbody>
			</table>
			<button type="button" class="btn btn-default btn-xs emi-tag-all-emi">${__("Tag all as EMI")}</button>
		</div>
	`;
}

function wire_tagging_dialog_pi(d) {
	d.$wrapper.on("click", ".emi-tag-all-emi", function (e) {
		e.preventDefault();
		d.$wrapper.find("select.emi-row-tag").val("EMI");
	});
}

function collect_row_tags_pi(d) {
	let tags = {};
	d.$wrapper.find("select.emi-row-tag").each(function () {
		let name = $(this).attr("data-row-name");
		let val = $(this).val();
		if (name && val) tags[name] = val;
	});
	return tags;
}

function validate_payment_schedule_pi(frm) {
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
			__("Payment Schedule portions sum to {0}%, expected 100%.", [flt(total_portion, 3)]),
		);
		frappe.validated = false;
	}

	if (Math.abs(total_amount - flt(frm.doc.grand_total)) > 1) {
		frappe.msgprint(
			__("Payment Schedule amounts sum to {0}, expected {1}.", [
				format_currency(total_amount, frm.doc.currency),
				format_currency(frm.doc.grand_total, frm.doc.currency),
			]),
		);
		frappe.validated = false;
	}
}
