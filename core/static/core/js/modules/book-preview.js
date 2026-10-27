window.Songstery = window.Songstery || {};

window.Songstery.createBookPreview = (root, form) => {
    const {createCoverChecker, dom} = window.Songstery;
    const preview = root.querySelector('[data-preview]');
    if (!preview || !createCoverChecker) return null;

    const MODIFIERS = Object.freeze({pending: 'pending', ok: 'ok', invalid: 'error', broken: 'error'});
    const FEEDBACK_CLASS = 'field-feedback';

    const copy = dom.readJson(preview, '[data-preview-copy]');
    const part = (name) => preview.querySelector(`[data-preview-${name}]`);
    const cover = part('cover');
    const fallback = part('fallback');
    const title = part('title');
    const author = part('author');
    const meta = part('meta');
    const feedback = root.querySelector('[data-cover-feedback]');
    const field = (name) => form.elements[name];
    const read = (name) => field(name).value.trim();

    const image = dom.element('img');
    image.alt = '';

    function renderText() {
        const heading = read('title') || copy.placeholder;
        title.textContent = heading;
        fallback.textContent = heading;

        author.textContent = read('author_name');
        author.hidden = !author.textContent;

        meta.textContent = [read('year'), read('genre_name')].filter(Boolean).join(' · ');
        meta.hidden = !meta.textContent;
    }

    function renderCover(state, url) {
        if (url) {
            image.src = url;
            cover.append(image);
        } else {
            image.remove();
        }

        const modifier = MODIFIERS[state];
        feedback.textContent = copy.cover[state] ?? '';
        feedback.className = modifier ? `${FEEDBACK_CLASS} ${FEEDBACK_CLASS}--${modifier}` : FEEDBACK_CLASS;
    }

    const coverChecker = createCoverChecker({delay: Number(preview.dataset.coverDelay), onState: renderCover});

    form.addEventListener('input', (event) => {
        renderText();
        if (event.target === field('cover_url')) coverChecker.schedule(event.target.value);
    });

    renderText();
    coverChecker.check(field('cover_url').value);
    preview.hidden = false;

    return {refresh: renderText};
};
