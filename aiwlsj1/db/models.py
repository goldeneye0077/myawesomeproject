from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base() 

class Zbk(Base):
    """指标库表模型"""
    __tablename__ = "zbk"
    xh = Column(Integer, primary_key=True, autoincrement=True, comment="序号")
    zbx = Column(Text, comment="指标项")
    fz = Column(Text, comment="分值")
    qspm = Column(Text, comment="全省排名")
    qnljdfzb = Column(Text, comment="全年累计得分占比")
    nddcpg = Column(Text, comment="年度达成评估")
    y1zb = Column(Text, comment="1月指标")
    y2zb = Column(Text, comment="2月指标")
    y3zb = Column(Text, comment="3月指标")
    y4zb = Column(Text, comment="4月指标")
    y5zb = Column(Text, comment="5月指标")
    y6zb = Column(Text, comment="6月指标")
    cjsj = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    gxsj = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    jzz = Column(Text, comment="基准值")
    tzz = Column(Text, comment="挑战值")
    type = Column(String(20), default="contract", comment="指标类型：contract(契约化攻坚指标)或kpi(KPI指标)")

class PUEData(Base):
    """PUE数据模型"""
    __tablename__ = "pue_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String(255), comment="地点")
    month = Column(String(50), comment="月份")
    year = Column(String(50), comment="年份")
    pue_value = Column(Float, comment="PUE值")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PUEComment(Base):
    """PUE备注模型，按地点-年月维度存储多条评论"""
    __tablename__ = "pue_comment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String(255))
    month = Column(String(50))
    year = Column(String(50))
    content = Column(Text)
    creator = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PUERectifyRecord(Base):
    """PUE整改记录模型，对应三级下钻工单信息"""
    __tablename__ = "pue_rectify_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    drill_down_id = Column(Integer, comment="关联的PUEDrillDownData记录ID")
    order_no = Column(String(100), comment="工单号")
    status = Column(String(100), comment="完成状态")
    image_url = Column(String(255), comment="整改图片")
    description = Column(Text, comment="整改说明")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PUEDrillDownData(Base):
    """PUE下钻数据模型 - 存储机房运维详细工作信息"""
    __tablename__ = "pue_drill_down_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联字段
    location = Column(String(255), comment="地点/机房")
    month = Column(String(50), comment="月份")
    year = Column(String(50), comment="年份")
    
    # 作业信息
    work_type = Column(String(100), comment="作业形式")
    work_category = Column(String(100), comment="作业分类")
    sequence_no = Column(Integer, comment="序号")
    work_object = Column(String(255), comment="作业对象")
    check_item = Column(Text, comment="检查项")
    operation_method = Column(Text, comment="操作方法及建议值")
    
    # 标准和执行情况
    benchmark_value = Column(Text, comment="标杆值")
    execution_standard = Column(Text, comment="执行标准")
    execution_status = Column(Text, comment="执行情况")
    detailed_situation = Column(Text, comment="详细情况")
    
    # 量化信息
    quantification_standard = Column(String(100), comment="量化标准")
    last_month_standard = Column(String(100), comment="上月量化标准")
    quantification_unit = Column(String(50), comment="量化单位")
    
    # 责任人
    executor = Column(String(100), comment="执行人")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Huijugugan(Base):
    """汇聚故障感知多维表数据模型"""
    __tablename__ = "huijugugan"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    city = Column(String(16), comment="城市")
    huiju_amount = Column(Integer, comment="汇聚全量")
    over_4h = Column(Integer, comment="超4小时")
    important_amount = Column(Integer, comment="重要环全量")
    over_12h = Column(Integer, comment="超12小时")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CenterTopTop(Base):
    __tablename__ = "center_top_top"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(128), comment="类型")
    status = Column(String(128), comment="是否达标")
    year = Column(Integer, comment="年份")

class CenterTopBottom(Base):
    __tablename__ = "center_top_bottom"
    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String(128), comment="区域")
    value = Column(Float, comment="数据")
    ratio = Column(Float, comment="比例")
    year = Column(Integer, comment="年份")

class LeftTop(Base):
    __tablename__ = "left_top"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    indicator = Column(Float, comment="指标")
    year = Column(Integer, comment="年份")

class LeftMiddle(Base):
    __tablename__ = "left_middle"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    indicator = Column(Float, comment="指标")
    year = Column(Integer, comment="年份")

class RightTop(Base):
    __tablename__ = "right_top"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    indicator = Column(Float, comment="指标")
    year = Column(Integer, comment="年份")

class RightMiddle(Base):
    __tablename__ = "right_middle"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    indicator = Column(Float, comment="指标")
    year = Column(Integer, comment="年份")

class Bottom(Base):
    __tablename__ = "bottom"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    battery_voltage_ratio = Column(Float, comment="蓄电池组总电压采集率")
    mains_load_ratio = Column(Float, comment="开关电源负载电流采集率")
    ups_load_ratio = Column(Float, comment="UPS负载电流采集率")
    env_signal_ratio = Column(Float, comment="动环关键信号采集完整率")
    year = Column(Integer, comment="年份")

class LeftMiddleKPI(Base):
    __tablename__ = "left_middle_kpi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    offline_duration = Column(Float, comment="无线退服时长")
    year = Column(Integer, comment="年份")

class CenterMiddleKPI(Base):
    __tablename__ = "center_middle_kpi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    broadband_rate = Column(Float, comment="家企宽回单率")
    delivery_rate = Column(Float, comment="到企网络侧交付率")
    year = Column(Integer, comment="年份")

class RightMiddleKPI(Base):
    __tablename__ = "right_middle_kpi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    r_and_d_completion = Column(Float, comment="研发投入完成度")
    year = Column(Integer, comment="年份")

class LeftBottomKPI(Base):
    __tablename__ = "left_bottom_kpi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    indicator = Column(String(64), comment="指标项")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    current = Column(Float, comment="当前值")
    year = Column(Integer, comment="年份")

class RightBottomKPI(Base):
    __tablename__ = "right_bottom_kpi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(16), comment="月份")
    baseline = Column(Float, comment="基准值")
    challenge = Column(Float, comment="挑战值")
    broadband_rate = Column(Float, comment="家企宽回单率")
    year = Column(Integer, comment="年份")

class TopKPI(Base):
    __tablename__ = "top_kpi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(64), comment="类型")
    status = Column(String(16), comment="是否达标")
    year = Column(Integer, comment="年份")

class FaultRecord(Base):
    """故障记录数据模型"""
    __tablename__ = "fault_record"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_no = Column(Integer, comment="序号")
    fault_date = Column(DateTime, comment="日期")
    fault_name = Column(Text, comment="故障名称")
    province_cause_analysis = Column(Text, comment="省-故障原因分析")
    province_cause_category = Column(String(100), comment="省-原因分类")
    province_fault_type = Column(String(100), comment="省-故障类型")
    notification_level = Column(String(50), comment="通报级别")
    cause_category = Column(String(100), comment="原因分类")
    fault_duration_hours = Column(Float, comment="故障处理时长（小时）")
    complaint_situation = Column(Text, comment="投诉情况")
    start_time = Column(DateTime, comment="发生时间")
    end_time = Column(DateTime, comment="结束时间")
    fault_cause = Column(Text, comment="故障原因")
    fault_handling = Column(Text, comment="故障处理")
    is_proactive_discovery = Column(String(10), comment="是否主动发现")
    remarks = Column(Text, comment="备注")
    
    # 系统字段
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

class SystemFaultLog(Base):
    """系统故障日志模型 - 用于记录应用系统运行过程中的故障"""
    __tablename__ = "system_fault_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fault_type = Column(String(50), comment="故障类型: database, api, system, application")
    severity = Column(String(20), comment="严重级别: critical, error, warning, info")
    title = Column(String(255), comment="故障标题")
    description = Column(Text, comment="故障详细描述")
    error_message = Column(Text, comment="错误信息")
    stack_trace = Column(Text, comment="堆栈追踪")
    affected_module = Column(String(100), comment="影响的模块/组件")
    status = Column(String(20), default="open", comment="状态: open, resolved, closed")
    resolved_at = Column(DateTime, comment="解决时间")
    resolution_notes = Column(Text, comment="解决方案说明")
    user_impact = Column(String(20), comment="用户影响: none, low, medium, high, critical")
    
    # 环境信息
    environment = Column(String(50), default="production", comment="环境: development, testing, production")
    server_info = Column(JSON, comment="服务器信息(JSON格式)")
    request_info = Column(JSON, comment="请求信息(JSON格式)")
    
    # 时间戳
    occurred_at = Column(DateTime, default=datetime.utcnow, comment="故障发生时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="记录创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
