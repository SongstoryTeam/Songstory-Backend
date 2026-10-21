(() => {
    const picker = document.querySelector('[data-theme-picker]');
    const theme = window.Songstery?.theme;
    if (!picker || !theme) return;

    const radios = Array.from(picker.querySelectorAll('[data-theme-option]'));
    const status = document.querySelector('[data-theme-status]');
    const summary = document.querySelector('[data-theme-summary]');

    const {SYSTEM} = theme.PREFERENCES;
    const CHOICE_LABELS = {light: 'Світла', dark: 'Темна', system: 'Як в системі'};
    const APPLIED_LABELS = {light: 'світлу', dark: 'темну'};

    function describe({preference, theme: applied}) {
        const base = `Зараз застосовано ${APPLIED_LABELS[applied]} тему`;
        return preference === SYSTEM ? `${base} — за налаштуванням вашого пристрою.` : `${base}.`;
    }

    function render(state) {
        radios.forEach((radio) => {
            radio.checked = radio.value === state.preference;
        });
        if (summary) summary.textContent = describe(state);
    }

    radios.forEach((radio) => {
        radio.addEventListener('change', () => {
            if (!radio.checked) return;
            theme.setPreference(radio.value);
            if (status) status.textContent = `Тему змінено: ${CHOICE_LABELS[radio.value]}`;
        });
    });

    theme.subscribe(render);
    render({preference: theme.preference(), theme: theme.resolved()});
})();
