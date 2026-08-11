/**
 * Profile page tab switching.
 *
 * Reads the initial tab from the URL hash (e.g. #tab-playlists) so the
 * sidebar's "Мій простір" links can deep-link straight into a tab, and
 * keeps the hash in sync as the user clicks between tabs so the state
 * survives a refresh or gets shared via the URL. No-ops on any page that
 * doesn't have a tab bar.
 */
const ProfileTabs = (() => {
    const tabs = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-panel');

    function tabNameFromHash() {
        return location.hash.replace('#tab-', '');
    }

    function activate(tabName, { updateHash = true } = {}) {
        const panel = document.getElementById(`tab-${tabName}`);
        if (!panel) return;

        tabs.forEach((btn) => btn.classList.toggle('active', btn.dataset.tab === tabName));
        panels.forEach((p) => p.classList.toggle('active', p === panel));

        if (updateHash) {
            history.replaceState(null, '', `#tab-${tabName}`);
        }
    }

    function bind() {
        tabs.forEach((btn) => {
            btn.addEventListener('click', () => activate(btn.dataset.tab));
        });

        window.addEventListener('hashchange', () => {
            const tabName = tabNameFromHash();
            if (tabName) activate(tabName, { updateHash: false });
        });
    }

    function init() {
        if (!tabs.length) return;

        bind();

        const initialTab = tabNameFromHash();
        const hasInitialTab = initialTab && document.getElementById(`tab-${initialTab}`);
        if (hasInitialTab) {
            activate(initialTab, { updateHash: false });
        }
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', ProfileTabs.init);
