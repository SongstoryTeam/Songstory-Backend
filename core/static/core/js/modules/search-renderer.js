window.Songstery = window.Songstery || {};

/**
 * Відмальовування вмісту панелі пошуку. Весь текст вставляється через
 * textContent, тому дані з сервера не можуть внести розмітку (XSS).
 */
window.Songstery.searchRenderer = (() => {
    const OPTION_PREFIX = 'site-search-option-';
    const SKELETON_ROWS = 3;

    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function listItem(child) {
        const item = element('li');
        item.setAttribute('role', 'presentation');
        item.appendChild(child);
        return item;
    }

    function option(link, index) {
        link.id = `${OPTION_PREFIX}${index}`;
        link.setAttribute('role', 'option');
        link.setAttribute('aria-selected', 'false');
        return link;
    }

    function cover(url) {
        const wrapper = element('span', 'site-search__item-cover site-search__item-cover--empty');
        if (!url) return wrapper;
        const image = element('img');
        image.src = url;
        image.alt = '';
        image.loading = 'lazy';
        image.setAttribute('data-cover', '');
        wrapper.classList.remove('site-search__item-cover--empty');
        wrapper.appendChild(image);
        return wrapper;
    }

    function resultItem(result, index) {
        const link = option(element('a', 'site-search__item'), index);
        link.href = result.url;

        const body = element('span', 'site-search__item-body');
        body.appendChild(element('span', 'site-search__item-title', result.title));
        if (result.author) body.appendChild(element('span', 'site-search__item-meta', result.author));

        link.append(cover(result.cover_url), body);
        return listItem(link);
    }

    function footerItem(payload, query, index) {
        const link = option(element('a', 'site-search__footer'), index);
        link.href = payload.all_url;
        link.append(element('span', '', `Усі результати для «${query}»`), element('span', 'site-search__footer-hint', 'каталог і Google Books'));
        return listItem(link);
    }

    function message(text, modifier) {
        const className = modifier ? `site-search__state site-search__state--${modifier}` : 'site-search__state';
        return listItem(element('div', className, text));
    }

    function skeletonRow() {
        const row = element('div', 'site-search__skeleton-row');
        const lines = element('div', '');
        lines.style.flex = '1';
        lines.append(
            element('div', 'site-search__skeleton-block site-search__skeleton-block--line'),
            element('div', 'site-search__skeleton-block site-search__skeleton-block--line'),
        );
        row.append(element('div', 'site-search__skeleton-block site-search__skeleton-block--cover'), lines);
        return row;
    }

    return {
        results(payload, query) {
            const items = payload.results.length
                ? payload.results.map(resultItem)
                : [message('Нічого не знайдено в каталозі')];
            items.push(footerItem(payload, query, payload.results.length));
            return items;
        },
        loading() {
            return Array.from({length: SKELETON_ROWS}, () => listItem(skeletonRow()));
        },
        error(text) {
            return [message(text, 'error')];
        },
    };
})();
