const trackInput = document.getElementById('id_track_title');
const artistInput = document.getElementById('id_artist');
const embedInput = document.getElementById('id_embed_code');
const linkInput = document.getElementById('id_link_url');
const linkTypeInput = document.getElementById('id_link_type');
const resultsBox = document.getElementById('youtube-results');

if (trackInput && resultsBox) {
    let debounceTimer;

    trackInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const query = this.value.trim();

        if (query.length < 3) {
            resultsBox.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(
                    `/youtube-search/?q=${encodeURIComponent(query)}`
                );
                if (!response.ok) return;
                const data = await response.json();
                renderResults(data.results || []);
            } catch {
                // silently ignore network errors during search
            }
        }, 400);
    });

    document.addEventListener('click', (e) => {
        if (!resultsBox.contains(e.target) && e.target !== trackInput) {
            resultsBox.innerHTML = '';
        }
    });
}

function renderResults(results) {
    if (!results.length) {
        resultsBox.innerHTML = '';
        return;
    }

    resultsBox.innerHTML = results
        .map(
            (r) => `
        <div class="yt-result" data-id="${escHtml(r.id)}"
             data-title="${escHtml(r.title)}" data-channel="${escHtml(r.channel)}">
            <img src="${escHtml(r.thumbnail)}" width="60" height="45" loading="lazy">
            <div class="yt-result__body">
                <div class="yt-result__title">${escHtml(r.title)}</div>
                <div class="yt-result__channel">${escHtml(r.channel)}</div>
            </div>
        </div>
    `
        )
        .join('');

    resultsBox.querySelectorAll('.yt-result').forEach((el) => {
        el.addEventListener('click', () => selectResult(el));
    });
}

function selectResult(el) {
    const { id, title, channel } = el.dataset;
    if (trackInput) trackInput.value = title;
    if (artistInput) artistInput.value = channel;
    if (embedInput) embedInput.value = id;
    if (linkInput) linkInput.value = `https://www.youtube.com/watch?v=${id}`;
    if (linkTypeInput) linkTypeInput.value = 'youtube';
    resultsBox.innerHTML = '';
}

function escHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}