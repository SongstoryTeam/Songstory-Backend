(() => {
    const form = document.querySelector('[data-accent-form]');
    if (!form) return;

    const SAVE_DELAY_MS = 300;
    const JSON_MIME = 'application/json';

    const root = document.documentElement;
    const options = Array.from(form.querySelectorAll('[data-accent-option]'));
    const submit = form.querySelector('[data-accent-submit]');
    const status = form.querySelector('[data-accent-status]');
    const summary = document.querySelector('[data-accent-summary]');

    const labels = new Map(options.map((option) => [option.value, option.closest('[data-label]').dataset.label]));
    const initialSummary = summary?.textContent ?? '';

    let committed = options.find((option) => option.checked)?.value ?? root.dataset.accent;
    let timer = null;
    let inflight = null;

    function announce(message) {
        if (status) status.textContent = message;
    }

    function render(value) {
        root.dataset.accent = value;
        options.forEach((option) => {
            option.checked = option.value === value;
        });
        if (summary) summary.textContent = `Обрано: ${labels.get(value)}. ${initialSummary}`;
    }

    async function save(value) {
        inflight?.abort();
        const controller = new AbortController();
        inflight = controller;

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: {Accept: JSON_MIME},
                credentials: 'same-origin',
                keepalive: true,
                signal: controller.signal,
            });
            if (!response.ok) throw new Error(String(response.status));
            committed = value;
            announce(`Колір збережено: ${labels.get(value)}`);
        } catch (error) {
            if (error.name === 'AbortError') return;
            render(committed);
            announce('Не вдалося зберегти колір. Спробуйте ще раз.');
        } finally {
            if (inflight === controller) inflight = null;
        }
    }

    function flush() {
        if (timer === null) return;
        window.clearTimeout(timer);
        timer = null;
        const selected = options.find((option) => option.checked);
        if (selected) save(selected.value);
    }

    options.forEach((option) => {
        option.addEventListener('change', () => {
            if (!option.checked) return;
            render(option.value);
            window.clearTimeout(timer);
            timer = window.setTimeout(flush, SAVE_DELAY_MS);
        });
    });

    window.addEventListener('pagehide', flush);
    if (submit) submit.hidden = true;
    render(committed);
})();
