/**
 * Sidebar navigation module.
 *
 * Owns two independent concerns that both live on the same <aside id="sidebar">:
 *  - the mobile drawer (topbar hamburger opens/closes an overlay panel)
 *  - the persistent desktop collapse rail (icon-only mode, remembered per browser)
 *
 * It also keeps the "Мій простір" profile links (which all point at the same
 * URL but different tabs) highlighted according to the current hash, since
 * that state only exists on the client.
 *
 * The storage key and the anti-flicker bootstrap live in sidebar-init.js,
 * which runs synchronously before this file — see window.Songstery.sidebar.
 */
const SidebarNav = (() => {
    const {storage, drawerBreakpoint} = window.Songstery.sidebar;

    const root = document.documentElement;
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileToggle = document.getElementById('sidebarToggle');
    const collapseToggle = document.getElementById('sidebarCollapseToggle');
    const collapseIcon = collapseToggle?.querySelector('[data-icon="collapse"]');
    const expandIcon = collapseToggle?.querySelector('[data-icon="expand"]');

    function isMobile() {
        return window.matchMedia(`(max-width: ${drawerBreakpoint()})`).matches;
    }

    function openDrawer() {
        sidebar.classList.add('open');
        overlay.hidden = false;
        document.body.style.overflow = 'hidden';
        mobileToggle?.setAttribute('aria-expanded', 'true');
        sidebar.querySelector('.nav-link')?.focus();
    }

    function closeDrawer({restoreFocus = false} = {}) {
        if (!sidebar.classList.contains('open')) return;
        sidebar.classList.remove('open');
        overlay.hidden = true;
        document.body.style.overflow = '';
        mobileToggle?.setAttribute('aria-expanded', 'false');
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
        // Native `hidden` rather than a CSS class: the correct icon shows
        // even if a stylesheet fails to load, and it stays in sync across
        // the lucide.createIcons() swap from <i> to <svg> because lucide
        // copies every attribute — including `hidden` — onto the new node.
        if (collapseIcon) collapseIcon.hidden = collapsed;
        if (expandIcon) expandIcon.hidden = !collapsed;
        storage.set(collapsed ? '1' : '0');
    }

    function toggleCollapsed() {
        setCollapsed(!root.classList.contains('sidebar-collapsed'));
    }

    function highlightProfileTab() {
        const links = sidebar.querySelectorAll('[data-profile-tab]');
        if (!links.length) return;

        const currentTab = location.pathname.includes('/profile')
            ? (location.hash.replace('#tab-', '') || 'saved')
            : null;

        links.forEach((link) => {
            link.classList.toggle('active', link.dataset.profileTab === currentTab);
        });
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

    function bindProfileHighlight() {
        window.addEventListener('hashchange', highlightProfileTab);
        highlightProfileTab();
    }

    function init() {
        if (!sidebar) return;
        bindDrawer();
        bindCollapse();
        bindProfileHighlight();
    }

    return {init, setCollapsed};
})();

document.addEventListener('DOMContentLoaded', SidebarNav.init);