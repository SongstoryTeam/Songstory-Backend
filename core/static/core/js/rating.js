const ratingWidget = document.getElementById('star-rating');
if (ratingWidget) {
    const scoreInput = ratingWidget.querySelector('input[name="score"]');
    const stars = ratingWidget.querySelectorAll('.star-btn');

    stars.forEach((star) => {
        star.addEventListener('mouseenter', () => highlightUpTo(star.dataset.value));
        star.addEventListener('mouseleave', () => highlightUpTo(scoreInput.value || 0));
        star.addEventListener('click', (e) => {
            e.preventDefault();
            scoreInput.value = star.dataset.value;
            highlightUpTo(star.dataset.value);
            ratingWidget.submit();
        });
    });

    function highlightUpTo(value) {
        stars.forEach((s) => {
            s.classList.toggle('star-btn--active', Number(s.dataset.value) <= Number(value));
        });
    }

    highlightUpTo(scoreInput.value || 0);
}