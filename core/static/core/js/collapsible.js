const READY_CLASS = 'is-ready';
const OPEN_CLASS = 'is-open';
const STAGGER_STEP = 45;

function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function closePlayers(body) {
    body.querySelectorAll('.track-card.is-playing [data-play]').forEach((button) => button.click());
}

function setOpen(root, open) {
    const toggle = root.querySelector('[data-collapsible-toggle]');
    const body = root.querySelector('[data-collapsible-body]');
    const label = root.querySelector('[data-collapsible-label]');

    root.classList.toggle(OPEN_CLASS, open);
    toggle.setAttribute('aria-expanded', String(open));
    label.textContent = open ? toggle.dataset.labelOpen : toggle.dataset.labelClosed;
    body.inert = !open;

    if (open) return;
    closePlayers(body);
    if (toggle.getBoundingClientRect().top < 0) {
        toggle.scrollIntoView({block: 'center', behavior: prefersReducedMotion() ? 'auto' : 'smooth'});
    }
}

function setupCollapsible(root) {
    const toggle = root.querySelector('[data-collapsible-toggle]');
    const body = root.querySelector('[data-collapsible-body]');

    root.querySelectorAll('[data-collapsible-item]').forEach((item, index) => {
        item.style.setProperty('--i', index);
        item.style.setProperty('--stagger', `${STAGGER_STEP}ms`);
    });

    body.inert = true;
    toggle.hidden = false;
    root.classList.add(READY_CLASS);
    toggle.addEventListener('click', () => setOpen(root, !root.classList.contains(OPEN_CLASS)));
}

document.querySelectorAll('[data-collapsible]').forEach(setupCollapsible);
