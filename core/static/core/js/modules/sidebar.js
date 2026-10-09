const SidebarNav = (() => {
    const OPEN_CLASS = 'sidebar-open';
    const DRAWER_QUERY_TOKEN = '--mq-drawer';

    const root = document.documentElement;
    const sidebar = document.querySelector('[data-sidebar]');
    const toggle = document.querySelector('[data-sidebar-toggle]');
    const closers = document.querySelectorAll('[data-sidebar-close]');
    const backgroundRegions = document.querySelectorAll('[data-sidebar-background]');
    const drawerQuery = window.matchMedia(getComputedStyle(root).getPropertyValue(DRAWER_QUERY_TOKEN).trim());

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
        sidebar.querySelector('[data-sidebar-initial-focus]')?.focus();
    }

    function close({restoreFocus = true} = {}) {
        if (!isOpen()) return;
        render(false);
        if (restoreFocus) toggle.focus();
    }

    function bind() {
        toggle.addEventListener('click', () => (isOpen() ? close() : open()));
        closers.forEach((closer) => closer.addEventListener('click', () => close()));

        sidebar.addEventListener('click', (event) => {
            if (event.target.closest('a[href]')) close({restoreFocus: false});
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') close();
        });

        drawerQuery.addEventListener('change', (event) => {
            if (!event.matches) close({restoreFocus: false});
        });
    }

    function init() {
        if (!sidebar || !toggle) return;
        bind();
    }

    return {init, open, close};
})();

document.addEventListener('DOMContentLoaded', SidebarNav.init);
