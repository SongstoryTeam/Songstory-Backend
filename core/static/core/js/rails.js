const SCROLL_FRACTION = 0.9;
const EDGE_TOLERANCE = 2;

function setupRail(shelf) {
    const rail = shelf.querySelector('[data-rail]');
    const controls = shelf.querySelector('[data-rail-controls]');
    const previous = shelf.querySelector('[data-rail-prev]');
    const next = shelf.querySelector('[data-rail-next]');
    if (!rail || !controls || !previous || !next) return;

    const update = () => {
        const overflowing = rail.scrollWidth - rail.clientWidth > EDGE_TOLERANCE;
        controls.hidden = !overflowing;
        previous.disabled = rail.scrollLeft <= EDGE_TOLERANCE;
        next.disabled = rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - EDGE_TOLERANCE;
    };
    const scroll = (direction) =>
        rail.scrollBy({left: direction * rail.clientWidth * SCROLL_FRACTION, behavior: 'smooth'});

    previous.addEventListener('click', () => scroll(-1));
    next.addEventListener('click', () => scroll(1));
    rail.addEventListener('scroll', update, {passive: true});
    window.addEventListener('resize', update);
    update();
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.shelf').forEach(setupRail);
});
