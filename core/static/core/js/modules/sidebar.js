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
 */
const SidebarNav = (() => {
    const COLLAPSE_STORAGE_KEY = 'songstery:sidebar-collapsed';
    const MOBILE_QUERY = '(max-width: 900px)';

    const root = document.documentElement;
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileToggle = document.getElementById('sidebarToggle');
    const collapseToggle = document.getElementById('sidebarCollapseToggle');

    function isMobile() {
        return window.matchMedia(MOBILE_QUERY).matches;
    }

    function openDrawer() {
        sidebar.classList.add('open');
        overlay.hidden = false;
        document.body.style.overflow = 'hidden';
        mobileToggle?.setAttribute('aria-expanded', 'true');
    }

    function closeDrawer() {
        sidebar.classList.remove('open');
        overlay.hidden = true;
        document.body.style.overflow = '';
        mobileToggle?.setAttribute('aria-expanded', 'false');
    }

    function toggleDrawer() {
        if (sidebar.classList.contains('open')) {
            closeDrawer();
        } else {
            openDrawer();
        }
    }

    function persistCollapsed(collapsed) {
        try {
            localStorage.setItem(COLLAPSE_STORAGE_KEY, collapsed ? '1' : '0');
        } catch (error) {
            /* storage unavailable — collapse state just won't survive reload */
        }
    }

    function setCollapsed(collapsed) {
        root.classList.toggle('sidebar-collapsed', collapsed);
        collapseToggle?.setAttribute('aria-expanded', String(!collapsed));
        collapseToggle?.setAttribute(
            'aria-label',
            collapsed ? 'Розгорнути бічну панель' : 'Згорнути бічну панель',
        );
        persistCollapsed(collapsed);
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
        overlay?.addEventListener('click', closeDrawer);

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && sidebar.classList.contains('open')) {
                closeDrawer();
            }
        });

        window.addEventListener('resize', () => {
            if (!isMobile()) closeDrawer();
        });

        sidebar.querySelectorAll('.nav-link, .sidebar__user').forEach((link) => {
            link.addEventListener('click', () => {
                if (isMobile() && sidebar.classList.contains('open')) closeDrawer();
            });
        });
    }

    function bindCollapse() {
        if (!collapseToggle) return;
        collapseToggle.addEventListener('click', toggleCollapsed);
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

    return { init, setCollapsed };
})();

document.addEventListener('DOMContentLoaded', SidebarNav.init);
