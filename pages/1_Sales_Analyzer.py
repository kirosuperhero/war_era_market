import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime

st.set_page_config(page_title="Sales Analyzer", layout="wide")
st.title("📊 تحليل المبيعات الفعلية")

SALES_CACHE_FILE = "data/sales_cache.json"

def get_secret(key, default):
    try:
        return st.secrets[key]
    except:
        return default

YOUR_JWT = get_secret("YOUR_JWT", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7Il9pZCI6IjY5Y2VlY2Y1MTk3Zjg0NWZjOWZlZGU1YyJ9LCJpYXQiOjE3NzUxNjg3NTcsImV4cCI6MTc3Nzc2MDc1N30.nIKi8ohQAYsAVXQL9_rlRUr93TDg-G-DVOCQOrRdOtY")

ITEM_TYPE_SKILL = {
    "jet":     ("jet",     "attack",         "criticalChance"),
    "tank":    ("tank",    "attack",         "criticalChance"),
    "boots5":  ("dodge",   "dodge",          None),
    "boots6":  ("dodge",   "dodge",          None),
    "chest5":  ("armor",   "armor",          None),
    "chest6":  ("armor",   "armor",          None),
    "gloves5": ("precision","precision",     None),
    "gloves6": ("precision","precision",     None),
    "pants5":  ("armor",   "armor",          None),
    "pants6":  ("armor",   "armor",          None),
    "helmet5": ("criticalDamages","criticalDamages", None),
    "helmet6": ("criticalDamages","criticalDamages", None),
}

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

def load_cache():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(SALES_CACHE_FILE):
        return {}
    try:
        with open(SALES_CACHE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except:
        return {}

def save_cache(cache):
    os.makedirs("data", exist_ok=True)
    with open(SALES_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def process_and_save(item_code, transactions):
    """يضيف المبيعات الجديدة للـ cache بدون حذف القديمة."""
    cache = load_cache()
    if item_code not in cache:
        cache[item_code] = []

    existing_ids = {(s.get('time'), s.get('price')) for s in cache[item_code]}
    _, main_skill, secondary_skill = ITEM_TYPE_SKILL.get(item_code, (None, 'attack', None))
    added = 0

    for tx in transactions:
        item_info = tx.get('item', {})
        skills    = item_info.get('skills', {})
        tx_time   = tx.get('createdAt')
        tx_price  = tx.get('money')

        if (tx_time, tx_price) in existing_ids:
            continue

        main_value      = skills.get(main_skill, 0) if main_skill else 0
        secondary_value = skills.get(secondary_skill, 0) if secondary_skill else 0

        cache[item_code].append({
            'price':           tx_price,
            'time':            tx_time,
            'main_value':      main_value,
            'secondary_value': secondary_value
        })
        existing_ids.add((tx_time, tx_price))
        added += 1

    # الاحتفاظ بآخر 500 سجل
    cache[item_code] = sorted(cache[item_code], key=lambda x: x.get('time', ''), reverse=True)[:500]
    save_cache(cache)
    return added

# ========== الواجهة ==========
item_type = st.selectbox("اختر نوع العنصر:", list(ITEM_TYPE_SKILL.keys()))

col_btn1, col_btn2 = st.columns([1, 3])
with col_btn1:
    fetch_clicked = st.button("📥 جلب المبيعات", type="primary")

if fetch_clicked:
    with st.spinner("جاري جلب البيانات..."):
        transactions = fetch_transactions(item_type, limit=100)

    if transactions:
        # --- عرض البيانات ---
        sales_data = []
        for tx in transactions:
            item_info = tx.get('item', {})
            skills    = item_info.get('skills', {})
            sales_data.append({
                'السعر':      tx.get('money'),
                'الوقت':      tx.get('createdAt'),
                'الهجوم':     skills.get('attack', 0),
                'الكريتيكال': skills.get('criticalChance', 0),
                'الدفاع':     skills.get('armor', 0),
                'المراوغة':   skills.get('dodge', 0),
                'الدقة':      skills.get('precision', 0),
                'الضرر الحاسم': skills.get('criticalDamages', 0)
            })

        df = pd.DataFrame(sales_data)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("عدد المبيعات", len(df))
        with col2:
            st.metric("متوسط السعر", f"${df['السعر'].mean():.2f}")
        with col3:
            st.metric("أقل / أعلى سعر", f"${df['السعر'].min():.2f} / ${df['السعر'].max():.2f}")

        st.subheader("آخر المبيعات")
        st.dataframe(df.head(20), use_container_width=True)

        df['الوقت'] = pd.to_datetime(df['الوقت'])
        fig = px.line(df.sort_values('الوقت'), x='الوقت', y='السعر',
                      title=f'تطور أسعار {item_type}', markers=True)
        fig.update_layout(template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)

        # --- حفظ في الـ cache (Append, لا Overwrite) ---
        added = process_and_save(item_type, transactions)
        st.success(f"✅ تم حفظ البيانات — {added} سجل جديد أُضيف للـ cache")
    else:
        st.warning("لا توجد مبيعات مسجلة")

st.divider()
st.caption(
    "💡 **ملاحظة:** بيانات المبيعات تُجمَّع تلقائياً كل ساعة من الصفحة الرئيسية. "
    "هذه الصفحة مفيدة للجلب اليدوي أو للتحقق السريع من المبيعات."
)

# --- عرض إحصائيات الـ cache الحالي ---
with st.expander("📊 إحصائيات الـ cache الحالي"):
    cache = load_cache()
    if cache:
        rows = []
        for code, records in cache.items():
            rows.append({
                'النوع': code,
                'عدد السجلات': len(records),
                'أحدث سجل': records[0].get('time', '—')[:16] if records else '—'
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("الـ cache فارغ حتى الآن.")
