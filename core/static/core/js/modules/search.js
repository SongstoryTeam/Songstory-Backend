/**
 * Контролер пошуку в топбарі (ARIA combobox): дебаунс, клавіатурна навігація,
 * стани завантаження/помилки. Мережа — у search-api.js, DOM — у search-renderer.js.
 */
(() => {
    const form = document.querySelector('[data-site-search]');
    const {searchApi, searchRenderer} = window.Songstery || {};
    if (!form || !searchApi || !searchRenderer) return;

    const input = form.querySelector('[data-site-search-input]');
    const panel = form.querySelector('[data-site-search-panel]');
    const listbox = form.querySelector('[data-site-search-listbox]');
    const clearButton = form.querySelector('[data-site-search-clear]');
    const status = form.querySelector('[data-site-search-status]');

    const minLength = Number(form.dataset.minLength) || 2;
    const debounceMs = Number(form.dataset.debounceMs) || 250;
    const SKELETON_DELAY_MS = 120;

    const MESSAGES = {
        [searchApi.ERROR_KINDS.RATE_LIMITED]: 'Забагато запитів. Спробуйте за хвилину.',
        [searchApi.ERROR_KINDS.NETWORK]: 'Немає з’єднання. Перевірте інтернет.',
        [searchApi.ERROR_KINDS.SERVER]: 'Не вдалося виконати пошук. Спробуйте ще раз.',
    };
    const IMPORT_FAILED = 'Не вдалося додати книгу. Спробуйте ще раз.';

    const client = searchApi.createClient(form.dataset.suggestUrl);
    let debounceTimer = null;
    let skeletonTimer = null;
    let activeIndex = -1;
    let lastQuery = '';
    let lastPayload = null;

    const options = () => Array.from(listbox.querySelectorAll('[role="option"]'));
    const currentQuery = () => input.value.trim();

    function announce(text) {
        if (status) status.textContent = text;
    }

    function setOpen(open) {
        panel.hidden = !open;
        panel.toggleAttribute('data-open', open);
        input.setAttribute('aria-expanded', String(open));
        if (!open) clearActive();
    }

    function clearActive() {
        activeIndex = -1;
        input.removeAttribute('aria-activedescendant');
        options().forEach((item) => item.setAttribute('aria-selected', 'false'));
    }

    function setActive(index) {
        const items = options();
        if (!items.length) return;
        activeIndex = (index + items.length) % items.length;
        items.forEach((item, position) => item.setAttribute('aria-selected', String(position === activeIndex)));
        input.setAttribute('aria-activedescendant', items[activeIndex].id);
        items[activeIndex].scrollIntoView({block: 'nearest'});
    }

    function show(items) {
        listbox.replaceChildren(...items);
        clearActive();
        setOpen(true);
    }

    function stopPending() {
        window.clearTimeout(debounceTimer);
        window.clearTimeout(skeletonTimer);
        client.abort();
    }

    async function search(query) {
        lastQuery = query;
        skeletonTimer = window.setTimeout(() => {
            listbox.setAttribute('aria-busy', 'true');
            if (panel.hidden) show(searchRenderer.loading());
        }, SKELETON_DELAY_MS);

        try {
            const payload = await client.suggest(query);
            window.clearTimeout(skeletonTimer);
            listbox.removeAttribute('aria-busy');
            lastPayload = payload;
            show(searchRenderer.results(payload, query));
            const total = payload.results.length + (payload.external || []).length;
            announce(total ? `Знайдено підказок: ${total}` : 'Нічого не знайдено');
        } catch (error) {
            window.clearTimeout(skeletonTimer);
            if (error.name === 'AbortError') return;
            listbox.removeAttribute('aria-busy');
            show(searchRenderer.error(MESSAGES[error.kind] || MESSAGES.server));
            announce(MESSAGES[error.kind] || MESSAGES.server);
        }
    }

    async function chooseExternal(button) {
        if (!lastPayload) return;
        if (!lastPayload.can_import) {
            window.location.assign(lastPayload.login_url);
            return;
        }
        button.classList.add('is-busy');
        button.setAttribute('aria-busy', 'true');
        try {
            window.location.assign(await searchApi.importBook(lastPayload.import_url, button.dataset.externalId));
        } catch (error) {
            button.classList.remove('is-busy');
            button.removeAttribute('aria-busy');
            announce(IMPORT_FAILED);
        }
    }

    function onListboxClick(event) {
        const button = event.target.closest('[data-external-id]');
        if (button) chooseExternal(button);
    }

    function onInput() {
        const query = currentQuery();
        clearButton.hidden = !input.value.length;
        stopPending();
        if (query.length < minLength) {
            setOpen(false);
            return;
        }
        debounceTimer = window.setTimeout(() => search(query), debounceMs);
    }

    function onKeydown(event) {
        const items = options();
        switch (event.key) {
            case 'ArrowDown':
                if (panel.hidden || !items.length) return;
                event.preventDefault();
                setActive(activeIndex + 1);
                break;
            case 'ArrowUp':
                if (panel.hidden || !items.length) return;
                event.preventDefault();
                setActive(activeIndex < 0 ? items.length - 1 : activeIndex - 1);
                break;
            case 'Enter':
                if (activeIndex < 0) {
                    stopPending();
                    setOpen(false);
                    return;
                }
                event.preventDefault();
                items[activeIndex].click();
                break;
            case 'Escape':
                if (!panel.hidden) {
                    event.preventDefault();
                    setOpen(false);
                }
                break;
            default:
        }
    }

    function onClear() {
        stopPending();
        input.value = '';
        clearButton.hidden = true;
        setOpen(false);
        input.focus();
    }

    function onFocus() {
        const query = currentQuery();
        if (query.length >= minLength && query === lastQuery && listbox.children.length) setOpen(true);
    }

    function onFocusOut(event) {
        if (!form.contains(event.relatedTarget)) setOpen(false);
    }

    input.addEventListener('input', onInput);
    input.addEventListener('keydown', onKeydown);
    input.addEventListener('focus', onFocus);
    clearButton.addEventListener('click', onClear);
    listbox.addEventListener('click', onListboxClick);
    form.addEventListener('focusout', onFocusOut);
    form.addEventListener('submit', () => {
        stopPending();
        setOpen(false);
    });
    panel.addEventListener('mousedown', (event) => event.preventDefault());
    document.addEventListener('click', (event) => {
        if (!form.contains(event.target)) setOpen(false);
    });

    clearButton.hidden = !input.value.length;
})();
