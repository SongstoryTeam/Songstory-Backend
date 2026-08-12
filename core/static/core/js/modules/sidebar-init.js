/**
 * Sidebar bootstrap.
 *
 * Loaded synchronously (no `defer`) before the sidebar markup, so the
 * collapsed rail is applied before first paint and never flashes open on
 * reload. Also the single place that owns the storage key and a safe
 * localStorage wrapper, so sidebar.js (deferred, loaded later) never has to
 * redeclare either — one source of truth instead of two files agreeing on a
 * magic string by convention.
 */
window.Songstery = window.Songstery || {};

Songstery.sidebar = (() => {
    const STORAGE_KEY = 'songstery:sidebar-collapsed';

    const storage = {
        get() {
            try {
                return window.localStorage.getItem(STORAGE_KEY);
            } catch (error) {
                return null;
            }
        },
        set(value) {
            try {
                window.localStorage.setItem(STORAGE_KEY, value);
            } catch (error) {
                /* storage unavailable (private mode, blocked cookies) —
                   the collapsed state just won't survive a reload */
            }
        },
    };

    /**
     * Reads the drawer breakpoint from CSS (`--bp-sidebar-drawer` in
     * tokens.css) instead of hardcoding it here too. Media query conditions
     * themselves still hardcode the same value — CSS can't read a custom
     * property there — so this keeps at least the JS side in sync with the
     * design token by construction rather than by a comment.
     */
    function drawerBreakpoint() {
        const value = getComputedStyle(document.documentElement)
            .getPropertyValue('--bp-sidebar-drawer')
            .trim();
        return value || '900px';
    }

    if (storage.get() === '1') {
        document.documentElement.classList.add('sidebar-collapsed');
    }

    return { storage, drawerBreakpoint };
})();
