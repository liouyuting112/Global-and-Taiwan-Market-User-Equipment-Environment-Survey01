#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StatCounter 月度自動更新腳本
可以設置為每月自動運行，更新所有國家/地區的數據
"""

import os
import sys
from datetime import datetime

def log_message(message):
    """記錄日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_file = 'statcounter_update_log.txt'
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def main():
    """
    主函數：
    - 依據資料/statcounter_data 底下最新的原始 JSON
    - 產生前端需要的 {country}_data.json 到 deploy/statcounter_data
    """
    log_message("=" * 70)
    log_message("開始匯出 StatCounter 前端用 JSON 到 deploy/statcounter_data")
    log_message("=" * 70)
    
    try:
        # 匯出前端 JSON 檔
        from export_statcounter_frontend_data import export_frontend_files

        export_frontend_files()
        log_message("[OK] 已完成前端 JSON 匯出")
        log_message("=" * 70)
        return 0
            
    except Exception as e:
        log_message(f"[X] 執行過程中發生錯誤: {e}")
        import traceback
        log_message(traceback.format_exc())
        log_message("=" * 70)
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)



