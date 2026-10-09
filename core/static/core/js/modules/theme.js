document.addEventListener('click', (event) => {
    if (event.target.closest('[data-theme-toggle]')) window.Songstery.theme.toggle();
});
