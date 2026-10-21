function applyIconSizes() {
    document.querySelectorAll('[data-lucide][size]').forEach((element) => {
        const size = element.getAttribute('size');
        element.setAttribute('width', size);
        element.setAttribute('height', size);
        element.removeAttribute('size');
    });
}

async function setupServiceWorker() {
    if (!('serviceWorker' in navigator)) return;

    const {serviceWorkerUrl, cachePrefix} = document.documentElement.dataset;
    try {
        if (serviceWorkerUrl) {
            await navigator.serviceWorker.register(serviceWorkerUrl);
            return;
        }

        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map((registration) => registration.unregister()));

        if ('caches' in window) {
            const keys = await caches.keys();
            await Promise.all(keys.filter((key) => key.startsWith(cachePrefix)).map((key) => caches.delete(key)));
        }
    } catch (error) {
        return;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    applyIconSizes();
    window.lucide?.createIcons();
    setupServiceWorker();
});
