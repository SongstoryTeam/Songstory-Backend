const sidebar = document.getElementById('sidebar');
const toggle  = document.getElementById('sidebarToggle');
const overlay = document.getElementById('sidebarOverlay');

function openSidebar() {
  sidebar.classList.add('open');
  overlay.style.display = 'block';
}
function closeSidebar() {
  sidebar.classList.remove('open');
  overlay.style.display = 'none';
}

if (toggle) {
    toggle.addEventListener('click', () => {
        sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
}

if (overlay) {
    overlay.addEventListener('click', closeSidebar);
}


document.addEventListener('DOMContentLoaded', () => {
    const likeButtons = document.querySelectorAll('.like-btn');

    likeButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            this.classList.toggle('liked');
            const icon = this.querySelector('svg');

            if (icon) {
                if (this.classList.contains('liked')) {
                    icon.style.fill = 'currentColor';
                    icon.style.transform = 'scale(1.1)';
                } else {
                    icon.style.fill = 'none';
                    icon.style.transform = 'scale(1)';
                }
            }
        });
    });
});


document.addEventListener('DOMContentLoaded', () => {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const bookCards = document.querySelectorAll('.book-card');

    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => {
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-ghost');
            });
            button.classList.remove('btn-ghost');
            button.classList.add('btn-primary');

            const filterValue = button.getAttribute('data-filter');

            bookCards.forEach(card => {
                const cardCategory = card.getAttribute('data-category');

                if (filterValue === 'all' || filterValue === cardCategory) {
                    card.classList.remove('hidden');
                } else {
                    card.classList.add('hidden');
                }
            });
        });
    });
});