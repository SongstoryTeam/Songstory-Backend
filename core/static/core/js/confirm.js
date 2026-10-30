(() => {
    const dialog = document.querySelector('[data-confirm-dialog]');
    if (!dialog) return;

    const CONFIRMED_VALUE = 'confirm';
    const BYPASS_ATTRIBUTE = 'data-confirmed';
    const slot = (name) => dialog.querySelector(`[data-confirm-${name}]`);
    const title = slot('title');
    const message = slot('message');
    const action = slot('action');

    function originOf(form, submitter) {
        return submitter && submitter.hasAttribute('data-confirm') ? submitter : form;
    }

    function submitConfirmed(form, submitter) {
        form.setAttribute(BYPASS_ATTRIBUTE, '');
        try {
            form.requestSubmit(submitter || undefined);
        } finally {
            form.removeAttribute(BYPASS_ATTRIBUTE);
        }
    }

    function ask(form, submitter, origin) {
        const {confirmTitle, confirmMessage, confirmAction} = origin.dataset;
        title.textContent = confirmTitle;
        message.textContent = confirmMessage || '';
        message.hidden = !confirmMessage;
        action.textContent = confirmAction;
        dialog.returnValue = '';
        dialog.addEventListener(
            'close',
            () => {
                if (dialog.returnValue === CONFIRMED_VALUE) submitConfirmed(form, submitter);
            },
            {once: true},
        );
        dialog.showModal();
    }

    document.addEventListener(
        'submit',
        (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement) || form.hasAttribute(BYPASS_ATTRIBUTE)) return;
            const origin = originOf(form, event.submitter);
            if (!origin.hasAttribute('data-confirm')) return;
            event.preventDefault();
            ask(form, event.submitter, origin);
        },
        true,
    );
})();
