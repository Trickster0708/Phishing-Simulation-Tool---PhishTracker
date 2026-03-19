// PhishTracker — Main JavaScript

// ── Sidebar Toggle ────────────────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('open');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function(e) {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('menuToggle');
    if (!sidebar || !toggle) return;
    if (window.innerWidth <= 768 &&
        !sidebar.contains(e.target) &&
        !toggle.contains(e.target) &&
        sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
    }
});

// ── Auto-dismiss alerts after 5s ────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Animate metric bars in
    const fills = document.querySelectorAll('.metric-bar-fill');
    fills.forEach(function(fill) {
        const target = fill.style.width;
        fill.style.width = '0';
        setTimeout(() => { fill.style.width = target; }, 200);
    });
});

// ── Confirm dangerous actions ────────────────────────────────────────
function confirmLaunch(e) {
    if (!confirm('🚀 Launch this campaign?\n\nThis will send phishing simulation emails to all target addresses. Continue?')) {
        e.preventDefault();
        return false;
    }
}
