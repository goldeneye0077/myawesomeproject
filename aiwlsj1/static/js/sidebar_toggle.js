document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.sidebar .nav-item').forEach(function(item) {
        var submenu = item.querySelector('.submenu');
        var link = item.querySelector('a');
        if(submenu && link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                var isOpen = submenu.style.display === 'block';
                // 关闭所有
                document.querySelectorAll('.sidebar .submenu').forEach(function(sm) {
                    sm.style.display = 'none';
                });
                // 展开当前
                submenu.style.display = isOpen ? 'none' : 'block';
            });
        }
    });
});
