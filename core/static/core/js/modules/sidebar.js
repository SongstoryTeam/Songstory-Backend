const SidebarNav = (() => {
    const {storage, drawerBreakpoint} = window.Songstery.sidebar;

    const root = document.documentElement;
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileToggle = document.getElementById('sidebarToggle');
    const collapseToggle = document.getElementById('sidebarCollapseToggle');

    function isMobile() {
        return window.matchMedia(`(max-width: ${drawerBreakpoint()})`).matches;
    }

    function openDrawer() {
        sidebar.classList.add('open');
        overlay.hidden = false;

        requestAnimationFrame(() => overlay.classList.add('is-visible'));
        document.body.style.overflow = 'hidden';
        mobileToggle?.setAttribute('aria-expanded', 'true');
        sidebar.querySelector('.nav-link')?.focus();
    }

    function closeDrawer({restoreFocus = false} = {}) {
        if (!sidebar.classList.contains('open')) return;
        sidebar.classList.remove('open');
        overlay.classList.remove('is-visible');
        document.body.style.overflow = '';
        mobileToggle?.setAttribute('aria-expanded', 'false');

        window.setTimeout(() => {
            if (!sidebar.classList.contains('open')) overlay.hidden = true;
        }, 220);
        if (restoreFocus) mobileToggle?.focus();
    }

    function toggleDrawer() {
        if (sidebar.classList.contains('open')) {
            closeDrawer({restoreFocus: true});
        } else {
            openDrawer();
        }
    }

    function setCollapsed(collapsed) {
        root.classList.toggle('sidebar-collapsed', collapsed);
        collapseToggle?.setAttribute('aria-expanded', String(!collapsed));
        collapseToggle?.setAttribute(
            'aria-label',
            collapsed ? 'Розгорнути бічну панель' : 'Згорнути бічну панель',
        );
        storage.set(collapsed ? '1' : '0');
    }

    function toggleCollapsed() {
        setCollapsed(!root.classList.contains('sidebar-collapsed'));
    }

    function bindDrawer() {
        mobileToggle?.addEventListener('click', toggleDrawer);
        overlay?.addEventListener('click', () => closeDrawer({restoreFocus: true}));

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') closeDrawer({restoreFocus: true});
        });

        window.addEventListener('resize', () => {
            if (!isMobile()) closeDrawer();
        });

        sidebar.querySelectorAll('.nav-link, .sidebar__user').forEach((link) => {
            link.addEventListener('click', () => {
                if (isMobile()) closeDrawer();
            });
        });
    }

    function bindCollapse() {
        collapseToggle?.addEventListener('click', toggleCollapsed);
    }

    function init() {
        if (!sidebar) return;
        bindDrawer();
        bindCollapse();
    }

    return {init, setCollapsed};
})();

document.addEventListener('DOMContentLoaded', SidebarNav.init);
