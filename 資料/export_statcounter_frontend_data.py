#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
從完整 StatCounter 爬蟲輸出的 JSON 中，整理出前端儀表板需要的
{country}_data.json（放在 deploy/statcounter_data 底下）。
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple

BASE_DIR = os.path.dirname(__file__)
RAW_DATA_DIR = os.path.join(BASE_DIR, "statcounter_data")
# 修正：Vercel 目前是從專案根目錄服務，因此直接輸出到根目錄的 statcounter_data
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, "statcounter_data")
# 保留備份路徑
BACKUP_FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, "deploy", "statcounter_data")


def find_latest_files() -> Dict[str, str]:
    """
    掃描 RAW_DATA_DIR，找出每個 country_code 最新的一個原始 JSON 檔。
    這些檔名格式為：{country_code}_YYYYMMDD_HHMMSS.json
    """
    latest: Dict[str, Tuple[str, datetime]] = {}

    if not os.path.isdir(RAW_DATA_DIR):
        print(f"[X] 找不到原始數據資料夾：{RAW_DATA_DIR}")
        return {}

    for filename in os.listdir(RAW_DATA_DIR):
        if not filename.endswith(".json"):
            continue
        # 排除匯總檔 all_countries_*.json
        if filename.startswith("all_countries_"):
            continue

        # 期望格式 1：{country}_{timestamp}.json
        # 期望格式 2：{country}_data.json (舊格式保底)
        name, _ext = os.path.splitext(filename)
        
        if name.endswith("_data"):
            country_code = name[:-5]
            ts = datetime.min
        else:
            parts = name.split("_", 1)
            if len(parts) != 2:
                continue
            country_code, ts_str = parts
            try:
                ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            except ValueError:
                continue

        current = latest.get(country_code)
        if current is None or ts > current[1]:
            latest[country_code] = (os.path.join(RAW_DATA_DIR, filename), ts)

    return {code: path for code, (path, _ts) in latest.items()}


def normalize_country_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    根據前端需求整理資料結構。
    目前完整爬蟲輸出的結構已經與前端期望的 countryData 結構相容，
    因此這裡主要是做保底處理與欄位存在性檢查。
    """
    country_code = raw.get("country_code")
    country_name = raw.get("country_name", country_code or "")
    update_time = raw.get("update_time")
    data = raw.get("data") or {}

    # 確保基本欄位存在
    return {
        "country_code": country_code,
        "country_name": country_name,
        "update_time": update_time,
        "data": data,
    }


def has_non_empty_series(data: Dict[str, Any]) -> bool:
    """
    檢查 data 結構裡是否至少有一個非空的 data 陣列。
    若全部都是 []，就不要覆蓋前端既有的 JSON，以免畫面沒有任何數據。
    """
    if not isinstance(data, dict):
        return False

    def visit(node: Any) -> bool:
        if isinstance(node, dict):
            # 若有 key "data" 且是非空 list，就視為有內容
            if "data" in node and isinstance(node["data"], list) and len(node["data"]) > 0:
                return True
            return any(visit(v) for v in node.values())
        elif isinstance(node, list):
            return any(visit(v) for v in node)
        return False

    return visit(data)


def export_frontend_files() -> None:
    """
    主流程：
    - 讀取最新原始檔
    - 同步輸出到這兩個資料夾（結構相同）：
      1) deploy/statcounter_data
      2) 專案根目錄的 statcounter_data
    這樣無論前端實際使用哪一層的 index.html，都能抓到最新 JSON。
    """
    latest_files = find_latest_files()
    if not latest_files:
        print("[!] 沒有找到可用的原始 JSON 檔，請先執行完整爬蟲。")
        return

    # 同步輸出的目標目錄
    output_dirs = [FRONTEND_DATA_DIR, BACKUP_FRONTEND_DATA_DIR]
    for d in output_dirs:
        os.makedirs(d, exist_ok=True)

    count = 0
    for country_code, path in sorted(latest_files.items()):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"[X] 無法讀取 {path}：{e}")
            continue

        normalized = normalize_country_data(raw)

        # 若新資料完全沒有任何數值，則跳過，不覆蓋前端舊有檔案
        if not has_non_empty_series(normalized.get("data") or {}):
            print(f"[!] {country_code}: 新資料全部為空陣列，略過匯出，保留前端原有 JSON。來源檔：{path}")
            continue

        # 前端固定檔名：{country}_data.json
        out_name = f"{country_code}_data.json"

        for target_dir in output_dirs:
            out_path = os.path.join(target_dir, out_name)
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(normalized, f, ensure_ascii=False, indent=2)
                print(f"已輸出前端數據：{out_path}")
            except Exception as e:
                print(f"[X] 寫入 {out_path} 失敗：{e}")

        count += 1

    print(f"\n[OK] 匯出完成，共產生 {count} 個前端 JSON 檔（每個輸出目錄各一份）")


if __name__ == "__main__":
    export_frontend_files()
