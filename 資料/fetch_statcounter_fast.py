#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速StatCounter數據獲取腳本 - 僅全球和台灣
優化速度，目標15分鐘內完成
"""

import re
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# 所有需要處理的國家/地區
COUNTRIES_TO_PROCESS = {
    # 全球和地區
    'global': {'name': 'worldwide', 'cn': '全球'},
    'asia': {'name': 'asia', 'cn': '亞洲'},
    'europe': {'name': 'europe', 'cn': '歐洲'},
    'africa': {'name': 'africa', 'cn': '非洲'},
    'north-america': {'name': 'north-america', 'cn': '北美洲'},
    
    # 台灣、中國、香港、澳門
    'tw': {'name': 'taiwan', 'cn': '台灣'},
    'cn': {'name': 'china', 'cn': '中國'},
    'hk': {'name': 'hong-kong', 'cn': '香港'},
    'mo': {'name': 'macao', 'cn': '澳門'},
    
    # 東亞和東南亞
    'kr': {'name': 'south-korea', 'cn': '韓國'},
    'ph': {'name': 'philippines', 'cn': '菲律賓'},
    'th': {'name': 'thailand', 'cn': '泰國'},
    # StatCounter 對越南使用 slug 'viet-nam'
    'vn': {'name': 'viet-nam', 'cn': '越南'},
    'id': {'name': 'indonesia', 'cn': '印尼'},
    'mm': {'name': 'myanmar', 'cn': '緬甸'},
    'jp': {'name': 'japan', 'cn': '日本'},
    'my': {'name': 'malaysia', 'cn': '馬來西亞'},
    
    # 印度相關
    'in': {'name': 'india', 'cn': '印度'},
    'bd': {'name': 'bangladesh', 'cn': '孟加拉國'},
    
    # 英語系國家（分別處理）
    'us': {'name': 'united-states-of-america', 'cn': '美國'},
    'gb': {'name': 'united-kingdom', 'cn': '英國'},
    'ca': {'name': 'canada', 'cn': '加拿大'},
    'au': {'name': 'australia', 'cn': '澳洲'},
    'nz': {'name': 'new-zealand', 'cn': '紐西蘭'},
    'ie': {'name': 'ireland', 'cn': '愛爾蘭'},
    'za': {'name': 'south-africa', 'cn': '南非'},
    
    # 歐洲其他國家
    'es': {'name': 'spain', 'cn': '西班牙'},
    'pt': {'name': 'portugal', 'cn': '葡萄牙'},
    'it': {'name': 'italy', 'cn': '義大利'},
    'se': {'name': 'sweden', 'cn': '瑞典'},
    'de': {'name': 'germany', 'cn': '德國'},
    'dk': {'name': 'denmark', 'cn': '丹麥'},
    'ro': {'name': 'romania', 'cn': '羅馬尼亞'},
    'nl': {'name': 'netherlands', 'cn': '荷蘭'},
    'gr': {'name': 'greece', 'cn': '希臘'},
    'fr': {'name': 'france', 'cn': '法國'},
    
    # 其他
    'tr': {'name': 'turkey', 'cn': '土耳其'},
    # StatCounter 對俄羅斯使用 slug 'russian-federation'
    'ru': {'name': 'russian-federation', 'cn': '俄羅斯'},
    'pk': {'name': 'pakistan', 'cn': '巴基斯坦'},
    'br': {'name': 'brazil', 'cn': '巴西'},
}

def format_decimal(value):
    """確保數值保留兩位小數"""
    return round(float(value), 2)

def init_browser(headless=True):
    """初始化瀏覽器 - 優化設置"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-images')  # 禁用圖片加載加快速度
    # 注意：StatCounter需要JavaScript，所以不能禁用
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # 禁用不必要的功能
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)  # 減少等待時間
        return driver
    except Exception as e:
        print(f"[X] 無法啟動瀏覽器: {e}")
        return None

def extract_table_data(driver, max_items=10):
    """快速提取表格數據 - 改進版本"""
    data = []
    try:
        # 等待頁面加載完成 - 增加等待時間讓JavaScript渲染
        time.sleep(5)
        
        # 等待表格出現，增加超時時間
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            # 額外等待讓數據完全渲染
            time.sleep(3)
        except TimeoutException:
            print("    ⚠️  等待表格超時，嘗試繼續...")
            time.sleep(2)  # 即使超時也等待一下
        
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            try:
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows[1:]:  # 跳過表頭
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            name = cells[0].text.strip()
                            value_str = cells[1].text.strip().replace('%', '').replace(',', '').strip()
                            
                            if not name or not value_str:
                                continue
                            
                            # 提取數值
                            value_match = re.search(r'(\d+\.?\d*)', value_str)
                            if value_match:
                                value = format_decimal(float(value_match.group(1)))
                                if value > 0:
                                    data.append({'name': name, 'value': value})
                                    if len(data) >= max_items:
                                        break
                    except Exception as e:
                        continue
                if len(data) >= max_items:
                    break
            except:
                continue
        
        # 方法2: 如果表格沒有數據，從頁面源碼提取
        if not data:
            page_source = driver.page_source
            
            # 嘗試多種模式
            patterns = [
                r'<td[^>]*>([^<]+)</td>\s*<td[^>]*>([\d.]+)%</td>',
                r'<td[^>]*>([^<]+)</td>\s*<td[^>]*>([\d.]+)\s*%</td>',
                r'"name":"([^"]+)","value":([\d.]+)',
                r'label["\']?\s*:\s*["\']([^"\']+)["\']\s*,\s*value["\']?\s*:\s*([\d.]+)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches[:max_items]:
                    try:
                        if len(match) == 2:
                            name = match[0].strip()
                            value_str = match[1].strip()
                            value = format_decimal(float(value_str))
                            if value > 0 and name:
                                # 避免重複
                                if not any(d['name'] == name for d in data):
                                    data.append({'name': name, 'value': value})
                                    if len(data) >= max_items:
                                        break
                    except:
                        continue
                if len(data) >= max_items:
                    break
        
        # 方法3: 嘗試執行JavaScript獲取數據（改進版）
        if not data:
            try:
                # StatCounter可能使用JavaScript渲染數據
                js_data = driver.execute_script("""
                    var data = [];
                    
                    // 方法3.1: 從表格提取
                    var tables = document.querySelectorAll('table');
                    tables.forEach(function(table) {
                        var rows = table.querySelectorAll('tr');
                        for (var i = 1; i < rows.length; i++) {
                            var cells = rows[i].querySelectorAll('td, th');
                            if (cells.length >= 2) {
                                var name = cells[0].textContent.trim();
                                var valueStr = cells[1].textContent.trim().replace('%', '').replace(',', '').replace(' ', '');
                                var value = parseFloat(valueStr);
                                if (name && !isNaN(value) && value > 0) {
                                    data.push({name: name, value: value});
                                }
                            }
                        }
                    });
                    
                    // 方法3.2: 從頁面中的文本內容提取（如果表格為空）
                    if (data.length === 0) {
                        var pageText = document.body.innerText;
                        var lines = pageText.split('\\n');
                        for (var i = 0; i < lines.length; i++) {
                            var line = lines[i].trim();
                            // 查找包含百分比的行的模式，如 "Chrome 71.23%"
                            var match = line.match(/([A-Za-z\\s]+)\\s+([\\d.]+)%/);
                            if (match && match.length === 3) {
                                var name = match[1].trim();
                                var value = parseFloat(match[2]);
                                if (name && !isNaN(value) && value > 0 && value <= 100) {
                                    data.push({name: name, value: value});
                                }
                            }
                        }
                    }
                    
                    return data;
                """)
                if js_data and len(js_data) > 0:
                    for item in js_data[:max_items]:
                        try:
                            data.append({
                                'name': item['name'],
                                'value': format_decimal(item['value'])
                            })
                        except:
                            continue
            except Exception as e:
                print(f"    ⚠️  JavaScript提取失敗: {e}")
        
        # 方法4: 嘗試從頁面可見文本中提取（最後嘗試）
        if not data:
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                lines = page_text.split('\n')
                for line in lines:
                    # 查找模式：名稱 + 數字 + %
                    match = re.search(r'([A-Za-z\s]{2,30})\s+(\d+\.?\d*)%', line)
                    if match:
                        name = match.group(1).strip()
                        value = format_decimal(float(match.group(2)))
                        if value > 0 and value <= 100 and len(name) > 1:
                            # 避免重複和無效名稱
                            if not any(d['name'] == name for d in data) and name.lower() not in ['total', 'other', 'unknown']:
                                data.append({'name': name, 'value': value})
                                if len(data) >= max_items:
                                    break
            except:
                pass
        
        # 排序並限制數量
        data.sort(key=lambda x: x['value'], reverse=True)
        return data[:max_items]
        
    except Exception as e:
        print(f"    ⚠️  提取數據時出錯: {e}")
        return []

def get_url(country_code, data_type):
    """獲取StatCounter URL"""
    country_info = COUNTRIES_TO_PROCESS.get(country_code)
    if not country_info:
        return None
    
    base_url = 'https://gs.statcounter.com'
    country_name = country_info['name']
    
    url_map = {
        # 關鍵數據類型
        'platform': f'{base_url}/platform-market-share/desktop-mobile-tablet/{country_name}',
        'os_all': f'{base_url}/os-market-share/all/{country_name}',
        'browser_all': f'{base_url}/browser-market-share/all/{country_name}',
        'resolution_all': f'{base_url}/screen-resolution-stats/all/{country_name}',
        'vendor_mobile': f'{base_url}/vendor-market-share/mobile-device/{country_name}',
        'search_engine_all': f'{base_url}/search-engine-market-share/all/{country_name}',
        'social_media_all': f'{base_url}/social-media-stats/all/{country_name}',
    }
    
    # 處理全球和地區的特殊URL
    if country_code == 'global':
        if data_type == 'platform':
            return f'{base_url}/platform-market-share/desktop-mobile-tablet/worldwide'
        elif data_type == 'browser_all':
            return f'{base_url}/browser-market-share/all-worldwide/worldwide'
    
    # 處理地區URL
    if country_code in ['asia', 'europe', 'africa', 'north-america']:
        # 地區使用相同的URL結構
        pass
    
    return url_map.get(data_type, '')

def scrape_country_data_fast(driver, country_code):
    """快速爬取單個國家的關鍵數據"""
    country_info = COUNTRIES_TO_PROCESS.get(country_code)
    if not country_info:
        return None
    
    country_name = country_info['cn']
    print(f"\n{'='*60}")
    print(f"處理 {country_name} ({country_code})...")
    print(f"{'='*60}")
    
    scraped_data = {
        'country_code': country_code,
        'country_name': country_name,
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data': {}
    }
    
    # 只爬取關鍵數據類型，減少時間
    data_types = [
        ('platform', '平台市場佔有率', 5),
        ('os_all', '作業系統', 10),
        ('browser_all', '瀏覽器', 10),
        ('resolution_all', '屏幕分辨率', 5),
        ('vendor_mobile', '手機品牌', 5),
        ('search_engine_all', '搜索引擎', 5),
        ('social_media_all', '社交媒體', 5),
    ]
    
    for data_type, name, max_items in data_types:
        print(f"  {name}...", end=' ', flush=True)
        url = get_url(country_code, data_type)
        if not url:
            print("[X] URL無效")
            continue
        
        try:
            print(f"    訪問: {url[:80]}...")
            driver.get(url)
            
            # 增加等待時間，確保JavaScript完全渲染
            data = extract_table_data(driver, max_items=max_items)
            
            if data:
                scraped_data['data'][data_type] = {
                    'url': url,
                    'data': data
                }
                print(f"OK {len(data)} 條")
                # 顯示前3條數據作為預覽
                for item in data[:3]:
                    print(f"      - {item['name']}: {item['value']}%")
            else:
                print("[!] 無數據")
                scraped_data['data'][data_type] = {
                    'url': url,
                    'data': []
                }
                # 保存頁面截圖用於調試
                try:
                    screenshot_path = f"debug_{country_code}_{data_type}_{int(time.time())}.png"
                    driver.save_screenshot(screenshot_path)
                    print(f"      已保存調試截圖: {screenshot_path}")
                except:
                    pass
        except Exception as e:
            print(f"[X] 錯誤: {e}")
            scraped_data['data'][data_type] = {
                'url': url,
                'data': []
            }
        
        time.sleep(1)  # 請求間短暫延遲
    
    print(f"\n  [OK] {country_name} 完成")
    return scraped_data

def save_data_to_json(data, output_dir='statcounter_data'):
    """保存數據到JSON文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    country_code = data['country_code']
    filename = f"{country_code}_data.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  已保存: {filepath}")
    return filepath

def main():
    """主函數"""
    print("=" * 60)
    print("StatCounter 數據獲取 - 所有國家/地區（快速版）")
    print("=" * 60)
    print(f"將處理 {len(COUNTRIES_TO_PROCESS)} 個國家/地區")
    print()
    
    start_time = time.time()
    
    # 初始化瀏覽器
    print("正在初始化瀏覽器...")
    driver = init_browser(headless=True)
    if not driver:
        print("[X] 無法啟動瀏覽器")
        return
    
    all_data = {}
    
    try:
        for country_code in COUNTRIES_TO_PROCESS.keys():
            try:
                data = scrape_country_data_fast(driver, country_code)
                if data:
                    all_data[country_code] = data
                    save_data_to_json(data)
            except Exception as e:
                print(f"[X] 處理 {country_code} 時發生錯誤: {e}")
                import traceback
                traceback.print_exc()
        
        # 保存匯總文件
        summary_file = os.path.join('statcounter_data', 'summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\n匯總文件已保存: {summary_file}")
        
        elapsed_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"[OK] 完成！耗時: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分鐘)")
        print(f"{'='*60}")
        
    finally:
        driver.quit()
        print("\n瀏覽器已關閉")

if __name__ == '__main__':
    main()

