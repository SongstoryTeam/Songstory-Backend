document.querySelectorAll('[data-catalog-filters]').forEach((form) => {
    form.addEventListener('change', () => form.requestSubmit());
});
