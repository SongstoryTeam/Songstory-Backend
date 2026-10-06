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

            }
        },
    };

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
