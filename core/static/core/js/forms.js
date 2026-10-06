const BUSY_LABEL = 'Зачекайте…';

document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.hasAttribute('data-no-busy')) return;

    window.setTimeout(() => {
        form.querySelectorAll('button[type="submit"]').forEach((button) => {
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
            button.dataset.label = button.textContent;
            button.textContent = BUSY_LABEL;
        });
    }, 0);
});

window.addEventListener('pageshow', (event) => {
    if (!event.persisted) return;
    document.querySelectorAll('button[aria-busy="true"]').forEach((button) => {
        button.disabled = false;
        button.removeAttribute('aria-busy');
        button.textContent = button.dataset.label;
    });
});
