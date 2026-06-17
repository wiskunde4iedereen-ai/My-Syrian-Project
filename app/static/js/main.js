document.addEventListener('DOMContentLoaded', function() {
    var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.display = 'none';
        }, 5000);
    });
    var links = document.querySelectorAll('body .sidebar-nav .nav-link');
    var path = window.location.pathname.replace(/\/+$/, '');
    links.forEach(function(link) {
        var href = link.getAttribute('href').replace(/\/+$/, '');
        if (href === path) {
            link.classList.add('active');
        }
    });
    var badge = document.querySelector('.badge-notif');
    if (badge) {
        fetch('/notifications/count')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var count = data.count || 0;
                document.querySelectorAll('.badge-notif').forEach(function(el) {
                    el.textContent = count;
                    el.style.display = count > 0 ? 'inline' : 'none';
                });
            })
            .catch(function() {});
    }
});
