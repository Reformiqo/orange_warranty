frappe.ui.form.on("Warranty Registration", {
	refresh(frm) {
		frm.set_query("serial_number", () => ({
			filters: { item_code: frm.doc.item_code },
		}));

		if (!frm.is_new()) {
			frm.add_custom_button(__("Create RMA Request"), () => {
				frappe.new_doc("RMA Request", {
					warranty_registration: frm.doc.name,
				});
			});
		}
	},

	warranty_start_date(frm) {
		calc_end_date(frm);
	},

	item_code(frm) {
		calc_end_date(frm);
	},
});

function calc_end_date(frm) {
	if (frm.doc.item_code && frm.doc.warranty_start_date) {
		frappe.db.get_value("Item", frm.doc.item_code, "custom_warranty_months", (r) => {
			if (r && r.custom_warranty_months) {
				frm.set_value(
					"warranty_end_date",
					frappe.datetime.add_months(
						frm.doc.warranty_start_date,
						r.custom_warranty_months
					)
				);
			}
		});
	}
}
