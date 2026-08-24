function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
}

document.querySelectorAll('.like-btn[data-url]').forEach((btn) => {
    btn.addEventListener('click', async function (e) {
        e.preventDefault();

        const url = this.dataset.url;
        const countEl = this.querySelector('.like-count');

        this.disabled = true;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (countEl) {
                countEl.textContent = data.likes_count;
            }
            this.classList.toggle('liked', data.liked);
        } catch (err) {
            console.error('Like request failed:', err);
        } finally {
            this.disabled = false;
        }
    });
});