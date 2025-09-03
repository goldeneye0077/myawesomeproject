// 只用 axios 动态获取后端数据并渲染
var hostname = window.location.hostname;
if (hostname == '') hostname = '127.0.0.1';
var port = '8000';
var baseUrl = `http://${hostname}:${port}`;

axios.get(baseUrl + '/api/bi_data').then(res => {
    const {
        centerTopTopData,
        centerTopBottomData,
        leftTopData,
        leftMiddleData,
        rightTopData,
        rightMiddleData,
        bottomData
    } = res.data;

    new Vue({
        el: '#pageContainer',
        data: {
            baseUrl: baseUrl,
            curDate: '',
            curTime: '',
            curWeek: '',
            centerTopTopData: centerTopTopData,
        },
        methods: {
            format(number) {
                let arr = (number + '').split('.')
                let int = arr[0].split('')
                const fraction = arr[1] || ''
                let r = ''
                let len = int.length
                int.reverse().forEach((v, i) => {
                    if (i !== 0 && i % 3 === 0) {
                        r = v + ',' + r
                    } else {
                        r = v + r
                    }
                })
                return r + (!!fraction ? '.' + fraction : '')
            },
            updateDate() {
                let timer;
                clearInterval(timer);
                timer = setInterval(() => {
                    let date = new Date();
                    let year = date.getFullYear();
                    let month = date.getMonth() + 1;
                    let day = date.getDate();
                    let hours = date.getHours();
                    let minutes = date.getMinutes();
                    let seconds = date.getSeconds();
                    let week = date.getDay()
                    month = (month < 10 ? "0" : "") + month;
                    day = (day < 10 ? "0" : "") + day;
                    hours = (hours < 10 ? "0" : "") + hours;
                    minutes = (minutes < 10 ? "0" : "") + minutes;
                    seconds = (seconds < 10 ? "0" : "") + seconds;
                    this.curDate = year + "-" + month + "-" + day;
                    this.curTime = hours + ":" + minutes + ":" + seconds;
                    this.curWeek = "星期" + "日一二三四五六".charAt(week)
                }, 1000);
            },
            startScroll(prefix) {
                var data = prefix + 'Data'
                var allRows = prefix + 'AllRows'
                var scrollIndex = prefix + 'ScrollIndex'
                var timer = prefix + 'Timer'
                var interval = prefix + 'Interval'
                var duration = prefix + 'Duration'
                var distance = prefix + 'Distance'
                this[allRows] = [...this[data], ...this[data], ...this[data], ...this[data]]
                const scrollList = document.querySelector(`#${prefix} .scrollList`)
                if (this[timer]) {
                    clearInterval(this[timer])
                }
                this[timer] = setInterval(() => {
                    var allDistance = this[scrollIndex] * this[distance]
                    scrollList.style.transform = `translate3d(0,-${allDistance}px,0)`
                    if (allDistance >= scrollList.clientHeight / 2 + this[distance]) {
                        this[scrollIndex] = 0;
                        scrollList.style.transition = `all 0s ease 0s`;
                    } else {
                        scrollList.style.transition = `all ${this[duration]}s ease 0s`;
                    }
                    this[scrollIndex] += 1;
                }, this[interval] * 1000);
            },
            stopScroll(prefix) {
                var timer = prefix + 'Timer'
                clearInterval(this[timer]);
            },
            handleImageLoad(event) {
                event.target.style.opacity = 1;
            },
            onTopItemClick(item) {
                try {
                    const label = (Array.isArray(item) ? item[0] : (item && (item.type || item.label))) || '';
                    if (String(label).includes('故障')) {
                        window.location.href = '/fault/dashboard';
                    }
                } catch (e) {
                    // ignore
                }
            },
        },
        mounted() {
            this.updateDate()
        },
    });

    echarts.registerMap('shenzhen', mapData);
    leftTop(leftTopData);
    leftMiddle(leftMiddleData);
    centerTopBottom(centerTopBottomData);
    rightTop(rightTopData);
    rightMiddle(rightMiddleData);
    bottomContainer(bottomData);
});

// ========== leftTop 渲染函数 ==========
function leftTop(data) {
    const transformedData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] },
        { 月份: row[0], type: '指标', value: row[3] }
    ]);
    const ele = document.querySelector('#leftTop>.panelContent');
    const spec = {
        background: 'transparent',
        type: 'line',
        padding: { top: 30, bottom: 5, left: 10, right: 10 },
        data: { values: transformedData },
        xField: '月份',
        yField: 'value',
        seriesField: 'type',
        stack: false,
        animationAppear: {
            duration: 2000,
            easing: 'bounceOut',
            oneByOne: 1000,
            loop: true,
        },
        line: {
            style: { curveType: 'monotone', connectNulls: true }
        },
        point: {
            style: { size: 0, fill: 'white', stroke: null, lineWidth: 2 },
            state: { myCustomState: { size: 10 } }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'bottom',
                item: {
                    shape: { style: { symbolType: 'rect', size: [25, 4] } },
                    label: { style: { fill: '#fff' } }
                }
            }
        ],
        axes: [
            {
                orient: 'bottom',
                label: { style: { fill: '#fff' } },
                domainLine: { visible: true, style: {} },
                tick: { visible: true, style: { lineWidth: 2, length: 10 } }
            },
            {
                orient: 'left',
                min: 0.8,
                max: 1,
                grid: { visible: false },
                label: { style: { fill: '#fff' }, formatter: `{label:.0%}` }
            }
        ]
    };
    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
}

// ========== leftMiddle 渲染函数 ==========
function leftMiddle(data) {
    const transformedData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] },
        { 月份: row[0], type: '指标', value: row[3] }
    ]);
    const ele = document.querySelector('#leftMiddle>.panelContent');
    const spec = {
        background: 'transparent',
        type: 'bar',
        padding: { top: 30, bottom: 5, left: 10, right: 10 },
        data: { values: transformedData },
        xField: ['月份', 'type'],
        yField: 'value',
        seriesField: 'type',
        animationAppear: {
            duration: 2000,
            easing: 'bounceOut',
            oneByOne: 1000,
            loop: true,
        },
        point: {
            style: { size: 0, fill: 'white', stroke: null, lineWidth: 2 },
            state: { myCustomState: { size: 10 } }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'right',
                item: {
                    shape: { style: { width: 50, symbolType: 'rect', size: [20, 10] } },
                    label: { style: { fill: '#fff' } }
                }
            }
        ],
        axes: [
            {
                orient: 'bottom',
                label: { style: { fill: '#fff' } },
                domainLine: { visible: true, style: {} },
                tick: { visible: true, style: { lineWidth: 2, length: 10 } }
            },
            {
                orient: 'left',
                min: 0,
                max: 1,
                grid: { visible: false },
                label: { style: { fill: '#fff' }, formatter: `{label:.0%}` }
            }
        ]
    };
    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
}

// ========== centerTopBottom 渲染函数 ==========
function centerTopBottom(data) {
    var mapObj = {};
    mapData.features.forEach(item => {
        mapObj[item.properties.name] = item.properties.center;
    });
    var seriesData = [];
    data.forEach(row => {
        seriesData.push({ name: row[0], value: mapObj[row[0]], row: row });
    });
    var myChart = echarts.init(document.querySelector("#centerTopBottom>.panelContent"));
    var option = {
        autoTooltip: true,
        title: { show: false },
        legend: { show: false },
        geo: {
            map: "shenzhen",
            label: { show: false, color: "#fff", emphasis: { show: false, color: "#fff" } },
            roam: true,
            itemStyle: {
                areaColor: {
                    type: "linear-gradient",
                    x: 0, y: 300, x2: 0, y2: 0,
                    colorStops: [
                        { offset: 0, color: "RGBA(19,96,187,0.5)" },
                        { offset: 1, color: "RGBA(7,193,223,0.5)" }
                    ],
                    global: true
                },
                borderColor: "#4ECEE6",
                borderWidth: 1,
                emphasis: {
                    areaColor: "#4f7fff",
                    borderColor: "rgba(0,242,252,.6)",
                    borderWidth: 2,
                    shadowBlur: 10,
                    shadowColor: "#00f2fc"
                }
            }
        },
        series: [
            {
                name: "散点图",
                type: "effectScatter",
                coordinateSystem: "geo",
                zlevel: 2,
                rippleEffect: { brushType: "stroke" },
                symbolSize: 8,
                label: {
                    show: true,
                    offset: [10, 30],
                    color: "#fff",
                    fontSize: 12,
                    formatter: function (params) {
                        return params.data.name + '\n数值:' + params.data.row[1] + '\n比例:' + params.data.row[2] * 100 + '%'
                    }
                },
                itemStyle: { color: "#a6c84c" },
                data: seriesData,
                tooltip: {
                    trigger: "item",
                    formatter: function (params) {
                        var row = params.data.row;
                        var text = '门店：' + row[0] + '<br>地址：' + row[1] + '<br>经度：' + row[2].split(',')[0] + '<br>纬度：' + row[2].split(',')[1];
                        return text;
                    }
                },
                emphasis: {
                    label: {
                        show: false,
                        offset: [10, -30],
                        color: "#fff",
                        fontSize: 14,
                        formatter: function (params) {
                            return params.data.name + '\n数值：' + params.data.row[1] + '\n比例：' + params.data.row[2];
                        }
                    }
                }
            }
        ]
    };
    myChart.setOption(option);
}

// ========== rightTop 渲染函数 ==========
function rightTop(data) {
    const transformedData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] },
        { 月份: row[0], type: '指标', value: row[3] }
    ]);
    const ele = document.querySelector('#rightTop>.panelContent');
    const spec = {
        background: 'transparent',
        type: 'line',
        padding: { top: 30, bottom: 5, left: 10, right: 10 },
        data: { values: transformedData },
        xField: '月份',
        yField: 'value',
        seriesField: 'type',
        stack: false,
        animationAppear: {
            duration: 2000,
            easing: 'bounceOut',
            oneByOne: 1000,
            loop: true,
        },
        line: { style: { curveType: 'monotone', connectNulls: true } },
        point: {
            style: { size: 0, fill: 'white', stroke: null, lineWidth: 2 },
            state: { myCustomState: { size: 10 } }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'bottom',
                item: {
                    shape: { style: { symbolType: 'rect', size: [25, 4] } },
                    label: { style: { fill: '#fff' } }
                }
            }
        ],
        axes: [
            {
                orient: 'bottom',
                label: { style: { fill: '#fff' } },
                domainLine: { visible: true, style: {} },
                tick: { visible: true, style: { lineWidth: 2, length: 10 } }
            },
            {
                orient: 'left',
                min: 0.8,
                max: 1,
                grid: { visible: false },
                label: { style: { fill: '#fff' }, formatter: `{label:.0%}` }
            }
        ]
    };
    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
}

// ========== rightMiddle 渲染函数 ==========
function rightMiddle(data) {
    const transformedData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] },
        { 月份: row[0], type: '指标', value: row[3] }
    ]);
    const ele = document.querySelector('#rightMiddle>.panelContent');
    const spec = {
        background: 'transparent',
        type: 'bar',
        padding: { top: 30, bottom: 5, left: 10, right: 10 },
        data: { values: transformedData },
        yField: ['月份', 'type'],
        xField: 'value',
        seriesField: 'type',
        direction: 'horizontal',
        animationAppear: {
            duration: 2000,
            easing: 'bounceOut',
            oneByOne: 1000,
            loop: true,
        },
        point: {
            style: { size: 0, fill: 'white', stroke: null, lineWidth: 2 },
            state: { myCustomState: { size: 10 } }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'right',
                item: {
                    shape: { style: { width: 50, symbolType: 'rect', size: [20, 10] } },
                    label: { style: { fill: '#fff' } }
                }
            }
        ],
        axes: [
            {
                orient: 'left',
                label: { style: { fill: '#fff' } },
                domainLine: { visible: true, style: {} },
                tick: { visible: true, style: { lineWidth: 2, length: 10 } }
            },
            {
                orient: 'bottom',
                min: 0,
                max: 1,
                grid: { visible: false },
                label: { style: { fill: '#fff' }, formatter: `{label:.0%}` }
            }
        ]
    };
    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
}

// ========== bottomContainer 渲染函数 ==========
function bottomContainer(data) {
    const transformedData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] },
        { 月份: row[0], type: '蓄电池组总电压采集率', value: row[3] },
        { 月份: row[0], type: '开关电源负载电流采集率', value: row[4] },
        { 月份: row[0], type: 'UPS负载电流采集率', value: row[5] },
        { 月份: row[0], type: '动环关键信号采集完整率', value: row[6] }
    ]);
    const ele = document.querySelector('#bottomContainer>.panelContent');
    const spec = {
        background: 'transparent',
        type: 'line',
        padding: { top: 30, bottom: 5, left: 10, right: 10 },
        data: { values: transformedData },
        xField: '月份',
        yField: 'value',
        seriesField: 'type',
        stack: false,
        animationAppear: {
            duration: 2000,
            easing: 'bounceOut',
            oneByOne: 1000,
            loop: true,
        },
        line: { style: { curveType: 'monotone', connectNulls: true } },
        point: {
            style: { size: 0, fill: 'white', stroke: null, lineWidth: 2 },
            state: { myCustomState: { size: 10 } }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'bottom',
                item: {
                    shape: { style: { symbolType: 'rect', size: [25, 4] } },
                    label: { style: { fill: '#fff' } }
                }
            }
        ],
        axes: [
            {
                orient: 'bottom',
                label: { style: { fill: '#fff' } },
                domainLine: { visible: true, style: {} },
                tick: { visible: true, style: { lineWidth: 2, length: 10 } }
            },
            {
                orient: 'left',
                min: 0.8,
                max: 1,
                grid: { visible: false },
                label: { style: { fill: '#fff' }, formatter: `{label:.0%}` }
            }
        ]
    };
    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
}
