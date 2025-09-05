#!/usr/bin/env python3
"""
数据完整性监控脚本

用于定期检查数据库完整性，监控数据量变化，发现异常情况
支持命令行运行和定时任务调用
"""

import asyncio
import logging
import sys
import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

# 添加项目路径到Python路径
sys.path.append(str(Path(__file__).parent))

from db.session import AsyncSessionLocal
from db.models import (
    PUEData, FaultRecord, Huijugugan, Zbk, 
    PUEComment, PUEDrillDownData
)
from sqlalchemy import select, func, text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_integrity.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataIntegrityMonitor:
    """数据完整性监控器"""
    
    def __init__(self):
        self.baseline_data = {
            'pue_data': 240,
            'fault_record': 272,
            'huijugugan': 28,
            'zbk': 0,
            'pue_comment': 34,
            'pue_drill_down_data': 13680
        }
        
        self.table_models = {
            'pue_data': PUEData,
            'fault_record': FaultRecord,
            'huijugugan': Huijugugan,
            'zbk': Zbk,
            'pue_comment': PUEComment,
            'pue_drill_down_data': PUEDrillDownData
        }
        
        # 告警阈值
        self.warning_threshold = 10  # 10%变化触发警告
        self.critical_threshold = 25  # 25%变化触发严重告警
    
    async def check_database_connection(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
                return {
                    'status': 'connected',
                    'message': '数据库连接正常'
                }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'数据库连接失败: {str(e)}'
            }
    
    async def check_data_integrity(self) -> Dict[str, Any]:
        """检查数据完整性"""
        try:
            async with AsyncSessionLocal() as db:
                current_data = {}
                
                # 检查各表记录数
                for table_name, model in self.table_models.items():
                    if table_name == 'zbk':
                        # zbk表使用xh作为主键
                        result = await db.execute(select(func.count(model.xh)))
                    else:
                        result = await db.execute(select(func.count(model.id)))
                    current_data[table_name] = result.scalar()
                
                return {
                    'status': 'success',
                    'baseline_data': self.baseline_data,
                    'current_data': current_data,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"数据完整性检查失败: {e}")
            return {
                'status': 'error',
                'message': f'检查失败: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def analyze_data_changes(self, integrity_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析数据变化"""
        if integrity_result['status'] != 'success':
            return []
        
        baseline = integrity_result['baseline_data']
        current = integrity_result['current_data']
        alerts = []
        
        for table_name in baseline:
            baseline_count = baseline[table_name]
            current_count = current[table_name]
            
            if baseline_count == 0 and current_count == 0:
                continue  # 跳过两个都为0的情况
            
            if baseline_count == 0:
                # 基线为0，任何数据都是增长
                change_percent = 100 if current_count > 0 else 0
                change_type = 'increase'
            else:
                # 计算变化百分比
                change_percent = abs(current_count - baseline_count) / baseline_count * 100
                change_type = 'increase' if current_count > baseline_count else 'decrease'
            
            # 判断告警级别
            if change_percent > self.critical_threshold:
                alert_level = 'critical'
            elif change_percent > self.warning_threshold:
                alert_level = 'warning'
            else:
                alert_level = 'info'
            
            if alert_level in ['critical', 'warning']:
                alerts.append({
                    'table': table_name,
                    'alert_level': alert_level,
                    'baseline_count': baseline_count,
                    'current_count': current_count,
                    'change_percent': round(change_percent, 2),
                    'change_type': change_type,
                    'message': f"{table_name}表数据{change_type} {change_percent:.1f}% ({baseline_count}->{current_count})"
                })
        
        return alerts
    
    async def check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            async with AsyncSessionLocal() as db:
                # 检查数据库完整性
                result = await db.execute(text("PRAGMA integrity_check"))
                integrity_result = result.scalar()
                
                # 检查WAL模式状态
                result = await db.execute(text("PRAGMA journal_mode"))
                journal_mode = result.scalar()
                
                # 检查数据库大小
                result = await db.execute(text("PRAGMA page_count"))
                page_count = result.scalar()
                
                result = await db.execute(text("PRAGMA page_size"))
                page_size = result.scalar()
                
                db_size_bytes = page_count * page_size
                
                return {
                    'integrity_check': integrity_result,
                    'journal_mode': journal_mode,
                    'database_size_mb': round(db_size_bytes / (1024 * 1024), 2),
                    'page_count': page_count,
                    'page_size': page_size,
                    'status': 'healthy' if integrity_result == 'ok' else 'unhealthy'
                }
                
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def generate_report(self) -> Dict[str, Any]:
        """生成完整监控报告"""
        logger.info("开始生成数据完整性监控报告")
        
        # 检查数据库连接
        connection_status = await self.check_database_connection()
        
        # 检查数据完整性
        integrity_result = await self.check_data_integrity()
        
        # 分析数据变化
        alerts = self.analyze_data_changes(integrity_result)
        
        # 检查数据库健康
        health_status = await self.check_database_health()
        
        # 汇总报告
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'connection_status': connection_status,
            'data_integrity': integrity_result,
            'health_status': health_status,
            'alerts': alerts,
            'summary': {
                'total_alerts': len(alerts),
                'critical_alerts': len([a for a in alerts if a['alert_level'] == 'critical']),
                'warning_alerts': len([a for a in alerts if a['alert_level'] == 'warning']),
                'overall_status': self._calculate_overall_status(connection_status, alerts)
            }
        }
        
        # 记录日志
        if report['summary']['critical_alerts'] > 0:
            logger.critical(f"发现{report['summary']['critical_alerts']}个严重告警")
        elif report['summary']['warning_alerts'] > 0:
            logger.warning(f"发现{report['summary']['warning_alerts']}个警告")
        else:
            logger.info("数据完整性检查正常")
        
        return report
    
    def _calculate_overall_status(self, connection_status: Dict, alerts: List[Dict]) -> str:
        """计算整体状态"""
        if connection_status['status'] != 'connected':
            return 'critical'
        
        critical_alerts = [a for a in alerts if a['alert_level'] == 'critical']
        warning_alerts = [a for a in alerts if a['alert_level'] == 'warning']
        
        if critical_alerts:
            return 'critical'
        elif warning_alerts:
            return 'warning'
        else:
            return 'healthy'
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """保存报告到文件"""
        if filename is None:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"logs/integrity_report_{timestamp}.json"
        
        Path("logs").mkdir(exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"监控报告已保存到: {filename}")

async def main():
    """主函数"""
    monitor = DataIntegrityMonitor()
    
    try:
        # 生成监控报告
        report = await monitor.generate_report()
        
        # 保存报告
        monitor.save_report(report)
        
        # 输出摘要
        print(f"数据完整性监控报告 - {report['timestamp']}")
        print("=" * 50)
        print(f"整体状态: {report['summary']['overall_status']}")
        print(f"数据库连接: {report['connection_status']['status']}")
        print(f"告警总数: {report['summary']['total_alerts']}")
        print(f"严重告警: {report['summary']['critical_alerts']}")
        print(f"警告告警: {report['summary']['warning_alerts']}")
        
        if report['alerts']:
            print("\n告警详情:")
            for alert in report['alerts']:
                level_icon = "🚨" if alert['alert_level'] == 'critical' else "⚠️"
                print(f"{level_icon} {alert['message']}")
        
        # 返回适当的退出码
        if report['summary']['overall_status'] == 'critical':
            sys.exit(1)
        elif report['summary']['overall_status'] == 'warning':
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"监控脚本执行失败: {e}")
        print(f"错误: {e}")
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(main())