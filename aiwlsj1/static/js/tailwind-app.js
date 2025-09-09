// Tailwind App JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 初始化侧边栏折叠功能
    initSidebarCollapse();
    
    // 初始化表格功能
    initTableFeatures();
    
    // 初始化模态框
    initModals();
    
    // 初始化提示信息
    initTooltips();
    
    // 初始化图表交互
    initChartInteractions();
});

// 侧边栏折叠功能
function initSidebarCollapse() {
    const collapseButtons = document.querySelectorAll('[data-collapse-toggle]');
    
    collapseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-collapse-toggle');
            const targetElement = document.getElementById(targetId);
            const icon = this.querySelector('svg');
            
            if (targetElement) {
                if (targetElement.classList.contains('hidden')) {
                    targetElement.classList.remove('hidden');
                    icon && icon.classList.add('rotate-180');
                } else {
                    targetElement.classList.add('hidden');
                    icon && icon.classList.remove('rotate-180');
                }
            }
        });
    });
}

// 表格功能增强
function initTableFeatures() {
    // 表格行悬停效果
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.classList.add('bg-gray-50');
        });
        
        row.addEventListener('mouseleave', function() {
            this.classList.remove('bg-gray-50');
        });
    });
    
    // 表格排序功能
    const sortableHeaders = document.querySelectorAll('[data-sort]');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const column = this.getAttribute('data-sort');
            sortTable(column, this);
        });
    });
}

// 表格排序
function sortTable(column, header) {
    const table = header.closest('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAscending = header.getAttribute('data-sort-direction') !== 'asc';
    
    // 重置所有排序图标
    const allHeaders = table.querySelectorAll('[data-sort]');
    allHeaders.forEach(h => {
        h.removeAttribute('data-sort-direction');
        const icon = h.querySelector('.sort-icon');
        if (icon) icon.textContent = '↕️';
    });
    
    // 设置当前排序方向
    header.setAttribute('data-sort-direction', isAscending ? 'asc' : 'desc');
    const icon = header.querySelector('.sort-icon');
    if (icon) icon.textContent = isAscending ? '↑' : '↓';
    
    // 排序行
    const columnIndex = Array.from(header.parentNode.children).indexOf(header);
    rows.sort((a, b) => {
        const aValue = a.children[columnIndex].textContent.trim();
        const bValue = b.children[columnIndex].textContent.trim();
        
        // 尝试数字比较
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // 字符串比较
        return isAscending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
    });
    
    // 重新插入排序后的行
    rows.forEach(row => tbody.appendChild(row));
}

// 模态框功能
function initModals() {
    // 打开模态框
    const modalTriggers = document.querySelectorAll('[data-modal-toggle]');
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal-toggle');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove('hidden');
                modal.classList.add('flex');
                document.body.style.overflow = 'hidden';
            }
        });
    });
    
    // 关闭模态框
    const modalCloses = document.querySelectorAll('[data-modal-hide]');
    modalCloses.forEach(close => {
        close.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal-hide');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                document.body.style.overflow = 'auto';
            }
        });
    });
    
    // 点击背景关闭模态框
    const modals = document.querySelectorAll('.modal-backdrop');
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
                this.classList.remove('flex');
                document.body.style.overflow = 'auto';
            }
        });
    });
}

// 提示信息功能
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    
    tooltips.forEach(element => {
        const tooltipText = element.getAttribute('data-tooltip');
        
        element.addEventListener('mouseenter', function() {
            showTooltip(this, tooltipText);
        });
        
        element.addEventListener('mouseleave', function() {
            hideTooltip();
        });
    });
}

function showTooltip(element, text) {
    const tooltip = document.createElement('div');
    tooltip.className = 'absolute z-50 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg shadow-sm opacity-0 tooltip';
    tooltip.textContent = text;
    
    document.body.appendChild(tooltip);
    
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
    
    setTimeout(() => {
        tooltip.style.opacity = '1';
    }, 10);
}

function hideTooltip() {
    const tooltip = document.querySelector('.tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// 图表交互功能
function initChartInteractions() {
    // 图表缩放功能
    const charts = document.querySelectorAll('.chart-container');
    charts.forEach(chart => {
        const fullscreenBtn = chart.querySelector('.fullscreen-btn');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', function() {
                toggleChartFullscreen(chart);
            });
        }
    });
}

function toggleChartFullscreen(chartContainer) {
    if (chartContainer.classList.contains('fullscreen')) {
        chartContainer.classList.remove('fullscreen', 'fixed', 'inset-0', 'z-50', 'bg-white');
        document.body.style.overflow = 'auto';
    } else {
        chartContainer.classList.add('fullscreen', 'fixed', 'inset-0', 'z-50', 'bg-white');
        document.body.style.overflow = 'hidden';
    }
}

// 通用工具函数
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full opacity-0`;
    
    switch(type) {
        case 'success':
            notification.classList.add('bg-green-500', 'text-white');
            break;
        case 'error':
            notification.classList.add('bg-red-500', 'text-white');
            break;
        case 'warning':
            notification.classList.add('bg-yellow-500', 'text-white');
            break;
        default:
            notification.classList.add('bg-blue-500', 'text-white');
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.remove('translate-x-full', 'opacity-0');
    }, 100);
    
    setTimeout(() => {
        notification.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 导出全局函数
window.showNotification = showNotification;
window.debounce = debounce;