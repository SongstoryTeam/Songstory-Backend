const BUSY_CLASS = 'is-busy';
const ERROR_CLASS = 'has-error';
const ENTER_CLASS = 'is-entering';

async function loadPage(url) {
    const response = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
    if (!response.ok) throw new Error(`Track page request failed: ${response.status}`);
    return response.text();
}

function appendPage(list, html) {
    const template = document.createElement('template');
    template.innerHTML = html;
    template.content.querySelectorAll('.track-card').forEach((card, index) => {
        card.classList.add(ENTER_CLASS);
        card.style.setProperty('--i', index);
    });
    const firstPlay = template.content.querySelector('[data-play]');
    list.append(template.content);
    window.applyIconSizes?.();
    window.lucide?.createIcons();
    firstPlay?.focus({preventScroll: true});
}

function setBusy(button, busy) {
    button.classList.toggle(BUSY_CLASS, busy);
    button.setAttribute('aria-busy', String(busy));
    if (busy) button.classList.remove(ERROR_CLASS);
}

function showError(button) {
    setBusy(button, false);
    button.classList.add(ERROR_CLASS);
    button.querySelector('[data-track-more-label]').textContent = button.dataset.errorLabel;
}

document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-track-more]');
    if (!button || button.classList.contains(BUSY_CLASS)) return;

    const list = button.closest('[data-track-list]');
    setBusy(button, true);
    try {
        const html = await loadPage(button.dataset.url);
        button.remove();
        appendPage(list, html);
    } catch (error) {
        showError(button);
    }
});
