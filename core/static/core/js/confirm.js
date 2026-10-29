(() => {
    const dialog = document.querySelector('[data-confirm-dialog]');
    if (!dialog) return;

    const CONFIRMED_VALUE = 'confirm';
    const BYPASS_ATTRIBUTE = 'data-confirmed';
    const slot = (name) => dialog.querySelector(`[data-confirm-${name}]`);
    const title = slot('title');
    const message = slot('message');
    const action = slot('action');

    function submitConfirmed(form) {
        form.setAttribute(BYPASS_ATTRIBUTE, '');
        form.requestSubmit();
        form.removeAttribute(BYPASS_ATTRIBUTE);
    }

    function ask(form) {
        title.textContent = form.dataset.confirmTitle;
        message.textContent = form.dataset.confirmMessage;
        action.textContent = form.dataset.confirmAction;
        dialog.returnValue = '';
        dialog.addEventListener(
            'close',
            () => {
                if (dialog.returnValue === CONFIRMED_VALUE) submitConfirmed(form);
            },
            {once: true},
        );
        dialog.showModal();
    }

    document.addEventListener(
        'submit',
        (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement) || !form.hasAttribute('data-confirm')) return;
            if (form.hasAttribute(BYPASS_ATTRIBUTE)) return;
            event.preventDefault();
            ask(form);
        },
        true,
    );
})();
