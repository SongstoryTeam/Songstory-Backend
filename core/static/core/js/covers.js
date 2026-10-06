document.addEventListener(
    'error',
    (event) => {
        const image = event.target;
        if (image instanceof HTMLImageElement && image.hasAttribute('data-cover')) {
            image.remove();
        }
    },
    true,
);
