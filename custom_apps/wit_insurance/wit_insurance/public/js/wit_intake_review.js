frappe.ui.form.on('WIT Intake Review', {
	refresh(frm) {
		add_review_banner(frm);

		if (!frm.is_new() && frm.doc.status === 'Pending Review') {
			frm.add_custom_button(__('Approve to Lead'), () => {
				frappe.call({
					method: 'wit_insurance.intake_review.approve_intake_review',
					args: { review_name: frm.doc.name },
					callback(response) {
						if (response.message && response.message.lead) {
							frappe.show_alert({ message: __('Lead created/updated'), indicator: 'green' });
							frm.reload_doc();
						}
					}
				});
			}, __('We Insure Things'));

			frm.add_custom_button(__('Reject'), () => {
				frappe.prompt(
					[{ fieldname: 'reason', label: __('Reason'), fieldtype: 'Small Text' }],
					(values) => {
						frappe.call({
							method: 'wit_insurance.intake_review.reject_intake_review',
							args: { review_name: frm.doc.name, reason: values.reason },
							callback() {
								frappe.show_alert({ message: __('Review rejected'), indicator: 'red' });
								frm.reload_doc();
							}
						});
					},
					__('Reject Intake Review'),
					__('Reject')
				);
			}, __('We Insure Things'));
		}

		if (frm.doc.converted_lead) {
			frm.add_custom_button(__('Open Lead'), () => {
				frappe.set_route('Form', 'Lead', frm.doc.converted_lead);
			}, __('We Insure Things'));
		}
	}
});

function add_review_banner(frm) {
	if (frm.dashboard.wrapper.find('.wit-insurance-banner').length) {
		return;
	}

	const status = frm.doc.status || 'Pending Review';
	frm.dashboard.wrapper.prepend(`
		<div class="wit-insurance-banner">
			<strong>We Insure Things Intake Review</strong><br>
			<small>Status: ${frappe.utils.escape_html(status)}. Review parsed info before converting to a Lead.</small>
		</div>
	`);
}
