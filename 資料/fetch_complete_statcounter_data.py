#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的StatCounter數據獲取腳本
支持所有需要的數據類型：OS、分辨率、設備供應商、平台、搜索引擎、社交媒體、瀏覽器及版本
支持所有指定的國家/地區，包括英語系國家分別處理
"""

import re
import sys
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from selenium import webdriver

# Windows 命令列 cp950 無法顯示 emoji，強制 stdout/stderr 用 UTF-8 並忽略無法編碼的字元，避免 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 國家/地區代碼到StatCounter URL的映射
COUNTRY_URL_MAP = {
    # 全球和地區
    'global': {'name': 'worldwide', 'code': 'worldwide'},
    'asia': {'name': 'asia', 'code': 'asia'},
    'europe': {'name': 'europe', 'code': 'europe'},
    'africa': {'name': 'africa', 'code': 'africa'},
    'north-america': {'name': 'north-america', 'code': 'north-america'},
    
    # 台灣、中國、香港、澳門
    'tw': {'name': 'taiwan', 'code': 'tw'},
    'cn': {'name': 'china', 'code': 'cn'},
    'hk': {'name': 'hong-kong', 'code': 'hk'},
    'mo': {'name': 'macao', 'code': 'mo'},
    
    # 東亞和東南亞
    'kr': {'name': 'south-korea', 'code': 'kr'},
    'ph': {'name': 'philippines', 'code': 'ph'},
    'th': {'name': 'thailand', 'code': 'th'},
    # StatCounter 對越南使用 slug 'viet-nam'
    'vn': {'name': 'viet-nam', 'code': 'vn'},
    'id': {'name': 'indonesia', 'code': 'id'},
    'mm': {'name': 'myanmar', 'code': 'mm'},
    'jp': {'name': 'japan', 'code': 'jp'},
    'my': {'name': 'malaysia', 'code': 'my'},
    
    # 印度相關（注意：StatCounter可能沒有北印度/南印度的單獨數據）
    'in': {'name': 'india', 'code': 'in'},
    'in-north': {'name': 'india', 'code': 'in'},  # 使用印度整體數據
    'in-south': {'name': 'india', 'code': 'in'},  # 使用印度整體數據
    'bd': {'name': 'bangladesh', 'code': 'bd'},
    
    # 英語系國家（分別處理）
    'us': {'name': 'united-states-of-america', 'code': 'us'},
    'gb': {'name': 'united-kingdom', 'code': 'gb'},
    'ca': {'name': 'canada', 'code': 'ca'},
    'au': {'name': 'australia', 'code': 'au'},
    'nz': {'name': 'new-zealand', 'code': 'nz'},
    'ie': {'name': 'ireland', 'code': 'ie'},
    'za': {'name': 'south-africa', 'code': 'za'},
    
    # 歐洲其他國家
    'es': {'name': 'spain', 'code': 'es'},
    'pt': {'name': 'portugal', 'code': 'pt'},
    'it': {'name': 'italy', 'code': 'it'},
    'se': {'name': 'sweden', 'code': 'se'},
    'de': {'name': 'germany', 'code': 'de'},
    'dk': {'name': 'denmark', 'code': 'dk'},
    'ro': {'name': 'romania', 'code': 'ro'},
    'nl': {'name': 'netherlands', 'code': 'nl'},
    'gr': {'name': 'greece', 'code': 'gr'},
    'fr': {'name': 'france', 'code': 'fr'},
    
    # 其他
    'tr': {'name': 'turkey', 'code': 'tr'},
    # StatCounter 對俄羅斯使用 slug 'russian-federation'
    'ru': {'name': 'russian-federation', 'code': 'ru'},
    'pk': {'name': 'pakistan', 'code': 'pk'},
    'br': {'name': 'brazil', 'code': 'br'},
}

# 國家/地區中文名稱映射
COUNTRY_NAMES_CN = {
    'global': '全球',
    'asia': '亞洲',
    'europe': '歐洲',
    'africa': '非洲',
    'north-america': '北美洲',
    'tw': '台灣',
    'cn': '中國',
    'hk': '香港',
    'mo': '澳門',
    'kr': '韓國',
    'ph': '菲律賓',
    'th': '泰國',
    'vn': '越南',
    'id': '印尼',
    'mm': '緬甸',
    'jp': '日本',
    'my': '馬來西亞',
    'in': '印度',
    'in-north': '北印度',
    'in-south': '南印度',
    'bd': '孟加拉國',
    'us': '美國',
    'gb': '英國',
    'ca': '加拿大',
    'au': '澳洲',
    'nz': '紐西蘭',
    'ie': '愛爾蘭',
    'za': '南非',
    'es': '西班牙',
    'pt': '葡萄牙',
    'it': '義大利',
    'se': '瑞典',
    'de': '德國',
    'dk': '丹麥',
    'ro': '羅馬尼亞',
    'nl': '荷蘭',
    'gr': '希臘',
    'fr': '法國',
    'tr': '土耳其',
    'ru': '俄羅斯',
    'pk': '巴基斯坦',
    'br': '巴西',
}

def format_decimal(value):
    """確保數值保留兩位小數"""
    return round(float(value), 2)

def init_browser(headless=True):
    """初始化瀏覽器"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        print(f"[X] 無法啟動瀏覽器: {e}")
        print("請確保已安裝Chrome瀏覽器和ChromeDriver")
        return None

def scrape_table_data(driver, url, max_items=10, wait_time=5):
    """爬取表格數據"""
    try:
        print(f"    訪問: {url}")
        driver.get(url)
        
        # 等待頁面加載
        time.sleep(wait_time)
        
        # 等待表格出現
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
        except TimeoutException:
            print(f"    [!] 頁面加載超時，嘗試繼續...")
        
        data = []
        
        # 查找數據表格
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row in rows[1:]:  # 跳過表頭
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        name = cells[0].text.strip()
                        value_str = cells[1].text.strip().replace('%', '').replace(',', '').strip()
                        
                        # 嘗試提取數值
                        value_match = re.search(r'(\d+\.?\d*)', value_str)
                        if value_match:
                            value = format_decimal(float(value_match.group(1)))
                            if name and value > 0:
                                data.append({'name': name, 'value': value})
                except Exception as e:
                    continue
        
        # 如果表格中沒有數據，嘗試從頁面文本中提取
        if not data:
            page_text = driver.page_source
            # 查找可能的JSON數據
            json_match = re.search(r'var\s+\w+\s*=\s*(\[.*?\])', page_text, re.DOTALL)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    if isinstance(json_data, list):
                        for item in json_data:
                            if isinstance(item, dict):
                                name = item.get('name', '') or item.get('label', '') or item.get('browser', '') or item.get('os', '')
                                value = item.get('value', 0) or item.get('share', 0) or item.get('percentage', 0)
                                if name and value:
                                    data.append({'name': str(name), 'value': format_decimal(float(value))})
                except:
                    pass
        
        # 排序並只保留前N個
        data.sort(key=lambda x: x['value'], reverse=True)
        return data[:max_items]
        
    except Exception as e:
        print(f"    [X] 爬取失敗: {e}")
        return []

def get_url(country_code, data_type, **kwargs):
    """獲取StatCounter URL"""
    country_info = COUNTRY_URL_MAP.get(country_code, {'name': country_code, 'code': country_code})
    base_url = 'https://gs.statcounter.com'
    country_name = country_info['name']
    
    url_map = {
        # 平台數據
        'platform': f'{base_url}/platform-market-share/desktop-mobile-tablet/{country_name}',
        
        # OS市場佔有率
        'os_all': f'{base_url}/os-market-share/all/{country_name}',
        'os_desktop': f'{base_url}/os-market-share/desktop/{country_name}',
        'os_mobile': f'{base_url}/os-market-share/mobile/{country_name}',
        'os_tablet': f'{base_url}/os-market-share/tablet/{country_name}',
        
        # OS版本
        'os_version_windows': f'{base_url}/windows-version-market-share/desktop/{country_name}',
        'os_version_macos': f'{base_url}/macos-version-market-share/desktop/{country_name}',
        'os_version_ios_mobile': f'{base_url}/ios-version-market-share/mobile/{country_name}',
        'os_version_android_mobile': f'{base_url}/android-version-market-share/mobile/{country_name}',
        'os_version_ios_tablet': f'{base_url}/ios-version-market-share/tablet/{country_name}',
        'os_version_android_tablet': f'{base_url}/android-version-market-share/tablet/{country_name}',
        
        # 屏幕分辨率
        'resolution_all': f'{base_url}/screen-resolution-stats/all/{country_name}',
        'resolution_desktop': f'{base_url}/screen-resolution-stats/desktop/{country_name}',
        'resolution_mobile': f'{base_url}/screen-resolution-stats/mobile/{country_name}',
        'resolution_tablet': f'{base_url}/screen-resolution-stats/tablet/{country_name}',
        
        # 設備供應商
        'vendor_all': f'{base_url}/vendor-market-share/all/{country_name}',
        'vendor_mobile': f'{base_url}/vendor-market-share/mobile-device/{country_name}',
        'vendor_tablet': f'{base_url}/vendor-market-share/tablet/{country_name}',
        
        # 搜索引擎
        'search_engine_all': f'{base_url}/search-engine-market-share/all/{country_name}',
        'search_engine_desktop': f'{base_url}/search-engine-market-share/desktop/{country_name}',
        'search_engine_mobile': f'{base_url}/search-engine-market-share/mobile/{country_name}',
        'search_engine_tablet': f'{base_url}/search-engine-market-share/tablet/{country_name}',
        
        # 社交媒體
        'social_media_all': f'{base_url}/social-media-stats/all/{country_name}',
        'social_media_desktop': f'{base_url}/social-media-stats/desktop/{country_name}',
        'social_media_mobile': f'{base_url}/social-media-stats/mobile/{country_name}',
        'social_media_tablet': f'{base_url}/social-media-stats/tablet/{country_name}',
        
        # 瀏覽器
        'browser_all': f'{base_url}/browser-market-share/all/{country_name}',
        'browser_desktop': f'{base_url}/browser-market-share/desktop/{country_name}',
        'browser_mobile': f'{base_url}/browser-market-share/mobile/{country_name}',
        'browser_tablet': f'{base_url}/browser-market-share/tablet/{country_name}',
        
        # 瀏覽器版本
        'browser_version_all': f'{base_url}/browser-version-market-share/all/{country_name}',
        'browser_version_desktop': f'{base_url}/browser-version-market-share/desktop/{country_name}',
        'browser_version_mobile': f'{base_url}/browser-version-market-share/mobile/{country_name}',
        'browser_version_tablet': f'{base_url}/browser-version-market-share/tablet/{country_name}',
    }
    
    # 處理全球數據的特殊URL
    if country_code == 'global':
        if data_type == 'platform':
            return f'{base_url}/platform-market-share/desktop-mobile-tablet/worldwide'
        elif data_type.startswith('browser') and 'all' in data_type:
            return f'{base_url}/browser-market-share/all-worldwide/worldwide'
    
    return url_map.get(data_type, '')

def scrape_country_data(driver, country_code):
    """爬取單個國家的所有數據"""
    country_name = COUNTRY_NAMES_CN.get(country_code, country_code)
    print(f"\n{'='*70}")
    print(f"處理 {country_name} ({country_code})...")
    print(f"{'='*70}")
    
    scraped_data = {
        'country_code': country_code,
        'country_name': country_name,
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data': {}
    }
    
    # 1. 平台數據 (Mobile/Tablet/Desktop)
    print("\n  1. 爬取平台數據 (Platform)...")
    platform_url = get_url(country_code, 'platform')
    platform_data = scrape_table_data(driver, platform_url, max_items=10)
    scraped_data['data']['platform'] = {
        'url': platform_url,
        'data': platform_data
    }
    print(f"     [OK] 獲取 {len(platform_data)} 條平台數據")
    time.sleep(2)
    
    # 2. OS市場佔有率
    print("\n  2. 爬取OS市場佔有率...")
    os_data = {}
    for platform_type in ['all', 'desktop', 'mobile', 'tablet']:
        os_url = get_url(country_code, f'os_{platform_type}')
        if os_url:
            data = scrape_table_data(driver, os_url, max_items=10)
            os_data[platform_type] = {
                'url': os_url,
                'data': data
            }
            print(f"     [OK] {platform_type}: {len(data)} 條")
            time.sleep(1)
    scraped_data['data']['os_market_share'] = os_data
    time.sleep(2)
    
    # 3. OS版本數據
    print("\n  3. 爬取OS版本數據...")
    os_version_data = {}
    os_version_configs = [
        ('windows', 'desktop'),
        ('macos', 'desktop'),
        ('ios', 'mobile'),
        ('android', 'mobile'),
        ('ios', 'tablet'),
        ('android', 'tablet'),
    ]
    for os_type, platform in os_version_configs:
        os_url = get_url(country_code, f'os_version_{os_type}_{platform}')
        if os_url:
            data = scrape_table_data(driver, os_url, max_items=15)
            key = f'{os_type}_{platform}'
            os_version_data[key] = {
                'url': os_url,
                'data': data
            }
            print(f"     [OK] {os_type} ({platform}): {len(data)} 條")
            time.sleep(1)
    scraped_data['data']['os_version'] = os_version_data
    time.sleep(2)
    
    # 4. 屏幕分辨率
    print("\n  4. 爬取屏幕分辨率數據...")
    resolution_data = {}
    for platform_type in ['all', 'desktop', 'mobile', 'tablet']:
        res_url = get_url(country_code, f'resolution_{platform_type}')
        if res_url:
            data = scrape_table_data(driver, res_url, max_items=10)
            resolution_data[platform_type] = {
                'url': res_url,
                'data': data
            }
            print(f"     [OK] {platform_type}: {len(data)} 條")
            time.sleep(1)
    scraped_data['data']['resolution'] = resolution_data
    time.sleep(2)
    
    # 5. 設備供應商
    print("\n  5. 爬取設備供應商數據...")
    vendor_data = {}
    for device_type in ['all', 'mobile', 'tablet']:
        vendor_url = get_url(country_code, f'vendor_{device_type}')
        if vendor_url:
            data = scrape_table_data(driver, vendor_url, max_items=10)
            vendor_data[device_type] = {
                'url': vendor_url,
                'data': data
            }
            print(f"     [OK] {device_type}: {len(data)} 條")
            time.sleep(1)
    scraped_data['data']['vendor'] = vendor_data
    time.sleep(2)
    
    # 6. 搜索引擎
    print("\n  6. 爬取搜索引擎數據...")
    search_engine_data = {}
    for platform_type in ['all', 'desktop', 'mobile', 'tablet']:
        se_url = get_url(country_code, f'search_engine_{platform_type}')
        if se_url:
            data = scrape_table_data(driver, se_url, max_items=10)
            search_engine_data[platform_type] = {
                'url': se_url,
                'data': data
            }
            print(f"     [OK] {platform_type}: {len(data)} 條")
            time.sleep(1)
    scraped_data['data']['search_engine'] = search_engine_data
    time.sleep(2)
    
    # 7. 社交媒體
    print("\n  7. 爬取社交媒體數據...")
    social_media_data = {}
    for platform_type in ['all', 'desktop', 'mobile', 'tablet']:
        sm_url = get_url(country_code, f'social_media_{platform_type}')
        if sm_url:
            data = scrape_table_data(driver, sm_url, max_items=10)
            social_media_data[platform_type] = {
                'url': sm_url,
                'data': data
            }
            print(f"     [OK] {platform_type}: {len(data)} 條")
            time.sleep(1)
    scraped_data['data']['social_media'] = social_media_data
    time.sleep(2)
    
    # 8. 瀏覽器
    print("\n  8. 爬取瀏覽器數據...")
    browser_data = {}
    for platform_type in ['all', 'desktop', 'mobile', 'tablet']:
        browser_url = get_url(country_code, f'browser_{platform_type}')
        if browser_url:
            data = scrape_table_data(driver, browser_url, max_items=10)
            browser_data[platform_type] = {
                'url': browser_url,
                'data': data
            }
            print(f"     [OK] {platform_type}: {len(data)} 條")
            time.sleep(1)
    scraped_data['data']['browser'] = browser_data
    time.sleep(2)
    
    # 9. 瀏覽器版本
    print("\n  9. 爬取瀏覽器版本數據...")
    browser_version_data = {}
    for platform_type in ['all', 'desktop', 'mobile', 'tablet']:
        bv_url = get_url(country_code, f'browser_version_{platform_type}')
        if bv_url:
            data = scrape_table_data(driver, bv_url, max_items=15)
            browser_version_data[platform_type] = {
                'url': bv_url,
                'data': data
            }
            print(f"     [OK] {platform_type}: {len(data)} 條")
            time.sleep(1)
    scraped_data['data']['browser_version'] = browser_version_data
    time.sleep(2)
    
    print(f"\n  [OK] {country_name} 數據爬取完成")
    return scraped_data

def save_data_to_json(data, output_dir='statcounter_data'):
    """保存數據到JSON文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    country_code = data['country_code']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{country_code}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  數據已保存到: {filepath}")
    return filepath

def main():
    """主函數"""
    print("=" * 70)
    print("StatCounter 完整數據獲取工具")
    print("=" * 70)
    print()
    print("支持的數據類型：")
    print("  1. 平台市場佔有率 (Platform)")
    print("  2. 作業系統市場佔有率 (OS Market Share)")
    print("  3. 作業系統版本 (OS Version)")
    print("  4. 屏幕分辨率 (Screen Resolution)")
    print("  5. 設備供應商 (Device Vendor)")
    print("  6. 搜索引擎 (Search Engine)")
    print("  7. 社交媒體 (Social Media)")
    print("  8. 瀏覽器 (Browser)")
    print("  9. 瀏覽器版本 (Browser Version)")
    print()
    
    # 需要處理的國家/地區列表
    countries_to_process = [
        'global', 'tw', 'cn', 'hk', 'mo', 'kr', 'ph', 'th', 'vn', 'id', 'mm', 'jp',
        'in', 'in-north', 'in-south', 'bd', 'my',
        'us', 'gb', 'ca', 'au', 'nz', 'ie', 'za',  # 英語系國家分別處理
        'es', 'pt', 'br', 'it', 'se', 'de', 'dk', 'ro', 'nl', 'tr', 'ru', 'fr', 'pk', 'gr',
        'asia', 'europe', 'africa', 'north-america'
    ]
    
    print(f"將處理 {len(countries_to_process)} 個國家/地區")
    print()
    
    # 初始化瀏覽器
    print("正在初始化瀏覽器...")
    driver = init_browser(headless=True)
    if not driver:
        print("[X] 無法啟動瀏覽器")
        return
    
    all_data = {}
    
    try:
        for idx, country_code in enumerate(countries_to_process, 1):
            print(f"\n[{idx}/{len(countries_to_process)}]")
            try:
                data = scrape_country_data(driver, country_code)
                all_data[country_code] = data
                
                # 保存單個國家的數據
                save_data_to_json(data)
                
                # 批次間延遲
                if idx < len(countries_to_process):
                    print(f"\n等待 5 秒後處理下一個國家...")
                    time.sleep(5)
                    
            except Exception as e:
                print(f"  [X] 處理 {country_code} 時發生錯誤: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 保存所有數據的匯總文件
        summary_file = os.path.join('statcounter_data', f'all_countries_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\n所有數據匯總已保存到: {summary_file}")
        
        print("\n" + "=" * 70)
        print("[OK] 所有國家/地區數據爬取完成")
        print("=" * 70)
        
    finally:
        driver.quit()
        print("\n瀏覽器已關閉")

if __name__ == '__main__':
    main()



