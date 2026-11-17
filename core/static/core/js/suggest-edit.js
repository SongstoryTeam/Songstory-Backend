(() => {
    const root = document.querySelector('[data-suggest-edit]');
    const {createBookPreview, createChangeTracker} = window.Songstory || {};
    const form = root?.querySelector('[data-book-form]');
    if (!form || !createBookPreview || !createChangeTracker) return;

    createBookPreview(root, form);
    createChangeTracker(root, form);
})();
