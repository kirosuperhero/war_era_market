import streamlit as st
import sys
import traceback

try:
    # باقي الكود الحالي (بما في ذلك set_page_config وكل شيء)
    # ...
except Exception as e:
    with open("error.log", "w") as f:
        f.write(traceback.format_exc())
    raise
import pandas as pd
import plotly.express as px
import requests
import time
import json
import os
import math
from datetime import datetime
import numpy as np


st.set_page_config(
    page_title="War Era - Market Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CSS ==========
st.markdown("""
<style>
    div[data-testid="stMetricValue"] { color: #00ff88 !important; }
    .stDataFrame th { background-color: #2d2d3d !important; color: #00ff88 !important; }
    .stTabs [data-baseweb="tab"] { background-color: #2d2d3d !important; color: white !important; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #ff4b4b 0%, #ff6b6b 100%) !important; }
    .stButton button { background: linear-gradient(135deg, #ff4b4b 0%, #ff6b6b 100%) !important; color: white !important; }
    .deal-card { border-right: 4px solid #00ff00; border-radius: 10px; padding: 15px; margin: 10px 0; background: #1e1e2e; }
    .best-flip { border-right: 4px solid #ff4b4b; border-radius: 10px; padding: 15px; margin: 10px 0; background: #1e1e2e; }
</style>
""", unsafe_allow_html=True)

# ========== ملفات البيانات ==========
SENT_ALERTS_FILE   = "data/sent_alerts.json"
SALES_CACHE_FILE   = "data/sales_cache.json"
PRICE_HISTORY_FILE = "data/price_history.json"
ALERTS_HISTORY_FILE = "data/alerts_history.json"
LAST_SYNC_FILE     = "data/last_sync.json"

# ========== دوال تحميل / حفظ البيانات ==========
def _load_json(path, default):
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except:
        return default

def _save_json(path, data):
    try:
        os.makedirs("data", exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(convert_numpy_to_python(data), f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def load_sent_alerts():     return _load_json(SENT_ALERTS_FILE, [])
def save_sent_alerts(d):    return _save_json(SENT_ALERTS_FILE, d)
def load_sales_cache():     return _load_json(SALES_CACHE_FILE, {})
def save_sales_cache(d):    return _save_json(SALES_CACHE_FILE, d)
def load_price_history():   return _load_json(PRICE_HISTORY_FILE, {})
def save_price_history(d):  return _save_json(PRICE_HISTORY_FILE, d)
def load_alerts_history():
    data = _load_json(ALERTS_HISTORY_FILE, {"alerts_sent": []})
    if 'alerts_sent' not in data:
        data['alerts_sent'] = []
    return data
def save_alerts_history(d): return _save_json(ALERTS_HISTORY_FILE, d)

def convert_numpy_to_python(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(v) for v in obj]
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj)
    return obj

# ========== الأسرار والتوكنز ==========
def get_secret(key, default):
    try:
        return st.secrets[key]
    except:
        return default

YOUR_JWT           = get_secret("YOUR_JWT", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7Il9pZCI6IjY5Y2VlY2Y1MTk3Zjg0NWZjOWZlZGU1YyJ9LCJpYXQiOjE3NzUxNjg3NTcsImV4cCI6MTc3Nzc2MDc1N30.nIKi8ohQAYsAVXQL9_rlRUr93TDg-G-DVOCQOrRdOtY")
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN", "8261610629:AAFs-el5LK236x1xkDuUM8k-6NOi81X4FU8")
TELEGRAM_CHAT_ID   = get_secret("TELEGRAM_CHAT_ID",   "1690550033")

# ========== تيليجرام ==========
def send_telegram_alert(title, message, price=None, profit=None):
    text = f"🔔 *{title}*\n{message}"
    if price:
        text += f"\n💰 السعر بعد الضريبة: ${price:.2f}"
    if profit:
        text += f"\n💎 الربح المتوقع: +${profit:.2f}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# ========== تعريفات الأصناف ==========
ITEM_CATEGORIES = {
    "✈️ طيارات (Jets)": {
        "code": "jet", "type": "jet",
        "min_attack": 221, "max_attack": 300,
        "min_critical": 41, "max_critical": 50
    },
    "🚀 دبابات (Tanks)": {
        "code": "tank", "type": "tank",
        "min_attack": 141, "max_attack": 170,
        "min_critical": 26, "max_critical": 35
    },
    "👑 خوذة Legendary":  {"code": "helmet5", "type": "equipment", "skill": "criticalDamages", "min_value": 91,  "max_value": 110},
    "✨ خوذة Mythic":     {"code": "helmet6", "type": "equipment", "skill": "criticalDamages", "min_value": 121, "max_value": 150},
    "🦺 صدر Legendary":   {"code": "chest5",  "type": "equipment", "skill": "armor",          "min_value": 36,  "max_value": 50},
    "💪 صدر Mythic":      {"code": "chest6",  "type": "equipment", "skill": "armor",          "min_value": 56,  "max_value": 70},
    "🧤 قفاز Legendary":  {"code": "gloves5", "type": "equipment", "skill": "precision",      "min_value": 31,  "max_value": 40},
    "⚡ قفاز Mythic":     {"code": "gloves6", "type": "equipment", "skill": "precision",      "min_value": 51,  "max_value": 60},
    "👖 بنطلون Legendary":{"code": "pants5",  "type": "equipment", "skill": "armor",          "min_value": 36,  "max_value": 50},
    "👖 بنطلون Mythic":   {"code": "pants6",  "type": "equipment", "skill": "armor",          "min_value": 56,  "max_value": 70},
    "👢 حذاء Legendary":  {"code": "boots5",  "type": "equipment", "skill": "dodge",          "min_value": 31,  "max_value": 40},
    "👢 حذاء Mythic":     {"code": "boots6",  "type": "equipment", "skill": "dodge",          "min_value": 51,  "max_value": 60},
}

# ========== دوال المساعدة ==========
def calculate_quality_score(skills, category_config):
    item_type = category_config["type"]
    if item_type in ["jet", "tank"]:
        attack   = skills.get('attack', 0)
        critical = skills.get('criticalChance', 0)
        a_score = max(0, min(1, (attack   - category_config["min_attack"])   / (category_config["max_attack"]   - category_config["min_attack"])   if attack   >= category_config["min_attack"]   else 0))
        c_score = max(0, min(1, (critical - category_config["min_critical"]) / (category_config["max_critical"] - category_config["min_critical"]) if critical >= category_config["min_critical"] else 0))
        return round(((a_score + c_score) / 2) * 100, 1)
    elif item_type == "equipment":
        val = skills.get(category_config["skill"], 0)
        score = (val - category_config["min_value"]) / (category_config["max_value"] - category_config["min_value"]) if val >= category_config["min_value"] else 0
        return round(max(0, min(1, score)) * 100, 1)
    return 0

def get_main_value(skills, category_config):
    if category_config["type"] in ["jet", "tank"]:
        return skills.get('attack', 0)
    elif category_config["type"] == "equipment":
        return skills.get(category_config["skill"], 0)
    return 0

def get_secondary_value(skills, category_config):
    if category_config["type"] in ["jet", "tank"]:
        return skills.get('criticalChance', 0)
    return 0

def get_main_name(category_config):
    if category_config["type"] in ["jet", "tank"]:
        return "الهجوم"
    names = {"dodge": "المراوغة", "armor": "الدفاع", "precision": "الدقة", "criticalDamages": "الضرر الحاسم"}
    return names.get(category_config.get("skill", ""), "القيمة")

def get_secondary_name(category_config):
    return "الكريتيكال" if category_config["type"] in ["jet", "tank"] else ""

def get_range_text(category_config):
    if category_config["type"] in ["jet", "tank"]:
        return f"({category_config['min_attack']}-{category_config['max_attack']} هجوم | {category_config['min_critical']}-{category_config['max_critical']}% كريتيكال)"
    elif category_config["type"] == "equipment":
        return f"({category_config['min_value']}-{category_config['max_value']})"
    return ""

def add_tax(price):
    return price * 1.01

def time_ago(created_at_str):
    try:
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        diff = datetime.now().astimezone() - created_at
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1:   return f"{int(diff.total_seconds())} ثانية"
        elif minutes < 60: return f"{minutes} دقيقة"
        else:              return f"{minutes // 60} ساعة"
    except:
        return "غير معروف"

def categorize_item(item, category_config):
    code = category_config['code']
    if category_config['type'] in ["jet", "tank"]:
        a = round(item['main_value'] / 5) * 5
        c = round(item['secondary_value'] / 2) * 2
        return f"{code}_A{a}_C{c}"
    else:
        v = round(item['main_value'] / 5) * 5
        return f"{code}_V{v}"

# ========== متوسط سعر البيع الفعلي ==========
def get_average_sale_price(item_code, main_value, days_back=3):
    cache = load_sales_cache()
    if item_code not in cache:
        return None
    now = datetime.now().astimezone()
    valid_prices = []
    for sale in cache[item_code]:
        try:
            sale_time = datetime.fromisoformat(sale['time'].replace('Z', '+00:00'))
            if (now - sale_time).total_seconds() / 3600 <= days_back * 24:
                if abs(sale.get('main_value', 0) - main_value) <= 10 and sale.get('price', 0) > 0:
                    valid_prices.append(sale['price'])
        except:
            continue
    return sum(valid_prices) / len(valid_prices) if valid_prices else None

# ========== سرعة البيع لعنصر محدد (Change 2) ==========
def get_item_sell_velocity(item_code, main_value, secondary_value, category_config):
    """
    احسب متوسط الوقت بين مبيعات عناصر بنفس المواصفات.
    يجمّع بنفس منطق categorize_item:
      - Jets/Tanks: attack (rounded/5) + criticalChance (rounded/2)
      - Equipment: main_value (rounded/5)
    يرجع (avg_hours, count) أو (None, count).
    """
    cache = load_sales_cache()
    if item_code not in cache or len(cache[item_code]) < 2:
        return None, 0

    # حساب المجموعة المستهدفة
    if category_config['type'] in ["jet", "tank"]:
        target_a = round(main_value      / 5) * 5
        target_c = round(secondary_value / 2) * 2
    else:
        target_v = round(main_value / 5) * 5

    matching = []
    for sale in cache[item_code]:
        try:
            s_main = sale.get('main_value', 0)
            if category_config['type'] in ["jet", "tank"]:
                s_a = round(s_main / 5) * 5
                s_c = round(sale.get('secondary_value', 0) / 2) * 2
                if s_a == target_a and s_c == target_c:
                    matching.append(sale)
            else:
                s_v = round(s_main / 5) * 5
                if s_v == target_v:
                    matching.append(sale)
        except:
            continue

    count = len(matching)
    if count < 2:
        return None, count

    try:
        times  = sorted([datetime.fromisoformat(s['time'].replace('Z', '+00:00')) for s in matching])
        gaps   = [(times[i+1] - times[i]).total_seconds() / 3600 for i in range(len(times) - 1)]
        avg_hr = sum(gaps) / len(gaps)
        return avg_hr, count
    except:
        return None, count

def format_velocity(avg_hours):
    """تحويل الساعات إلى نص مقروء: X ساعة Y دقيقة"""
    if avg_hours is None:
        return None
    total_minutes = int(avg_hours * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    if h == 0:
        return f"~{m} دقيقة"
    elif m == 0:
        return f"~{h} ساعة"
    else:
        return f"~{h} ساعة {m} دقيقة"

# ========== سرعة البيع العامة للهيدر ==========
def get_category_sell_velocity(item_code):
    cache = load_sales_cache()
    if item_code not in cache or len(cache[item_code]) < 2:
        return None
    try:
        times = sorted([datetime.fromisoformat(s['time'].replace('Z', '+00:00')) for s in cache[item_code]])
        gaps  = [(times[i+1] - times[i]).total_seconds() / 3600 for i in range(len(times) - 1)]
        return round(sum(gaps) / len(gaps), 1)
    except:
        return None

# ========== نسبة السعر المئوية ==========
def get_price_percentile(price, all_prices):
    if len(all_prices) <= 1:
        return None
    cheaper_than = sum(1 for p in all_prices if p > price)
    return round((cheaper_than / len(all_prices)) * 100, 0)

# ========== Deal Score — مبني على بيانات السوق الفعلية ==========
# معايرة من تحليل 712 عملية بيع فعلية:
#   متوسط الهامش: 5.8% | p50: 4.2% | p90 (أفضل 10%): 12.7%
#   الانحراف المطلق: p50=$7.5 | p90=$30.5

def get_bucket_full_stats(item_code, main_value, secondary_value, category_config, days_back=14, hours_back=None):
    """
    إحصائيات شاملة للمجموعة من sales_cache.
    يرجع: dict فيه count, min, max, avg, p25, p50, p75 + قائمة الأسعار الخام + window_hours + newest_age_hours.
    None إذا لم توجد بيانات.
    إذا حُدِّد hours_back فهو يلغي days_back.
    """
    cache = load_sales_cache()
    if item_code not in cache:
        return None
    is_combat = category_config['type'] in ['jet', 'tank']
    if is_combat:
        target_a = round(main_value      / 5) * 5
        target_c = round(secondary_value / 2) * 2
    else:
        target_v = round(main_value / 5) * 5

    cutoff_hours = hours_back if hours_back is not None else days_back * 24
    now = datetime.now().astimezone()
    prices = []
    times  = []
    for sale in cache[item_code]:
        try:
            if not sale.get('price') or sale['price'] <= 0:
                continue
            t = datetime.fromisoformat(sale['time'].replace('Z', '+00:00'))
            age_hr = (now - t).total_seconds() / 3600
            if age_hr > cutoff_hours:
                continue
            s_main = sale.get('main_value', 0)
            matched = False
            if is_combat:
                if round(s_main/5)*5 == target_a and round(sale.get('secondary_value',0)/2)*2 == target_c:
                    matched = True
            else:
                if round(s_main/5)*5 == target_v:
                    matched = True
            if matched:
                prices.append(sale['price'])
                times.append(age_hr)
        except:
            continue

    if not prices:
        return None
    prices_sorted = sorted(prices)
    n = len(prices_sorted)
    return {
        'count':  n,
        'min':    prices_sorted[0],
        'max':    prices_sorted[-1],
        'avg':    sum(prices_sorted) / n,
        'p25':    prices_sorted[max(0, int(n * 0.25) - 1)],
        'p50':    prices_sorted[n // 2],
        'p75':    prices_sorted[min(n - 1, int(n * 0.75))],
        'prices': prices_sorted,
        'window_hours':    cutoff_hours,
        'newest_age_hours': min(times),
        'oldest_age_hours': max(times),
    }


def get_category_window_stats(item_code, start_hours_ago, end_hours_ago=0):
    """
    إحصائيات على مستوى الصنف كاملاً (كل المواصفات) داخل نافذة زمنية.
    start_hours_ago > end_hours_ago. مثال: (24, 0) = آخر 24 ساعة.
    يرجع: dict فيه count, avg, min, max, prices, times أو None.
    """
    cache = load_sales_cache()
    if item_code not in cache:
        return None
    now = datetime.now().astimezone()
    prices, ages = [], []
    for sale in cache[item_code]:
        try:
            if not sale.get('price') or sale['price'] <= 0:
                continue
            t = datetime.fromisoformat(sale['time'].replace('Z', '+00:00'))
            age_hr = (now - t).total_seconds() / 3600
            if age_hr <= end_hours_ago or age_hr > start_hours_ago:
                continue
            prices.append(sale['price'])
            ages.append(age_hr)
        except:
            continue
    if not prices:
        return None
    n = len(prices)
    avg_gap = (start_hours_ago - end_hours_ago) / n if n > 0 else None
    return {
        'count':   n,
        'avg':     sum(prices) / n,
        'min':     min(prices),
        'max':     max(prices),
        'prices':  prices,
        'ages':    ages,
        'avg_gap_hours': avg_gap,
    }


def get_bucket_stats(item_code, main_value, secondary_value, category_config, days_back=7):
    """
    يحسب متوسط سعر البيع وعدد الصفقات للمجموعة المحددة (نفس منطق categorize_item).
    يتجاهل السجلات بدون سعر (null = عناصر انتهت أو سُحبت، لم تُباع).
    """
    cache = load_sales_cache()
    if item_code not in cache:
        return None, 0

    is_combat = category_config['type'] in ['jet', 'tank']
    if is_combat:
        target_a = round(main_value      / 5) * 5
        target_c = round(secondary_value / 2) * 2
    else:
        target_v = round(main_value / 5) * 5

    now    = datetime.now().astimezone()
    prices = []
    for sale in cache[item_code]:
        try:
            if sale.get('price') is None or sale['price'] <= 0:
                continue
            sale_time = datetime.fromisoformat(sale['time'].replace('Z', '+00:00'))
            if (now - sale_time).total_seconds() / 3600 > days_back * 24:
                continue
            s_main = sale.get('main_value', 0)
            if is_combat:
                s_a = round(s_main / 5) * 5
                s_c = round(sale.get('secondary_value', 0) / 2) * 2
                if s_a == target_a and s_c == target_c:
                    prices.append(sale['price'])
            else:
                s_v = round(s_main / 5) * 5
                if s_v == target_v:
                    prices.append(sale['price'])
        except:
            continue

    if not prices:
        return None, 0
    return sum(prices) / len(prices), len(prices)


def calc_freshness_score(created_at_str):
    """
    تحلل أسي: e^(-0.025 * دقيقة_عمر_الإعلان)
    0 دقيقة → 1.00 | 15 دقيقة → 0.69 | 30 دقيقة → 0.47 | 60 دقيقة → 0.22 | 120 دقيقة → 0.05
    """
    try:
        created_at  = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        minutes_old = (datetime.now().astimezone() - created_at).total_seconds() / 60
        return round(math.exp(-0.025 * max(0, minutes_old)), 4)
    except:
        return 0.0


def calc_velocity_score(avg_hours):
    """
    e^(-0.05 * ساعات_متوسط_البيع)
    0h → 1.0 | 12h → 0.55 | 24h → 0.30 | 48h → 0.09
    إذا لم تتوفر بيانات: نقاط محايدة (تعادل ~22 ساعة)
    """
    if avg_hours is None:
        return 0.33
    return round(math.exp(-0.05 * max(0, avg_hours)), 4)


def calc_scarcity_score(similar_count):
    """
    1 / (1 + عدد_العناصر_المشابهة/5)
    0 عناصر → 1.0 | 5 → 0.50 | 10 → 0.33 | 20 → 0.20
    """
    return round(1.0 / (1.0 + similar_count / 5.0), 4)


def calc_deal_score(margin_pct, freshness, velocity_score, scarcity_score):
    """
    Deal Score (0–100) مُعاير على بيانات السوق الفعلية.
    الأوزان: هامش 30% | حداثة 30% | سرعة بيع 25% | ندرة 15%
    الهامش مُعاير على 10% (متوسط p90 عبر الأصناف؛ تانكس p90=6.3%, جيتس 12.8%).
    """
    margin_score = min(1.0, margin_pct / 10.0)
    raw = (
        margin_score   * 0.30 +
        freshness      * 0.30 +
        velocity_score * 0.25 +
        scarcity_score * 0.15
    )
    return round(raw * 100, 1)


def get_deal_badge(score):
    if score >= 65:
        return "🔥🔥 Prime Snipe", "#ff2244"
    elif score >= 50:
        return "🔥 Hot Deal", "#ff6600"
    elif score >= 35:
        return "👍 Good Flip", "#00cc66"
    else:
        return "✅ Possible Flip", "#888888"


def get_bucket_key_str(main_value, secondary_value, category_config):
    if category_config['type'] in ['jet', 'tank']:
        a = round(main_value      / 5) * 5
        c = round(secondary_value / 2) * 2
        return f"A{a}_C{c}"
    else:
        v = round(main_value / 5) * 5
        return f"V{v}"

# ========== جلب المبيعات لنوع معين ==========
def fetch_transactions(item_code, limit=100):
    API_URL = "https://api4.warera.io/trpc/transaction.getPaginatedTransactions?batch=1"
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"jwt={YOUR_JWT}",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {"0": {"itemCode": item_code, "limit": limit, "direction": "forward"}}
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data[0].get('result', {}).get('data', {}).get('items', [])
    except:
        pass
    return []

# ========== Change 1: مزامنة المبيعات في الخلفية ==========
SYNC_INTERVAL_HOURS = 1

def _get_last_sync_time():
    data = _load_json(LAST_SYNC_FILE, {"last_sync": None})
    return data.get("last_sync")

def _save_last_sync_time():
    _save_json(LAST_SYNC_FILE, {"last_sync": datetime.now().isoformat()})

def run_sales_sync(status_placeholder=None):
    """
    يجلب آخر 100 مبيعة لكل نوع من الأصناف الـ 12 ويضيفها للـ cache.
    يضيف فقط السجلات الجديدة (append, لا overwrite).
    """
    cache = load_sales_cache()
    total_added = 0

    for cat_name, cat_config in ITEM_CATEGORIES.items():
        code = cat_config["code"]
        if status_placeholder:
            status_placeholder.caption(f"🔄 جاري مزامنة: {cat_name}...")

        transactions = fetch_transactions(code, limit=100)
        if not transactions:
            continue

        if code not in cache:
            cache[code] = []

        # بناء مجموعة المعرّفات الموجودة لتجنب التكرار
        existing_ids = {(s.get('time'), s.get('price')) for s in cache[code]}

        for tx in transactions:
            item_info = tx.get('item', {})
            skills    = item_info.get('skills', {})
            tx_time   = tx.get('createdAt')
            tx_price  = tx.get('money')

            if (tx_time, tx_price) in existing_ids:
                continue

            if code in ['jet', 'tank']:
                main_value      = skills.get('attack', 0)
                secondary_value = skills.get('criticalChance', 0)
            else:
                skill_key       = cat_config.get('skill', '')
                main_value      = skills.get(skill_key, 0)
                secondary_value = 0

            cache[code].append({
                'price':          tx_price,
                'time':           tx_time,
                'main_value':     main_value,
                'secondary_value': secondary_value
            })
            existing_ids.add((tx_time, tx_price))
            total_added += 1

        # احتفظ بآخر 500 سجل لكل نوع
        cache[code] = sorted(cache[code], key=lambda x: x.get('time', ''), reverse=True)[:500]

    save_sales_cache(cache)
    _save_last_sync_time()
    return total_added

def maybe_auto_sync():
    """يشغّل المزامنة التلقائية إذا مرّت أكثر من SYNC_INTERVAL_HOURS."""
    last_sync_str = _get_last_sync_time()
    if last_sync_str:
        try:
            last_sync = datetime.fromisoformat(last_sync_str)
            elapsed   = (datetime.now() - last_sync).total_seconds() / 3600
            if elapsed < SYNC_INTERVAL_HOURS:
                return False, elapsed
        except:
            pass
    return True, 0

# ========== جلب عروض السوق ==========
@st.cache_data(ttl=60)
def fetch_single_item(item_code, limit=50, cursor=None):
    API_URL = "https://api4.warera.io/trpc/itemOffer.getItemOffers,transaction.getPaginatedTransactions?batch=1"
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"jwt={YOUR_JWT}",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "0": {"itemCode": item_code, "limit": limit, "direction": "forward"},
        "1": {"itemCode": item_code, "limit": 1, "transactionType": "itemMarket", "direction": "forward"}
    }
    if cursor:
        payload["0"]["cursor"] = cursor
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        if r.status_code == 200:
            data       = r.json()
            items_data = data[0].get('result', {}).get('data', {})
            return items_data.get('items', []), items_data.get('nextCursor')
    except:
        pass
    return [], None

@st.cache_data(ttl=60)
def fetch_all_items(item_code, max_pages=5):
    all_items, cursor = [], None
    for _ in range(max_pages):
        items, cursor = fetch_single_item(item_code, limit=50, cursor=cursor)
        if not items:
            break
        for item in items:
            item_info = item.get('item', {})
            skills    = item_info.get('skills', {})
            user_id   = item.get('user', '')
            all_items.append({
                'id':        item.get('_id'),
                'price':     item.get('price'),
                'user':      user_id[:8] if user_id else 'unknown',
                'skills':    skills,
                'attack':    skills.get('attack', 0),
                'critical':  skills.get('criticalChance', 0),
                'createdAt': item.get('createdAt'),
                'time_ago':  time_ago(item.get('createdAt', ''))
            })
        if not cursor:
            break
        time.sleep(0.2)
    return all_items

# ========== Change 1: تشغيل المزامنة التلقائية ==========
should_sync, elapsed_h = maybe_auto_sync()
if should_sync:
    if 'sync_running' not in st.session_state:
        st.session_state.sync_running = True
        with st.spinner("⚙️ جاري المزامنة التلقائية لبيانات المبيعات..."):
            added = run_sales_sync()
        st.session_state.sync_running = False
        if added > 0:
            st.toast(f"✅ تمت المزامنة التلقائية — {added} سجل جديد", icon="🔄")

# ========== الشريط الجانبي ==========
with st.sidebar:
    st.header("⚙️ إعدادات التحليل")

    auto_refresh = st.checkbox("🔄 تحديث تلقائي كل دقيقة", value=False)
    if auto_refresh:
        st_autorefresh = __import__('streamlit_autorefresh').st_autorefresh
        st_autorefresh(interval=60000, limit=100, key="auto_refresh")

    item_category = st.selectbox("📦 اختر نوع المعدات:", list(ITEM_CATEGORIES.keys()))
    max_pages     = st.slider("عدد صفحات الجلب", 1, 10, 5, help="كل صفحة = 50 عنصر")
    min_quality   = st.slider("الحد الأدنى للجودة (%)", 0, 100, 0)
    max_price     = st.number_input("الحد الأقصى للسعر", 0, 10000, 5000, step=100)

    st.divider()
    st.header("⏰ فلتر الوقت")
    time_filter = st.selectbox(
        "عرض العروض من آخر:",
        ["الكل", "آخر ساعة", "آخر 6 ساعات", "آخر 12 ساعة", "آخر 24 ساعة", "آخر 3 أيام", "آخر أسبوع"]
    )
    TIME_MAP = {
        "الكل": 0, "آخر ساعة": 1, "آخر 6 ساعات": 6,
        "آخر 12 ساعة": 12, "آخر 24 ساعة": 24,
        "آخر 3 أيام": 72, "آخر أسبوع": 168
    }
    hours_limit = TIME_MAP[time_filter]

    st.divider()
    sort_by = st.selectbox("ترتيب حسب", [
        "القيمة مقابل السعر", "الجودة",
        "السعر (أقل سعر أولاً)", "السعر (أعلى سعر أولاً)", "الأحدث"
    ])

    if st.button("🔄 تحديث البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # حالة المزامنة التلقائية
    last_sync_str = _get_last_sync_time()
    if last_sync_str:
        try:
            last_sync = datetime.fromisoformat(last_sync_str)
            elapsed   = (datetime.now() - last_sync).total_seconds() / 3600
            next_in   = max(0, SYNC_INTERVAL_HOURS - elapsed)
            st.caption(f"🔄 **المزامنة التلقائية**\nآخر مزامنة: منذ {elapsed*60:.0f} دقيقة\nالتالية خلال: {next_in*60:.0f} دقيقة")
        except:
            st.caption("🔄 المزامنة التلقائية: فعّالة")
    else:
        st.caption("🔄 المزامنة التلقائية: ستبدأ قريباً")

    if st.button("🔄 مزامنة يدوية الآن", use_container_width=True):
        with st.spinner("جاري المزامنة..."):
            added = run_sales_sync()
        st.success(f"✅ تمت — {added} سجل جديد")

    st.divider()
    st.caption(f"📏 **رينج القيم:** {get_range_text(ITEM_CATEGORIES[item_category])}")

# ========== جلب بيانات السوق ==========
category_config = ITEM_CATEGORIES[item_category]
item_code       = category_config["code"]

with st.spinner(f"جاري تحليل {item_category}..."):
    raw_items = fetch_all_items(item_code, max_pages=max_pages)

if not raw_items:
    st.error("❌ لا توجد عروض حالياً")
    st.stop()

# ========== معالجة البيانات ==========
main_name      = get_main_name(category_config)
secondary_name = get_secondary_name(category_config)

all_items = []
for item in raw_items:
    quality         = calculate_quality_score(item['skills'], category_config)
    main_value      = get_main_value(item['skills'], category_config)
    secondary_value = get_secondary_value(item['skills'], category_config)
    value_for_money = (quality / item['price']) * 1000 if item['price'] > 0 else 0
    all_items.append({
        'id':              item['id'],
        'price':           item['price'],
        'user':            item['user'],
        'main_value':      main_value,
        'secondary_value': secondary_value,
        'main_name':       main_name,
        'secondary_name':  secondary_name,
        'quality_score':   quality,
        'value_for_money': value_for_money,
        'createdAt':       item['createdAt'],
        'time_ago':        item['time_ago'],
        'attack':          item['attack'],
        'critical':        item['critical']
    })

df = pd.DataFrame(all_items)
df_filtered = df[(df['quality_score'] >= min_quality) & (df['price'] <= max_price)].copy()

if hours_limit > 0:
    now = datetime.now().astimezone()
    df_filtered = df_filtered[
        df_filtered['createdAt'].apply(
            lambda x: (now - datetime.fromisoformat(x.replace('Z', '+00:00'))).total_seconds() / 3600 <= hours_limit
        )
    ]

# متوسط البيع الفعلي
df_filtered['actual_avg_price'] = df_filtered.apply(
    lambda row: get_average_sale_price(item_code, row['main_value'], 3), axis=1
)
df_filtered['actual_profit'] = df_filtered.apply(
    lambda row: row['actual_avg_price'] - row['price'] if row['actual_avg_price'] else 0, axis=1
)
df_filtered['actual_profit_pct'] = df_filtered.apply(
    lambda row: (row['actual_profit'] / row['price'] * 100) if row['price'] > 0 and row['actual_profit'] > 0 else 0, axis=1
)
df_filtered['enhanced_value'] = df_filtered.apply(
    lambda row: row['value_for_money'] * (1 + max(0, row['actual_profit'] / row['price']))
    if row['actual_profit'] > 0 else row['value_for_money'], axis=1
)

all_prices_list = df_filtered['price'].tolist()
df_filtered['price_percentile'] = df_filtered['price'].apply(
    lambda p: get_price_percentile(p, all_prices_list)
)

# ========== حساب Deal Score ==========
# خطوة 1: مفتاح المجموعة (نفس منطق categorize_item)
df_filtered['bucket_key'] = df_filtered.apply(
    lambda r: get_bucket_key_str(r['main_value'], r['secondary_value'], category_config), axis=1
)

# خطوة 2: عدد العناصر في نفس المجموعة (ندرة)
bucket_counts = df_filtered['bucket_key'].value_counts().to_dict()
df_filtered['bucket_similar_count'] = df_filtered['bucket_key'].map(bucket_counts)

# خطوة 3: متوسط سعر البيع الفعلي للمجموعة (من التاريخ، ليس السوق الحالي)
def _bucket_stats(row):
    return get_bucket_stats(item_code, row['main_value'], row['secondary_value'], category_config, days_back=7)

bucket_stats_series = df_filtered.apply(_bucket_stats, axis=1)
df_filtered['bucket_avg_price'] = bucket_stats_series.apply(lambda x: x[0])
df_filtered['bucket_sale_count'] = bucket_stats_series.apply(lambda x: x[1])

# خطوة 4: هامش الربح من المجموعة (أدق من actual_avg_price)
df_filtered['bucket_profit']     = df_filtered.apply(
    lambda r: (r['bucket_avg_price'] - r['price']) if r['bucket_avg_price'] else None, axis=1
)
df_filtered['bucket_margin_pct'] = df_filtered.apply(
    lambda r: (r['bucket_profit'] / r['price'] * 100)
    if (r['bucket_profit'] is not None and r['price'] > 0) else None, axis=1
)

# خطوة 5: مكونات Deal Score
df_filtered['freshness_score']  = df_filtered['createdAt'].apply(calc_freshness_score)

# سرعة البيع لكل عنصر (محسوبة مسبقاً)
def _vel(row):
    avg_hr, _ = get_item_sell_velocity(item_code, row['main_value'], row['secondary_value'], category_config)
    return calc_velocity_score(avg_hr)

df_filtered['velocity_score']   = df_filtered.apply(_vel, axis=1)
df_filtered['scarcity_score']   = df_filtered['bucket_similar_count'].apply(calc_scarcity_score)

# خطوة 6: Deal Score النهائي
df_filtered['deal_score'] = df_filtered.apply(
    lambda r: calc_deal_score(
        r['bucket_margin_pct'] if r['bucket_margin_pct'] is not None else 0,
        r['freshness_score'],
        r['velocity_score'],
        r['scarcity_score']
    ), axis=1
)

# البوابات الصارمة (Hard Gates)
# السعر المطلق: $5 للعناصر الرخيصة، $10 للعناصر الغالية
def _min_abs_profit(price):
    return 10.0 if price > 250 else 5.0

df_filtered['min_abs_profit']    = df_filtered['price'].apply(_min_abs_profit)
df_filtered['passes_hard_gates'] = (
    df_filtered['bucket_margin_pct'].notna() &
    (df_filtered['bucket_margin_pct']  >= 3.0) &
    (df_filtered['bucket_profit']      >= df_filtered['min_abs_profit']) &
    (df_filtered['bucket_sale_count']  >= 3)
)
# مستوى الثقة: ≥5 موثّق، 3-4 محدود
df_filtered['confidence_tier'] = df_filtered['bucket_sale_count'].apply(
    lambda n: 'verified' if (n is not None and n >= 5) else ('tentative' if (n is not None and n >= 3) else 'low')
)

# الترتيب
if sort_by == "القيمة مقابل السعر":
    df_sorted = df_filtered.sort_values('value_for_money', ascending=False)
elif sort_by == "الجودة":
    df_sorted = df_filtered.sort_values('quality_score', ascending=False)
elif sort_by == "السعر (أقل سعر أولاً)":
    df_sorted = df_filtered.sort_values('price', ascending=True)
elif sort_by == "السعر (أعلى سعر أولاً)":
    df_sorted = df_filtered.sort_values('price', ascending=False)
else:
    df_sorted = df_filtered.sort_values('createdAt', ascending=False)

# ========== هيدر الإحصائيات ==========
st.title("🎯 War Era - Market Analyzer")
st.markdown(f"تحليل متقدم لسوق **الطيارات، الدبابات، والمعدات النادرة** — {item_category}")

if len(df_filtered) > 0:
    cat_velocity = get_category_sell_velocity(item_code)

    h1, h2, h3, h4, h5 = st.columns(5)
    with h1:
        st.metric("📦 إجمالي العناصر", len(df_filtered))
    with h2:
        st.metric("💰 أقل سعر (بعد الضريبة)", f"${add_tax(df_filtered['price'].min()):,.2f}")
    with h3:
        st.metric("🏅 أعلى جودة", f"{df_filtered['quality_score'].max():.1f}%")
    with h4:
        st.metric("📊 متوسط السعر", f"${add_tax(df_filtered['price'].mean()):,.2f}")
    with h5:
        if cat_velocity is not None:
            st.metric("⚡ سرعة البيع (عام)", f"~{cat_velocity:.1f} ساعة", help="متوسط الوقت بين مبيعات هذا النوع عموماً")
        else:
            st.metric("⚡ سرعة البيع", "لا يوجد بيانات", help="تحتاج مبيعات مسجلة أولاً — تتم المزامنة تلقائياً كل ساعة")
    st.divider()

# ========== التبويبات ==========
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📋 الجدول",
    "🔥 أفضل الصفقات",
    "🔍 تحليل العنصر",
    "💰 صائد الأرباح",
    "🎯 صيد القناصة",
    "🧮 حاسبة البيع",
    "📈 اتجاهات السوق"
])

# ------------------------------------------------------------------
# TAB 1: الجدول
# ------------------------------------------------------------------
with tab1:
    st.subheader(f"📋 عرض {len(df_sorted)} عنصر")
    st.caption(f"📏 {get_range_text(category_config)}")

    if category_config["type"] in ["jet", "tank"]:
        display_df = df_sorted[['price', 'main_value', 'secondary_value', 'quality_score',
                                 'price_percentile', 'value_for_money', 'user', 'time_ago']].copy()
        display_df['price'] = display_df['price'].apply(add_tax)
        display_df.columns = ['السعر بعد الضريبة', main_name, f'{secondary_name}%',
                               'الجودة%', 'أرخص من%', 'القيمة/السعر', 'البائع', 'منذ']
    else:
        display_df = df_sorted[['price', 'main_value', 'quality_score',
                                 'price_percentile', 'value_for_money', 'user', 'time_ago']].copy()
        display_df['price'] = display_df['price'].apply(add_tax)
        display_df.columns = ['السعر بعد الضريبة', main_name,
                               'الجودة%', 'أرخص من%', 'القيمة/السعر', 'البائع', 'منذ']

    st.data_editor(
        display_df,
        column_config={
            "السعر بعد الضريبة": st.column_config.NumberColumn("💰 السعر بعد الضريبة", format="$ %.2f"),
            "الجودة%": st.column_config.ProgressColumn("الجودة%", format="%.1f %%", min_value=0, max_value=100),
            "أرخص من%": st.column_config.ProgressColumn("أرخص من%", format="%.0f %%", min_value=0, max_value=100,
                help="هذا السعر أقل من X% من العروض الحالية — كلما ارتفعت النسبة كلما كانت الصفقة أفضل"),
        },
        use_container_width=True, height=500, hide_index=True, disabled=True
    )

    # تنبيهات تيليجرام للعناصر الجديدة
    recent_in_table = df_sorted[df_sorted['createdAt'].apply(
        lambda x: (datetime.now().astimezone() - datetime.fromisoformat(x.replace('Z', '+00:00'))).total_seconds() / 3600 <= 1
    )]
    if len(recent_in_table) > 0:
        sent_alerts = load_sent_alerts()
        for _, item_row in recent_in_table.iterrows():
            alert_id = f"table_{item_category}_{item_row['main_value']}_{item_row['secondary_value']}_{item_row['price']}"
            if alert_id not in sent_alerts:
                sent_alerts.append(alert_id)
                send_telegram_alert(
                    title="🆕 عنصر جديد في السوق!",
                    message=f"{item_category}\n🔍 {item_row['main_name']}: {item_row['main_value']} | {item_row['secondary_name']}: {item_row['secondary_value']}",
                    price=add_tax(item_row['price']),
                    profit=None
                )
        save_sent_alerts(sent_alerts)

# ------------------------------------------------------------------
# TAB 2: أفضل الصفقات — Deal Score المعاير على بيانات السوق الفعلية
# ------------------------------------------------------------------
with tab2:
    st.subheader("🔥 أفضل الصفقات — Deal Score")
    st.caption(
        "مُعاير على بيانات السوق الفعلية · "
        "الأوزان: هامش 30% · حداثة 30% · سرعة بيع 25% · ندرة 15% · "
        "البوابات: هامش ≥3% · ربح مطلق ≥$5 (أو $10 للعناصر +$250) · 3+ مبيعات مسجّلة"
    )

    # العناصر التي تجتاز البوابات الصارمة
    deals_df = df_filtered[df_filtered['passes_hard_gates']].copy()
    deals_df = deals_df.sort_values('deal_score', ascending=False)

    if len(deals_df) > 0:
        st.success(f"✅ **{len(deals_df)}** عنصر اجتاز البوابات الصارمة — مرتّبة حسب Deal Score")

        for rank, (_, row) in enumerate(deals_df.head(12).iterrows(), start=1):
            badge_text, badge_color = get_deal_badge(row['deal_score'])
            margin_pct  = row['bucket_margin_pct']
            abs_profit  = row['bucket_profit']
            bucket_avg  = row['bucket_avg_price']
            sale_count  = row['bucket_sale_count']

            # مكونات النقاط (للعرض)
            m_contrib = min(1.0, margin_pct / 10.0) * 0.30 * 100
            f_contrib = row['freshness_score']   * 0.30 * 100
            v_contrib = row['velocity_score']    * 0.25 * 100
            s_contrib = row['scarcity_score']    * 0.15 * 100

            # شارة الثقة
            conf = row['confidence_tier']
            if conf == 'verified':
                conf_badge = "✓ موثّق"
                conf_color = "#00cc66"
            else:
                conf_badge = "📊 ثقة محدودة"
                conf_color = "#ffaa00"

            with st.container(border=True):
                top_left, top_right = st.columns([4, 1])
                with top_left:
                    st.markdown(
                        f"**{rank}. {badge_text}** — "
                        f"<span style='color:{badge_color};font-size:1.3em;font-weight:bold'>"
                        f"Deal Score: {row['deal_score']:.0f}/100</span> "
                        f"<span style='color:{conf_color};font-size:0.85em;margin-right:10px'>{conf_badge}</span>",
                        unsafe_allow_html=True
                    )
                    if row['secondary_name']:
                        st.write(f"🔍 {row['main_name']}: **{row['main_value']}** | {row['secondary_name']}: **{row['secondary_value']}%** | جودة: {row['quality_score']}%")
                    else:
                        st.write(f"🔍 {row['main_name']}: **{row['main_value']}** | جودة: {row['quality_score']}%")
                with top_right:
                    st.caption(f"منذ {row['time_ago']}")
                    st.caption(f"👤 {row['user']}")

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("💰 سعر الشراء", f"${add_tax(row['price']):.2f}")
                    st.caption(f"متوسط البيع الفعلي: ${bucket_avg:.2f}")
                with c2:
                    st.metric("💎 الربح المتوقع", f"+${abs_profit:.2f}")
                    st.caption(f"هامش: {margin_pct:.1f}%")
                with c3:
                    st.metric("📦 عروض مشابهة", int(row['bucket_similar_count']))
                    st.caption(f"{int(sale_count)} صفقة مرجعية (7 أيام)")
                with c4:
                    if row['price_percentile'] is not None:
                        st.metric("أرخص من", f"{int(row['price_percentile'])}%")

                # شريط تفصيل النقاط
                with st.expander("📊 تفصيل النقاط"):
                    bar_c1, bar_c2, bar_c3, bar_c4 = st.columns(4)
                    with bar_c1:
                        st.metric("هامش (30%)", f"{m_contrib:.1f} نقطة",
                                  help=f"هامش {margin_pct:.1f}% من أصل 13% حد المقارنة")
                    with bar_c2:
                        age_min = (1.0 - row['freshness_score']) / 0.025 if row['freshness_score'] < 1.0 else 0
                        freshness_pct = row['freshness_score'] * 100
                        st.metric("حداثة (30%)", f"{f_contrib:.1f} نقطة",
                                  help=f"عمر العرض ~{age_min:.0f} دقيقة · حداثة {freshness_pct:.0f}%")
                    with bar_c3:
                        vel_pct = row['velocity_score'] * 100
                        st.metric("سرعة بيع (25%)", f"{v_contrib:.1f} نقطة",
                                  help=f"درجة سرعة البيع {vel_pct:.0f}%")
                    with bar_c4:
                        scar_pct = row['scarcity_score'] * 100
                        st.metric("ندرة (15%)", f"{s_contrib:.1f} نقطة",
                                  help=f"{int(row['bucket_similar_count'])} عنصر مشابه في السوق")
    else:
        # لا توجد عناصر تجتاز البوابات — اشرح السبب وأظهر أفضل ما هو متاح
        st.warning("⚠️ لا توجد عناصر تجتاز البوابات الصارمة حالياً.")

        # تشخيص: كم عنصر يملك بيانات مبيعات، كم يملك هامش ≥3%
        has_bucket = df_filtered['bucket_avg_price'].notna().sum()
        has_margin = (df_filtered['bucket_margin_pct'].fillna(0) >= 3).sum()
        has_count  = (df_filtered['bucket_sale_count'] >= 3).sum()

        d1, d2, d3 = st.columns(3)
        with d1: st.metric("لديها بيانات مبيعات", f"{has_bucket}/{len(df_filtered)}")
        with d2: st.metric("هامش ≥3%", f"{has_margin}/{len(df_filtered)}")
        with d3: st.metric("3+ مبيعات مرجعية", f"{has_count}/{len(df_filtered)}")

        st.caption(
            "أسباب محتملة: بيانات المبيعات قليلة للمجموعة المحددة — "
            "المزامنة التلقائية تُضيف بيانات كل ساعة — "
            "أو جميع العروض الحالية مسعّرة فوق المتوسط التاريخي."
        )

        # Fallback: أفضل Deal Score بدون بوابات صارمة
        st.markdown("---")
        st.subheader("📊 أفضل نقاط متاحة (بدون فلتر البوابات)")
        best_available = df_filtered.nlargest(8, 'deal_score')
        for rank, (_, row) in enumerate(best_available.iterrows(), start=1):
            badge_text, _ = get_deal_badge(row['deal_score'])
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{rank}. Deal Score: {row['deal_score']:.0f}** — منذ {row['time_ago']}")
                    if row['secondary_name']:
                        st.write(f"   {row['main_name']}: {row['main_value']} | {row['secondary_name']}: {row['secondary_value']}%")
                    else:
                        st.write(f"   {row['main_name']}: {row['main_value']}")
                    if row['bucket_avg_price']:
                        st.caption(f"متوسط البيع: ${row['bucket_avg_price']:.2f} | هامش: {row['bucket_margin_pct']:.1f}%")
                    else:
                        st.caption("لا توجد بيانات مبيعات لهذه المجموعة بعد")
                with col2:
                    st.metric("💰 السعر", f"${add_tax(row['price']):.2f}")
                with col3:
                    st.metric("الجودة", f"{row['quality_score']}%")
                st.caption(f"👤 {row['user']}")

# ------------------------------------------------------------------
# TAB 3: تحليل العنصر — مع سرعة البيع الخاصة (Change 2)
# ------------------------------------------------------------------
with tab3:
    st.subheader("🔍 تحليل العنصر — التاريخي والسوقي")
    st.markdown("اختر عنصراً لتحليل تاريخ أسعاره، مقارنته بالسوق، وسرعة بيعه")

    temp_df = df_sorted.head(50).copy()
    temp_df['display'] = temp_df.apply(
        lambda x: f"💰 ${add_tax(x['price']):.2f} | {x['main_name']}: {x['main_value']} | جودة {x['quality_score']}% | 👤 {x['user']}",
        axis=1
    )

    selected_display = st.selectbox("اختر عنصر للتحليل:", options=temp_df['display'].tolist())

    if selected_display:
        selected      = temp_df[temp_df['display'] == selected_display].iloc[0]
        current_price = selected['price']

        # --- تحديث سجل الأسعار ---
        price_history = load_price_history()
        item_key      = categorize_item(selected, category_config)
        if item_key not in price_history:
            price_history[item_key] = []
        is_dup = any(
            r.get('user') == selected['user'] and r['price'] == current_price
            for r in price_history[item_key][-5:]
        )
        if not is_dup:
            price_history[item_key].append({
                'price':           current_price,
                'time':            datetime.now().isoformat(),
                'user':            selected['user'],
                'main_value':      selected['main_value'],
                'secondary_value': selected['secondary_value']
            })
            price_history[item_key] = price_history[item_key][-50:]
            save_price_history(price_history)

        history        = price_history[item_key]
        prices         = [h['price'] for h in history]
        min_price_hist = min(prices)
        max_price_hist = max(prices)
        avg_price_hist = sum(prices) / len(prices)

        # --- عناصر مشابهة ---
        similar_items = df_filtered[
            (df_filtered['main_value'].between(selected['main_value'] - 10, selected['main_value'] + 10)) &
            (df_filtered['quality_score'].between(selected['quality_score'] - 10, selected['quality_score'] + 10))
        ].copy()
        market_avg    = similar_items['price'].mean() if len(similar_items) > 1 else None
        market_min    = similar_items['price'].min()  if len(similar_items) > 1 else None
        market_max    = similar_items['price'].max()  if len(similar_items) > 1 else None
        similar_count = len(similar_items)

        actual_avg_price = get_average_sale_price(item_code, selected['main_value'], 3)

        # --- Change 2: سرعة البيع الخاصة بهذا العنصر ---
        item_velocity_hr, velocity_count = get_item_sell_velocity(
            item_code, selected['main_value'], selected['secondary_value'], category_config
        )
        velocity_text = format_velocity(item_velocity_hr)

        # --- شريط سرعة البيع ---
        if velocity_text:
            st.info(
                f"🕐 **سرعة البيع لهذا النوع:** عناصر مشابهة تُباع كل **{velocity_text}** "
                f"(بناءً على {velocity_count} صفقة مسجّلة)"
            )
        else:
            if velocity_count > 0:
                st.caption(f"🕐 سرعة البيع: سجلنا {velocity_count} صفقة فقط — نحتاج 2+ لحساب الوقت")
            else:
                st.caption("🕐 سرعة البيع: لا توجد مبيعات مسجّلة لهذا النوع بعد — تتم المزامنة تلقائياً كل ساعة")

        # --- إحصائيات السعر ---
        st.markdown("#### 📊 إحصائيات السعر")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("💰 السعر الحالي", f"${add_tax(current_price):.2f}")
        with c2:
            delta = ((current_price - min_price_hist) / min_price_hist * 100) if current_price > min_price_hist else 0
            st.metric("📉 أقل سعر (تاريخي)", f"${add_tax(min_price_hist):.2f}",
                      delta=f"-{delta:.1f}%" if delta > 0 else "أقل سعر!")
        with c3:
            st.metric("📈 متوسط تاريخي", f"${add_tax(avg_price_hist):.0f}")
        with c4:
            st.metric("🏪 متوسط السوق الحالي", f"${add_tax(market_avg):.2f}" if market_avg else "—")
        with c5:
            if actual_avg_price:
                st.metric("✅ متوسط البيع الفعلي", f"${actual_avg_price:.2f}",
                          help="متوسط أسعار المبيعات الحقيقية (آخر 3 أيام)")
            else:
                st.metric("✅ متوسط البيع الفعلي", "جاري التجميع...")

        # --- تقييم الصفقة ---
        st.markdown("#### 🎯 تقييم الصفقة")
        col_hist, col_market = st.columns(2)

        with col_hist:
            st.markdown("**بناءً على التاريخ:**")
            if current_price <= min_price_hist * 1.05:
                st.success("✅ أقل سعر شوهد أو قريب جداً")
            elif current_price <= avg_price_hist:
                st.info("👍 سعر جيد — أقل من المتوسط التاريخي")
            elif current_price <= max_price_hist * 0.8:
                st.warning("⚠️ سعر متوسط — ممكن تلاقي أحسن")
            else:
                st.error("❌ سعر مرتفع — الأفضل تستنى")

        with col_market:
            st.markdown("**بناءً على البيع الفعلي / السوق:**")
            if actual_avg_price and actual_avg_price > 0:
                profit_pct = (actual_avg_price - current_price) / current_price * 100
                if current_price <= actual_avg_price * 0.8:
                    st.success(f"✅ فرصة ممتازة — أقل من متوسط البيع بـ {profit_pct:.1f}%")
                elif current_price <= actual_avg_price:
                    st.success(f"👍 سعر جيد — أقل من متوسط البيع بـ {profit_pct:.1f}%")
                elif current_price <= actual_avg_price * 1.1:
                    st.warning("⚠️ سعر مقبول — قريب من متوسط البيع الفعلي")
                else:
                    st.error("❌ سعر مرتفع — أعلى من متوسط البيع الفعلي")
            elif market_avg:
                if current_price <= market_min:
                    st.success("✅ أقل سعر في السوق حالياً!")
                elif current_price < market_avg * 0.8:
                    st.success(f"✅ سعر ممتاز — أقل من المتوسط بـ {((market_avg-current_price)/market_avg*100):.0f}%")
                elif current_price < market_avg:
                    st.info("👍 سعر جيد — أقل بقليل من المتوسط")
                elif current_price < market_avg * 1.2:
                    st.warning(f"⚠️ سعر مرتفع — أعلى من المتوسط بـ {((current_price-market_avg)/market_avg*100):.0f}%")
                else:
                    st.error(f"❌ سعر مرتفع جداً — أعلى من المتوسط بـ {((current_price-market_avg)/market_avg*100):.0f}%")
            else:
                st.caption("📊 لا توجد عناصر مشابهة كافية للمقارنة")

        # --- السيولة ---
        if similar_count > 1:
            st.markdown("#### 🔄 سيولة السوق")
            liq_c1, liq_c2, liq_c3 = st.columns(3)
            with liq_c1:
                st.metric("عناصر مشابهة", similar_count)
            with liq_c2:
                if market_min:
                    st.metric("أدنى سعر مشابه", f"${add_tax(market_min):.2f}")
            with liq_c3:
                if market_max:
                    st.metric("أعلى سعر مشابه", f"${add_tax(market_max):.2f}")

            if similar_count <= 3:
                st.success(f"✅ سوق نادر جداً — {similar_count} عنصر فقط")
            elif similar_count <= 8:
                st.success(f"✅ سوق جيد — {similar_count} عناصر مشابهة")
            elif similar_count <= 15:
                st.info(f"👍 سوق متوسط — {similar_count} عناصر مشابهة")
            elif similar_count <= 25:
                st.warning(f"⚠️ سوق مشبع — {similar_count} عناصر مشابهة")
            else:
                st.error(f"❌ سوق مشبع جداً — {similar_count} عناصر مشابهة")

        # --- الرسوم البيانية ---
        chart_c1, chart_c2 = st.columns(2)
        with chart_c1:
            st.markdown("#### 📈 تطور الأسعار التاريخي")
            history_df             = pd.DataFrame(sorted(history, key=lambda x: x['time']))
            history_df['time_dt']  = pd.to_datetime(history_df['time'])
            fig_hist               = px.line(history_df, x='time_dt', y='price', title='تاريخ الأسعار', markers=True)
            fig_hist.add_hline(y=current_price,  line_dash="dash", line_color="red",   annotation_text="الحالي")
            fig_hist.add_hline(y=min_price_hist, line_dash="dash", line_color="green", annotation_text="أقل سعر")
            if actual_avg_price:
                fig_hist.add_hline(y=actual_avg_price, line_dash="dot", line_color="cyan", annotation_text="متوسط البيع")
            fig_hist.update_layout(template='plotly_dark', margin=dict(t=40, b=0))
            st.plotly_chart(fig_hist, use_container_width=True)

        with chart_c2:
            if similar_count > 1:
                st.markdown("#### 📊 توزيع أسعار السوق الحالي")
                fig_dist = px.histogram(similar_items, x='price',
                                        title='توزيع الأسعار المشابهة',
                                        labels={'price': 'السعر ($)'})
                if market_avg:
                    fig_dist.add_vline(x=current_price, line_dash="dash", line_color="red",   annotation_text="الحالي")
                    fig_dist.add_vline(x=market_avg,    line_dash="dash", line_color="green",  annotation_text="المتوسط")
                if actual_avg_price:
                    fig_dist.add_vline(x=actual_avg_price, line_dash="dot", line_color="cyan", annotation_text="متوسط البيع")
                fig_dist.update_layout(template='plotly_dark', margin=dict(t=40, b=0))
                st.plotly_chart(fig_dist, use_container_width=True)

        with st.expander("📜 آخر 10 أسعار شوهدت"):
            for h in sorted(history, key=lambda x: x['time'], reverse=True)[:10]:
                ago_str = time_ago(h['time'])
                emoji   = "🟢" if h['price'] <= min_price_hist * 1.05 else "🟡" if h['price'] <= avg_price_hist else "🔴"
                st.write(f"{emoji} ${add_tax(h['price']):.2f} — منذ {ago_str} — البائع: {h['user']}")

        if similar_count > 1:
            with st.expander("🔍 عرض العناصر المشابهة"):
                display_similar = similar_items[['price', 'quality_score', 'main_value',
                                                  'secondary_value', 'user', 'time_ago']].head(15).copy()
                display_similar['price'] = display_similar['price'].apply(add_tax)
                st.dataframe(display_similar, use_container_width=True)

# ------------------------------------------------------------------
# TAB 4: صائد الأرباح
# ------------------------------------------------------------------
with tab4:
    st.subheader("💰 صائد الأرباح الشامل")
    st.markdown("أفضل فرص الربح عبر **جميع الأصناف** — اضغط المسح عشان تبدأ التحليل")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        comparison_time = st.selectbox(
            "مقارنة بأسعار آخر:",
            ["آخر ساعة", "آخر 6 ساعات", "آخر 12 ساعة", "آخر 24 ساعة", "آخر 3 أيام", "الكل"],
            index=2
        )
    with col2:
        min_profit_usd = st.number_input("الحد الأدنى للربح ($)", 1, 500, 10)
    with col3:
        st.write("")
        st.write("")
        scan_now = st.button("🔍 مسح الآن", type="primary", use_container_width=True)

    hours_limit_profit = TIME_MAP.get(comparison_time, 0)

    if not scan_now:
        st.info("اضغط **🔍 مسح الآن** لبدء البحث عن فرص الربح عبر جميع الأصناف.")
    else:
        all_results = []
        with st.spinner(f"جاري التحليل عبر {len(ITEM_CATEGORIES)} صنف..."):
            progress_bar = st.progress(0)
            for idx, (cat_name, cat_config) in enumerate(ITEM_CATEGORIES.items()):
                temp_code  = cat_config["code"]
                temp_items = fetch_all_items(temp_code, max_pages=5)
                if temp_items:
                    now = datetime.now().astimezone()
                    for item in temp_items:
                        try:
                            created_at = datetime.fromisoformat(item['createdAt'].replace('Z', '+00:00'))
                            hours_diff = (now - created_at).total_seconds() / 3600
                            if hours_limit_profit > 0 and hours_diff > hours_limit_profit:
                                continue
                            quality  = calculate_quality_score(item['skills'], cat_config)
                            main_val = get_main_value(item['skills'], cat_config)
                            sec_val  = get_secondary_value(item['skills'], cat_config)
                            all_results.append({
                                'category':        cat_name,
                                'price':           item['price'],
                                'quality':         quality,
                                'main_value':      main_val,
                                'secondary_value': sec_val,
                                'main_name':       get_main_name(cat_config),
                                'secondary_name':  get_secondary_name(cat_config),
                                'user':            item['user'][:8],
                                'time_ago':        time_ago(item['createdAt']),
                                'hours_ago':       round(hours_diff, 1),
                                'createdAt':       item['createdAt']
                            })
                        except:
                            continue
                progress_bar.progress((idx + 1) / len(ITEM_CATEGORIES))
            progress_bar.empty()

        if not all_results:
            st.info(f"❌ لا توجد بيانات كافية في آخر {comparison_time}")
        else:
            df_temp = pd.DataFrame(all_results)
            df_temp['quality_group'] = (df_temp['quality'] // 10) * 10

            profit_results = []
            for (cat, quality_group), group in df_temp.groupby(['category', 'quality_group']):
                if len(group) >= 3:
                    group_avg = group['price'].mean()
                    for _, row in group.iterrows():
                        expected_profit = group_avg - row['price']
                        if expected_profit >= min_profit_usd:
                            profit_results.append({
                                'category':        cat,
                                'price':           row['price'],
                                'avg_price':       group_avg,
                                'expected_profit': expected_profit,
                                'profit_margin':   (expected_profit / row['price']) * 100,
                                'quality':         row['quality'],
                                'main_value':      row['main_value'],
                                'secondary_value': row['secondary_value'],
                                'main_name':       row['main_name'],
                                'secondary_name':  row['secondary_name'],
                                'user':            row['user'],
                                'time_ago':        row['time_ago'],
                                'hours_ago':       row['hours_ago'],
                                'similar_count':   len(group)
                            })

            if not profit_results:
                st.info(f"❌ لا توجد فرص ربح بـ ${min_profit_usd}+ في آخر {comparison_time}")
            else:
                df_results = pd.DataFrame(profit_results).sort_values('expected_profit', ascending=False).head(20)

                # تنبيهات تيليجرام
                recent_deals = df_results[df_results['hours_ago'] <= 1]
                if len(recent_deals) > 0:
                    sent_alerts = load_sent_alerts()
                    new_alerts  = []
                    for _, alert in recent_deals.iterrows():
                        alert_id = f"{alert['category']}_{alert['main_value']}_{alert['secondary_value']}_{alert['price']}"
                        if alert_id not in sent_alerts:
                            new_alerts.append(alert)
                            sent_alerts.append(alert_id)
                    if new_alerts:
                        save_sent_alerts(sent_alerts)
                        st.toast(f"🔔 {len(new_alerts)} صفقة ساخنة جديدة!", icon="🔥")
                        st.balloons()
                        for alert in new_alerts[:3]:
                            send_telegram_alert(
                                title="🔥 صفقة ساخنة جديدة!",
                                message=f"{alert['category']}\n🔍 {alert['main_name']}: {alert['main_value']} | {alert['secondary_name']}: {alert['secondary_value']}",
                                price=add_tax(alert['price']),
                                profit=alert['expected_profit']
                            )

                st.success(f"🎯 {len(df_results)} فرصة ربح وجدناها (آخر {comparison_time})")

                for _, row in df_results.iterrows():
                    if row['hours_ago'] <= 1:
                        freshness_icon, freshness_text = "🔥🔥", "جديد جداً (أقل من ساعة)"
                    elif row['hours_ago'] <= 6:
                        freshness_icon, freshness_text = "🔥", "جديد (أقل من 6 ساعات)"
                    elif row['hours_ago'] <= 24:
                        freshness_icon, freshness_text = "🟡", "حديث (أقل من يوم)"
                    else:
                        freshness_icon, freshness_text = "🟢", "قديم"

                    st.markdown(f"""
                    <div class="deal-card">
                        <b>📦 {row['category']}</b> {freshness_icon} <span style="color:#ffaa44">{freshness_text}</span><br>
                        <hr style="margin:5px 0">
                        <b>🔍 للبحث في اللعبة:</b><br>
                        • <b>{row['main_name']}:</b> {row['main_value']}<br>
                        • <b>{row['secondary_name']}:</b> {row['secondary_value']}<br>
                        • <b>الجودة:</b> {row['quality']:.0f}%<br>
                        <hr style="margin:5px 0">
                        💰 <b>سعر الشراء بعد الضريبة:</b> <b style="color:#ffaa44">${add_tax(row['price']):.2f}</b><br>
                        📈 متوسط السوق: ${add_tax(row['avg_price']):.2f}<br>
                        💎 <b style="color:#00ff00">الربح المتوقع: +${row['expected_profit']:.2f}</b>
                        &nbsp;|&nbsp; ROI: {row['profit_margin']:.0f}%<br>
                        👤 البائع: <code>{row['user']}</code> &nbsp;|&nbsp; 🕐 {row['time_ago']}
                    </div>
                    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# TAB 5: 🎯 صيد القناصة — Snipe Detection
# ------------------------------------------------------------------
with tab5:
    st.subheader("🎯 صيد القناصة — أسعار تحت أدنى سعر تاريخي مسجّل")
    st.caption(
        "يفحص جميع الأصناف ويكشف العروض المسعّرة **أرخص من أرخص بيع تاريخي مسجّل** "
        "في نفس مجموعة المواصفات (≥3 مبيعات مرجعية للموثوقية). "
        "هذه فرص ربح نادرة — البائع يبيع بسعر لم يره السوق من قبل."
    )

    snipe_c1, snipe_c2, snipe_c3 = st.columns([2, 1, 1])
    with snipe_c1:
        snipe_min_discount = st.slider(
            "الحد الأدنى للخصم تحت أدنى سعر تاريخي (%)",
            0, 30, 0,
            help="0% = أي سعر أرخص من أدنى تاريخي. 5% = أرخص بـ 5% على الأقل."
        )
    with snipe_c2:
        snipe_min_sales = st.number_input("أقل عدد مبيعات مرجعية", 2, 20, 3)
    with snipe_c3:
        st.write("")
        st.write("")
        scan_snipes = st.button("🎯 ابدأ المسح", type="primary", use_container_width=True, key="scan_snipes_btn")

    if not scan_snipes:
        st.info("اضغط **🎯 ابدأ المسح** لفحص جميع الأصناف الـ 12.")
    else:
        snipes = []
        with st.spinner(f"جاري فحص {len(ITEM_CATEGORIES)} صنف..."):
            pbar = st.progress(0)
            for idx, (cat_name, cat_config) in enumerate(ITEM_CATEGORIES.items()):
                code = cat_config['code']
                items = fetch_all_items(code, max_pages=5)
                for it in items:
                    main_v = get_main_value(it['skills'], cat_config)
                    sec_v  = get_secondary_value(it['skills'], cat_config)
                    bstats = get_bucket_full_stats(code, main_v, sec_v, cat_config, hours_back=48)
                    if not bstats or bstats['count'] < snipe_min_sales:
                        continue
                    threshold = bstats['min'] * (1 - snipe_min_discount / 100.0)
                    if it['price'] >= threshold:
                        continue
                    discount_pct = (bstats['min'] - it['price']) / bstats['min'] * 100
                    profit_vs_med = bstats['p50'] - it['price']
                    snipes.append({
                        'category':       cat_name,
                        'cat_config':     cat_config,
                        'price':          it['price'],
                        'main_value':     main_v,
                        'secondary_value': sec_v,
                        'main_name':      get_main_name(cat_config),
                        'secondary_name': get_secondary_name(cat_config),
                        'quality':        calculate_quality_score(it['skills'], cat_config),
                        'user':           it['user'],
                        'time_ago':       it['time_ago'],
                        'createdAt':      it['createdAt'],
                        'bucket_min':     bstats['min'],
                        'bucket_p50':     bstats['p50'],
                        'bucket_avg':     bstats['avg'],
                        'bucket_count':   bstats['count'],
                        'discount_pct':   discount_pct,
                        'profit_vs_med':  profit_vs_med,
                    })
                pbar.progress((idx + 1) / len(ITEM_CATEGORIES))
            pbar.empty()

        if not snipes:
            st.success("✅ لا توجد قناصات حالياً — السوق متوازن.")
            st.caption("حاول تخفيض شرط 'أقل عدد مبيعات' أو زيادة عدد الصفحات في الشريط الجانبي.")
        else:
            snipes.sort(key=lambda x: -x['discount_pct'])
            st.success(f"🎯 وُجدت **{len(snipes)}** قناصة عبر السوق")

            # تنبيهات تيليجرام للقناصات الجديدة
            sent_alerts = load_sent_alerts()
            new_count   = 0
            for s in snipes[:5]:
                aid = f"snipe_{s['category']}_{s['main_value']}_{s['secondary_value']}_{s['price']}"
                if aid in sent_alerts:
                    continue
                sent_alerts.append(aid)
                new_count += 1
                send_telegram_alert(
                    title=f"🎯 قناصة! خصم {s['discount_pct']:.1f}% تحت أدنى سعر",
                    message=f"{s['category']}\n{s['main_name']}: {s['main_value']}"
                            + (f" | {s['secondary_name']}: {s['secondary_value']}%" if s['secondary_name'] else ""),
                    price=add_tax(s['price']),
                    profit=s['profit_vs_med']
                )
            if new_count > 0:
                save_sent_alerts(sent_alerts)
                st.toast(f"📤 أُرسل {new_count} تنبيه قناصة جديد لتيليجرام", icon="🎯")

            # عرض القناصات
            for rank, s in enumerate(snipes[:20], start=1):
                tier_emoji = "🔥🔥🔥" if s['discount_pct'] >= 15 else "🔥🔥" if s['discount_pct'] >= 8 else "🔥"
                with st.container(border=True):
                    top1, top2 = st.columns([4, 1])
                    with top1:
                        st.markdown(
                            f"**{rank}. {tier_emoji} {s['category']}** — "
                            f"<span style='color:#ff2244;font-size:1.25em;font-weight:bold'>"
                            f"خصم {s['discount_pct']:.1f}% تحت أدنى سعر</span>",
                            unsafe_allow_html=True
                        )
                        if s['secondary_name']:
                            st.write(f"🔍 {s['main_name']}: **{s['main_value']}** | {s['secondary_name']}: **{s['secondary_value']}%** | جودة: {s['quality']:.0f}%")
                        else:
                            st.write(f"🔍 {s['main_name']}: **{s['main_value']}** | جودة: {s['quality']:.0f}%")
                    with top2:
                        st.caption(f"منذ {s['time_ago']}")
                        st.caption(f"👤 {s['user']}")

                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("💰 السعر بعد الضريبة", f"${add_tax(s['price']):.2f}")
                    with m2:
                        st.metric("📉 أدنى تاريخي", f"${s['bucket_min']:.2f}",
                                  delta=f"-${s['bucket_min'] - s['price']:.2f}", delta_color="inverse")
                    with m3:
                        st.metric("📊 وسيط البيع", f"${s['bucket_p50']:.2f}")
                    with m4:
                        st.metric("💎 ربح vs الوسيط", f"+${s['profit_vs_med']:.2f}",
                                  help=f"الربح إذا بعت بسعر وسيط البيع التاريخي")
                    st.caption(f"📚 {s['bucket_count']} صفقة مرجعية في آخر 14 يوم")

# ------------------------------------------------------------------
# TAB 6: 🧮 حاسبة البيع — Sell Calculator
# ------------------------------------------------------------------
with tab6:
    st.subheader("🧮 حاسبة البيع — احسب سعر البيع المتوقع والربح")
    st.caption(
        "أدخل مواصفات العنصر وسعر شرائك — الحاسبة بترجع السعر المقترح للبيع، "
        "والربح المتوقع، وسرعة بيع هذه المواصفات."
    )

    with st.form("sell_calc_form", border=True):
        f1, f2 = st.columns(2)
        with f1:
            calc_category = st.selectbox("📦 نوع العنصر:", list(ITEM_CATEGORIES.keys()), key="calc_cat")
            calc_cfg      = ITEM_CATEGORIES[calc_category]
            is_combat     = calc_cfg['type'] in ['jet', 'tank']
            if is_combat:
                main_label = "الهجوم (Attack)"
                main_min, main_max = calc_cfg['min_attack'], calc_cfg['max_attack']
            else:
                main_label = get_main_name(calc_cfg)
                main_min, main_max = calc_cfg['min_value'], calc_cfg['max_value']
            calc_main = st.number_input(f"⚔️ {main_label}", min_value=0, max_value=500,
                                        value=main_min, step=1, key="calc_main")
            if is_combat:
                calc_sec = st.number_input(
                    f"🎯 الكريتيكال (Critical %)",
                    min_value=0, max_value=100,
                    value=calc_cfg['min_critical'], step=1, key="calc_sec"
                )
            else:
                calc_sec = 0
        with f2:
            calc_price = st.number_input("💰 سعر الشراء الفعلي (الذي دفعته)", min_value=0.0, value=100.0, step=1.0, key="calc_price",
                                         help="أدخل المبلغ الفعلي الذي خرج من محفظتك — شامل أي ضريبة دفعتها.")
            st.caption(f"المدى المسموح: {get_range_text(calc_cfg)}")
            st.caption("✅ السعر يُستخدم كما هو لحساب الربح — لا تُضاف ضريبة.")

        submit_calc = st.form_submit_button("🧮 احسب", type="primary", use_container_width=True)

    if submit_calc:
        # نفضّل آخر 48 ساعة لأن الأسعار تتغير بسرعة. نعود للـ 14 يوم فقط لو البيانات قليلة جداً.
        bstats = get_bucket_full_stats(calc_cfg['code'], calc_main, calc_sec, calc_cfg, hours_back=48)
        used_fallback = False
        if not bstats or bstats['count'] < 3:
            bstats = get_bucket_full_stats(calc_cfg['code'], calc_main, calc_sec, calc_cfg, days_back=14)
            used_fallback = True

        if not bstats:
            st.warning("⚠️ لا توجد بيانات مبيعات مسجّلة لهذه المواصفات بعد.")
            st.caption("جرّب الانتظار حتى المزامنة التلقائية القادمة، أو اضغط 'مزامنة يدوية' من الشريط الجانبي.")
        else:
            cost_after_tax = calc_price
            n              = bstats['count']
            confidence     = "✓ ثقة عالية" if n >= 8 else "📊 ثقة متوسطة" if n >= 5 else "⚠️ ثقة محدودة"
            window_label   = "آخر 48 ساعة" if not used_fallback else "آخر 14 يوم (لا توجد بيانات حديثة كافية)"

            # شريط الثقة + نافذة البيانات
            conf_color = "#00cc66" if n >= 8 else "#ffaa00" if n >= 5 else "#ff6600"
            st.markdown(
                f"<div style='padding:10px;background:#1e1e2e;border-right:4px solid {conf_color};border-radius:6px'>"
                f"<b>{confidence}</b> — مبني على <b>{n}</b> صفقة في <b>{window_label}</b></div>",
                unsafe_allow_html=True
            )

            # تحذير لو البيانات قديمة (أحدث صفقة أكبر من 48 ساعة)
            if bstats.get('newest_age_hours', 0) > 48:
                st.warning(
                    f"⚠️ أحدث صفقة مسجّلة عمرها **{bstats['newest_age_hours']:.0f} ساعة** — "
                    f"الأسعار قد تكون تغيّرت. تعامل مع التوصيات بحذر."
                )

            st.markdown("### 💰 توصيات البيع")
            r1, r2, r3 = st.columns(3)
            fast_price   = bstats['p25']
            balanced     = bstats['p50']
            patient      = bstats['p75']

            with r1:
                profit_fast = fast_price - cost_after_tax
                st.metric("⚡ بيع سريع (p25)", f"${fast_price:.2f}",
                          delta=f"+${profit_fast:.2f}" if profit_fast >= 0 else f"-${abs(profit_fast):.2f}")
                st.caption("اعرضه بهذا السعر لبيع سريع — أرخص من 75% من المبيعات")
            with r2:
                profit_bal = balanced - cost_after_tax
                st.metric("⚖️ متوازن (وسيط)", f"${balanced:.2f}",
                          delta=f"+${profit_bal:.2f}" if profit_bal >= 0 else f"-${abs(profit_bal):.2f}")
                st.caption("سعر معقول — يبيع بسرعة متوسطة")
            with r3:
                profit_patient = patient - cost_after_tax
                st.metric("🐢 صبور (p75)", f"${patient:.2f}",
                          delta=f"+${profit_patient:.2f}" if profit_patient >= 0 else f"-${abs(profit_patient):.2f}")
                st.caption("أعلى ربح — يحتاج وقت أطول للبيع")

            # تحذير إذا الشراء غير مربح
            if balanced < cost_after_tax:
                st.error(
                    f"❌ سعر الشراء **${cost_after_tax:.2f}** أعلى من وسيط البيع **${balanced:.2f}** — "
                    f"خسارة محتملة ${cost_after_tax - balanced:.2f} على السعر المتوازن."
                )
            elif balanced - cost_after_tax < 5:
                st.warning(f"⚠️ هامش ربح ضيق ({(balanced - cost_after_tax) / cost_after_tax * 100:.1f}%) — تأكد من سرعة البيع.")
            else:
                margin_pct = (balanced - cost_after_tax) / cost_after_tax * 100
                st.success(f"✅ صفقة مربحة — هامش متوقع **{margin_pct:.1f}%** على السعر المتوازن.")

            # سرعة البيع
            vel_hr, vel_count = get_item_sell_velocity(calc_cfg['code'], calc_main, calc_sec, calc_cfg)
            vel_text          = format_velocity(vel_hr)

            st.markdown("### ⚡ سرعة البيع")
            v1, v2 = st.columns(2)
            with v1:
                if vel_text:
                    st.metric("متوسط الوقت بين المبيعات", vel_text)
                else:
                    st.metric("متوسط الوقت بين المبيعات", "غير متاح", help="يحتاج 2+ مبيعات للحساب")
            with v2:
                st.metric("عدد المبيعات المسجّلة", vel_count)

            # توزيع الأسعار التاريخي
            st.markdown("### 📊 توزيع أسعار البيع التاريخي")
            hist_df = pd.DataFrame({'price': bstats['prices']})
            fig = px.histogram(hist_df, x='price', nbins=min(20, n),
                               title=f"توزيع {n} مبيعة لنفس المواصفات (آخر 14 يوم)",
                               labels={'price': 'سعر البيع ($)', 'count': 'عدد'})
            fig.add_vline(x=cost_after_tax, line_dash="dash", line_color="red",
                          annotation_text="سعر شرائك")
            fig.add_vline(x=balanced, line_dash="dash", line_color="green",
                          annotation_text="وسيط البيع")
            fig.update_layout(template='plotly_dark', margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

            # تفاصيل إحصائية
            with st.expander("📈 إحصائيات تفصيلية"):
                d1, d2, d3, d4, d5 = st.columns(5)
                with d1: st.metric("أدنى", f"${bstats['min']:.2f}")
                with d2: st.metric("p25", f"${bstats['p25']:.2f}")
                with d3: st.metric("وسيط", f"${bstats['p50']:.2f}")
                with d4: st.metric("p75", f"${bstats['p75']:.2f}")
                with d5: st.metric("أعلى", f"${bstats['max']:.2f}")
                st.caption(f"متوسط حسابي: ${bstats['avg']:.2f}")

# ------------------------------------------------------------------
# TAB 7: 📈 اتجاهات السوق — Market Trends Dashboard
# ------------------------------------------------------------------
with tab7:
    st.subheader("📈 اتجاهات السوق — الصورة الكبيرة")
    st.caption(
        "نظرة شاملة على السوق بأكمله بناءً على آخر 48 ساعة فقط — "
        "تساعدك تحدد على أي صنف تركّز جهدك في الـ flipping."
    )

    trend_c1, trend_c2 = st.columns([3, 1])
    with trend_c2:
        st.write("")
        refresh_trends = st.button("🔄 تحديث الاتجاهات", type="primary", use_container_width=True, key="refresh_trends_btn")
    with trend_c1:
        st.caption("اضغط الزر لإعادة الحساب من الكاش الحالي. يفضّل عمل مزامنة أولاً من الشريط الجانبي.")

    if not refresh_trends:
        st.info("اضغط **🔄 تحديث الاتجاهات** لعرض اتجاهات السوق.")
    else:
        # ====== جمع البيانات لكل الأصناف ======
        trends_data = []
        with st.spinner("جاري تحليل اتجاهات السوق..."):
            tpbar = st.progress(0)
            for tidx, (cat_name, cat_cfg) in enumerate(ITEM_CATEGORIES.items()):
                code = cat_cfg['code']
                last_24h = get_category_window_stats(code, 24, 0)
                prev_24h = get_category_window_stats(code, 48, 24)
                last_48h = get_category_window_stats(code, 48, 0)

                # السوق الحالي (المعروضات النشطة)
                current_items = fetch_all_items(code, max_pages=5)
                current_count = len(current_items) if current_items else 0
                current_min   = min((i['price'] for i in current_items), default=None) if current_items else None
                current_avg   = (sum(i['price'] for i in current_items) / current_count) if current_count > 0 else None

                # حساب اتجاه السعر
                trend_emoji, trend_label, trend_pct = "🟡", "مستقر", 0.0
                if last_24h and prev_24h and last_24h['count'] >= 2 and prev_24h['count'] >= 2:
                    trend_pct = (last_24h['avg'] - prev_24h['avg']) / prev_24h['avg'] * 100
                    if trend_pct > 3:
                        trend_emoji, trend_label = "🟢", "صاعد"
                    elif trend_pct < -3:
                        trend_emoji, trend_label = "🔴", "هابط"

                # سرعة البيع (متوسط الفجوة بين المبيعات في 48h)
                avg_gap = last_48h['avg_gap_hours'] if last_48h else None

                trends_data.append({
                    'category':       cat_name,
                    'sales_24h':      last_24h['count'] if last_24h else 0,
                    'sales_48h':      last_48h['count'] if last_48h else 0,
                    'avg_24h':        last_24h['avg']   if last_24h else None,
                    'avg_prev_24h':   prev_24h['avg']   if prev_24h else None,
                    'avg_gap_hours':  avg_gap,
                    'trend_emoji':    trend_emoji,
                    'trend_label':    trend_label,
                    'trend_pct':      trend_pct,
                    'current_count':  current_count,
                    'current_min':    current_min,
                    'current_avg':    current_avg,
                })
                tpbar.progress((tidx + 1) / len(ITEM_CATEGORIES))
            tpbar.empty()

        # ====== Section 1: العناصر الأسرع بيعاً ======
        st.markdown("### 🔥 العناصر عالية الطلب (الأسرع بيعاً)")
        st.caption("متوسط الوقت بين كل عملية بيع — أصغر = طلب أعلى. آخر 48 ساعة فقط.")
        hot_items = [t for t in trends_data if t['avg_gap_hours'] is not None and t['sales_48h'] >= 2]
        hot_items.sort(key=lambda x: x['avg_gap_hours'])
        if not hot_items:
            st.info("لا توجد بيانات مبيعات كافية في آخر 48 ساعة.")
        else:
            hot_df = pd.DataFrame([{
                'الصنف':            t['category'],
                'متوسط الوقت بين المبيعات (ساعة)': round(t['avg_gap_hours'], 2),
                'مبيعات آخر 24س':   t['sales_24h'],
                'مبيعات آخر 48س':   t['sales_48h'],
            } for t in hot_items[:12]])
            st.dataframe(hot_df, use_container_width=True, hide_index=True)

        # ====== Section 2: اتجاه السعر صاعد/هابط ======
        st.markdown("### 📊 اتجاه الأسعار — صاعد أم هابط؟")
        st.caption("مقارنة متوسط سعر آخر 24 ساعة بمتوسط الـ 24 ساعة السابقة (تغيّر أكبر من ±3% فقط).")
        price_trend = [t for t in trends_data if t['sales_48h'] >= 5 and t['avg_24h'] and t['avg_prev_24h']]
        price_trend.sort(key=lambda x: -abs(x['trend_pct']))
        if not price_trend:
            st.info("لا توجد أصناف مع 5+ مبيعات في آخر 48 ساعة لحساب الاتجاه.")
        else:
            for t in price_trend[:12]:
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                with tc1:
                    st.markdown(f"{t['trend_emoji']} **{t['category']}** — {t['trend_label']}")
                with tc2:
                    st.metric("متوسط 24س", f"${t['avg_24h']:.2f}")
                with tc3:
                    st.metric("الـ 24س السابقة", f"${t['avg_prev_24h']:.2f}")
                with tc4:
                    delta_color = "normal" if t['trend_pct'] > 0 else "inverse"
                    st.metric("التغيّر", f"{t['trend_pct']:+.1f}%", delta_color=delta_color)

        # ====== Section 3: أفضل الفرص الآن ======
        st.markdown("### 💎 أفضل الفرص الآن")
        st.caption("أصناف فيها متوسط السوق الحالي **أرخص** من متوسط البيع في آخر 24 ساعة — احتمال ربح فوري.")
        opps = []
        for t in trends_data:
            if t['avg_24h'] and t['current_avg'] and t['sales_24h'] >= 3:
                if t['current_avg'] < t['avg_24h']:
                    profit_pct = (t['avg_24h'] - t['current_avg']) / t['current_avg'] * 100
                    opps.append({**t, 'profit_pct': profit_pct})
        opps.sort(key=lambda x: -x['profit_pct'])
        if not opps:
            st.info("لا توجد فرص واضحة الآن — السوق متوازن أو البيانات غير كافية.")
        else:
            opp_df = pd.DataFrame([{
                'الصنف':           o['category'],
                'متوسط السوق الآن': f"${o['current_avg']:.2f}",
                'متوسط البيع 24س':  f"${o['avg_24h']:.2f}",
                'فجوة الربح':       f"+{o['profit_pct']:.1f}%",
                'أرخص معروض':       f"${o['current_min']:.2f}" if o['current_min'] else "-",
                'مبيعات 24س':       o['sales_24h'],
            } for o in opps[:10]])
            st.dataframe(opp_df, use_container_width=True, hide_index=True)

        # ====== Section 4: عناصر يجب تجنبها ======
        st.markdown("### ⚠️ عناصر يجب تجنّبها")
        st.caption("أسعار هابطة (سوق ينزل) أو معروضات كثيرة (إفراط في العرض > 15 عنصر).")
        avoid = []
        for t in trends_data:
            reasons = []
            if t['trend_label'] == "هابط":
                reasons.append(f"📉 سعر هابط {t['trend_pct']:.1f}%")
            if t['current_count'] > 15:
                reasons.append(f"📦 إفراط في العرض ({t['current_count']} معروض)")
            if reasons:
                avoid.append({'category': t['category'], 'reasons': " | ".join(reasons),
                              'current_count': t['current_count'], 'trend_pct': t['trend_pct']})
        if not avoid:
            st.success("✅ لا توجد إشارات تحذير حالياً — السوق في حالة جيدة.")
        else:
            for a in avoid:
                st.warning(f"**{a['category']}** — {a['reasons']}")
