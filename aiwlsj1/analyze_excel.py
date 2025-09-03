#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import sys

def analyze_excel(filename):
    try:
        # 读取Excel文件
        df = pd.read_excel(filename)
        
        print("=" * 50)
        print(f"分析文件: {filename}")
        print("=" * 50)
        
        print("\n1. 数据形状:")
        print(f"   行数: {df.shape[0]}, 列数: {df.shape[1]}")
        
        print("\n2. 列名:")
        for i, col in enumerate(df.columns.tolist()):
            print(f"   {i+1}. {col}")
        
        print("\n3. 数据类型:")
        for col, dtype in df.dtypes.items():
            print(f"   {col}: {dtype}")
        
        print("\n4. 前5行数据:")
        print(df.head().to_string(index=False))
        
        print("\n5. 数据概览:")
        print(df.info())
        
        print("\n6. 缺失值统计:")
        missing = df.isnull().sum()
        for col, count in missing.items():
            if count > 0:
                print(f"   {col}: {count} 个缺失值")
        
        return df
        
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return None

if __name__ == "__main__":
    filename = "_深圳宝安区宝城.xlsx"
    df = analyze_excel(filename)
