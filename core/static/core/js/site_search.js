(() => {
    const form = document.querySelector('[data-site-search]');
    if (!form) return;

    const {
        suggestUrl,
        minLength,
        debounceMs,
    } = form.dataset;
    const input = form.querySelector('[data-site-search-input]');
    const panel = form.querySelector('[data-site-search-panel]');
    const listbox = form.querySelector('[data-site-search-listbox]');
    const clearButton = form.querySelector('[data-site-search-clear]');
    const optionPrefix = 'site-search-option-';

    let timer = null;
    let controller = null;
    let activeIndex = -1;

    const options = () => Array.from(listbox.querySelectorAll('[role="option"]'));

    function setOpen(open) {
        panel.hidden = !open;
        panel.toggleAttribute('data-open', open);
        input.setAttribute('aria-expanded', String(open));
        if (!open) {
            activeIndex = -1;
            input.removeAttribute('aria-activedescendant');
        }
    }

    function setActive(index) {
        const items = options();
        if (!items.length) return;
        activeIndex = (index + items.length) % items.length;
        items.forEach((item, position) => item.setAttribute('aria-selected', String(position === activeIndex)));
        input.setAttribute('aria-activedescendant', items[activeIndex].id);
        items[activeIndex].scrollIntoView({block: 'nearest'});
    }

    function textElement(tag, className, text) {
        const element = document.createElement(tag);
        element.className = className;
        element.textContent = text;
        return element;
    }

    function stateItem(message) {
        const item = document.createElement('li');
        item.appendChild(textElement('div', 'site-search__state', message));
        return item;
    }

    function resultItem(result, index) {
        const item = document.createElement('li');
        const link = document.createElement('a');
        link.id = `${optionPrefix}${index}`;
        link.href = result.url;
        link.className = 'site-search__item';
        link.setAttribute('role', 'option');
        link.setAttribute('aria-selected', 'false');

        const cover = document.createElement('span');
        cover.className = 'site-search__item-cover site-search__item-cover--empty';
        if (result.cover_url) {
            const image = document.createElement('img');
            image.src = result.cover_url;
            image.alt = '';
            image.loading = 'lazy';
            image.setAttribute('data-cover', '');
            cover.classList.remove('site-search__item-cover--empty');
            cover.appendChild(image);
        }

        const body = document.createElement('span');
        body.className = 'site-search__item-body';
        body.appendChild(textElement('span', 'site-search__item-title', result.title));
        if (result.author) body.appendChild(textElement('span', 'site-search__item-meta', result.author));

        link.append(cover, body);
        item.appendChild(link);
        return item;
    }

    function render(payload) {
        listbox.replaceChildren();
        if (!payload.results.length) {
            listbox.appendChild(stateItem('Нічого не знайдено в каталозі'));
        } else {
            payload.results.forEach((result, index) => listbox.appendChild(resultItem(result, index)));
        }
        const footer = document.createElement('li');
        const link = textElement('a', 'site-search__footer', 'Шукати у Google Books та каталозі');
        link.href = payload.all_url;
        footer.appendChild(link);
        listbox.appendChild(footer);
        setActive(-1);
        setOpen(true);
    }

    async function search(query) {
        controller?.abort();
        controller = new AbortController();
        try {
            const response = await fetch(`${suggestUrl}?q=${encodeURIComponent(query)}`, {
                signal: controller.signal,
                headers: {Accept: 'application/json'},
            });
            if (!response.ok) throw new Error(String(response.status));
            render(await response.json());
        } catch (error) {
            if (error.name === 'AbortError') return;
            listbox.replaceChildren(stateItem('Не вдалося виконати пошук'));
            setOpen(true);
        }
    }

    function onInput() {
        const query = input.value.trim();
        clearButton.hidden = !input.value.length;
        window.clearTimeout(timer);
        if (query.length < Number(minLength)) {
            controller?.abort();
            setOpen(false);
            return;
        }
        timer = window.setTimeout(() => search(query), Number(debounceMs));
    }

    input.addEventListener('input', onInput);
    input.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            setActive(activeIndex + 1);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            setActive(activeIndex - 1);
        } else if (event.key === 'Enter' && activeIndex >= 0) {
            event.preventDefault();
            options()[activeIndex].click();
        } else if (event.key === 'Escape') {
            setOpen(false);
        }
    });
    clearButton.addEventListener('click', () => {
        input.value = '';
        clearButton.hidden = true;
        setOpen(false);
        input.focus();
    });
    document.addEventListener('click', (event) => {
        if (!form.contains(event.target)) setOpen(false);
    });
    clearButton.hidden = !input.value.length;
})();
