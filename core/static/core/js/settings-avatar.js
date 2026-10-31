(() => {
    const root = document.querySelector('[data-avatar-editor]');
    const {createAvatarEditor} = window.Songstery || {};
    if (!root || !createAvatarEditor) return;

    createAvatarEditor(root);
})();
