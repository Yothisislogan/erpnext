frappe.ui.form.on('Lead', {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Decode VINs / Refresh Follow-Ups'), () => {
				frm.save();
			}, __('WIT Insurance'));
		}

		if (frm.doc.custom_missing_information) {
			frm.dashboard.add_comment(__('Missing intake info: {0}', [frm.doc.custom_missing_information]), 'orange', true);
		}
	},

	custom_policy_type(frm) {
		if (frm.doc.custom_policy_type === 'Personal Auto' || frm.doc.custom_policy_type === 'Commercial Auto') {
			frm.toggle_display('custom_wit_vehicles', true);
		}
	}
});
