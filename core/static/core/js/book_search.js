const SEARCH_MIN_LENGTH = 2;
const SEARCH_DEBOUNCE_MS = 400;
const SEARCH_ENDPOINT = '/api/search/books/';
const IMPORT_ENDPOINT = '/book/import/';

const searchInput = document.getElementById('book-search-input');
const resultsBox = document.getElementById('book-search-results');
const manualFormToggle = document.getElementById('show-manual-form');
const manualFormBox = document.getElementById('manual-form-box');

if (manualFormToggle && manualFormBox) {
    manualFormToggle.addEventListener('click', () => {
        const isHidden = manualFormBox.style.display === 'none';
        manualFormBox.style.display = isHidden ? 'block' : 'none';
    });
}

if (searchInput && resultsBox) {
    let debounceTimer;

    searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const query = this.value.trim();

        if (query.length < SEARCH_MIN_LENGTH) {
            resultsBox.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(() => searchBooks(query), SEARCH_DEBOUNCE_MS);
    });

    document.addEventListener('click', (event) => {
        const clickedOutside = !resultsBox.contains(event.target) && event.target !== searchInput;
        if (clickedOutside) {
            resultsBox.innerHTML = '';
        }
    });
}

async function searchBooks(query) {
    try {
        const response = await fetch(`${SEARCH_ENDPOINT}?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            resultsBox.innerHTML = '';
            return;
        }
        const data = await response.json();
        renderResults(data.results || []);
    } catch {
        resultsBox.innerHTML = '';
    }
}

function renderResults(results) {
    if (!results.length) {
        resultsBox.innerHTML = '<div class="book-search-empty">Нічого не знайдено</div>';
        return;
    }

    resultsBox.innerHTML = results
        .map((book, index) => `
            <div class="book-search-result" data-index="${index}">
                ${renderCover(book)}
                <div class="book-search-result__body">
                    <div class="book-search-result__title">${escapeHtml(book.title)}</div>
                    <div class="book-search-result__author">${renderSubtitle(book)}</div>
                </div>
            </div>
        `)
        .join('');

    resultsBox.querySelectorAll('.book-search-result').forEach((element) => {
        const book = results[Number(element.dataset.index)];
        element.addEventListener('click', () => importBook(element, book));
    });
}

function renderCover(book) {
    if (!book.cover_url) {
        return '<div class="book-search-result__no-cover"></div>';
    }
    return `<img src="${escapeHtml(book.cover_url)}" alt="" width="40" height="60" loading="lazy">`;
}

function renderSubtitle(book) {
    const author = escapeHtml(book.author || '');
    return book.year ? `${author} · ${book.year}` : author;
}

async function importBook(element, book) {
    setResultsLocked(true);
    element.classList.add('book-search-result--loading');

    try {
        const response = await fetch(IMPORT_ENDPOINT, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                open_library_id: book.open_library_id,
                title: book.title,
                author: book.author || '',
                year: book.year || '',
                isbn: book.isbn || '',
                cover_url: book.cover_url || '',
                description: book.description || '',
            }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        window.location.href = data.url;
    } catch (error) {
        console.error('Book import failed:', error);
        setResultsLocked(false);
        element.classList.remove('book-search-result--loading');
    }
}

function setResultsLocked(locked) {
    resultsBox.querySelectorAll('.book-search-result').forEach((element) => {
        element.style.pointerEvents = locked ? 'none' : '';
    });
}

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