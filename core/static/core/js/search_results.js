(function () {
    const IMPORT_ENDPOINT = '/book/import/';
    const CONFIRMED_LANGUAGE = 'uk';

    document.querySelectorAll('[data-import-book]').forEach((button) => {
        button.addEventListener('click', () => importBook(button));
    });

    async function importBook(button) {
        if (button.disabled) return;
        setButtonState(button, 'loading');

        const payload = new URLSearchParams({
            open_library_id: button.dataset.openLibraryId || '',
            title: button.dataset.title || '',
            author: button.dataset.author || '',
            year: button.dataset.year || '',
            isbn: button.dataset.isbn || '',
            cover_url: button.dataset.coverUrl || '',
            description: button.dataset.description || '',
            language: CONFIRMED_LANGUAGE,
        });

        try {
            const response = await fetch(IMPORT_ENDPOINT, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: payload,
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }

            window.location.href = data.url;
        } catch (error) {
            console.error('Book import failed:', error);
            setButtonState(button, 'error');
        }
    }

    function setButtonState(button, state) {
        if (state === 'loading') {
            button.disabled = true;
            button.innerHTML = '<i data-lucide="loader-2" class="spin-icon" style="width:13px;height:13px;"></i> Додаємо…';
        } else if (state === 'error') {
            button.disabled = false;
            button.innerHTML = '<i data-lucide="rotate-ccw" style="width:13px;height:13px;"></i> Не вдалось. Спробувати ще раз';
        }
        refreshIcons();
    }

    function refreshIcons() {
        if (window.lucide) window.lucide.createIcons();
    }

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }
})();
