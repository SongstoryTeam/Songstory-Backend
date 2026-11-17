(() => {
    const root = document.querySelector('[data-avatar-editor]');
    const {createAvatarEditor} = window.Songstory || {};
    if (!root || !createAvatarEditor) return;

    createAvatarEditor(root);
})();
