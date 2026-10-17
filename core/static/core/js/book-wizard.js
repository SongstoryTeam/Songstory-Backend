/**
 * Додавання книги: покроковий майстер із живим пошуком схожих книг, імпортом в один клік,
 * блокуванням точних дублікатів і попереднім переглядом картки. Мережа — у search-api.js,
 * кроки — у wizard.js. Увесь текст з сервера вставляється через textContent.
 */
(() => {
    const root = document.querySelector('[data-book-wizard]');
    const {createWizard, searchApi} = window.Songstery || {};
    if (!root || !createWizard || !searchApi) return;

    const COVER_CHECK_DELAY_MS = 400;
    const FEEDBACK_BASE = 'field-feedback';
    const COPY = Object.freeze({
        previewTitle: 'Назва книги',
        lookupLoading: 'Шукаємо в каталозі та в інтернеті…',
        lookupEmpty: 'Схожих книг не знайдено. Продовжуйте, і ми додамо її вручну.',
        lookupUnavailable: 'Пошук тимчасово недоступний. Можна продовжити й додати книгу вручну.',
        lookupRateLimited: 'Забагато запитів. Зачекайте хвилину або продовжуйте вручну.',
        localHeading: 'Уже в каталозі',
        localHint: 'Якщо це ваша книга, відкрийте її замість створення копії.',
        externalHeading: 'Знайдено в інтернеті',
        externalHint: 'Додайте одним кліком: обкладинка й опис підтягнуться автоматично.',
        open: 'Відкрити',
        add: 'Додати',
        importFailed: 'Не вдалося додати книгу. Спробуйте ще раз.',
        duplicateExists: 'Така книга вже є: ',
        duplicatePending: 'Така книга вже надіслана на перевірку.',
        authorUnknown: 'Автор невідомий',
        coverChecking: 'Перевіряємо зображення…',
        coverOk: 'Зображення знайдено.',
        coverInvalid: 'Потрібне посилання, що починається з https://',
        coverBroken: 'Не вдалося завантажити зображення. Перевірте посилання або залиште поле порожнім.',
    });

    const form = root.querySelector('[data-wizard-form]');
    const titleInput = form.elements.title;
    const authorInput = form.elements.author_name;
    const yearInput = form.elements.year;
    const genreInput = form.elements.genre_name;
    const coverInput = form.elements.cover_url;

    const lookup = root.querySelector('[data-lookup]');
    const lookupResults = root.querySelector('[data-lookup-results]');
    const lookupStatus = root.querySelector('[data-lookup-status]');
    const duplicateAlert = root.querySelector('[data-duplicate]');
    const coverFeedback = root.querySelector('[data-cover-feedback]');

    const preview = root.querySelector('[data-preview]');
    const previewCover = root.querySelector('[data-preview-cover]');
    const previewFallback = root.querySelector('[data-preview-fallback]');
    const previewTitle = root.querySelector('[data-preview-title]');
    const previewAuthor = root.querySelector('[data-preview-author]');
    const previewMeta = root.querySelector('[data-preview-meta]');

    const minLength = Number(root.dataset.minLength) || 2;
    const debounceMs = Number(root.dataset.debounceMs) || 350;
    const client = searchApi.createClient(root.dataset.suggestUrl);

    let lookupTimer = null;
    let coverTimer = null;
    let coverToken = 0;

    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function announce(text) {
        lookupStatus.textContent = text;
    }

    function setFeedback(text, modifier) {
        coverFeedback.textContent = text;
        coverFeedback.className = modifier ? `${FEEDBACK_BASE} ${FEEDBACK_BASE}--${modifier}` : FEEDBACK_BASE;
    }

    /* ---------- Пошук схожих книг ---------- */

    function lookupQuery() {
        return [titleInput.value, authorInput.value]
            .map((value) => value.trim())
            .filter(Boolean)
            .join(' ');
    }

    function coverBox(url) {
        const box = element('div', 'result-item__cover');
        if (!url) return box;
        const image = element('img');
        image.src = url;
        image.alt = '';
        image.loading = 'lazy';
        image.setAttribute('data-cover', '');
        box.appendChild(image);
        return box;
    }

    function resultItem({title, author, year, cover_url: cover}, action) {
        const meta = [author || COPY.authorUnknown, year].filter(Boolean).join(' · ');
        const body = element('div', 'result-item__body');
        body.append(element('div', 'result-item__title', title), element('div', 'result-item__meta', meta));
        const item = element('li', 'result-item');
        item.append(coverBox(cover), body, action);
        return item;
    }

    function group(heading, hint, items) {
        const list = element('ul', 'result-list');
        list.append(...items);
        const wrapper = element('section', 'book-lookup__group');
        wrapper.append(element('h3', 'book-lookup__heading', heading), element('p', 'book-lookup__hint', hint), list);
        return wrapper;
    }

    function openLink(url) {
        const link = element('a', 'btn btn-ghost btn-sm', COPY.open);
        link.href = url;
        return link;
    }

    function importButton(externalId) {
        const button = element('button', 'btn btn-accent btn-sm', COPY.add);
        button.type = 'button';
        button.dataset.externalId = externalId;
        return button;
    }

    function renderLookup(payload) {
        const local = payload.results || [];
        const external = payload.external || [];
        root.dataset.importUrl = payload.import_url || '';

        const blocks = [];
        if (local.length) {
            blocks.push(group(COPY.localHeading, COPY.localHint, local.map((book) => resultItem(book, openLink(book.url)))));
        }
        if (external.length && payload.import_url) {
            blocks.push(
                group(
                    COPY.externalHeading,
                    COPY.externalHint,
                    external.map((book) => resultItem(book, importButton(book.external_id))),
                ),
            );
        }
        if (!blocks.length) {
            const unavailable = payload.external_unavailable || (payload.external_failed || []).length;
            blocks.push(element('p', 'book-lookup__empty', unavailable ? COPY.lookupUnavailable : COPY.lookupEmpty));
        }
        lookupResults.replaceChildren(...blocks);
        announce(local.length + external.length ? `Знайдено схожих книг: ${local.length + external.length}` : COPY.lookupEmpty);
    }

    function renderLookupError(error) {
        const text = error.kind === searchApi.ERROR_KINDS.RATE_LIMITED ? COPY.lookupRateLimited : COPY.lookupUnavailable;
        lookupResults.replaceChildren(element('p', 'book-lookup__empty', text));
        announce(text);
    }

    async function runLookup() {
        const query = lookupQuery();
        if (query.length < minLength) {
            client.abort();
            lookup.hidden = true;
            lookupResults.replaceChildren();
            return;
        }
        lookup.hidden = false;
        lookup.setAttribute('aria-busy', 'true');
        announce(COPY.lookupLoading);
        try {
            renderLookup(await client.suggest(query));
        } catch (error) {
            if (error.name === 'AbortError') return;
            renderLookupError(error);
        }
        lookup.removeAttribute('aria-busy');
    }

    function scheduleLookup(delay = debounceMs) {
        window.clearTimeout(lookupTimer);
        lookupTimer = window.setTimeout(runLookup, delay);
    }

    async function importExternal(button) {
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        try {
            window.location.assign(await searchApi.importBook(root.dataset.importUrl, button.dataset.externalId));
        } catch (error) {
            button.disabled = false;
            button.removeAttribute('aria-busy');
            announce(COPY.importFailed);
        }
    }

    lookupResults.addEventListener('click', (event) => {
        const button = event.target.closest('[data-external-id]');
        if (button) importExternal(button);
    });

    /* ---------- Захист від дублікатів ---------- */

    function hideDuplicate() {
        duplicateAlert.hidden = true;
        duplicateAlert.removeAttribute('data-wizard-error');
        duplicateAlert.replaceChildren();
    }

    function showDuplicate(duplicate) {
        if (duplicate.url) {
            const link = element('a', 'text-accent', duplicate.title);
            link.href = duplicate.url;
            duplicateAlert.replaceChildren(COPY.duplicateExists, link, '.');
        } else {
            duplicateAlert.replaceChildren(COPY.duplicatePending);
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
        } catch (error) {
            return true;
        }
    }

    /* ---------- Попередній перегляд ---------- */

    function normalizedCoverUrl(value) {
        try {
            const url = new URL(value.trim());
            if (url.protocol === 'http:') url.protocol = 'https:';
            return url.protocol === 'https:' ? url.href : '';
        } catch (error) {
            return '';
        }
    }

    function updatePreview() {
        const title = titleInput.value.trim();
        const author = authorInput.value.trim();
        previewTitle.textContent = title || COPY.previewTitle;
        previewFallback.textContent = title || COPY.previewTitle;
        previewAuthor.textContent = author;
        previewAuthor.hidden = !author;
        previewMeta.textContent = [yearInput.value.trim(), genreInput.value.trim()].filter(Boolean).join(' · ');
        previewMeta.hidden = !previewMeta.textContent;
    }

    function setPreviewCover(url) {
        previewCover.querySelector('img')?.remove();
        if (!url) return;
        const image = element('img');
        image.src = url;
        image.alt = '';
        previewCover.appendChild(image);
    }

    function checkCover() {
        coverToken += 1;
        const token = coverToken;
        const raw = coverInput.value.trim();
        if (!raw) {
            setPreviewCover('');
            setFeedback('');
            return;
        }
        const url = normalizedCoverUrl(raw);
        if (!url) {
            setPreviewCover('');
            setFeedback(COPY.coverInvalid, 'error');
            return;
        }
        setFeedback(COPY.coverChecking, 'pending');
        const probe = new Image();
        probe.addEventListener('load', () => {
            if (token !== coverToken) return;
            setPreviewCover(url);
            setFeedback(COPY.coverOk, 'ok');
        });
        probe.addEventListener('error', () => {
            if (token !== coverToken) return;
            setPreviewCover('');
            setFeedback(COPY.coverBroken, 'error');
        });
        probe.src = url;
    }

    function scheduleCoverCheck() {
        window.clearTimeout(coverTimer);
        coverTimer = window.setTimeout(checkCover, COVER_CHECK_DELAY_MS);
    }

    /* ---------- Збірка ---------- */

    if (!createWizard(root, {beforeLeave: (index) => (index === 0 ? hasNoDuplicate() : Promise.resolve(true))})) return;

    form.addEventListener('input', (event) => {
        updatePreview();
        if (event.target === coverInput) scheduleCoverCheck();
        if (event.target === titleInput || event.target === authorInput) {
            hideDuplicate();
            scheduleLookup();
        }
    });

    preview.hidden = false;
    updatePreview();
    if (coverInput.value.trim()) checkCover();
    if (lookupQuery()) scheduleLookup(0);
})();
