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

    function groupHeading(text) {
        return listItem(element('div', 'site-search__group', text));
    }

    function externalItem(result, index) {
        const button = option(element('button', 'site-search__item'), index);
        button.type = 'button';
        button.dataset.externalId = result.external_id;

        const meta = [result.author, result.year].filter(Boolean).join(' · ');
        const body = element('span', 'site-search__item-body');
        body.appendChild(element('span', 'site-search__item-title', result.title));
        if (meta) body.appendChild(element('span', 'site-search__item-meta', meta));

        button.append(cover(result.cover_url), body, element('span', 'site-search__item-flag', 'Додати'));
        return listItem(button);
    }

    function footerItem(payload, query, index) {
        const link = option(element('a', 'site-search__footer'), index);
        link.href = payload.all_url;
        link.append(element('span', '', `Усі результати для «${query}»`), element('span', 'site-search__footer-hint', 'каталог та інтернет'));
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
            const local = payload.results;
            const external = payload.external || [];
            const items = [];
            let index = 0;

            if (local.length) {
                items.push(groupHeading('У каталозі'));
                local.forEach((result) => items.push(resultItem(result, index++)));
            }
            if (external.length) {
                items.push(groupHeading('Можна додати з інтернету'));
                external.forEach((result) => items.push(externalItem(result, index++)));
            }
            if (!local.length && !external.length) {
                items.push(message(payload.external_unavailable ? 'Пошук в інтернеті тимчасово недоступний' : 'Нічого не знайдено'));
            }
            items.push(footerItem(payload, query, index));
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
