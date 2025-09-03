// 可视化适配

// 初始化大屏宽、高
let width = 1920;
let height = 1080;
// ScaleBox适配容器
let scaleBox=document.getElementById('scaleBox')
// 计算缩放比例
let getScale = function () {
    // 水平伸缩比例
    const w = window.innerWidth / width;
    // 垂直伸缩比例
    const h = window.innerHeight / height;
    // 返回水平、垂直伸缩比例,如果两个返回w,则是适配宽度;如果两个返回h,则是适配高度;
    // console.log(w,h);
    return w < h ? w : h;  //  根据高宽缩放
    // return [w,h]; 
};
// 设置ScaleBox容器缩放
let setScale = function () {
    // 获得水平、垂直伸缩比例
    scale = getScale();
    // 水平伸缩比例
    scale_x=scale
    // 垂直伸缩比例
    scale_y=scale
    // scale_y=scale_x
    // 伸缩元素,垂直居中大屏
    if (scaleBox) {
        // scaleBox.style.setProperty("transform", "scale("+ scale+","+scale+")"+" "+"translateX("+"-50%"+")"+" "+"translateY("+"-50%"+")");
        scaleBox.style.setProperty("--scale", scale);
    }
};
// 防抖函数
let debounce = function (fn, delay) {
    const delays = delay || 200;
    let timer;
    return function () {
        const th = this;
        const args = arguments;
        if (timer) {
            clearTimeout(timer);
        }
        timer = setTimeout(function () {
            timer = null;
            fn.apply(th, args);
        }, delays);
    };
};
// 添加resize事件监听
window.addEventListener("resize",debounce(setScale));
// 添加加载事件监听
window.addEventListener("load",debounce(setScale));


