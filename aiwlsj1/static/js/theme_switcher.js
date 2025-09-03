// 主题切换工具
class ThemeSwitcher {
    constructor() {
        this.themes = {
            'professional': '专业蓝色',
            'modern': '现代灰色',
            'nature': '自然绿色'
        };
        this.currentTheme = localStorage.getItem('selectedTheme') || 'professional';
        this.init();
    }

    init() {
        this.createSwitcher();
        this.applyTheme(this.currentTheme);
    }

    createSwitcher() {
        // 创建主题切换按钮
        const switcher = document.createElement('div');
        switcher.className = 'theme-switcher';
        switcher.innerHTML = `
            <div class="theme-switcher-toggle" title="切换主题">
                🎨
            </div>
            <div class="theme-switcher-panel">
                <div class="theme-switcher-title">选择主题</div>
                ${Object.entries(this.themes).map(([key, name]) => `
                    <div class="theme-option ${key === this.currentTheme ? 'active' : ''}" 
                         data-theme="${key}">
                        <div class="theme-preview theme-preview-${key}"></div>
                        <span>${name}</span>
                    </div>
                `).join('')}
            </div>
        `;

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .theme-switcher {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
            }

            .theme-switcher-toggle {
                width: 25px;
                height: 25px;
                background: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                cursor: pointer;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
                transition: all 0.3s ease;
                border: 1px solid #e2e8f0;
            }

            .theme-switcher-toggle:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
            }

            .theme-switcher-panel {
                position: absolute;
                top: 35px;
                right: 0;
                background: white;
                border-radius: 8px;
                padding: 12px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                min-width: 160px;
                opacity: 0;
                visibility: hidden;
                transform: translateY(-10px);
                transition: all 0.3s ease;
            }

            .theme-switcher.active .theme-switcher-panel {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }

            .theme-switcher-title {
                font-weight: 600;
                margin-bottom: 12px;
                color: #374151;
                font-size: 14px;
            }

            .theme-option {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 8px 12px;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s ease;
                margin-bottom: 4px;
            }

            .theme-option:hover {
                background: #f8fafc;
            }

            .theme-option.active {
                background: #dbeafe;
                color: #1d4ed8;
                font-weight: 600;
            }

            .theme-preview {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 1px solid #e2e8f0;
            }

            .theme-preview-professional {
                background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            }

            .theme-preview-modern {
                background: linear-gradient(135deg, #374151 0%, #6b7280 100%);
            }

            .theme-preview-nature {
                background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            }

            @media (max-width: 768px) {
                .theme-switcher {
                    top: 10px;
                    right: 10px;
                }

                .theme-switcher-toggle {
                    width: 40px;
                    height: 40px;
                    font-size: 16px;
                }

                .theme-switcher-panel {
                    right: -50px;
                    min-width: 180px;
                }
            }
        `;
        document.head.appendChild(style);

        // 添加到页面
        document.body.appendChild(switcher);

        // 绑定事件
        this.bindEvents(switcher);
    }

    bindEvents(switcher) {
        const toggle = switcher.querySelector('.theme-switcher-toggle');
        const panel = switcher.querySelector('.theme-switcher-panel');
        const options = switcher.querySelectorAll('.theme-option');

        // 切换面板显示
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            switcher.classList.toggle('active');
        });

        // 点击其他地方关闭面板
        document.addEventListener('click', (e) => {
            if (!switcher.contains(e.target)) {
                switcher.classList.remove('active');
            }
        });

        // 主题选择
        options.forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const theme = option.dataset.theme;
                this.switchTheme(theme);
                
                // 更新选中状态
                options.forEach(opt => opt.classList.remove('active'));
                option.classList.add('active');
                
                // 关闭面板
                switcher.classList.remove('active');
            });
        });
    }

    switchTheme(theme) {
        this.currentTheme = theme;
        localStorage.setItem('selectedTheme', theme);
        this.applyTheme(theme);
        
        // 显示切换提示
        this.showNotification(`已切换到${this.themes[theme]}主题`);
    }

    applyTheme(theme) {
        // 移除所有主题类
        document.body.classList.remove('theme-professional', 'theme-modern', 'theme-nature');
        
        // 添加新主题类
        if (theme !== 'professional') {
            document.body.classList.add(`theme-${theme}`);
        }
    }

    showNotification(message) {
        // 创建通知
        const notification = document.createElement('div');
        notification.className = 'theme-notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            z-index: 1001;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;

        document.body.appendChild(notification);

        // 显示动画
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // 自动隐藏
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 2000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new ThemeSwitcher();
});
