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

# ========== تحسينات الشكل ==========
st.markdown("""
<style>
    body, .stApp, .main, .stMarkdown, .stText, p, div, span, label {
        color: #FFFFFF !important;
        font-size: 14px !important;
    }
    .stDataFrame { background-color: #1e1e2e !important; }
    .stDataFrame table { background-color: #1e1e2e !important; color: #ffffff !important; }
    .stDataFrame th { background-color: #2d2d3d !important; color: #00ff88 !important; }
    .stDataFrame td { background-color: #1e1e2e !important; color: #ffffff !important; }
    div[data-testid="stMetricValue"] { color: #00ff88 !important; background: linear-gradient(135deg, #1e1e2e 0%, #2d2d3d 100%); }
    .stSidebar { background-color: #1a1a2a !important; }
    .stButton button { background: linear-gradient(135deg, #ff4b4b 0%, #ff6b6b 100%) !important; color: white !important; }
    .stTabs [data-baseweb="tab"] { background-color: #2d2d3d !important; color: white !important; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #ff4b4b 0%, #ff6b6b 100%) !important; }
</style>
""", unsafe_allow_html=True)

YOUR_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7Il9pZCI6IjY5Y2VlY2Y1MTk3Zjg0NWZjOWZlZGU1YyJ9LCJpYXQiOjE3NzUxNjg3NTcsImV4cCI6MTc3Nzc2MDc1N30.nIKi8ohQAYsAVXQL9_rlRUr93TDg-G-DVOCQOrRdOtY"

# ========== إعدادات الأصناف ==========
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
        attack = skills.get('attack', 0)
        critical = skills.get('criticalChance', 0)
        min_attack = category_config.get("min_attack", 0)
        max_attack = category_config.get("max_attack", 1)
        min_critical = category_config.get("min_critical", 0)
        max_critical = category_config.get("max_critical", 1)
        
        attack_score = (attack - min_attack) / (max_attack - min_attack) if attack >= min_attack else 0
        critical_score = (critical - min_critical) / (max_critical - min_critical) if critical >= min_critical else 0
        attack_score = max(0, min(1, attack_score))
        critical_score = max(0, min(1, critical_score))
        return round(((attack_score + critical_score) / 2) * 100, 1)
    
    elif item_type == "equipment":
        skill_value = skills.get(category_config["skill"], 0)
        min_value = category_config.get("min_value", 0)
        max_value = category_config.get("max_value", 1)
        score = (skill_value - min_value) / (max_value - min_value) if skill_value >= min_value else 0
        return round(max(0, min(1, score)) * 100, 1)
    
    return 0

def get_main_value(skills, category_config):
    item_type = category_config["type"]
    if item_type in ["jet", "tank"]:
        return skills.get('attack', 0)
    elif item_type == "equipment":
        return skills.get(category_config["skill"], 0)
    return 0

def get_secondary_value(skills, category_config):
    if category_config["type"] in ["jet", "tank"]:
        return skills.get('criticalChance', 0)
    return 0

def get_main_name(category_config):
    if category_config["type"] in ["jet", "tank"]:
        return "الهجوم"
    elif category_config["type"] == "equipment":
        names = {"dodge": "المراوغة", "armor": "الدفاع", "precision": "الدقة", "criticalDamages": "الضرر الحاسم"}
        return names.get(category_config["skill"], "القيمة")
    return "القيمة"

def get_secondary_name(category_config):
    if category_config["type"] in ["jet", "tank"]:
        return "الكريتيكال"
    return ""

def get_range_text(category_config):
    if category_config["type"] in ["jet", "tank"]:
        return f"({category_config['min_attack']}-{category_config['max_attack']} هجوم | {category_config['min_critical']}-{category_config['max_critical']}% كريتيكال)"
    elif category_config["type"] == "equipment":
        return f"({category_config['min_value']}-{category_config['max_value']})"
    return ""

def time_ago(created_at_str):
    try:
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        now = datetime.now().astimezone()
        diff = now - created_at
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1:
            return f"{int(diff.total_seconds())} ثانية"
        elif minutes < 60:
            return f"{minutes} دقيقة"
        else:
            return f"{minutes // 60} ساعة"
    except:
        return "غير معروف"

# ========== دوال جلب البيانات ==========
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
            items = items_data.get('items', [])
            next_cursor = items_data.get('nextCursor')
            return items, next_cursor
    except:
        pass
    return [], None

def fetch_all_items(item_code, max_pages=5):
    all_items = []
    cursor = None
    
    for page in range(max_pages):
        items, cursor = fetch_single_item(item_code, limit=50, cursor=cursor)
        if not items:
            break
        
        for item in items:
            item_info = item.get('item', {})
            skills = item_info.get('skills', {})
            user_id = item.get('user', '')
            
            all_items.append({
                'id': item.get('_id'),
                'price': item.get('price'),
                'user': user_id[:8] if user_id else 'unknown',
                'skills': skills,
                'attack': skills.get('attack', 0),
                'critical': skills.get('criticalChance', 0),
                'createdAt': item.get('createdAt'),
                'time_ago': time_ago(item.get('createdAt', ''))
            })
        
        if not cursor:
            break
        time.sleep(0.2)
    
    return all_items

# ========== دوال تحليل الأسعار التاريخي ==========
import numpy as np

PRICE_HISTORY_FILE = "data/price_history.json"
ALERTS_HISTORY_FILE = "data/alerts_history.json"

def convert_numpy_to_python(obj):
    """تحويل numpy types إلى Python types عشان JSON"""
    if isinstance(obj, dict):
        return {k: convert_numpy_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(v) for v in obj]
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj)
    return obj

def load_price_history():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(PRICE_HISTORY_FILE):
        return {}
    try:
        with open(PRICE_HISTORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except:
        return {}

def save_price_history(history):
    try:
        os.makedirs("data", exist_ok=True)
        history_clean = convert_numpy_to_python(history)
        with open(PRICE_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_clean, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def load_alerts_history():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(ALERTS_HISTORY_FILE):
        return {"alerts_sent": []}
    try:
        with open(ALERTS_HISTORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"alerts_sent": []}
            data = json.loads(content)
            if 'alerts_sent' not in data:
                data['alerts_sent'] = []
            return data
    except:
        return {"alerts_sent": []}

def save_alerts_history(alerts):
    try:
        os.makedirs("data", exist_ok=True)
        alerts_clean = convert_numpy_to_python(alerts)
        with open(ALERTS_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(alerts_clean, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def categorize_jet(jet):
    attack_group = round(jet['attack'] / 5) * 5
    critical_group = round(jet['critical'] / 2) * 2
    return f"A{attack_group}_C{critical_group}"

def check_price_alert(jet_category, current_price, price_history):
    if jet_category in price_history and len(price_history[jet_category]) > 0:
        history = price_history[jet_category]
        min_price = min([h['price'] for h in history])
        if current_price < min_price:
            return True, min_price
    return False, None

def predict_price(prices):
    if len(prices) < 3:
        return None, None
    from sklearn.linear_model import LinearRegression
    X = np.array(range(len(prices))).reshape(-1, 1)
    y = np.array(prices)
    model = LinearRegression()
    model.fit(X, y)
    next_price = model.predict([[len(prices)]])[0]
    trend = "صاعد" if model.coef_[0] > 0 else "هابط"
    return next_price, trend

def compare_sellers(jet_category, price_history, current_user=None):
    if jet_category not in price_history:
        return None
    sellers = {}
    for record in price_history[jet_category]:
        user = record.get('user', 'unknown')
        if user not in sellers:
            sellers[user] = {'prices': [], 'count': 0}
        sellers[user]['prices'].append(record['price'])
        sellers[user]['count'] += 1
    seller_stats = []
    for user, data in sellers.items():
        seller_stats.append({
            'user': user,
            'avg_price': sum(data['prices']) / len(data['prices']),
            'min_price': min(data['prices']),
            'max_price': max(data['prices']),
            'count': data['count']
        })
    return pd.DataFrame(seller_stats).sort_values('avg_price')

def categorize_item(item, category_config):
    """تصنيف العنصر حسب نوعه - عشان نخزن كل نوع لوحده"""
    item_code = category_config['code']
    item_type = category_config['type']
    
    if item_type in ["jet", "tank"]:
        attack_group = round(item['main_value'] / 5) * 5
        critical_group = round(item['secondary_value'] / 2) * 2
        return f"{item_code}_A{attack_group}_C{critical_group}"
    else:
        value_group = round(item['main_value'] / 5) * 5
        return f"{item_code}_V{value_group}"

# ========== واجهة المستخدم ==========
st.title("🎯 War Era - Market Analyzer")
st.markdown("تحليل متقدم لسوق **الطيارات، الدبابات، والمعدات النادرة**")

# ========== Auto Refresh مع Checkbox ==========
with st.sidebar:
    st.header("⚙️ إعدادات التحليل")
    
    # Auto Refresh
    auto_refresh = st.checkbox("🔄 تحديث تلقائي كل دقيقة", value=False)
    if auto_refresh:
        st_autorefresh = __import__('streamlit_autorefresh').st_autorefresh
        st_autorefresh(interval=60000, limit=100, key="auto_refresh")
    
    item_category = st.selectbox("📦 اختر نوع المعدات:", list(ITEM_CATEGORIES.keys()))
    
    max_pages = st.slider("عدد صفحات الجلب", 1, 10, 5, help="كل صفحة = 50 عنصر")
    min_quality = st.slider("الحد الأدنى للجودة (%)", 0, 100, 0)
    max_price = st.number_input("الحد الأقصى للسعر", 0, 10000, 5000, step=100)

    st.divider()
    st.header("⏰ فلتر الوقت")
    
    time_filter = st.selectbox(
        "عرض العروض من آخر:",
        ["الكل", "آخر ساعة", "آخر 6 ساعات", "آخر 12 ساعة", "آخر 24 ساعة", "آخر 3 أيام", "آخر أسبوع"]
    )
    
    time_map = {
        "الكل": 0,
        "آخر ساعة": 1,
        "آخر 6 ساعات": 6,
        "آخر 12 ساعة": 12,
        "آخر 24 ساعة": 24,
        "آخر 3 أيام": 72,
        "آخر أسبوع": 168
    }
    hours_limit = time_map[time_filter]
    st.divider()
    
    sort_by = st.selectbox("ترتيب حسب", 
                          ["القيمة مقابل السعر", "الجودة", "السعر (أقل سعر أولاً)", "السعر (أعلى سعر أولاً)", "الأحدث"])
    
    if st.button("🔄 تحديث البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# جلب البيانات
category_config = ITEM_CATEGORIES[item_category]
item_code = category_config["code"]

with st.spinner(f"جاري تحليل {item_category}..."):
    raw_items = fetch_all_items(item_code, max_pages=max_pages)

if not raw_items:
    st.error("❌ لا توجد عروض حالياً")
    st.stop()

# معالجة البيانات
all_items = []
for item in raw_items:
    quality = calculate_quality_score(item['skills'], category_config)
    main_value = get_main_value(item['skills'], category_config)
    secondary_value = get_secondary_value(item['skills'], category_config)
    main_name = get_main_name(category_config)
    secondary_name = get_secondary_name(category_config)
    value_for_money = (quality / item['price']) * 1000 if item['price'] > 0 else 0
    
    all_items.append({
        'id': item['id'],
        'price': item['price'],
        'user': item['user'],
        'main_value': main_value,
        'secondary_value': secondary_value,
        'main_name': main_name,
        'secondary_name': secondary_name,
        'quality_score': quality,
        'value_for_money': value_for_money,
        'createdAt': item['createdAt'],
        'time_ago': item['time_ago'],
        'attack': item['attack'],
        'critical': item['critical']
    })

df = pd.DataFrame(all_items)
df_filtered = df[(df['quality_score'] >= min_quality) & (df['price'] <= max_price)]

    # تطبيق فلتر الوقت
if hours_limit > 0:
        now = datetime.now().astimezone()
        df_filtered = df_filtered[
            df_filtered['createdAt'].apply(lambda x: 
                (now - datetime.fromisoformat(x.replace('Z', '+00:00'))).total_seconds() / 3600 <= hours_limit
            )
        ]

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

# إحصائيات sidebar
with st.sidebar:
    st.divider()
    st.header("📊 إحصائيات سريعة")
    st.metric("إجمالي العناصر", len(df_filtered))
    if len(df_filtered) > 0:
        st.metric("أقل سعر", f"${df_filtered['price'].min():,.2f}")
        st.metric("أعلى جودة", f"{df_filtered['quality_score'].max():.1f}%")
        st.metric("متوسط السعر", f"${df_filtered['price'].mean():,.2f}")
    
    st.divider()
    st.caption(f"📏 **رينج القيم:** {get_range_text(category_config)}")

# ========== تبويبات ==========
tab1, tab2, tab3 = st.tabs(["📋 جدول الطائرات", "🏆 أفضل الصفقات", "📊 تحليل الأسعار التاريخي"])

# TAB 1: جدول الطائرات
with tab1:
    st.subheader(f"📋 عرض {len(df_sorted)} عنصر")
    st.caption(f"📏 {get_range_text(category_config)}")
    
    if category_config["type"] in ["jet", "tank"]:
        display_df = df_sorted[['price', 'main_value', 'secondary_value', 'quality_score', 'value_for_money', 'user', 'time_ago']].copy()
        display_df.columns = ['السعر', main_name, f'{secondary_name}%', 'الجودة%', 'القيمة/السعر', 'البائع', 'منذ']
    else:
        display_df = df_sorted[['price', 'main_value', 'quality_score', 'value_for_money', 'user', 'time_ago']].copy()
        display_df.columns = ['السعر', main_name, 'الجودة%', 'القيمة/السعر', 'البائع', 'منذ']
    
    st.data_editor(
        display_df,
        column_config={
            "السعر": st.column_config.NumberColumn("💰 السعر", format="$ %.2f"),
            "الجودة%": st.column_config.ProgressColumn("الجودة%", format="%.1f %%", min_value=0, max_value=100),
        },
        use_container_width=True,
        height=500,
        hide_index=True,
        disabled=True
    )

# TAB 2: أفضل الصفقات
with tab2:
    st.subheader("🏆 أفضل 10 صفقات (أعلى قيمة مقابل السعر)")
    
    best_value = df_sorted.nlargest(10, 'value_for_money')
    
    for i, row in best_value.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{i+1}. 💰 السعر: ${row['price']:,.2f}** (منذ {row['time_ago']})")
                if row['secondary_name']:
                    st.write(f"   {row['main_name']}: {row['main_value']} | {row['secondary_name']}: {row['secondary_value']}%")
                else:
                    st.write(f"   {row['main_name']}: {row['main_value']}")
            with col2:
                st.metric("الجودة", f"{row['quality_score']}%")
                st.metric("القيمة", f"{row['value_for_money']:.2f}")
            st.caption(f"👤 البائع: {row['user']}")

# TAB 3: تحليل الأسعار التاريخي (بتاعك الأصلي)
with tab3:
    st.subheader("📊 تحليل الأسعار التاريخي")
    
    # تحميل التاريخ
    price_history = load_price_history()
    alerts_history = load_alerts_history()
    
    # اختيار عنصر للتحليل
    temp_df = df_sorted.head(30).copy()
    temp_df['display'] = temp_df.apply(
        lambda x: f"[{item_category}] 💰 ${x['price']} | {x['main_name']}: {x['main_value']} | 👤 {x['user']}", 
        axis=1
    )
    
    selected_display = st.selectbox(
        "اختر عنصر لتحليل تاريخ أسعاره:",
        options=temp_df['display'].tolist()
    )
    
    if selected_display:
        selected_item = temp_df[temp_df['display'] == selected_display].iloc[0]
        
        # استخدام التصنيف الجديد
        item_category_key = categorize_item(selected_item, category_config)
        current_price = selected_item['price']
        current_time = datetime.now().isoformat()
        
        # تسجيل السعر الحالي
        if item_category_key not in price_history:
            price_history[item_category_key] = []
        
        # تجنب التكرار
        is_duplicate = False
        for record in price_history[item_category_key][-5:]:
            if record.get('user') == selected_item['user'] and record['price'] == current_price:
                is_duplicate = True
                break
        
        if not is_duplicate:
            price_history[item_category_key].append({
                'price': current_price,
                'time': current_time,
                'user': selected_item['user'],
                'main_value': selected_item['main_value'],
                'secondary_value': selected_item['secondary_value']
            })
            price_history[item_category_key] = price_history[item_category_key][-50:]
            save_price_history(price_history)
        
        # عرض الإحصائيات
        history = price_history[item_category_key]
        prices = [h['price'] for h in history]
        
        min_price_hist = min(prices)
        max_price_hist = max(prices)
        avg_price_hist = sum(prices) / len(prices)
        
        st.info(f"📌 **تحليل لـ: {item_category}**")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 السعر الحالي", f"${current_price:.2f}")
        with col2:
            delta = ((current_price - min_price_hist) / min_price_hist * 100) if current_price > min_price_hist else 0
            st.metric("📉 أقل سعر", f"${min_price_hist:.2f}", delta=f"-{delta:.1f}%" if delta > 0 else "أقل سعر!")
        with col3:
            st.metric("📈 أعلى سعر", f"${max_price_hist:.2f}")
        with col4:
            st.metric("📊 المتوسط", f"${avg_price_hist:.0f}")
        
        # تقييم الصفقة
        st.subheader("🎯 تقييم الصفقة")
        if current_price <= min_price_hist * 1.05:
            st.success("✅ **صفقة ممتازة!** هذا أقل سعر أو قريب جداً")
        elif current_price <= avg_price_hist:
            st.info("👍 **صفقة جيدة** - السعر أقل من المتوسط")
        elif current_price <= max_price_hist * 0.8:
            st.warning("⚠️ **سعر متوسط** - ممكن تلاقي أحسن")
        else:
            st.error("❌ **سعر مرتفع** - الأفضل تستنى")
        
        # رسم بياني
        st.subheader("📈 تطور الأسعار")
        history_df = pd.DataFrame(sorted(history, key=lambda x: x['time']))
        history_df['time_dt'] = pd.to_datetime(history_df['time'])
        
        fig_history = px.line(
            history_df, 
            x='time_dt', 
            y='price',
            title=f'تاريخ أسعار {item_category}',
            markers=True
        )
        fig_history.add_hline(y=current_price, line_dash="dash", line_color="red", annotation_text="السعر الحالي")
        fig_history.add_hline(y=min_price_hist, line_dash="dash", line_color="green", annotation_text="أقل سعر")
        fig_history.update_layout(template='plotly_dark')
        st.plotly_chart(fig_history, use_container_width=True)
        
        # آخر 10 أسعار
        with st.expander("📜 آخر 10 أسعار شوهدت"):
            for h in sorted(history, key=lambda x: x['time'], reverse=True)[:10]:
                time_ago_str = time_ago(h['time'])
                emoji = "🟢" if h['price'] <= min_price_hist * 1.05 else "🟡" if h['price'] <= avg_price_hist else "🔴"
                st.write(f"{emoji} ${h['price']:.2f} - منذ {time_ago_str} - البائع: {h['user']}")
                
# التوصية النهائية
st.divider()
st.subheader("🎯 التوصية النهائية")

good_deals = df_filtered[df_filtered['quality_score'] >= 60]
if len(good_deals) > 0:
    best = good_deals.loc[good_deals['value_for_money'].idxmax()]
    st.success(f"""
    ✅ **أفضل صفقة حالياً (جودة عالية + سعر مناسب):**
    - 💰 سعر الشراء: ${best['price']:,.2f} (منذ {best['time_ago']})
    - 📊 جودة العنصر: {best['quality_score']}%
    - {best['main_name']}: {best['main_value']}
    - 👤 البائع: {best['user']}
    """)
else:
    st.warning("⚠️ لا توجد عناصر بجودة عالية حالياً (جودة ≥ 60%)")