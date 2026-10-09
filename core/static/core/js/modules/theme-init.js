window.Songstery = window.Songstery || {};

window.Songstery.theme = (() => {
    const STORAGE_KEY = 'songstery:theme';
    const ATTRIBUTE = 'data-theme';
    const THEMES = Object.freeze({LIGHT: 'light', DARK: 'dark'});

    const root = document.documentElement;
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)');

    function readStored() {
        try {
            return window.localStorage.getItem(STORAGE_KEY);
        } catch {
            return null;
        }
    }

    function writeStored(theme) {
        try {
            window.localStorage.setItem(STORAGE_KEY, theme);
        } catch {
            return;
        }
    }

    function resolve() {
        const stored = readStored();
        if (Object.values(THEMES).includes(stored)) return stored;
        return systemPrefersDark.matches ? THEMES.DARK : THEMES.LIGHT;
    }

    function apply(theme) {
        root.setAttribute(ATTRIBUTE, theme);
    }

    function current() {
        return root.getAttribute(ATTRIBUTE);
    }

    function set(theme) {
        apply(theme);
        writeStored(theme);
    }

    function toggle() {
        set(current() === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK);
    }

    systemPrefersDark.addEventListener('change', () => {
        if (!readStored()) apply(resolve());
    });

    apply(resolve());

    return {THEMES, current, set, toggle};
})();
