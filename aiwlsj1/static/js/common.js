// 共享函数 - Tab切换  
function switchTab(tabId) {  
    // 隐藏所有tab内容  
    const tabContents = document.querySelectorAll('.tab-content');  
    tabContents.forEach(tab => tab.classList.remove('active'));  

    // 显示选中的tab内容  
    document.getElementById(tabId + '-tab').classList.add('active');  

    // 更新tab样式  
    const tabs = document.querySelectorAll('.tab');  
    tabs.forEach(tab => tab.classList.remove('active'));  

    // 激活当前选中的tab  
    event.currentTarget.classList.add('active');  
}  

// 共享函数 - 文件名更新  
function updateFileName(input) {  
    const fileNameDiv = document.getElementById('file-name');  
    if (input.files.length > 0) {  
        fileNameDiv.textContent = '已选择: ' + input.files[0].name;  
    } else {  
        fileNameDiv.textContent = '';  
    }  
}  

// 共享函数 - 初始化拖拽上传功能  
function initDropArea() {  
    // 拖拽上传逻辑...  
}