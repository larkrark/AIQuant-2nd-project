# -*- coding: utf-8 -*-
"""
Created on Wed Jul  1 00:04:47 2026

@author: user
"""



import pandas as pd
import openpyxl


file_path = 'C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\주식 이외 데이터.xlsx'
# 엑셀 파일의 모든 시트 불러오기
xls = pd.ExcelFile(file_path)

# 각 시트를 CSV로 저장
for sheet_name in xls.sheet_names:
    # 시트 데이터 읽기
    df = pd.read_excel(xls, sheet_name=sheet_name)
    
    # CSV 파일로 저장
    df.to_csv(f'{sheet_name}.csv', index=False, encoding='utf-8-sig')

print("모든 시트가 CSV 파일로 저장되었습니다.")
# import os
# # 현재 작업 중인 디렉토리 확인
# current_directory = os.getcwd()
# print("현재 작업 디렉토리:", current_directory)
# 현재 작업 디렉토리: C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project
# C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\주식 이외 데이터.xlsx