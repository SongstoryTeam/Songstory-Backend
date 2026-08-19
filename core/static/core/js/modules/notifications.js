(function () {
    const FEED_ENDPOINT = '/notifications/feed/';
    const PANEL_CLOSE_DELAY_MS = 150;

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function refreshIcons() {
        if (window.lucide) window.lucide.createIcons();
    }

    function formatTimestamp(isoString) {
        const date = new Date(isoString);
        if (Number.isNaN(date.getTime())) return '';
        return date.toLocaleString('uk-UA', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function markRead(id) {
        // Fire-and-forget: the click that opens the target page shouldn't
        // wait on this. `keepalive` lets it survive the navigation.
        fetch(`/notifications/${id}/read/`, {
            method: 'POST',
            keepalive: true,
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        }).catch(() => {
        });
    }

    async function markAllRead() {
        const response = await fetch('/notifications/read-all/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }

    function initDropdown() {
        const wrap = document.querySelector('[data-notify]');
        if (!wrap) return;

        const toggle = wrap.querySelector('[data-notify-toggle]');
        const panel = wrap.querySelector('[data-notify-panel]');
        const list = wrap.querySelector('[data-notify-list]');
        const dot = wrap.querySelector('[data-notify-dot]');
        const markAllBtn = wrap.querySelector('[data-notify-mark-all]');

        let hidingTimer = null;
        let loaded = false;
        let isOpen = false;

        function openPanel() {
            window.clearTimeout(hidingTimer);
            panel.hidden = false;
            requestAnimationFrame(() => panel.setAttribute('data-open', ''));
            toggle.setAttribute('aria-expanded', 'true');
            isOpen = true;
            if (!loaded) loadFeed();
        }

        function closePanel() {
            panel.removeAttribute('data-open');
            toggle.setAttribute('aria-expanded', 'false');
            isOpen = false;
            hidingTimer = window.setTimeout(() => {
                panel.hidden = true;
            }, PANEL_CLOSE_DELAY_MS);
        }

        function setUnreadCount(count) {
            dot.hidden = count <= 0;
            markAllBtn.hidden = count <= 0;
        }

        function renderState(message, variant) {
            const variantClass = variant ? ` notify__state--${variant}` : '';
            list.innerHTML = `<li class="notify__state${variantClass}">${escapeHtml(message)}</li>`;
        }

        function renderItems(notifications) {
            if (!notifications.length) {
                renderState('Немає нових сповіщень', '');
                return;
            }

            list.innerHTML = notifications
                .map((item) => {
                    const readClass = item.is_read ? ' notify__item--read' : '';
                    const inner = `
                        <span class="notify__item-dot" aria-hidden="true"></span>
                        <span class="notify__item-body">
                            <span class="notify__item-message">${escapeHtml(item.message)}</span>
                            <span class="notify__item-meta">${formatTimestamp(item.created_at)}</span>
                        </span>
                    `;
                    const tag = item.url ? 'a' : 'span';
                    const href = item.url ? ` href="${escapeHtml(item.url)}"` : '';
                    return `
                        <li class="notify__item${readClass}">
                            <${tag} class="notify__item-link" data-notify-item data-id="${item.id}"
                                data-read="${item.is_read}"${href}>
                                ${inner}
                            </${tag}>
                        </li>
                    `;
                })
                .join('');
        }

        async function loadFeed() {
            renderState('Завантаження…', '');
            try {
                const response = await fetch(FEED_ENDPOINT, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                loaded = true;
                renderItems(data.notifications || []);
                setUnreadCount(data.unread_count || 0);
            } catch (error) {
                renderState('Не вдалось завантажити сповіщення', 'error');
            }
        }

        toggle.addEventListener('click', (event) => {
            event.preventDefault();
            if (isOpen) {
                closePanel();
            } else {
                openPanel();
            }
        });

        list.addEventListener('click', (event) => {
            const item = event.target.closest('[data-notify-item]');
            if (!item || item.dataset.read === 'true') return;
            item.dataset.read = 'true';
            item.closest('.notify__item')?.classList.add('notify__item--read');
            markRead(item.dataset.id);
            setUnreadCount(list.querySelectorAll('[data-read="false"]').length);
        });

        markAllBtn.addEventListener('click', async () => {
            markAllBtn.disabled = true;
            try {
                await markAllRead();
                list.querySelectorAll('[data-notify-item]').forEach((item) => {
                    item.dataset.read = 'true';
                    item.closest('.notify__item')?.classList.add('notify__item--read');
                });
                setUnreadCount(0);
            } catch (error) {
                // Leave state untouched; the user can retry.
            } finally {
                markAllBtn.disabled = false;
            }
        });

        document.addEventListener('click', (event) => {
            if (!wrap.contains(event.target)) closePanel();
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && isOpen) closePanel();
        });

        window.addEventListener('pageshow', (event) => {
            if (event.persisted) {
                panel.removeAttribute('data-open');
                panel.hidden = true;
                isOpen = false;
            }
        });
    }

    function initPage() {
        const list = document.querySelector('[data-notify-page-list]');
        const markAllBtn = document.querySelector('[data-notify-page-mark-all]');
        if (!list && !markAllBtn) return;

        if (list) {
            list.addEventListener('click', (event) => {
                const link = event.target.closest('[data-notify-page-open]');
                if (!link) return;
                markRead(link.dataset.id);
                link.closest('[data-notify-page-item]')?.classList.remove('notify-page-item--unread');
            });
        }

        if (markAllBtn) {
            markAllBtn.addEventListener('click', async () => {
                markAllBtn.disabled = true;
                try {
                    await markAllRead();
                    document.querySelectorAll('[data-notify-page-item]').forEach((item) => {
                        item.classList.remove('notify-page-item--unread');
                    });
                    markAllBtn.hidden = true;
                } catch (error) {
                    markAllBtn.disabled = false;
                }
            });
        }
    }

    refreshIcons();
    initDropdown();
    initPage();
})();
