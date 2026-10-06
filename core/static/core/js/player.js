const PLAYER_HEIGHTS = {youtube: '', spotify: '152px'};
const OPEN_CLASS = 'is-playing';

function closePlayer(card) {
    card.classList.remove(OPEN_CLASS);
    card.querySelector('.track-card__player')?.replaceChildren();
    card.querySelector('[data-play]')?.setAttribute('aria-expanded', 'false');
}

function openPlayer(card, button) {
    const container = card.querySelector('.track-card__player');
    const frame = document.createElement('iframe');
    const source = new URL(button.dataset.embedUrl);
    if (button.dataset.platform === 'youtube') {
        source.searchParams.set('autoplay', '1');
        source.searchParams.set('rel', '0');
    }
    frame.src = source.toString();
    frame.title = button.dataset.title;
    frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    frame.loading = 'lazy';
    frame.className = `track-card__frame track-card__frame--${button.dataset.platform}`;
    const height = PLAYER_HEIGHTS[button.dataset.platform];
    if (height) frame.style.height = height;
    container.replaceChildren(frame);
    card.classList.add(OPEN_CLASS);
    button.setAttribute('aria-expanded', 'true');
}

document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-play]');
    if (!button) return;

    const card = button.closest('.track-card');
    const wasOpen = card.classList.contains(OPEN_CLASS);
    document.querySelectorAll(`.track-card.${OPEN_CLASS}`).forEach(closePlayer);
    if (!wasOpen) openPlayer(card, button);
});
