function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
}

const searchInput = document.getElementById('book-search-input');
const resultsBox = document.getElementById('book-search-results');
const manualToggle = document.getElementById('show-manual-form');
const manualBox = document.getElementById('manual-form-box');

if (manualToggle && manualBox) {
    manualToggle.addEventListener('click', () => {
        manualBox.style.display = manualBox.style.display === 'none' ? 'block' : 'none';
    });
}

if (searchInput && resultsBox) {
    let debounceTimer;
    searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        if (query.length < 2) {
            resultsBox.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/search/books/?q=${encodeURIComponent(query)}`);
                if (!response.ok) return;
                const data = await response.json();
                renderResults(data.results || []);
            } catch { /* ignore */
            }
        }, 400);
    });

    document.addEventListener('click', (e) => {
        if (!resultsBox.contains(e.target) && e.target !== searchInput) resultsBox.innerHTML = '';
    });
}

function renderResults(results) {
    if (!results.length) {
        resultsBox.innerHTML = '<div class="book-search-empty">Нічого не знайдено</div>';
        return;
    }
    resultsBox.innerHTML = results.map((b, i) => `
        <div class="book-search-result" data-index="${i}">
            ${b.cover_url ? `<img src="${escHtml(b.cover_url)}" width="40" height="60" loading="lazy">` : '<div class="book-search-result__no-cover"></div>'}
            <div class="book-search-result__body">
                <div class="book-search-result__title">${escHtml(b.title)}</div>
                <div class="book-search-result__author">${escHtml(b.author)}${b.year ? ` · ${b.year}` : ''}</div>
            </div>
        </div>`).join('');

    resultsBox.querySelectorAll('.book-search-result').forEach((el) => {
        el.addEventListener('click', () => importBook(el, results[Number(el.dataset.index)]));
    });
}

async function importBook(el, book) {
    resultsBox.querySelectorAll('.book-search-result').forEach((r) => r.style.pointerEvents = 'none');
    el.classList.add('book-search-result--loading');
    try {
        const response = await fetch('/book/import/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                open_library_id: book.open_library_id, title: book.title,
                author: book.author || '', year: book.year || '',
                isbn: book.isbn || '', cover_url: book.cover_url || '',
                description: book.description || '',
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        window.location.href = data.url;
    } catch (err) {
        console.error('Book import failed:', err);
        resultsBox.querySelectorAll('.book-search-result').forEach((r) => r.style.pointerEvents = '');
        el.classList.remove('book-search-result--loading');
    }
}

function escHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}