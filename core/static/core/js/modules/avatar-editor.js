window.Songstery = window.Songstery || {};

window.Songstery.createAvatarEditor = (root) => {
    const {createCoverChecker, createFieldFeedback, createAvatarCrop, dom} = window.Songstery;
    const stage = root.querySelector('[data-avatar-stage]');
    const feedbackNode = root.querySelector('[data-avatar-feedback]');
    const resetButton = root.querySelector('[data-avatar-reset]');
    if (!stage || !feedbackNode || !resetButton || !createCoverChecker || !createFieldFeedback || !createAvatarCrop) {
        return null;
    }

    const IMAGE_CLASS = 'user-avatar__image';
    const CSS_VARIABLES = Object.freeze({x: '--avatar-x', y: '--avatar-y', zoom: '--avatar-zoom'});

    const {avatar_url: urlInput, avatar_x: xInput, avatar_y: yInput, avatar_zoom: zoomInput} = root.elements;
    const slots = Array.from(root.querySelectorAll('.user-avatar'));
    const zoomUnit = Number(zoomInput.getAttribute('min'));
    const feedback = createFieldFeedback(feedbackNode, dom.readJson(root, '[data-avatar-copy]'));

    function render({x, y, zoom}) {
        xInput.value = Math.round(x);
        yInput.value = Math.round(y);
        zoomInput.value = Math.round(zoom);
        slots.forEach((slot) => {
            slot.style.setProperty(CSS_VARIABLES.x, `${x}%`);
            slot.style.setProperty(CSS_VARIABLES.y, `${y}%`);
            slot.style.setProperty(CSS_VARIABLES.zoom, String(zoom / zoomUnit));
        });
    }

    function imageIn(slot) {
        const existing = slot.querySelector(`.${IMAGE_CLASS}`);
        if (existing) return existing;
        const image = dom.element('img', IMAGE_CLASS);
        image.alt = '';
        image.referrerPolicy = 'no-referrer';
        image.decoding = 'async';
        slot.prepend(image);
        return image;
    }

    function renderImage(url) {
        slots.forEach((slot) => {
            if (!url) {
                slot.querySelector(`.${IMAGE_CLASS}`)?.remove();
                return;
            }
            const image = imageIn(slot);
            if (image.src !== url) image.src = url;
        });
    }

    const crop = createAvatarCrop({stage, fields: {x: xInput, y: yInput, zoom: zoomInput}, onChange: render});

    const checker = createCoverChecker({
        delay: Number(root.dataset.checkDelay),
        onState(state, url, image) {
            feedback.show(state);
            renderImage(url);
            crop.setImage(image ?? null);
            resetButton.hidden = state !== checker.STATES.OK;
        },
    });

    urlInput.addEventListener('input', () => {
        crop.reset();
        checker.schedule(urlInput.value);
    });
    zoomInput.addEventListener('input', () => crop.setZoom(Number(zoomInput.value)));
    resetButton.addEventListener('click', () => crop.reset());

    render(crop.state);
    checker.check(urlInput.value);
    if (urlInput.getAttribute('aria-invalid') === 'true') urlInput.focus();

    return {crop, checker};
};
