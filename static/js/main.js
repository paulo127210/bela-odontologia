// Sidebar toggle (mobile)
document.addEventListener('DOMContentLoaded', () => {
    const toggler = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggler && sidebar) {
        toggler.addEventListener('click', () => sidebar.classList.toggle('open'));
    }

    // Mark active nav link
    const links = document.querySelectorAll('#sidebar .nav-link');
    links.forEach(link => {
        if (link.href === window.location.href ||
            (link.href !== window.location.origin + '/' &&
             window.location.pathname.startsWith(new URL(link.href).pathname))) {
            link.classList.add('active');
        }
    });

    // Auto-dismiss alerts
    document.querySelectorAll('.alert-auto').forEach(el => {
        setTimeout(() => {
            el.style.transition = 'opacity .5s';
            el.style.opacity = 0;
            setTimeout(() => el.remove(), 500);
        }, 3500);
    });
});
