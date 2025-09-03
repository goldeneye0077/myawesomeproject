// 网址中输入的域名
var hostname = window.location.hostname
if (hostname == '') {
    hostname = '127.0.0.1'
}

// 后端服务器服务端口
var port = '8000'
var baseUrl = `http://${hostname}:${port}`
const params = {
    data: "pageTwo",
    map: "no",
    img: "no",
};

// 新增：KPI相关图表的数据接口
function fetchKPIData(apiField, callback) {
    axios.get(baseUrl + "/api/bi_data").then((res) => {
        const data = res.data;
        // 容错处理：如果数据不存在，返回空数组
        callback(Array.isArray(data[apiField]) ? data[apiField] : []);
    });
}

// 顶部 top_kpi 数据
fetchKPIData("topData", function(topData) {
    // 用于顶部展示的 Vue 数据绑定
    new Vue({
        el: '#pageContainer',
        data: {
            baseUrl: baseUrl,
            curDate: '',
            curTime: '',
            curWeek: '',
            topData: topData,
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
                // 原始列表数据
                var data = prefix + 'Data'
                // 滚动列表数据
                var allRows = prefix + 'AllRows'
                // 滚动的位置-像素
                var scrollIndex = prefix + 'ScrollIndex'
                // 计时器
                var timer = prefix + 'Timer'
                // 滚动的间隔时间
                var interval = prefix + 'Interval'
                // 滚动的持续时间
                var duration = prefix + 'Duration'
                // 滚动的距离
                var distance = prefix + 'Distance'
                // 为了背景无缝衔接，列表重复了4次
                this[allRows] = [...this[data], ...this[data], ...this[data], ...this[data]]
                // 滚动的列表-容器
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
            // 停止滚动
            stopScroll(prefix) {
                var timer = prefix + 'Timer'
                clearInterval(this[timer]);
            },
            handleImageLoad(event) {
                event.target.style.opacity = 1;
            },
        },
        mounted() {
            this.updateDate()
        },
    });
});

// leftMiddle 图表数据从 LeftMiddleKPI
fetchKPIData("leftMiddleData", function(leftMiddleData) {
    leftMiddle(leftMiddleData);
});

// centerMiddle 图表数据从 CenterMiddleKPI
fetchKPIData("centerMiddleData", function(centerMiddleData) {
    centerMiddle(centerMiddleData);
});

// rightMiddle 图表数据从 RightMiddleKPI
fetchKPIData("rightMiddleKPIData", function(rightMiddleData) {
    rightMiddle(rightMiddleData);
});

// leftBottom 图表数据从 LeftBottomKPI
fetchKPIData("leftBottomData", function(leftBottomData) {
    leftBottom(leftBottomData);
});

// rightBottom 图表数据从 RightBottomKPI
fetchKPIData("rightBottomData", function(rightBottomData) {
    rightBottom(rightBottomData);
});

function leftMiddle(data) {
    var xData = []
    var yData1 = []
    var yData2 = []
    var yData3 = []
    data.forEach(row => {
        xData.push(row[0])
        yData1.push(row[1])
        yData2.push(row[2])
        yData3.push(row[3])
    })
    var myChart = echarts.init(document.querySelector("#leftMiddle>.panelContent"));
    var option = {
        grid: {
            top: 20,
            bottom: 60,
        },
        legend: {
            left: 'center',
            bottom: '1%',
            itemHeight: 30,
            itemWidth: 20,
            textStyle: {
                color: '#fff',
            },
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'none'
            },
            formatter: function (params) {
                return params[0].name + ': ' + params[0].value;
            }
        },
        xAxis: {
            data: xData,
            axisTick: { show: false },
            axisLine: { show: true },
            axisLabel: {
                color: '#fff'
            }
        },
        yAxis: {
            splitLine: { show: false },
            axisTick: { show: false },
            axisLine: { show: false },
            axisLabel: {
                color: '#fff',
                formatter: function name(params) {
                    return params * 100 + '%'
                }
            }
        },
        color: ['#9e5d61', '#487298', '#7da464'],
        // dataset:{
        //     source:data,
        // },
        series: [
            {
                name: '基准值',
                type: 'pictorialBar',
                symbol: 'path://M0,10 L10,10 C5.5,10 5.5,5 5,0 C4.5,5 4.5,10 0,10 z',
                // barGap: 20,
                // label: labelOption,
                emphasis: {
                    focus: 'series'
                },
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0,
                        y: 0,
                        x2: 0,
                        y2: 1,
                        colorStops: [{
                            offset: 0, color: '#e2756b'
                        }, {
                            offset: 1, color: '#8f585f88'
                        }],
                        global: false
                    }
                },
                data: yData1
            },
            {
                name: '挑战值',
                type: 'pictorialBar',
                symbol: 'path://M0,10 L10,10 C5.5,10 5.5,5 5,0 C4.5,5 4.5,10 0,10 z',
                barGap: -0.8,
                barCategoryGap: 0.2,
                // label: labelOption,
                emphasis: {
                    focus: 'series'
                },
                data: yData2,
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0,
                        y: 0,
                        x2: 0,
                        y2: 1,
                        colorStops: [{
                            offset: 0, color: '#72a2c7'
                        }, {
                            offset: 1, color: '#72a2c788'
                        }],
                        global: false
                    }
                },
            },
            {
                name: '无线退服时长',
                type: 'pictorialBar',
                symbol: 'path://M0,10 L10,10 C5.5,10 5.5,5 5,0 C4.5,5 4.5,10 0,10 z',
                barGap: -0.8,
                barCategoryGap: 0.2,
                // label: labelOption,
                emphasis: {
                    focus: 'series'
                },
                data: yData3,
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0,
                        y: 0,
                        x2: 0,
                        y2: 1,
                        colorStops: [{
                            offset: 0, color: '#a0cd5f'
                        }, {
                            offset: 1, color: '#a0cd5f88'
                        }],
                        global: false
                    }
                },
            }
        ]
    };
    myChart.setOption(option);
}

function centerMiddle(data) {
    const barData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] }
    ]);
    const lineData = data.flatMap(row => [
        { 月份: row[0], type: '家企宽回单率', value: row[3] },
        { 月份: row[0], type: '到企网络侧交付率', value: row[4] }
    ]);

    const ele = document.querySelector('#centerMiddle>.panelContent');

    const spec = {
        background: 'transparent',
        padding: {
            top: 30,
            bottom: 5,
            left: 10,
            right: 10,
        },
        type: 'common',
        seriesField: 'color',
        data: [
            {
                id: 'barData',
                values: barData,
            },
            {
                id: 'lineData',
                values: lineData,
            }
        ],
        series: [
            {
                type: 'bar',
                dataIndex: 0,
                seriesField: 'type',
                xField: ['月份', 'type'],
                yField: 'value',
            },
            {
                type: 'line',
                dataIndex: 1,
                seriesField: 'type',
                xField: '月份',
                yField: 'value',
                stack: false,
                point: {
                    style: {
                        size: 0,
                        fill: 'white',
                        stroke: null,
                        lineWidth: 2
                    },
                    state: {
                        myCustomState: {
                            size: 10
                        }
                    }
                },
            }
        ],
        animationAppear: {
            duration: 2000,
            easing: 'bounceOut',
            oneByOne: 1000,
            loop: true,
        },
        line: {
            style: {
                curveType: 'monotone',
                connectNulls: true // 连接空值，确保线条连续
            }
        },
        point: {
            style: {
                size: 0,
                fill: 'white',
                stroke: null,
                lineWidth: 2
            },
            state: {
                myCustomState: {
                    size: 0
                }
            }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'bottom',
                item: {
                    shape: {
                        style: {
                            symbolType: 'rect',
                            size: [25, 4],
                        }
                    },
                    label: {
                        style: {
                            fill: '#fff' // 设置图例文字颜色为白色
                        }
                    }
                },
            }
        ],
        axes: [
            {
                orient: 'bottom',
                label: {
                    style: {
                        fill: '#fff'
                    },
                },
                domainLine: {
                    visible: true,
                    style: {
                        // stroke: 'red', // 轴线颜色
                        // lineWidth: 5,       // 轴线宽度
                        // lineDash: [5, 0],   // 虚线样式
                        // opacity: 1        // 透明度
                    }
                },
                tick: {
                    visible: true, // 显示刻度线
                    style: {
                        // stroke: '#000', // 刻度线颜色
                        lineWidth: 2,   // 刻度线宽度
                        length: 10      // 刻度线长度
                    }
                }
            },
            {
                orient: 'left',
                // min: 0.8,
                // max: 1,
                // zero: false,

                grid: {
                    visible: false // 显示 Y 轴方向的网格线
                },
                label: {
                    style: {
                        fill: '#fff',
                    },
                    formatter: `{label:.0%}`,
                },
            }
        ]
    };

    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
    // 主题热更新
    // vchart.setCurrentTheme('light');
}

function rightMiddle(data) {
    const transformedData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] },
        { 月份: row[0], type: '研发投入完成度', value: row[3] }
    ]);

    const ele = document.querySelector('#rightMiddle>.panelContent');

    const spec = {
        background: 'transparent',
        type: 'line',
        padding: {
            top: 30,
            bottom: 5,
            left: 10,
            right: 10,
        },
        data: {
            values: transformedData
        },
        // title: {
        //     visible: true,
        //     text: 'Stacked line chart'
        // },
        stack: true,
        xField: '月份',
        yField: 'value',
        seriesField: 'type',
        stack: false, // 禁用堆积效果
        animationAppear: {
            duration: 2000,
            easing: 'bounceOut',
            oneByOne: 1000,
            loop: true,
        },
        line: {
            style: {
                curveType: 'monotone',
                connectNulls: true // 连接空值，确保线条连续
            }
        },
        point: {
            style: {
                size: 0,
                fill: 'white',
                stroke: null,
                lineWidth: 2
            },
            state: {
                myCustomState: {
                    size: 10
                }
            }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'bottom',
                item: {
                    shape: {
                        style: {
                            symbolType: 'rect',
                            size: [25, 4],
                        }
                    },
                    label: {
                        style: {
                            fill: '#fff' // 设置图例文字颜色为白色
                        }
                    }
                },
            }
        ],
        axes: [
            {
                orient: 'bottom',
                label: {
                    style: {
                        fill: '#fff'
                    },
                },
                domainLine: {
                    visible: true,
                    style: {
                        // stroke: 'red', // 轴线颜色
                        // lineWidth: 5,       // 轴线宽度
                        // lineDash: [5, 0],   // 虚线样式
                        // opacity: 1        // 透明度
                    }
                },
                tick: {
                    visible: true, // 显示刻度线
                    style: {
                        // stroke: '#000', // 刻度线颜色
                        lineWidth: 2,   // 刻度线宽度
                        length: 10      // 刻度线长度
                    }
                }
            },
            {
                orient: 'left',
                min: 0.8,
                max: 1,
                // zero: false,

                grid: {
                    visible: false // 显示 Y 轴方向的网格线
                },
                label: {
                    style: {
                        fill: '#fff',
                    },
                    formatter: `{label:.0%}`,
                },
            }
        ]
    };

    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
    // 主题热更新
    // vchart.setCurrentTheme('light');
}

function leftBottom(data) {
    const transformedData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] },
        { 月份: row[0], type: '当前值', value: row[3] }
    ]);

    const ele = document.querySelector('#leftBottom>.panelContent');

    const spec = {
        background: 'transparent',
        type: 'bar',
        padding: {
            top: 30,
            bottom: 5,
            left: 10,
            right: 10,
        },
        data: {
            values: transformedData
        },
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
        // bar: {
        //     width: 2 // 设置柱子宽度
        // },

        point: {
            style: {
                size: 0,
                fill: 'white',
                stroke: null,
                lineWidth: 2
            },
            state: {
                myCustomState: {
                    size: 10
                }
            }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'right',
                item: {
                    shape: {
                        style: {
                            width: 50,
                            symbolType: 'rect',
                            size: [20, 10],
                        }
                    },
                    label: {
                        style: {
                            fill: '#fff' // 设置图例文字颜色为白色
                        }
                    }
                },
            }
        ],
        axes: [
            {
                orient: 'left',
                label: {
                    style: {
                        fill: '#fff'
                    },
                },
                domainLine: {
                    visible: true,
                    style: {
                        // stroke: 'red', // 轴线颜色
                        // lineWidth: 5,       // 轴线宽度
                        // lineDash: [5, 0],   // 虚线样式
                        // opacity: 1        // 透明度
                    }
                },
                tick: {
                    visible: true, // 显示刻度线
                    style: {
                        // stroke: '#000', // 刻度线颜色
                        lineWidth: 2,   // 刻度线宽度
                        length: 10      // 刻度线长度
                    }
                }
            },
            {
                orient: 'bottom',
                // min: 0,
                // max: 1,
                zero: false,
                grid: {
                    visible: false // 显示 Y 轴方向的网格线
                },
                label: {
                    style: {
                        fill: '#fff',
                    },
                    // formatter: `{label:.0%}`,
                },
            }
        ]
    };

    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
    // 主题热更新
    // vchart.setCurrentTheme('light');
}

function rightBottom(data) {
    const transformedData = data.flatMap(row => [
        { 月份: row[0], type: '基准值', value: row[1] },
        { 月份: row[0], type: '挑战值', value: row[2] },
        { 月份: row[0], type: '家企宽回单率', value: row[3] }
    ]);

    const ele = document.querySelector('#rightBottom>.panelContent');

    const spec = {
        background: 'transparent',
        type: 'line',
        padding: {
            top: 30,
            bottom: 5,
            left: 10,
            right: 10,
        },
        data: {
            values: transformedData
        },
        // title: {
        //     visible: true,
        //     text: 'Stacked line chart'
        // },
        stack: true,
        xField: '月份',
        yField: 'value',
        seriesField: 'type',
        stack: false, // 禁用堆积效果
        animationAppear: {
            duration: 2000,
            easing: 'bounceOut',
            oneByOne: 1000,
            loop: true,
        },
        line: {
            style: {
                curveType: 'monotone',
                connectNulls: true // 连接空值，确保线条连续
            }
        },
        point: {
            style: {
                size: 0,
                fill: 'white',
                stroke: null,
                lineWidth: 2
            },
            state: {
                myCustomState: {
                    size: 10
                }
            }
        },
        legends: [
            {
                visible: true,
                position: 'middle',
                orient: 'bottom',
                item: {
                    shape: {
                        style: {
                            symbolType: 'rect',
                            size: [25, 4],
                        }
                    },
                    label: {
                        style: {
                            fill: '#fff' // 设置图例文字颜色为白色
                        }
                    }
                },
            }
        ],
        axes: [
            {
                orient: 'bottom',
                label: {
                    style: {
                        fill: '#fff'
                    },
                },
                domainLine: {
                    visible: true,
                    style: {
                        // stroke: 'red', // 轴线颜色
                        // lineWidth: 5,       // 轴线宽度
                        // lineDash: [5, 0],   // 虚线样式
                        // opacity: 1        // 透明度
                    }
                },
                tick: {
                    visible: true, // 显示刻度线
                    style: {
                        // stroke: '#000', // 刻度线颜色
                        lineWidth: 2,   // 刻度线宽度
                        length: 10      // 刻度线长度
                    }
                }
            },
            {
                orient: 'left',
                // min: 0.8,
                // max: 1,
                // zero: false,

                grid: {
                    visible: false // 显示 Y 轴方向的网格线
                },
                label: {
                    style: {
                        fill: '#fff',
                    },
                    formatter: `{label:.0%}`,
                },
            }
        ]
    };

    const vchart = new VChart.default(spec, { dom: ele });
    vchart.renderSync();
    // 主题热更新
    // vchart.setCurrentTheme('light');
}

VChart.ThemeManager.registerTheme('theme', theme);
VChart.ThemeManager.setCurrentTheme('theme');
