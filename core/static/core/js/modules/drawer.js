const DrawerNav = (() => {
    const OPEN_CLASS = 'drawer-open';
    const STAGGER_PROPERTY = '--stagger-index';

    const root = document.documentElement;
    const drawer = document.querySelector('[data-drawer]');
    const toggle = document.querySelector('[data-drawer-toggle]');
    const closers = document.querySelectorAll('[data-drawer-close]');
    const backgroundRegions = document.querySelectorAll('[data-drawer-background]');

    function isOpen() {
        return root.classList.contains(OPEN_CLASS);
    }

    function render(open) {
        root.classList.toggle(OPEN_CLASS, open);
        toggle.setAttribute('aria-expanded', String(open));
        backgroundRegions.forEach((region) => {
            region.inert = open;
        });
    }

    function open() {
        if (isOpen()) return;
        render(true);
        drawer.querySelector('[data-drawer-initial-focus]')?.focus();
    }

    function close({restoreFocus = true} = {}) {
        if (!isOpen()) return;
        render(false);
        if (restoreFocus) toggle.focus();
    }

    function indexItems() {
        drawer.querySelectorAll('[data-drawer-item]').forEach((item, index) => {
            item.style.setProperty(STAGGER_PROPERTY, index);
        });
    }

    function bind() {
        toggle.addEventListener('click', () => (isOpen() ? close() : open()));
        closers.forEach((closer) => closer.addEventListener('click', () => close()));

        drawer.addEventListener('click', (event) => {
            if (event.target.closest('a[href]')) close({restoreFocus: false});
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') close();
        });
    }

    function init() {
        if (!drawer || !toggle) return;
        indexItems();
        bind();
    }

    return {init, open, close};
})();

document.addEventListener('DOMContentLoaded', DrawerNav.init);
