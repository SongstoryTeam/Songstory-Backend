window.Songstery = window.Songstery || {};

window.Songstery.createChangeTracker = (root, form) => {
    const {dom} = window.Songstery;
    const submit = form.querySelector('[data-change-submit]');
    const status = root.querySelector('[data-change-status]');
    const resetAll = root.querySelector('[data-change-reset-all]');
    const fields = Array.from(form.elements).filter((element) => 'initial' in element.dataset);
    if (!submit || !status || !fields.length) return null;

    const copy = dom.readJson(root, '[data-change-copy]');
    const hasSavedProposal = fields.some((field) => 'saved' in field.dataset);

    const normalize = (text) => text.replace(/\r\n?/g, '\n').trim();
    const differsFrom = (field, baseline) => normalize(field.value) !== normalize(baseline);
    const savedValue = (field) => field.dataset.saved ?? field.dataset.initial;
    const isChanged = (field) => differsFrom(field, field.dataset.initial);
    const isUnsaved = (field) => differsFrom(field, savedValue(field));
    const groupOf = (field) => field.closest('.form-group');

    function statusText(changedCount, hasUnsaved) {
        if (!changedCount) return hasSavedProposal ? copy.reverted : copy.unchanged;
        return hasUnsaved ? dom.format(copy.changed, {count: changedCount}) : copy.saved;
    }

    function restore(field) {
        field.value = field.dataset.initial;
        field.dispatchEvent(new Event('input', {bubbles: true}));
    }

    function sync() {
        const changed = fields.filter(isChanged);
        const hasUnsaved = fields.some(isUnsaved);
        fields.forEach((field) => groupOf(field).classList.toggle('is-changed', changed.includes(field)));
        submit.disabled = !changed.length || !hasUnsaved;
        resetAll.hidden = !changed.length;
        status.textContent = statusText(changed.length, hasUnsaved);
    }

    form.addEventListener('input', sync);
    form.addEventListener('click', (event) => {
        const button = event.target.closest('[data-field-reset]');
        if (button) restore(button.closest('.form-group').querySelector('[data-initial]'));
    });
    resetAll.addEventListener('click', () => fields.filter(isChanged).forEach(restore));
    window.addEventListener('pageshow', sync);

    sync();
    return {sync};
};
