frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Credit Summary"), () => {
				show_credit_summary(frm);
			});
		}
	},
});

function show_credit_summary(frm) {
	let d = new frappe.ui.Dialog({
		title: __("Credit Summary"),
		size: "large",
		fields: [
			{
				fieldname: "customer_name",
				fieldtype: "Data",
				label: __("Customer Name"),
				read_only: 1,
				default: frm.doc.customer_name,
			},
			{
				fieldname: "company",
				fieldtype: "MultiSelectList",
				label: __("Company"),
				get_data: function () {
					return frappe
						.xcall("orange_warranty.api.get_company_list")
						.then((companies) => {
							return companies.map((c) => ({
								value: c,
								description: c,
							}));
						});
				},
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "outstanding_amount",
				fieldtype: "Currency",
				label: __("Outstanding Amount"),
				read_only: 1,
				default: 0,
			},
			{
				fieldname: "current_so_amount",
				fieldtype: "Currency",
				label: __("Current SO Amount"),
				read_only: 1,
				default: frm.doc.grand_total,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "overdue_30_days",
				fieldtype: "Currency",
				label: __("Overdue Date + 30 Days Amount"),
				read_only: 1,
				default: 0,
			},
			{
				fieldname: "total_exposure",
				fieldtype: "Currency",
				label: __("Total Exposure"),
				read_only: 1,
				default: 0,
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "credit_limit",
				fieldtype: "Currency",
				label: __("Credit Limit"),
				read_only: 1,
				default: 0,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "payment_terms",
				fieldtype: "Data",
				label: __("Payment Terms"),
				read_only: 1,
			},
		],
	});

	d.show();

	// Auto-fetch for current company on load
	fetch_credit_data(d, frm.doc.customer, [frm.doc.company], frm.doc.grand_total);

	// Re-fetch when company selection changes
	d.fields_dict.company.$input &&
		d.fields_dict.company.$input.on("awesomplete-selectcomplete", () => {
			let companies = d.get_value("company") || [];
			if (companies.length) {
				fetch_credit_data(d, frm.doc.customer, companies, frm.doc.grand_total);
			}
		});

	// Also handle tag removal
	d.$wrapper.on("click", ".btn-remove", () => {
		setTimeout(() => {
			let companies = d.get_value("company") || [];
			if (companies.length) {
				fetch_credit_data(d, frm.doc.customer, companies, frm.doc.grand_total);
			} else {
				clear_credit_fields(d);
			}
		}, 100);
	});
}

function fetch_credit_data(dialog, customer, companies, so_amount) {
	frappe
		.xcall("orange_warranty.api.get_credit_summary", {
			customer: customer,
			companies: companies,
		})
		.then((data) => {
			dialog.set_value("outstanding_amount", data.outstanding_amount || 0);
			dialog.set_value("overdue_30_days", data.overdue_30_days || 0);
			dialog.set_value("credit_limit", data.credit_limit || 0);
			dialog.set_value("payment_terms", data.payment_terms || "");

			let total_exposure = (data.outstanding_amount || 0) + (so_amount || 0);
			dialog.set_value("total_exposure", total_exposure);
		});
}

function clear_credit_fields(dialog) {
	dialog.set_value("outstanding_amount", 0);
	dialog.set_value("overdue_30_days", 0);
	dialog.set_value("total_exposure", 0);
	dialog.set_value("credit_limit", 0);
	dialog.set_value("payment_terms", "");
}
