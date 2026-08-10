(function () {
    const SEARCH_ENDPOINT = '/api/search/discover/';
    const SEARCH_MIN_LENGTH = 2;
    const SEARCH_DEBOUNCE_MS = 150;
    const QUICK_RESULT_LIMIT = 6;
    const PANEL_CLOSE_DELAY_MS = 150;
    const SKELETON_ROW_COUNT = 3;

    const form = document.querySelector('[data-site-search]');
    if (!form) return;

    const input = form.querySelector('#site-search-input');
    const panel = form.querySelector('[data-site-search-panel]');
    const listbox = form.querySelector('#site-search-listbox');
    const clearButton = form.querySelector('[data-site-search-clear]');

    let debounceTimer = null;
    let hidingTimer = null;
    let activeController = null;
    let activeIndex = -1;
    let hasResults = false;

    function refreshIcons() {
        if (window.lucide) window.lucide.createIcons();
    }

    function updateClearButton() {
        clearButton.hidden = input.value.length === 0;
    }

    function openPanel() {
        window.clearTimeout(hidingTimer);
        panel.hidden = false;
        requestAnimationFrame(() => panel.setAttribute('data-open', ''));
        input.setAttribute('aria-expanded', 'true');
    }

    function closePanel() {
        panel.removeAttribute('data-open');
        input.setAttribute('aria-expanded', 'false');
        input.removeAttribute('aria-activedescendant');
        activeIndex = -1;
        hidingTimer = window.setTimeout(() => {
            panel.hidden = true;
        }, PANEL_CLOSE_DELAY_MS);
    }

    function renderSkeleton() {
        const rows = Array.from({ length: SKELETON_ROW_COUNT }, () => `
            <li class="site-search__skeleton-row">
                <div class="site-search__skeleton-block site-search__skeleton-block--cover"></div>
                <div style="flex:1">
                    <div class="site-search__skeleton-block site-search__skeleton-block--line"></div>
                    <div class="site-search__skeleton-block site-search__skeleton-block--line"></div>
                </div>
            </li>
        `).join('');
        listbox.innerHTML = rows;
        hasResults = false;
        openPanel();
    }

    function renderState(message, variant) {
        const variantClass = variant ? ` site-search__state--${variant}` : '';
        const icon = variant === 'error'
            ? '<i data-lucide="alert-circle" size="15"></i>'
            : '<i data-lucide="search-x" size="15"></i>';
        listbox.innerHTML = `
            <li class="site-search__state${variantClass}">
                ${icon}
                <span>${escapeHtml(message)}</span>
            </li>
        `;
        hasResults = false;
        refreshIcons();
    }

    function renderResults(query, results) {
        activeIndex = -1;
        hasResults = results.length > 0;

        if (!results.length) {
            renderState(`Нічого не знайдено для «${query}»`, '');
            return;
        }

        const items = results
            .map((book, index) => `
                <li role="presentation">
                    <a href="${escapeHtml(resultHref(book, query))}"
                       class="site-search__item"
                       role="option"
                       id="site-search-option-${index}"
                       data-index="${index}"
                       aria-selected="false">
                        ${renderCover(book)}
                        <div class="site-search__item-body">
                            <div class="site-search__item-title">${escapeHtml(book.title)}</div>
                            <div class="site-search__item-meta">${escapeHtml(renderMeta(book))}</div>
                        </div>
                        ${book.in_catalog ? '<span class="site-search__item-flag">У каталозі</span>' : ''}
                    </a>
                </li>
            `)
            .join('');

        const footer = `
            <li class="site-search__footer" data-see-all role="presentation">
                <span>Усі результати для «${escapeHtml(query)}»</span>
                <i data-lucide="arrow-right" size="14"></i>
            </li>
        `;

        listbox.innerHTML = items + footer;
        listbox.querySelector('[data-see-all]')?.addEventListener('click', () => form.submit());
        refreshIcons();
    }

    function resultHref(book, query) {
        if (book.in_catalog && book.url) return book.url;
        return `${form.action}?q=${encodeURIComponent(query)}`;
    }

    function renderCover(book) {
        if (!book.cover_url) {
            return '<div class="site-search__item-cover site-search__item-cover--empty"><i data-lucide="book" size="14"></i></div>';
        }
        return `<img class="site-search__item-cover" src="${escapeHtml(book.cover_url)}" alt="" loading="lazy">`;
    }

    function renderMeta(book) {
        const parts = [book.author, book.year].filter(Boolean);
        return parts.length ? parts.join(' · ') : 'Автор невідомий';
    }

    async function runSearch(query) {
        if (activeController) activeController.abort();
        activeController = new AbortController();

        renderSkeleton();

        try {
            const url = `${SEARCH_ENDPOINT}?q=${encodeURIComponent(query)}&limit=${QUICK_RESULT_LIMIT}`;
            const response = await fetch(url, { signal: activeController.signal });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            renderResults(query, data.results || []);
        } catch (error) {
            if (error.name === 'AbortError') return;
            renderState('Не вдалось виконати пошук. Спробуйте ще раз.', 'error');
        }
    }

    function moveActive(direction) {
        const options = Array.from(listbox.querySelectorAll('[role="option"]'));
        if (!options.length) return;

        options.forEach((option) => option.setAttribute('aria-selected', 'false'));
        activeIndex = (activeIndex + direction + options.length) % options.length;

        const active = options[activeIndex];
        active.setAttribute('aria-selected', 'true');
        active.scrollIntoView({ block: 'nearest' });
        input.setAttribute('aria-activedescendant', active.id);
    }

    input.addEventListener('input', () => {
        updateClearButton();
        window.clearTimeout(debounceTimer);

        const query = input.value.trim();
        if (query.length < SEARCH_MIN_LENGTH) {
            if (activeController) activeController.abort();
            closePanel();
            return;
        }

        debounceTimer = window.setTimeout(() => runSearch(query), SEARCH_DEBOUNCE_MS);
    });

    input.addEventListener('focus', () => {
        if (hasResults && input.value.trim().length >= SEARCH_MIN_LENGTH) {
            openPanel();
        }
    });

    input.addEventListener('keydown', (event) => {
        if (panel.hidden) return;

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            moveActive(1);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            moveActive(-1);
        } else if (event.key === 'Escape') {
            closePanel();
        } else if (event.key === 'Enter' && activeIndex >= 0) {
            event.preventDefault();
            listbox.querySelector(`[data-index="${activeIndex}"]`)?.click();
        }
    });

    clearButton.addEventListener('click', () => {
        input.value = '';
        updateClearButton();
        closePanel();
        input.focus();
    });

    document.addEventListener('click', (event) => {
        if (!form.contains(event.target)) closePanel();
    });

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    updateClearButton();
})();
