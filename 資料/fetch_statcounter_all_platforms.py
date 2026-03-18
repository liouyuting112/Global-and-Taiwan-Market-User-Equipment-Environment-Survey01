#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StatCounter數據獲取腳本 - 支持所有平台分類（所有平台、手機、電腦、平板）
優化速度，目標30分鐘內完成所有國家
支持實時更新HTML
"""

import re
import time
import json
import os
from datetime import datetime, timezone, timedelta
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
    'vn': {'name': 'viet-nam', 'cn': '越南'},  # StatCounter URL 格式：viet-nam（有連字符）
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
    'ru': {'name': 'russian-federation', 'cn': '俄羅斯'},  # StatCounter URL 格式：russian-federation（完整名稱）
    'pk': {'name': 'pakistan', 'cn': '巴基斯坦'},
    'br': {'name': 'brazil', 'cn': '巴西'},
}

# 平台列表
PLATFORMS = ['all', 'mobile', 'desktop', 'tablet']

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
    chrome_options.add_argument('--disable-images')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)
        return driver
    except Exception as e:
        print(f"❌ 無法啟動瀏覽器: {e}")
        return None

def extract_table_data(driver, max_items=10):
    """快速提取表格數據 - 改進版本"""
    data = []
    try:
        time.sleep(2)  # 減少等待時間
        
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            time.sleep(1)  # 減少額外等待
        except TimeoutException:
            time.sleep(2)
        
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            try:
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows[1:]:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            name = cells[0].text.strip()
                            value_str = cells[1].text.strip().replace('%', '').replace(',', '').strip()
                            
                            if not name or not value_str:
                                continue
                            
                            value_match = re.search(r'(\d+\.?\d*)', value_str)
                            if value_match:
                                value = format_decimal(float(value_match.group(1)))
                                if value > 0:
                                    data.append({'name': name, 'value': value})
                                    if len(data) >= max_items:
                                        break
                    except:
                        continue
                if len(data) >= max_items:
                    break
            except:
                continue
        
        if not data:
            page_source = driver.page_source
            patterns = [
                r'<td[^>]*>([^<]+)</td>\s*<td[^>]*>([\d.]+)%</td>',
                r'"name":"([^"]+)","value":([\d.]+)',
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
                                if not any(d['name'] == name for d in data):
                                    data.append({'name': name, 'value': value})
                                    if len(data) >= max_items:
                                        break
                    except:
                        continue
                if len(data) >= max_items:
                    break
        
        if not data:
            try:
                js_data = driver.execute_script("""
                    var data = [];
                    var tables = document.querySelectorAll('table');
                    tables.forEach(function(table) {
                        var rows = table.querySelectorAll('tr');
                        for (var i = 1; i < rows.length; i++) {
                            var cells = rows[i].querySelectorAll('td, th');
                            if (cells.length >= 2) {
                                var name = cells[0].textContent.trim();
                                var valueStr = cells[1].textContent.trim().replace('%', '').replace(',', '');
                                var value = parseFloat(valueStr);
                                if (name && !isNaN(value) && value > 0) {
                                    data.push({name: name, value: value});
                                }
                            }
                        }
                    });
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
            except:
                pass
        
        data.sort(key=lambda x: x['value'], reverse=True)
        return data[:max_items]
        
    except Exception as e:
        print(f"    ⚠️  提取數據時出錯: {e}")
        return []

def get_url(country_code, data_type, platform='all'):
    """獲取StatCounter URL - 支持平台分類"""
    country_info = COUNTRIES_TO_PROCESS.get(country_code)
    if not country_info:
        return None
    
    base_url = 'https://gs.statcounter.com'
    country_name = country_info['name']
    
    # 根據數據類型和平台構建URL
    url_templates = {
        'platform': {
            'all': f'{base_url}/platform-market-share/desktop-mobile-tablet/{country_name}',
        },
        'os': {
            'all': f'{base_url}/os-market-share/all/{country_name}',
            'mobile': f'{base_url}/os-market-share/mobile/{country_name}',
            'desktop': f'{base_url}/os-market-share/desktop/{country_name}',
            'tablet': f'{base_url}/os-market-share/tablet/{country_name}',
        },
        'browser': {
            'all': f'{base_url}/browser-market-share/all/{country_name}',
            'mobile': f'{base_url}/browser-market-share/mobile/{country_name}',
            'desktop': f'{base_url}/browser-market-share/desktop/{country_name}',
            'tablet': f'{base_url}/browser-market-share/tablet/{country_name}',
        },
        'resolution': {
            'all': f'{base_url}/screen-resolution-stats/all/{country_name}',
            'mobile': f'{base_url}/screen-resolution-stats/mobile/{country_name}',
            'desktop': f'{base_url}/screen-resolution-stats/desktop/{country_name}',
            'tablet': f'{base_url}/screen-resolution-stats/tablet/{country_name}',
        },
        'vendor_mobile': {
            'all': f'{base_url}/vendor-market-share/mobile/{country_name}',
            'mobile': f'{base_url}/vendor-market-share/mobile/{country_name}',
        },
        'vendor_tablet': {
            'all': f'{base_url}/vendor-market-share/tablet/{country_name}',
            'tablet': f'{base_url}/vendor-market-share/tablet/{country_name}',
        },
        'search_engine': {
            'all': f'{base_url}/search-engine-market-share/all/{country_name}',
            'mobile': f'{base_url}/search-engine-market-share/mobile/{country_name}',
            'desktop': f'{base_url}/search-engine-market-share/desktop/{country_name}',
            'tablet': f'{base_url}/search-engine-market-share/tablet/{country_name}',
        },
        'social_media': {
            'all': f'{base_url}/social-media-stats/all/{country_name}',
            'mobile': f'{base_url}/social-media-stats/mobile/{country_name}',
            'desktop': f'{base_url}/social-media-stats/desktop/{country_name}',
            'tablet': f'{base_url}/social-media-stats/tablet/{country_name}',
        },
    }
    
    # 處理全球的特殊URL
    if country_code == 'global':
        if data_type == 'platform':
            return f'{base_url}/platform-market-share/desktop-mobile-tablet/worldwide'
        elif data_type == 'browser' and platform == 'all':
            return f'{base_url}/browser-market-share/all-worldwide/worldwide'
        elif data_type == 'vendor_mobile':
            if platform == 'all' or platform == 'mobile':
                return f'{base_url}/vendor-market-share/mobile'
        elif data_type == 'vendor_tablet':
            if platform == 'all' or platform == 'tablet':
                return f'{base_url}/vendor-market-share/tablet'
    
    # 處理 vendor_mobile 和 vendor_tablet
    if data_type == 'vendor_mobile':
        templates = url_templates.get('vendor_mobile', {})
        if platform == 'all' or platform == 'mobile':
            return templates.get(platform, templates.get('all', ''))
        return None
    elif data_type == 'vendor_tablet':
        templates = url_templates.get('vendor_tablet', {})
        if platform == 'all' or platform == 'tablet':
            return templates.get(platform, templates.get('all', ''))
        return None
    
    data_type_map = {
        'platform': 'platform',
        'os_all': 'os',
        'browser_all': 'browser',
        'resolution_all': 'resolution',
        'search_engine_all': 'search_engine',
        'social_media_all': 'social_media',
    }
    
    mapped_type = data_type_map.get(data_type)
    if not mapped_type:
        return None
    
    templates = url_templates.get(mapped_type, {})
    return templates.get(platform, templates.get('all', ''))

def scrape_country_data(driver, country_code):
    """爬取單個國家的所有數據 - 支持平台分類"""
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
        'update_time': datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
        'data': {}
    }
    
    # 數據類型配置：(數據類型, 中文名, 最大項目數, 支持的平台列表)
    data_configs = [
        ('platform', '平台市場佔有率', 5, ['all']),
        ('os_all', '作業系統', 10, PLATFORMS),
        ('browser_all', '瀏覽器', 10, PLATFORMS),
        ('resolution_all', '屏幕分辨率', 5, PLATFORMS),
        ('vendor_mobile', '設備供應商(手機)', 5, ['all', 'mobile']),  # 所有平台和手機平台
        ('vendor_tablet', '設備供應商(平板)', 5, ['all', 'tablet']),  # 所有平台和平板平台
        ('search_engine_all', '搜索引擎', 5, PLATFORMS),
        ('social_media_all', '社交媒體', 5, PLATFORMS),
    ]
    
    for data_type, name, max_items, platforms in data_configs:
        print(f"\n  📊 {name}...")
        scraped_data['data'][data_type] = {}
        
        for platform in platforms:
            url = get_url(country_code, data_type, platform)
            if not url:
                continue
            
            print(f"    {platform}...", end=' ', flush=True)
            
            try:
                driver.get(url)
                data = extract_table_data(driver, max_items=max_items)
                
                if data:
                    scraped_data['data'][data_type][platform] = {
                        'url': url,
                        'data': data
                    }
                    print(f"✅ {len(data)} 條")
                else:
                    scraped_data['data'][data_type][platform] = {
                        'url': url,
                        'data': []
                    }
                    print("⚠️  無數據")
                
                time.sleep(0.5)  # 減少請求間延遲
                
            except Exception as e:
                print(f"❌ 錯誤: {e}")
                scraped_data['data'][data_type][platform] = {
                    'url': url,
                    'data': []
                }
    
    print(f"\n  ✅ {country_name} 完成")
    return scraped_data

def save_data_to_json(data, output_dir='statcounter_data'):
    """保存數據到JSON文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    country_code = data['country_code']
    # 格式化為 {country_code}_{YYYYMMDD_HHMMSS}.json，以支援月度更新腳本
    # 強制使用台灣時間 (UTC+8) 作為檔名時間戳
    tw_now = datetime.now(timezone(timedelta(hours=8)))
    timestamp = tw_now.strftime('%Y%m%d_%H%M%S')
    filename = f"{country_code}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

def main():
    """主函數"""
    import sys
    
    # 支持命令行參數指定批次
    batch_countries = None
    if len(sys.argv) > 1:
        batch_name = sys.argv[1]
        batch_map = {
            'batch1': ['global', 'tw', 'cn', 'hk', 'mo', 'kr', 'jp'],
            'batch2': ['ph', 'th', 'vn', 'id', 'mm', 'my'],
            'batch3': ['in', 'bd', 'pk'],
            'batch4': ['us', 'gb', 'ca', 'au', 'nz', 'ie', 'za'],
            'batch5': ['es', 'pt', 'it', 'se', 'de', 'dk', 'ro', 'nl', 'gr', 'fr'],
            'batch6': ['tr', 'ru', 'br', 'asia', 'europe', 'africa', 'north-america'],
        }
        if batch_name in batch_map:
            batch_countries = batch_map[batch_name]
            print(f"批次模式: {batch_name}")
            print(f"將處理: {', '.join(batch_countries)}")
    
    print("=" * 60)
    print("StatCounter 數據獲取 - 支持平台分類")
    print("=" * 60)
    
    if batch_countries:
        # 只處理指定批次
        countries_to_process = {k: v for k, v in COUNTRIES_TO_PROCESS.items() if k in batch_countries}
        print(f"將處理 {len(countries_to_process)} 個國家/地區")
    else:
        countries_to_process = COUNTRIES_TO_PROCESS
        print(f"將處理 {len(countries_to_process)} 個國家/地區")
    
    print(f"每個國家將爬取所有平台分類的數據")
    print()
    
    start_time = time.time()
    
    # 初始化瀏覽器
    print("正在初始化瀏覽器...")
    driver = init_browser(headless=True)
    if not driver:
        print("❌ 無法啟動瀏覽器")
        return
    
    all_data = {}
    completed_count = 0
    total_count = len(countries_to_process)
    
    try:
        for country_code in list(countries_to_process.keys()):
            try:
                data = scrape_country_data(driver, country_code)
                if data:
                    all_data[country_code] = data
                    
                    # 立即保存單個國家的數據
                    filepath = save_data_to_json(data)
                    print(f"  💾 已保存: {filepath}")
                    
                    completed_count += 1
                    elapsed = time.time() - start_time
                    avg_time = elapsed / completed_count
                    remaining = (total_count - completed_count) * avg_time
                    
                    print(f"\n進度: {completed_count}/{total_count} ({completed_count*100//total_count}%)")
                    print(f"已用時: {elapsed/60:.1f} 分鐘")
                    print(f"預計剩餘: {remaining/60:.1f} 分鐘")
                    print()
                    
            except Exception as e:
                print(f"❌ 處理 {country_code} 時發生錯誤: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 保存匯總文件
        summary_file = os.path.join('statcounter_data', 'summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 所有數據匯總已保存: {summary_file}")
        
        elapsed_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"✅ 完成！總耗時: {elapsed_time/60:.1f} 分鐘")
        print(f"{'='*60}")
        
    finally:
        driver.quit()
        print("\n瀏覽器已關閉")

if __name__ == '__main__':
    main()

