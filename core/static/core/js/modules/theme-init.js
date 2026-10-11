window.Songstery = window.Songstery || {};

/**
 * Модуль теми. Підключається синхронно в <head>, щоб тема застосувалась до
 * першого малювання сторінки (без «мигання»).
 *
 * Збережена перевага: 'light' | 'dark' | 'system' (за замовчуванням — 'system').
 * На <html> завжди виставляються:
 *   data-theme            — фактична тема ('light' | 'dark'), її читає CSS;
 *   data-theme-preference — вибір користувача ('light' | 'dark' | 'system').
 */
window.Songstery.theme = (() => {
    const STORAGE_KEY = 'songstery:theme';
    const CHANGE_EVENT = 'songstery:themechange';
    const PREFERENCES = Object.freeze({LIGHT: 'light', DARK: 'dark', SYSTEM: 'system'});

    const root = document.documentElement;
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    const isPreference = (value) => Object.values(PREFERENCES).includes(value);

    function readStored() {
        try {
            return window.localStorage.getItem(STORAGE_KEY);
        } catch {
            return null;
        }
    }

    function writeStored(preference) {
        try {
            if (preference === PREFERENCES.SYSTEM) window.localStorage.removeItem(STORAGE_KEY);
            else window.localStorage.setItem(STORAGE_KEY, preference);
        } catch {
            // Сховище недоступне (приватний режим) — тема діє лише на цій сторінці.
        }
    }

    function preference() {
        const stored = readStored();
        return isPreference(stored) ? stored : PREFERENCES.SYSTEM;
    }

    function resolve(value = preference()) {
        if (value !== PREFERENCES.SYSTEM) return value;
        return systemPrefersDark.matches ? PREFERENCES.DARK : PREFERENCES.LIGHT;
    }

    function apply() {
        const value = preference();
        root.setAttribute('data-theme', resolve(value));
        root.setAttribute('data-theme-preference', value);
        document.dispatchEvent(new CustomEvent(CHANGE_EVENT, {detail: {preference: value, theme: resolve(value)}}));
    }

    function setPreference(value) {
        if (!isPreference(value)) return;
        writeStored(value);
        apply();
    }

    function subscribe(listener) {
        document.addEventListener(CHANGE_EVENT, (event) => listener(event.detail));
    }

    systemPrefersDark.addEventListener('change', () => {
        if (preference() === PREFERENCES.SYSTEM) apply();
    });
    window.addEventListener('storage', (event) => {
        if (event.key === STORAGE_KEY || event.key === null) apply();
    });

    apply();

    return {PREFERENCES, preference, resolved: () => resolve(), setPreference, subscribe};
})();
