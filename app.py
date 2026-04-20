import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
import json
import os
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
</style>
""", unsafe_allow_html=True)

# ========== ملفات البيانات ==========
SENT_ALERTS_FILE  = "data/sent_alerts.json"
SALES_CACHE_FILE  = "data/sales_cache.json"
PRICE_HISTORY_FILE = "data/price_history.json"
ALERTS_HISTORY_FILE = "data/alerts_history.json"

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

def load_sent_alerts():    return _load_json(SENT_ALERTS_FILE, [])
def save_sent_alerts(d):   return _save_json(SENT_ALERTS_FILE, d)
def load_sales_cache():    return _load_json(SALES_CACHE_FILE, {})
def save_sales_cache(d):   return _save_json(SALES_CACHE_FILE, d)
def load_price_history():  return _load_json(PRICE_HISTORY_FILE, {})
def save_price_history(d): return _save_json(PRICE_HISTORY_FILE, d)
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
                if abs(sale['main_value'] - main_value) <= 10 and sale['price'] > 0:
                    valid_prices.append(sale['price'])
        except:
            continue
    return sum(valid_prices) / len(valid_prices) if valid_prices else None

# ========== سرعة البيع (Sell Velocity) ==========
def get_sell_velocity(item_code):
    """
    احسب متوسط الوقت بين عمليات البيع لنوع معين.
    يرجع النتيجة بالساعات أو None لو البيانات قليلة.
    """
    cache = load_sales_cache()
    if item_code not in cache or len(cache[item_code]) < 2:
        return None
    try:
        times = []
        for sale in cache[item_code]:
            t = datetime.fromisoformat(sale['time'].replace('Z', '+00:00'))
            times.append(t)
        times_sorted = sorted(times)
        gaps = [(times_sorted[i+1] - times_sorted[i]).total_seconds() / 3600
                for i in range(len(times_sorted) - 1)]
        avg_gap = sum(gaps) / len(gaps)
        return round(avg_gap, 1)
    except:
        return None

# ========== نسبة السعر المئوية (Price Percentile) ==========
def get_price_percentile(price, all_prices):
    """
    ارجع رتبة السعر: X% من العناصر الأخرى أغلى من هذا السعر.
    كلما كانت النسبة أعلى كلما كانت الصفقة أفضل.
    """
    if len(all_prices) <= 1:
        return None
    cheaper_than = sum(1 for p in all_prices if p > price)
    return round((cheaper_than / len(all_prices)) * 100, 0)

# ========== الضريبة ==========
def add_tax(price):
    return price * 1.01

# ========== الأسرار والتوكنز ==========
def get_secret(key, default):
    try:
        return st.secrets[key]
    except:
        return default

YOUR_JWT = get_secret("YOUR_JWT", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7Il9pZCI6IjY5Y2VlY2Y1MTk3Zjg0NWZjOWZlZGU1YyJ9LCJpYXQiOjE3NzUxNjg3NTcsImV4cCI6MTc3Nzc2MDc1N30.nIKi8ohQAYsAVXQL9_rlRUr93TDg-G-DVOCQOrRdOtY")
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN", "8261610629:AAFs-el5LK236x1xkDuUM8k-6NOi81X4FU8")
TELEGRAM_CHAT_ID   = get_secret("TELEGRAM_CHAT_ID",   "1690550033")

def send_telegram_alert(title, message, price=None, profit=None):
    text = f"🔔 *{title}*\n{message}"
    if price:
        text += f"\n💰 السعر بعد الضريبة: ${price:.2f}"
    if profit:
        text += f"\n💎 الربح المتوقع: +${profit:.2f}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=5)
        return response.status_code == 200
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
    "👑 خوذة Legendary": {
        "code": "helmet5", "type": "equipment",
        "skill": "criticalDamages", "min_value": 91, "max_value": 110
    },
    "✨ خوذة Mythic": {
        "code": "helmet6", "type": "equipment",
        "skill": "criticalDamages", "min_value": 121, "max_value": 150
    },
    "🦺 صدر Legendary": {
        "code": "chest5", "type": "equipment",
        "skill": "armor", "min_value": 36, "max_value": 50
    },
    "💪 صدر Mythic": {
        "code": "chest6", "type": "equipment",
        "skill": "armor", "min_value": 56, "max_value": 70
    },
    "🧤 قفاز Legendary": {
        "code": "gloves5", "type": "equipment",
        "skill": "precision", "min_value": 31, "max_value": 40
    },
    "⚡ قفاز Mythic": {
        "code": "gloves6", "type": "equipment",
        "skill": "precision", "min_value": 51, "max_value": 60
    },
    "👖 بنطلون Legendary": {
        "code": "pants5", "type": "equipment",
        "skill": "armor", "min_value": 36, "max_value": 50
    },
    "👖 بنطلون Mythic": {
        "code": "pants6", "type": "equipment",
        "skill": "armor", "min_value": 56, "max_value": 70
    },
    "👢 حذاء Legendary": {
        "code": "boots5", "type": "equipment",
        "skill": "dodge", "min_value": 31, "max_value": 40
    },
    "👢 حذاء Mythic": {
        "code": "boots6", "type": "equipment",
        "skill": "dodge", "min_value": 51, "max_value": 60
    },
}

# ========== دوال حساب الجودة ==========
def calculate_quality_score(skills, category_config):
    item_type = category_config["type"]
    if item_type in ["jet", "tank"]:
        attack   = skills.get('attack', 0)
        critical = skills.get('criticalChance', 0)
        min_attack   = category_config.get("min_attack", 0)
        max_attack   = category_config.get("max_attack", 1)
        min_critical = category_config.get("min_critical", 0)
        max_critical = category_config.get("max_critical", 1)
        a_score = max(0, min(1, (attack   - min_attack)   / (max_attack   - min_attack)   if attack   >= min_attack   else 0))
        c_score = max(0, min(1, (critical - min_critical) / (max_critical - min_critical) if critical >= min_critical else 0))
        return round(((a_score + c_score) / 2) * 100, 1)
    elif item_type == "equipment":
        val       = skills.get(category_config["skill"], 0)
        min_value = category_config.get("min_value", 0)
        max_value = category_config.get("max_value", 1)
        score = (val - min_value) / (max_value - min_value) if val >= min_value else 0
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
    if category_config["type"] in ["jet", "tank"]:
        return "الكريتيكال"
    return ""

def get_range_text(category_config):
    if category_config["type"] in ["jet", "tank"]:
        return (f"({category_config['min_attack']}-{category_config['max_attack']} هجوم"
                f" | {category_config['min_critical']}-{category_config['max_critical']}% كريتيكال)")
    elif category_config["type"] == "equipment":
        return f"({category_config['min_value']}-{category_config['max_value']})"
    return ""

def time_ago(created_at_str):
    try:
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        diff = datetime.now().astimezone() - created_at
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1:
            return f"{int(diff.total_seconds())} ثانية"
        elif minutes < 60:
            return f"{minutes} دقيقة"
        else:
            return f"{minutes // 60} ساعة"
    except:
        return "غير معروف"

def categorize_item(item, category_config):
    item_code = category_config['code']
    if category_config['type'] in ["jet", "tank"]:
        a = round(item['main_value'] / 5) * 5
        c = round(item['secondary_value'] / 2) * 2
        return f"{item_code}_A{a}_C{c}"
    else:
        v = round(item['main_value'] / 5) * 5
        return f"{item_code}_V{v}"

# ========== جلب البيانات ==========
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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items_data = data[0].get('result', {}).get('data', {})
            return items_data.get('items', []), items_data.get('nextCursor')
    except:
        pass
    return [], None

@st.cache_data(ttl=60)
def fetch_all_items(item_code, max_pages=5):
    all_items = []
    cursor = None
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

# ========== الشريط الجانبي ==========
with st.sidebar:
    st.header("⚙️ إعدادات التحليل")

    auto_refresh = st.checkbox("🔄 تحديث تلقائي كل دقيقة", value=False)
    if auto_refresh:
        st_autorefresh = __import__('streamlit_autorefresh').st_autorefresh
        st_autorefresh(interval=60000, limit=100, key="auto_refresh")

    item_category = st.selectbox("📦 اختر نوع المعدات:", list(ITEM_CATEGORIES.keys()))
    max_pages  = st.slider("عدد صفحات الجلب", 1, 10, 5, help="كل صفحة = 50 عنصر")
    min_quality = st.slider("الحد الأدنى للجودة (%)", 0, 100, 0)
    max_price  = st.number_input("الحد الأقصى للسعر", 0, 10000, 5000, step=100)

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
    st.caption(f"📏 **رينج القيم:** {get_range_text(ITEM_CATEGORIES[item_category])}")

# ========== جلب البيانات ==========
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
    quality          = calculate_quality_score(item['skills'], category_config)
    main_value       = get_main_value(item['skills'], category_config)
    secondary_value  = get_secondary_value(item['skills'], category_config)
    value_for_money  = (quality / item['price']) * 1000 if item['price'] > 0 else 0
    all_items.append({
        'id':             item['id'],
        'price':          item['price'],
        'user':           item['user'],
        'main_value':     main_value,
        'secondary_value': secondary_value,
        'main_name':      main_name,
        'secondary_name': secondary_name,
        'quality_score':  quality,
        'value_for_money': value_for_money,
        'createdAt':      item['createdAt'],
        'time_ago':       item['time_ago'],
        'attack':         item['attack'],
        'critical':       item['critical']
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
df_filtered['enhanced_value'] = df_filtered.apply(
    lambda row: row['value_for_money'] * (1 + max(0, row['actual_profit'] / row['price']))
    if row['actual_profit'] > 0 else row['value_for_money'], axis=1
)

# نسبة السعر المئوية (Price Percentile) لكل عنصر في القائمة الحالية
all_prices_list = df_filtered['price'].tolist()
df_filtered['price_percentile'] = df_filtered['price'].apply(
    lambda p: get_price_percentile(p, all_prices_list)
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

# ========== العنوان وإحصائيات الهيدر ==========
st.title("🎯 War Era - Market Analyzer")
st.markdown(f"تحليل متقدم لسوق **الطيارات، الدبابات، والمعدات النادرة** — {item_category}")

if len(df_filtered) > 0:
    sell_velocity = get_sell_velocity(item_code)

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
        if sell_velocity is not None:
            st.metric("⚡ سرعة البيع", f"~{sell_velocity:.1f} ساعة", help="متوسط الوقت بين كل عملية بيع بناءً على السجل التاريخي")
        else:
            st.metric("⚡ سرعة البيع", "لا يوجد بيانات", help="تحتاج مبيعات مسجلة في Sales Analyzer أولاً")
    st.divider()

# ========== التبويبات الأربعة ==========
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 الجدول",
    "🏆 أفضل الصفقات",
    "🔍 تحليل العنصر",
    "💰 صائد الأرباح"
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
        display_df.columns = [
            'السعر بعد الضريبة', main_name, f'{secondary_name}%',
            'الجودة%', 'أرخص من%', 'القيمة/السعر', 'البائع', 'منذ'
        ]
    else:
        display_df = df_sorted[['price', 'main_value', 'quality_score',
                                 'price_percentile', 'value_for_money', 'user', 'time_ago']].copy()
        display_df['price'] = display_df['price'].apply(add_tax)
        display_df.columns = [
            'السعر بعد الضريبة', main_name,
            'الجودة%', 'أرخص من%', 'القيمة/السعر', 'البائع', 'منذ'
        ]

    st.data_editor(
        display_df,
        column_config={
            "السعر بعد الضريبة": st.column_config.NumberColumn("💰 السعر بعد الضريبة", format="$ %.2f"),
            "الجودة%": st.column_config.ProgressColumn("الجودة%", format="%.1f %%", min_value=0, max_value=100),
            "أرخص من%": st.column_config.ProgressColumn("أرخص من%", format="%.0f %%", min_value=0, max_value=100,
                                                          help="هذا السعر أقل من X% من العناصر المماثلة — كلما ارتفعت النسبة كلما كانت الصفقة أفضل"),
        },
        use_container_width=True,
        height=500,
        hide_index=True,
        disabled=True
    )

    # تنبيهات تيليجرام للعناصر الجديدة
    recent_in_table = df_sorted[df_sorted['createdAt'].apply(
        lambda x: (datetime.now().astimezone() - datetime.fromisoformat(x.replace('Z', '+00:00'))).total_seconds() / 3600 <= 1
    )]
    if len(recent_in_table) > 0:
        sent_alerts = load_sent_alerts()
        for _, item in recent_in_table.iterrows():
            alert_id = f"table_{item_category}_{item['main_value']}_{item['secondary_value']}_{item['price']}"
            if alert_id not in sent_alerts:
                sent_alerts.append(alert_id)
                send_telegram_alert(
                    title="🆕 عنصر جديد في السوق!",
                    message=f"{item_category}\n🔍 {item['main_name']}: {item['main_value']} | {item['secondary_name']}: {item['secondary_value']}",
                    price=add_tax(item['price']),
                    profit=None
                )
        save_sent_alerts(sent_alerts)

# ------------------------------------------------------------------
# TAB 2: أفضل الصفقات
# ------------------------------------------------------------------
with tab2:
    st.subheader("🏆 أفضل 10 صفقات (بناءً على القيمة المعززة)")

    best_value = df_filtered.nlargest(10, 'enhanced_value')

    for rank, (_, row) in enumerate(best_value.iterrows(), start=1):
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{rank}. 💰 السعر بعد الضريبة: ${add_tax(row['price']):,.2f}** (منذ {row['time_ago']})")
                if row['secondary_name']:
                    st.write(f"   {row['main_name']}: {row['main_value']} | {row['secondary_name']}: {row['secondary_value']}%")
                else:
                    st.write(f"   {row['main_name']}: {row['main_value']}")
                if row['actual_avg_price'] and row['actual_avg_price'] > 0:
                    st.caption(f"📊 متوسط البيع الفعلي (آخر 3 أيام): ${row['actual_avg_price']:.2f}")
                    if row['actual_profit'] > 0:
                        st.caption(f"💰 الربح المتوقع: +${row['actual_profit']:.2f}")
            with col2:
                st.metric("الجودة", f"{row['quality_score']}%")
                if row['actual_avg_price'] and row['actual_avg_price'] > 0:
                    st.metric("الربح الفعلي", f"+{row['actual_profit']:.0f}$")
            with col3:
                if row['price_percentile'] is not None:
                    pct = int(row['price_percentile'])
                    label = "🔥 صفقة ممتازة" if pct >= 80 else "👍 سعر جيد" if pct >= 50 else "⚠️ سعر عالي"
                    st.metric("أرخص من%", f"{pct}%", help="نسبة العناصر الأغلى من هذا السعر")
                    st.caption(label)
            st.caption(f"👤 البائع: {row['user']}")

# ------------------------------------------------------------------
# TAB 3: تحليل العنصر (دمج تحليل الأسعار التاريخي + تحليل السوق)
# ------------------------------------------------------------------
with tab3:
    st.subheader("🔍 تحليل العنصر — التاريخي والسوقي")
    st.markdown("اختر عنصراً لتحليل تاريخ أسعاره ومقارنته بالسوق الحالي")

    temp_df = df_sorted.head(50).copy()
    temp_df['display'] = temp_df.apply(
        lambda x: f"💰 ${add_tax(x['price']):.2f} | {x['main_name']}: {x['main_value']} | جودة {x['quality_score']}% | 👤 {x['user']}",
        axis=1
    )

    selected_display = st.selectbox("اختر عنصر للتحليل:", options=temp_df['display'].tolist())

    if selected_display:
        selected = temp_df[temp_df['display'] == selected_display].iloc[0]
        current_price = selected['price']

        # --- تحديث سجل الأسعار ---
        price_history = load_price_history()
        item_key = categorize_item(selected, category_config)
        if item_key not in price_history:
            price_history[item_key] = []
        is_dup = any(
            r.get('user') == selected['user'] and r['price'] == current_price
            for r in price_history[item_key][-5:]
        )
        if not is_dup:
            price_history[item_key].append({
                'price':          current_price,
                'time':           datetime.now().isoformat(),
                'user':           selected['user'],
                'main_value':     selected['main_value'],
                'secondary_value': selected['secondary_value']
            })
            price_history[item_key] = price_history[item_key][-50:]
            save_price_history(price_history)

        history = price_history[item_key]
        prices  = [h['price'] for h in history]
        min_price_hist = min(prices)
        max_price_hist = max(prices)
        avg_price_hist = sum(prices) / len(prices)

        # --- عناصر مشابهة للتحليل السوقي ---
        similar_items = df_filtered[
            (df_filtered['main_value'].between(selected['main_value'] - 10, selected['main_value'] + 10)) &
            (df_filtered['quality_score'].between(selected['quality_score'] - 10, selected['quality_score'] + 10))
        ].copy()
        market_avg   = similar_items['price'].mean() if len(similar_items) > 1 else None
        market_min   = similar_items['price'].min()  if len(similar_items) > 1 else None
        market_max   = similar_items['price'].max()  if len(similar_items) > 1 else None
        similar_count = len(similar_items)

        actual_avg_price = get_average_sale_price(item_code, selected['main_value'], 3)

        # --- قسم: الإحصائيات المجمعة ---
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
            if market_avg:
                st.metric("🏪 متوسط السوق الحالي", f"${add_tax(market_avg):.2f}")
            else:
                st.metric("🏪 متوسط السوق الحالي", "—")
        with c5:
            if actual_avg_price:
                st.metric("✅ متوسط البيع الفعلي", f"${actual_avg_price:.2f}",
                          help="متوسط أسعار المبيعات الحقيقية (آخر 3 أيام)")
            else:
                st.metric("✅ متوسط البيع الفعلي", "لا يوجد بيانات")

        # --- قسم: تقييم الصفقة ---
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
            st.markdown("**بناءً على السوق الحالي:**")
            if actual_avg_price and actual_avg_price > 0:
                if current_price <= actual_avg_price * 0.8:
                    st.success("✅ فرصة ممتازة — أقل من متوسط البيع بـ 20%+")
                elif current_price <= actual_avg_price:
                    st.success("👍 سعر جيد — أقل من متوسط البيع الفعلي")
                elif current_price <= actual_avg_price * 1.1:
                    st.warning("⚠️ سعر مقبول — قريب من متوسط البيع الفعلي")
                else:
                    st.error("❌ سعر مرتفع — أعلى من متوسط البيع الفعلي")
            elif market_avg:
                if current_price <= market_min:
                    st.success("✅ أقل سعر في السوق حالياً!")
                elif current_price < market_avg * 0.8:
                    pct_below = ((market_avg - current_price) / market_avg * 100)
                    st.success(f"✅ سعر ممتاز — أقل من المتوسط بـ {pct_below:.0f}%")
                elif current_price < market_avg:
                    st.info("👍 سعر جيد — أقل بقليل من المتوسط")
                elif current_price < market_avg * 1.2:
                    pct_above = ((current_price - market_avg) / market_avg * 100)
                    st.warning(f"⚠️ سعر مرتفع — أعلى من المتوسط بـ {pct_above:.0f}%")
                else:
                    pct_above = ((current_price - market_avg) / market_avg * 100)
                    st.error(f"❌ سعر مرتفع جداً — أعلى من المتوسط بـ {pct_above:.0f}%")
            else:
                st.caption("📊 لا توجد عناصر مشابهة كافية للمقارنة")

        # --- قسم: السيولة ---
        if similar_count > 1:
            st.markdown("#### 🔄 سيولة السوق")
            liq_c1, liq_c2, liq_c3 = st.columns(3)
            with liq_c1:
                st.metric("عناصر مشابهة", similar_count)
            with liq_c2:
                if market_avg:
                    st.metric("أدنى سعر مشابه", f"${add_tax(market_min):.2f}")
            with liq_c3:
                if market_avg:
                    st.metric("أعلى سعر مشابه", f"${add_tax(market_max):.2f}")

            if similar_count <= 3:
                st.success(f"✅ سوق نادر جداً — {similar_count} عنصر فقط، سهولة بيع عالية")
            elif similar_count <= 8:
                st.success(f"✅ سوق جيد — {similar_count} عناصر مشابهة")
            elif similar_count <= 15:
                st.info(f"👍 سوق متوسط — {similar_count} عناصر مشابهة")
            elif similar_count <= 25:
                st.warning(f"⚠️ سوق مشبع — {similar_count} عناصر مشابهة")
            else:
                st.error(f"❌ سوق مشبع جداً — {similar_count} عناصر مشابهة")

        # --- قسم: الرسوم البيانية ---
        chart_c1, chart_c2 = st.columns(2)

        with chart_c1:
            st.markdown("#### 📈 تطور الأسعار التاريخي")
            history_df = pd.DataFrame(sorted(history, key=lambda x: x['time']))
            history_df['time_dt'] = pd.to_datetime(history_df['time'])
            fig_hist = px.line(history_df, x='time_dt', y='price',
                               title='تاريخ الأسعار', markers=True)
            fig_hist.add_hline(y=current_price, line_dash="dash", line_color="red",   annotation_text="الحالي")
            fig_hist.add_hline(y=min_price_hist, line_dash="dash", line_color="green", annotation_text="أقل سعر")
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
                fig_dist.update_layout(template='plotly_dark', margin=dict(t=40, b=0))
                st.plotly_chart(fig_dist, use_container_width=True)

        # --- آخر الأسعار المشوهدة ---
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
# TAB 4: صائد الأرباح — يعمل فقط عند الضغط على "مسح الآن"
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
        st.stop()

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
                            'category':       cat_name,
                            'price':          item['price'],
                            'quality':        quality,
                            'main_value':     main_val,
                            'secondary_value': sec_val,
                            'main_name':      get_main_name(cat_config),
                            'secondary_name': get_secondary_name(cat_config),
                            'user':           item['user'][:8],
                            'time_ago':       time_ago(item['createdAt']),
                            'hours_ago':      round(hours_diff, 1),
                            'createdAt':      item['createdAt']
                        })
                    except:
                        continue
            progress_bar.progress((idx + 1) / len(ITEM_CATEGORIES))
        progress_bar.empty()

    if not all_results:
        st.info(f"❌ لا توجد بيانات كافية في آخر {comparison_time}")
        st.stop()

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
                        'category':       cat,
                        'price':          row['price'],
                        'avg_price':      group_avg,
                        'expected_profit': expected_profit,
                        'profit_margin':  (expected_profit / row['price']) * 100,
                        'quality':        row['quality'],
                        'main_value':     row['main_value'],
                        'secondary_value': row['secondary_value'],
                        'main_name':      row['main_name'],
                        'secondary_name': row['secondary_name'],
                        'user':           row['user'],
                        'time_ago':       row['time_ago'],
                        'hours_ago':      row['hours_ago'],
                        'similar_count':  len(group)
                    })

    if not profit_results:
        st.info(f"❌ لا توجد فرص ربح بـ ${min_profit_usd}+ في آخر {comparison_time}")
        st.stop()

    df_results = pd.DataFrame(profit_results).sort_values('expected_profit', ascending=False).head(20)

    # تنبيهات تيليجرام للصفقات الجديدة
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
