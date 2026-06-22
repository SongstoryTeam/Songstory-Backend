document.querySelectorAll('button[type="submit"]').forEach(btn => {
    btn.addEventListener('click', function () {
        const form = this.closest('form');
        if (form && form.checkValidity()) {
            const original = this.textContent;
            setTimeout(() => {
                this.disabled = true;
                this.dataset.original = original;
                this.textContent = 'Зачекайте…';
            }, 10);
        }
    });
});
