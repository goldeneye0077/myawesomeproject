document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.fold-menu .fold-toggle').forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            var submenu = this.parentElement.querySelector('.submenu');
            var isOpen = submenu.style.display === 'block';
            // 关闭所有
            document.querySelectorAll('.fold-menu .submenu').forEach(function(sm) {
                sm.style.display = 'none';
            });
            submenu.style.display = isOpen ? 'none' : 'block';
        });
    });
});
