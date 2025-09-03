document.addEventListener('DOMContentLoaded', function() {
    var pueToggle = document.querySelector('.pue-toggle');
    var submenu = document.querySelector('.pue-parent .submenu');
    var arrow = document.querySelector('.pue-toggle .arrow svg');
    if (pueToggle && submenu) {
        pueToggle.addEventListener('click', function(e) {
            e.preventDefault();
            if (submenu.style.display === 'block') {
                submenu.style.display = 'none';
                arrow.style.transform = 'rotate(0deg)';
            } else {
                submenu.style.display = 'block';
                arrow.style.transform = 'rotate(180deg)';
            }
        });
        // 如果当前页面是子菜单，自动展开
        if (window.location.pathname === '/pue/chart') {
            submenu.style.display = 'block';
            arrow.style.transform = 'rotate(180deg)';
        }
    }

    // 契约化攻坚指标管理二级菜单
    var contractToggle = document.querySelector('.contract-toggle');
    var contractParent = document.querySelector('.contract-parent');
    var contractSubmenu = contractParent ? contractParent.querySelector('.submenu') : null;
    var contractArrow = contractToggle ? contractToggle.querySelector('.arrow svg') : null;
    if (contractToggle && contractSubmenu && contractArrow) {
        contractToggle.addEventListener('click', function(e) {
            e.preventDefault();
            if (contractSubmenu.style.display === 'block') {
                contractSubmenu.style.display = 'none';
                contractArrow.style.transform = 'rotate(0deg)';
            } else {
                contractSubmenu.style.display = 'block';
                contractArrow.style.transform = 'rotate(180deg)';
            }
        });
        // 如果当前页面是子菜单，自动展开
        if (window.location.pathname === '/bi') {
            contractSubmenu.style.display = 'block';
            contractArrow.style.transform = 'rotate(180deg)';
        }
    }

    // KPI指标管理二级菜单
    var kpiToggle = document.querySelector('.kpi-toggle');
    var kpiParent = document.querySelector('.kpi-parent');
    var kpiSubmenu = kpiParent ? kpiParent.querySelector('.submenu') : null;
    var kpiArrow = kpiToggle ? kpiToggle.querySelector('.arrow svg') : null;
    if (kpiToggle && kpiSubmenu && kpiArrow) {
        kpiToggle.addEventListener('click', function(e) {
            e.preventDefault();
            if (kpiSubmenu.style.display === 'block') {
                kpiSubmenu.style.display = 'none';
                kpiArrow.style.transform = 'rotate(0deg)';
            } else {
                kpiSubmenu.style.display = 'block';
                kpiArrow.style.transform = 'rotate(180deg)';
            }
        });
        // 如果当前页面是子菜单，自动展开
        if (window.location.pathname === '/bi2') {
            kpiSubmenu.style.display = 'block';
            kpiArrow.style.transform = 'rotate(180deg)';
        }
    }
});
