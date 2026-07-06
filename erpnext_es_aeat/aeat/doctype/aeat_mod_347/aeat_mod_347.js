// Copyright (c) 2026, BIT Technologies GmbH and contributors
// License: AGPL-3.0-or-later
frappe.ui.form.on('AEAT Mod 347', {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.add_custom_button(__('Calcular'), () => {
            frappe.call({
                method: 'frappe.handler.run_doc_method',
                args: { docs: frm.doc, method: 'calculate', args: null },
                freeze: true,
                freeze_message: __('Calculando…'),
                callback: (r) => { if (!r.exc) frm.reload_doc(); }
            });
        }).addClass('btn-primary');

        const calculated = frm.doc.calculation_state === 'Calculated' || frm.doc.docstatus === 1;
        if (calculated) {
            frm.add_custom_button(__('Generar fichero BOE'), () => {
                frappe.call({
                    method: 'frappe.handler.run_doc_method',
                    args: { docs: frm.doc, method: 'export_boe', args: null },
                    freeze: true,
                    freeze_message: __('Generando fichero…'),
                    callback: (r) => {
                        if (r && r.message) {
                            const a = document.createElement('a');
                            a.href = r.message;
                            a.download = r.message.split('/').pop();
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                        }
                        frm.reload_doc();
                    }
                });
            });
        }
    }
});

