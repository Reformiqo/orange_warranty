frappe.ui.form.on("RMA Request", {
	refresh(frm) {
		// Dashboard headline
		if (frm.doc.is_under_warranty)
			frm.dashboard.set_headline(
				__("Under Warranty — {0}", [frm.doc.warranty_type]),
				"green"
			);
		else if (frm.doc.warranty_end_date)
			frm.dashboard.set_headline(__("Warranty Expired"), "red");

		// Serial swap info
		if (frm.doc.old_serial_number && frm.doc.new_serial_number)
			frm.dashboard.add_comment(
				__("Serial: {0} → {1}", [
					frm.doc.old_serial_number,
					frm.doc.new_serial_number,
				]),
				"blue",
				true
			);

		// Filter new_serial_number by item + warehouse
		frm.set_query("new_serial_number", () => ({
			filters: {
				item_code: frm.doc.item_code,
				warehouse: frm.doc.warehouse,
			},
		}));

		if (frm.doc.docstatus !== 1) return;

		// === ACTION BUTTONS (call APIs) ===

		// 1. Enter replacement serial
		if (frm.doc.rma_status === "Approved" && !frm.doc.new_serial_number) {
			frm.add_custom_button(
				__("Enter Replacement Serial"),
				() => {
					frappe.prompt(
						[
							{
								fieldname: "sn",
								fieldtype: "Link",
								options: "Serial No",
								label: __("New Serial Number"),
								reqd: 1,
								get_query: () => ({
									filters: {
										item_code: frm.doc.item_code,
										warehouse: frm.doc.warehouse,
									},
								}),
							},
						],
						(v) => {
							frappe.xcall(
								"orange_warranty.api.set_replacement_serial",
								{
									rma_name: frm.doc.name,
									new_serial_number: v.sn,
								}
							).then(() => frm.reload_doc());
						},
						__("Replacement Serial"),
						__("Confirm")
					);
				},
				__("Actions")
			);
		}

		// 2. Receive faulty part
		if (
			["Approved", "Replacement Dispatched"].includes(
				frm.doc.rma_status
			) &&
			!frm.doc.faulty_part_received
		) {
			frm.add_custom_button(
				__("Receive Faulty Part"),
				() => {
					frappe.prompt(
						[
							{
								fieldname: "dt",
								fieldtype: "Date",
								label: __("Date Received"),
								default: frappe.datetime.get_today(),
								reqd: 1,
							},
							{
								fieldname: "ret",
								fieldtype: "Select",
								label: __("Returnable to Parent?"),
								options: "\nYes\nNo - Discard",
								reqd: 1,
							},
						],
						(v) => {
							frappe.xcall(
								"orange_warranty.api.mark_faulty_received",
								{
									rma_name: frm.doc.name,
									date_of_inward: v.dt,
									returnable_to_parent: v.ret,
								}
							).then(() => frm.reload_doc());
						},
						__("Receive Faulty"),
						__("Confirm")
					);
				},
				__("Actions")
			);
		}

		// 3. Return to parent
		if (
			frm.doc.faulty_part_received &&
			frm.doc.returnable_to_parent === "Yes" &&
			!frm.doc.returned_to_parent_date
		) {
			frm.add_custom_button(
				__("Return to Parent"),
				() => {
					frappe.prompt(
						[
							{
								fieldname: "dt",
								fieldtype: "Date",
								label: __("Return Date"),
								default: frappe.datetime.get_today(),
								reqd: 1,
							},
							{
								fieldname: "trk",
								fieldtype: "Data",
								label: __("Tracking Number"),
							},
						],
						(v) => {
							frappe.xcall(
								"orange_warranty.api.mark_returned_to_parent",
								{
									rma_name: frm.doc.name,
									returned_date: v.dt,
									tracking: v.trk,
								}
							).then(() => frm.reload_doc());
						},
						__("Return to Parent"),
						__("Confirm")
					);
				},
				__("Actions")
			);
		}

		// 4. Close RMA
		if (
			["Faulty Received", "Returned to Parent", "Discarded"].includes(
				frm.doc.rma_status
			)
		) {
			frm.add_custom_button(
				__("Close RMA"),
				() => {
					frappe.confirm(
						__("Close this RMA? Serial swap will be applied."),
						() => {
							frappe.xcall("orange_warranty.api.close_rma", {
								rma_name: frm.doc.name,
							}).then(() => frm.reload_doc());
						}
					);
				},
				__("Actions")
			);
		}

		// === QUICK-CREATE BUTTONS (open pre-filled standard forms) ===

		// Send faulty to manufacturer
		if (
			frm.doc.replacement_source === "Own Stock" &&
			frm.doc.faulty_part_received &&
			!frm.doc.sent_to_manufacturer_se
		) {
			frm.add_custom_button(
				__("Create Send-to-Mfg SE"),
				() => {
					frappe.new_doc("Stock Entry", {
						stock_entry_type: "Material Issue",
						custom_rma_reference: frm.doc.name,
						custom_rma_purpose: "Send to Manufacturer",
					});
				},
				__("Create")
			);
		}

		// Replenishment from manufacturer
		if (
			frm.doc.replacement_source === "Own Stock" &&
			frm.doc.sent_to_manufacturer_date &&
			!frm.doc.replenishment_pr
		) {
			frm.add_custom_button(
				__("Create Replenishment PR"),
				() => {
					frappe.new_doc("Purchase Receipt", {
						supplier: "Hanglory",
						custom_rma_reference: frm.doc.name,
					});
				},
				__("Create")
			);
		}
	},
});
