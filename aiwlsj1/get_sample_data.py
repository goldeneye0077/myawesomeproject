#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd

def get_sample_data():
    try:
        # 读取Excel文件
        df = pd.read_excel('_深圳宝安区宝城.xlsx')
        
        # 删除空列
        df_clean = df.drop(columns=[col for col in df.columns if 'Unnamed' in str(col)])
        
        print("清理后的列名:")
        for i, col in enumerate(df_clean.columns.tolist()):
            print(f"  {i+1}. {col}")
        
        print("\n前3行完整数据:")
        for i in range(min(3, len(df_clean))):
            print(f"\n=== 第{i+1}行数据 ===")
            for col in df_clean.columns:
                value = df_clean.iloc[i][col]
                print(f"  {col}: {value}")
        
        # 分析字段特征
        print("\n\n=== 字段分析 ===")
        for col in df_clean.columns:
            unique_count = df_clean[col].nunique()
            sample_values = df_clean[col].dropna().unique()[:3]
            print(f"{col}:")
            print(f"  - 唯一值数量: {unique_count}")
            print(f"  - 示例值: {list(sample_values)}")
            print()
            
    except Exception as e:
        print(f"处理文件时出错: {e}")

if __name__ == "__main__":
    get_sample_data()
