const dialog = document.querySelector('[data-confirm-dialog]');
const ACCEPT_VALUE = 'confirm';

const slots = {
    title: dialog?.querySelector('[data-confirm-title]'),
    message: dialog?.querySelector('[data-confirm-message]'),
    action: dialog?.querySelector('[data-confirm-action]'),
};

let pendingForm = null;

function openDialog(form) {
    pendingForm = form;
    slots.title.textContent = form.dataset.confirmTitle ?? '';
    slots.message.textContent = form.dataset.confirmMessage ?? '';
    slots.action.textContent = form.dataset.confirmAction ?? '';
    dialog.showModal();
}

document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!dialog || !(form instanceof HTMLFormElement) || !form.hasAttribute('data-confirm')) return;

    event.preventDefault();
    openDialog(form);
});

dialog?.addEventListener('close', () => {
    const form = pendingForm;
    const accepted = dialog.returnValue === ACCEPT_VALUE;
    pendingForm = null;
    dialog.returnValue = '';
    if (form && accepted) form.submit();
});

dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
});
