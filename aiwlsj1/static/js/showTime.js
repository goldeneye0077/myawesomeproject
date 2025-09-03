let timer;
// 放置的节点
let showNode = document.getElementById('showTime');
// 时间设置函数
let showTime = function () {
    let date = new Date();
    let year = date.getFullYear();
    let month = date.getMonth() + 1;
    let day = date.getDate();
    let hours = date.getHours();
    let minutes = date.getMinutes();
    let seconds = date.getSeconds();
    let week = date.getDay()
    // 补零
    month = (month < 10 ? "0" : "") + month;
    day = (day < 10 ? "0" : "") + day;
    hours = (hours < 10 ? "0" : "") + hours;
    minutes = (minutes < 10 ? "0" : "") + minutes;
    seconds = (seconds < 10 ? "0" : "") + seconds;
    // 设置时间
    let curDate = year + "-" + month + "-" + day;
    let curTime = hours + ":" + minutes + ":" + seconds;
    let curWeek = "星期" + "日一二三四五六".charAt(week)
    showNode.innerHTML = curTime+'    '+curDate;
};

// 清除定时器timer
clearInterval(timer);
// 启动定时器timer
timer = setInterval(() => {
    showTime();
}, 1000);