(() => {
    const root = document.querySelector('[data-book-wizard]');
    const {createWizard, createBookPreview, createBookLookup, searchApi, dom} = window.Songstery || {};
    if (!root || !createWizard || !createBookPreview || !createBookLookup || !searchApi) return;

    const FIRST_STEP = 0;

    const form = root.querySelector('[data-wizard-form]');
    const duplicateAlert = root.querySelector('[data-duplicate]');
    const copy = dom.readJson(root, '[data-book-copy]');
    const {title: titleInput, author_name: authorInput} = form.elements;

    const lookup = createBookLookup({root, form, searchApi, client: searchApi.createClient(root.dataset.suggestUrl)});

    function hideDuplicate() {
        duplicateAlert.hidden = true;
        duplicateAlert.removeAttribute('data-wizard-error');
        duplicateAlert.replaceChildren();
    }

    function showDuplicate({url, title}) {
        if (url) {
            const link = dom.element('a', 'text-accent', title);
            link.href = url;
            duplicateAlert.replaceChildren(copy.duplicateExists, link, '.');
        } else {
            duplicateAlert.replaceChildren(copy.duplicatePending);
        }
        duplicateAlert.hidden = false;
    }

    async function hasNoDuplicate() {
        hideDuplicate();
        const params = new URLSearchParams({title: titleInput.value, author: authorInput.value});
        try {
            const response = await fetch(`${root.dataset.checkUrl}?${params}`, {
                credentials: 'same-origin',
                headers: {Accept: 'application/json'},
            });
            if (!response.ok) return true;
            const {duplicate} = await response.json();
            if (!duplicate) return true;
            showDuplicate(duplicate);
            return false;
        } catch {
            return true;
        }
    }

    const wizard = createWizard(root, {
        beforeLeave: (index) => (index === FIRST_STEP ? hasNoDuplicate() : Promise.resolve(true)),
    });
    if (!wizard) return;

    form.addEventListener('input', (event) => {
        if (event.target !== titleInput && event.target !== authorInput) return;
        hideDuplicate();
        lookup.schedule();
    });

    createBookPreview(root, form);
    if (lookup.hasQuery()) lookup.schedule(0);
})();
