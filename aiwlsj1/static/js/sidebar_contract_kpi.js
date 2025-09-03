document.addEventListener('DOMContentLoaded', function() {
    // 一级菜单 toggle 选择器
    var toggles = document.querySelectorAll('.main-contract-parent > .main-contract-toggle, .main-kpi-parent > .main-kpi-toggle, .huiju-parent > .huiju-toggle');
    var parents = document.querySelectorAll('.main-contract-parent, .main-kpi-parent, .huiju-parent');

    // 点击一级菜单时，展开当前，折叠其它
    toggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            parents.forEach(function(parent) {
                var submenu = parent.querySelector('.submenu');
                if (!submenu) return;
                if (parent.contains(toggle)) {
                    // 当前 toggle
                    var isOpen = submenu.style.display === 'block';
                    submenu.style.display = isOpen ? 'none' : 'block';
                } else {
                    submenu.style.display = 'none';
                }
            });
        });
    });

    // 页面加载时自动展开当前页面对应的一级菜单
    function autoExpandMenu() {
        var path = window.location.pathname;
        var matched = false;
        parents.forEach(function(parent) {
            var submenu = parent.querySelector('.submenu');
            if (!submenu) return;
            // 遍历submenu下所有a标签
            var links = submenu.querySelectorAll('a');
            var found = false;
            links.forEach(function(link) {
                if (link.getAttribute('href') === path) {
                    found = true;
                }
            });
            if (found) {
                submenu.style.display = 'block';
                matched = true;
            } else {
                submenu.style.display = 'none';
            }
        });
    }
    autoExpandMenu();
});
