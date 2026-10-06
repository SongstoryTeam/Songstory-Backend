function applyIconSizes() {
    document.querySelectorAll('[data-lucide][size]').forEach((element) => {
        const size = element.getAttribute('size');
        element.setAttribute('width', size);
        element.setAttribute('height', size);
        element.removeAttribute('size');
    });
}

document.addEventListener('DOMContentLoaded', () => {
    applyIconSizes();
    window.lucide?.createIcons();

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
});
