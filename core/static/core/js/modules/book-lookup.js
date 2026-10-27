window.Songstery = window.Songstery || {};

window.Songstery.createBookLookup = ({root, form, client, searchApi}) => {
    const {dom} = window.Songstery;
    const {element, format} = dom;

    const panel = root.querySelector('[data-lookup]');
    const results = root.querySelector('[data-lookup-results]');
    const status = root.querySelector('[data-lookup-status]');
    const copy = dom.readJson(root, '[data-book-copy]');
    const minLength = Number(root.dataset.minLength);
    const debounceMs = Number(root.dataset.debounceMs);
    const inputs = [form.elements.title, form.elements.author_name];

    let timer = null;

    const query = () => inputs.map((input) => input.value.trim()).filter(Boolean).join(' ');
    const announce = (text) => {
        status.textContent = text;
    };

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
        const meta = [author || copy.authorUnknown, year].filter(Boolean).join(' · ');
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
        const link = element('a', 'btn btn-ghost btn-sm', copy.open);
        link.href = url;
        return link;
    }

    function importButton(externalId) {
        const button = element('button', 'btn btn-accent btn-sm', copy.add);
        button.type = 'button';
        button.dataset.externalId = externalId;
        return button;
    }

    function localGroup(books) {
        const items = books.map((book) => resultItem(book, openLink(book.url)));
        return group(copy.localHeading, copy.localHint, items);
    }

    function externalGroup(books) {
        const items = books.map((book) => resultItem(book, importButton(book.external_id)));
        return group(copy.externalHeading, copy.externalHint, items);
    }

    function render(payload) {
        const local = payload.results || [];
        const external = payload.external || [];
        const canImport = Boolean(payload.import_url);
        root.dataset.importUrl = payload.import_url || '';

        const blocks = [];
        if (local.length) blocks.push(localGroup(local));
        if (external.length && canImport) blocks.push(externalGroup(external));

        const total = local.length + (canImport ? external.length : 0);
        if (!total) {
            const unavailable = payload.external_unavailable || (payload.external_failed || []).length;
            blocks.push(element('p', 'book-lookup__empty', unavailable ? copy.unavailable : copy.empty));
        }
        results.replaceChildren(...blocks);
        announce(total ? format(copy.found, {count: total}) : copy.empty);
    }

    function renderError(error) {
        const text = error.kind === searchApi.ERROR_KINDS.RATE_LIMITED ? copy.rateLimited : copy.unavailable;
        results.replaceChildren(element('p', 'book-lookup__empty', text));
        announce(text);
    }

    async function run() {
        const value = query();
        if (value.length < minLength) {
            client.abort();
            panel.hidden = true;
            results.replaceChildren();
            return;
        }
        panel.hidden = false;
        panel.setAttribute('aria-busy', 'true');
        announce(copy.loading);
        try {
            render(await client.suggest(value));
        } catch (error) {
            if (error.name === 'AbortError') return;
            renderError(error);
        }
        panel.removeAttribute('aria-busy');
    }

    async function importBook(button) {
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        try {
            window.location.assign(await searchApi.importBook(root.dataset.importUrl, button.dataset.externalId, query()));
        } catch {
            button.disabled = false;
            button.removeAttribute('aria-busy');
            announce(copy.importFailed);
        }
    }

    function schedule(delay = debounceMs) {
        window.clearTimeout(timer);
        timer = window.setTimeout(run, delay);
    }

    results.addEventListener('click', (event) => {
        const button = event.target.closest('[data-external-id]');
        if (button) importBook(button);
    });

    return {schedule, hasQuery: () => Boolean(query())};
};
