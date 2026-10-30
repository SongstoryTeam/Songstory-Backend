(() => {
    const bar = document.querySelector('[data-bulk-bar]');
    if (!bar) return;

    const master = bar.querySelector('[data-select-all]');
    const counter = bar.querySelector('[data-bulk-count]');
    const actions = bar.querySelectorAll('[data-bulk-action]');
    const rows = () => Array.from(document.querySelectorAll('[data-select-row]'));

    function sync() {
        const all = rows();
        const checked = all.filter((row) => row.checked).length;
        master.checked = checked > 0 && checked === all.length;
        master.indeterminate = checked > 0 && checked < all.length;
        counter.textContent = checked
            ? bar.dataset.countLabel.replace('{count}', checked)
            : bar.dataset.emptyLabel;
        actions.forEach((button) => {
            button.disabled = checked === 0;
        });
    }

    master.addEventListener('change', () => {
        rows().forEach((row) => {
            row.checked = master.checked;
        });
        sync();
    });

    document.addEventListener('change', (event) => {
        if (event.target.matches('[data-select-row]')) sync();
    });

    window.addEventListener('pageshow', sync);
    sync();
})();
