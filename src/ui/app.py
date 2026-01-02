import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import sys
from pathlib import Path
import os
import shutil
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add root to sys.path
root_path = Path(__file__).parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from src.db import connect
from src.assistant import answer_from_rag, answer_from_reports, is_report_question
from src.ingest_pdf import ingest_one
from src.analysis import get_subscriptions, check_budget_alerts

# --- Page Config ---
st.set_page_config(
    page_title="SpendRAG: Akıllı Harcama Asistanı",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    /* Global Settings */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main Background */
    .stApp {
        background: radial-gradient(circle at top left, #f8f9fa, #e9ecef);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #eef2f6;
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }
    
    /* Card-like Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
        border: 1px solid #f3f6f9;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
        border-color: #e0e7ff;
    }
    
    /* Metric Label */
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 500;
    }
    
    /* Metric Value */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #1e293b;
        font-weight: 700;
    }

    /* Headers */
    h1 {
        color: #0f172a;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    h2, h3 {
        color: #334155;
        font-weight: 700;
    }
    
    /* Chat Messages */
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 12px;
        padding: 16px;
        border: 1px solid #f1f5f9;
    }
    
    /* Button Styling */
    .stButton button {
        background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(79, 70, 229, 0.3);
    }
    
    /* Data Editor */
    div[data-testid="stDataEditor"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# --- Validations & State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Welcome message
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Merhaba! Ben harcama asistanın. Fişlerinle ilgili ne bilmek istersin? (Örn: 'Geçen ay ne kadar harcadım?')"
    })

DB_PATH = Path("data/spendrag.sqlite")
INBOX_DIR = Path("data/inbox")
INBOX_DIR.mkdir(parents=True, exist_ok=True)

# --- LLM Ön Yükleme (İlk Soru Hızlı Olsun) ---
@st.cache_resource
def preload_llm():
    """LLM modelini önceden yükle (ilk soru için bekleme süresini azaltır)"""
    try:
        from src.assistant import get_llm
        with st.spinner("🤖 AI modeli yükleniyor... (İlk açılışta 10-20 saniye sürebilir)"):
            llm = get_llm()
        return llm
    except Exception as e:
        st.warning(f"⚠️ Model yükleme hatası: {e}")
        return None

# Model ön yükleme
preload_llm()

# --- Auto Ingest Watcher ---
class NewPdfHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pdf"):
            time.sleep(1)
            try:
                conn = connect()
                ingest_one(conn, Path(event.src_path))
                conn.commit()
                conn.close()
                print("Auto-ingested successfully.")
            except Exception as e:
                print(f"Auto-ingest failed: {e}")

@st.cache_resource
def start_watcher():
    path = str(INBOX_DIR)
    handler = NewPdfHandler()
    obs = Observer()
    obs.schedule(handler, path, recursive=False)
    obs.start()
    return obs

start_watcher()

# --- Helper Functions ---
def load_data():
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = connect()
    query = """
    SELECT r.receipt_date, r.merchant, i.name_raw, i.name_norm, i.category, i.qty, i.amount
    FROM items i JOIN receipts r ON r.id = i.receipt_id
    WHERE r.receipt_date IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    if not df.empty:
        df["month"] = df["receipt_date"].astype(str).str.slice(0, 7)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    return df

def save_uploaded_file(uploaded_file):
    try:
        file_path = INBOX_DIR / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #4338ca;'>💸 SpendRAG</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.9em;'>Akıllı Harcama Asistanınız</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    selected_page = st.radio(
        "Menü",
        [
            "💬 Sohbet Asistanı",
            "📊 Finansal Özet",
            "💰 Bütçe Yönetimi",
            "🔔 Uyarılar & Analizler",
            "📝 Veri İnceleme",
            "📤 Fiş Yükle"
        ],
        index=0
    )
    
    st.markdown("---")
    
    # Kapsamlı Bilgi Paneli
    conn = connect()
    result = conn.execute("SELECT COUNT(*) FROM receipts").fetchone()
    total_receipts = result[0] if result else 0
    conn.close()
    
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric("Fişler", total_receipts)
    col_stat2.metric("Durum", "Aktif", delta_color="normal")
    
    st.caption("Auto-ingest devrede 🟢")

# --- Pages ---

if selected_page == "💬 Sohbet Asistanı":
    st.title("💡 Akıllı Harcama Asistanı")
    st.caption("Verileriniz üzerinden doğal dille sorgulama yapın.")
    
    for msg in st.session_state.messages:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Harcamalarınla ilgili sor..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
            
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🧠 Düşünüyorum... (7B model, 10-30 saniye sürebilir)"):
                try:
                    if is_report_question(prompt) and (Path("data/reports/monthly_total.csv").exists()):
                        response = answer_from_reports(prompt)
                    else:
                        response = answer_from_rag(prompt)
                except Exception as e:
                    response = f"Bir hata oluştu: {e}"
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

elif selected_page == "📊 Finansal Özet":
    st.title("📊 Finansal Genel Bakış")
    df = load_data()
    
    if df.empty:
        st.info("Henüz görüntülenecek veri yok. Lütfen önce fiş yükleyin.")
    else:
        # Top Metrics Row
        total_spent = df["amount"].sum()
        unique_merchants = df["merchant"].nunique()
        top_category_name = df.groupby("category")["amount"].sum().idxmax()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Harcama", f"{total_spent:,.2f} ₺")
        m2.metric("Farklı İşyeri", unique_merchants)
        m3.metric("En Çok Harcanan", top_category_name)
        
        st.markdown("---")
        
        # Charts Row
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("🗓️ Aylık Harcama Trendi")
            monthly = df.groupby("month")["amount"].sum().reset_index()
            fig_line = px.area(monthly, x="month", y="amount", markers=True, color_discrete_sequence=["#4e73df"])
            fig_line.update_layout(xaxis_title="Ay", yaxis_title="Tutar (TRY)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_line, use_container_width=True)
            
        with c2:
            st.subheader("🛍️ Kategori Dağılımı")
            cat_data = df.groupby("category")["amount"].sum().reset_index()
            fig_pie = px.pie(cat_data, names="category", values="amount", hole=0.5)
            fig_pie.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

        # Smart Insights Section
        st.markdown("### 🧠 Akıllı Analizler")
        
        # Import new modules
        try:
            from src.analytics.subscriptions import get_subscription_tracker
            from src.analytics.anomaly import get_anomaly_detector
            
            # Subscriptions & Anomalies
            col_analysis1, col_analysis2 = st.columns(2)
            
            with col_analysis1:
                st.info("📅 **Abonelikler & Tekrarlayan Ödemeler**")
                tracker = get_subscription_tracker()
                subs = tracker.detect_subscriptions(min_occurrences=2)
                
                if subs:
                    for sub in subs[:5]:  # İlk 5 abonelik
                        with st.expander(f"💳 {sub['merchant']} - {sub['amount']:.2f} TL/{sub['period_tr']}"):
                            st.write(f"**Ürün**: {sub['name']}")
                            st.write(f"**Toplam Ödeme**: {sub['frequency_months']} kez")
                            st.write(f"**Yıllık Maliyet**: ~{sub['annual_cost']:.2f} TL")
                            st.write(f"**Son Ödeme**: {sub['last_payment']}")
                            if sub['days_until_next'] >= 0:
                                st.write(f"**Sonraki Ödeme**: {sub['next_payment']} ({sub['days_until_next']} gün sonra)")
                else:
                    st.write("Henüz abonelik tespit edilemedi.")
                    
            with col_analysis2:
                st.warning("🔍 **Anormal Harcamalar**")
                detector = get_anomaly_detector()
                anomalies = detector.detect_anomalies(days=30)
                
                if anomalies:
                    # Sadece yüksek önem dereceli anormallikleri göster
                    high_severity = [a for a in anomalies if a['severity'] == 'high'][:3]
                    for anomaly in high_severity:
                        st.error(f"{anomaly['message']}")
                    
                    if len(anomalies) > len(high_severity):
                        st.caption(f"+ {len(anomalies) - len(high_severity)} diğer anormallik tespit edildi")
                else:
                    st.success("✅ Anormal harcama tespit edilmedi")
                    
        except Exception as e:
            st.error(f"Analiz modülleri yüklenemedi: {e}")
            
            # Fallback to old analysis
            conn = connect()
            col_analysis1, col_analysis2 = st.columns(2)
            
            with col_analysis1:
                st.info("📅 **Düzenli Ödemeler (Abonelikler)**")
                subs_df = get_subscriptions(conn)
                if not subs_df.empty:
                    st.dataframe(subs_df[["merchant", "estimated_cost", "frequency_months"]], hide_index=True)
                else:
                    st.write("Henüz düzenli abonelik tespit edilemedi.")
                    
            with col_analysis2:
                st.success("💰 **Bütçe Durumu**")
                alerts = check_budget_alerts(conn)
                for al in alerts:
                    if al["type"] == "warning":
                        st.warning(f"⚠️ {al['msg']}")
                    else:
                        st.write(f"✅ {al['msg']}")
            conn.close()

elif selected_page == "💰 Bütçe Yönetimi":
    st.title("💰 Bütçe Yönetimi")
    st.caption("Kategori bazlı bütçe belirleyin ve harcamalarınızı takip edin")
    
    try:
        from src.analytics.budget import get_budget_manager
        
        budget_mgr = get_budget_manager()
        
        # Bütçe oluşturma formu
        with st.expander("➕ Yeni Bütçe Oluştur", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                category = st.selectbox("Kategori", ["Gida", "Temizlik", "Giyim", "Elektronik", "Restoran", "Diger"])
            with col2:
                limit_amount = st.number_input("Limit (TL)", min_value=0.0, value=1000.0, step=100.0)
            with col3:
                period = st.selectbox("Dönem", ["monthly", "weekly"])
            
            if st.button("💾 Bütçe Oluştur", type="primary"):
                budget_id = budget_mgr.create_budget(category, limit_amount, period)
                st.success(f"✅ {category} için {limit_amount:.2f} TL bütçe oluşturuldu!")
                st.rerun()
        
        # Aktif bütçeler
        st.markdown("### 📊 Aktif Bütçeler")
        budgets = budget_mgr.get_active_budgets()
        
        if budgets:
            for budget in budgets:
                usage_pct = budget["usage_percent"]
                
                # Renk belirleme
                if usage_pct >= 100:
                    color = "🔴"
                    status = "danger"
                elif usage_pct >= 80:
                    color = "🟡"
                    status = "warning"
                else:
                    color = "🟢"
                    status = "success"
                
                with st.container():
                    col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
                    
                    with col_b1:
                        st.markdown(f"### {color} {budget['category']}")
                        st.progress(min(usage_pct / 100, 1.0))
                        st.caption(f"{budget['spent_amount']:.2f} TL / {budget['limit_amount']:.2f} TL ({usage_pct:.1f}%)")
                    
                    with col_b2:
                        st.metric("Kalan", f"{budget['remaining']:.2f} TL", 
                                 delta=f"-{budget['spent_amount']:.2f} TL" if budget['spent_amount'] > 0 else "0 TL",
                                 delta_color="inverse")
                    
                    with col_b3:
                        st.caption(f"Dönem: {budget['period']}")
                        st.caption(f"{budget['start_date']} - {budget['end_date']}")
                        if st.button("🗑️ Sil", key=f"del_{budget['id']}"):
                            budget_mgr.delete_budget(budget['id'])
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("Henüz bütçe oluşturulmamış. Yukarıdan yeni bütçe ekleyin.")
        
        # Uyarılar
        st.markdown("### 🔔 Bütçe Uyarıları")
        alerts = budget_mgr.check_alerts()
        
        if alerts:
            for alert in alerts:
                if alert['type'] == 'critical':
                    st.error(alert['message'])
                elif alert['type'] == 'exceeded':
                    st.warning(alert['message'])
                else:
                    st.info(alert['message'])
        else:
            st.success("✅ Tüm bütçeler kontrol altında!")
            
    except Exception as e:
        st.error(f"Bütçe modülü yüklenemedi: {e}")
        st.info("Bütçe yönetimi özelliği şu an kullanılamıyor.")

elif selected_page == "🔔 Uyarılar & Analizler":
    st.title("🔔 Uyarılar & Detaylı Analizler")
    
    try:
        from src.analytics.anomaly import get_anomaly_detector
        from src.analytics.subscriptions import get_subscription_tracker
        from src.analytics.budget import get_budget_manager
        
        # Anomali Tespiti
        st.markdown("## 🔍 Anormal Harcamalar")
        detector = get_anomaly_detector()
        anomalies = detector.detect_anomalies(days=60)
        
        if anomalies:
            # Kategoriye göre grupla
            by_category = {}
            for a in anomalies:
                cat = a['category']
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(a)
            
            for category, items in by_category.items():
                with st.expander(f"📦 {category} ({len(items)} anormallik)", expanded=True):
                    for anomaly in items[:5]:  # İlk 5
                        severity_icon = "🔴" if anomaly['severity'] == 'high' else "🟡"
                        st.write(f"{severity_icon} {anomaly['message']}")
                        st.caption(f"Tarih: {anomaly['date']} | Market: {anomaly['merchant']}")
        else:
            st.success("✅ Son 60 günde anormal harcama tespit edilmedi")
        
        st.markdown("---")
        
        # Abonelik Detayları
        st.markdown("## 💳 Abonelik Analizi")
        tracker = get_subscription_tracker()
        subs = tracker.detect_subscriptions(min_occurrences=2)
        
        if subs:
            total_monthly = sum(s['amount'] for s in subs if s['period'] == 'monthly')
            total_annual = sum(s['annual_cost'] for s in subs)
            
            col_sub1, col_sub2, col_sub3 = st.columns(3)
            col_sub1.metric("Toplam Abonelik", len(subs))
            col_sub2.metric("Aylık Toplam", f"{total_monthly:.2f} TL")
            col_sub3.metric("Yıllık Tahmini", f"{total_annual:.2f} TL")
            
            st.markdown("### Detaylar")
            for sub in subs:
                with st.expander(f"💳 {sub['merchant']} - {sub['name']}"):
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        st.write(f"**Tutar**: {sub['amount']:.2f} TL")
                        st.write(f"**Periyot**: {sub['period_tr']}")
                        st.write(f"**Toplam Ödeme**: {sub['frequency_months']} kez")
                    with col_s2:
                        st.write(f"**Son Ödeme**: {sub['last_payment']}")
                        st.write(f"**Sonraki Ödeme**: {sub['next_payment']}")
                        st.write(f"**Yıllık Maliyet**: {sub['annual_cost']:.2f} TL")
        else:
            st.info("Henüz abonelik tespit edilemedi")
        
        st.markdown("---")
        
        # Yaklaşan Ödemeler
        st.markdown("## ⏰ Yaklaşan Ödemeler (7 Gün)")
        upcoming = tracker.get_upcoming_payments(days=7)
        
        if upcoming:
            for payment in upcoming:
                days = payment['days_until_next']
                if days == 0:
                    st.error(f"🔴 BUGÜN: {payment['merchant']} - {payment['amount']:.2f} TL")
                elif days <= 3:
                    st.warning(f"🟡 {days} gün sonra: {payment['merchant']} - {payment['amount']:.2f} TL")
                else:
                    st.info(f"🔵 {days} gün sonra: {payment['merchant']} - {payment['amount']:.2f} TL")
        else:
            st.success("✅ Önümüzdeki 7 günde yaklaşan ödeme yok")
            
    except Exception as e:
        st.error(f"Analiz modülleri yüklenemedi: {e}")

elif selected_page == "📝 Veri İnceleme":
    st.caption("LLM tarafından çıkarılan verileri filtreleyin, kontrol edin ve düzeltin.")
    
    # --- Filters ---
    st.markdown("### 🔍 Filtreler")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        date_range = st.date_input("Tarih Aralığı", [])
    
    with col_f2:
        cat_filter = st.selectbox("Kategori Seç", ["Tümü", "Gida", "Temizlik", "Giyim", "Elektronik", "Restoran", "Diger"])
        
    with col_f3:
        search_txt = st.text_input("Market/Ürün Ara", placeholder="Örn: Migros, Süt...")
        
    # Build Query with JOIN
    base_query = """
        SELECT 
            i.id, 
            r.receipt_date, 
            r.merchant, 
            i.name_norm, 
            i.category, 
            i.amount, 
            i.qty, 
            i.unit 
        FROM items i
        LEFT JOIN receipts r ON i.receipt_id = r.id
        WHERE 1=1
    """
    params = []
    
    if len(date_range) == 2:
        base_query += " AND r.receipt_date BETWEEN ? AND ?"
        params.extend([str(date_range[0]), str(date_range[1])])
        
    if cat_filter != "Tümü":
        base_query += " AND i.category = ?"
        params.append(cat_filter)
        
    if search_txt:
        base_query += " AND (r.merchant LIKE ? OR i.name_norm LIKE ?)"
        term = f"%{search_txt}%"
        params.extend([term, term])
        
    base_query += " ORDER BY r.receipt_date DESC LIMIT 200"
    
    conn = connect()
    df_items = pd.read_sql_query(base_query, conn, params=params)
    
    edited_df = st.data_editor(
        df_items,
        column_config={
            "id": st.column_config.TextColumn(disabled=True),
            "receipt_date": st.column_config.TextColumn("Tarih", disabled=True),
            "merchant": st.column_config.TextColumn("İşyeri", disabled=True),
            "name_norm": st.column_config.TextColumn("Ürün Adı"),
            "amount": st.column_config.NumberColumn("Tutar", format="%.2f ₺"),
            "category": st.column_config.SelectboxColumn("Kategori", options=["Gida", "Temizlik", "Giyim", "Elektronik", "Restoran", "Diger"]),
            "qty": st.column_config.NumberColumn("Adet"),
            "unit": st.column_config.TextColumn("Birim"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="data_editor"
    )
    
    if st.button("💾 Değişiklikleri Kaydet", type="primary"):
        cursor = conn.cursor()
        try:
            # Basit update döngüsü
            for index, row in edited_df.iterrows():
                # receipt_date ve merchant aslında receipts tablosunda ama burada basitleştirilmiş view kullanıyoruz.
                # items tablosunda receipt_id var. Gerçekte receipts'i update etmek gerekir.
                # Ancak kullanıcı deneyimi için şimdilik sadece items tablosundaki alanları (name_norm, category, amount...) güncelleyelim.
                # Eğer tarih/merchant değişecekse JOIN update gerekir, bu basit yapıda items üzerinden gidiyoruz.
                cursor.execute("""
                    UPDATE items 
                    SET name_norm=?, category=?, amount=?, qty=?, unit=?
                    WHERE id=?
                """, (row["name_norm"], row["category"], row["amount"], row["qty"], row["unit"], row["id"]))
                
                # Eğer tarih değişikliği isteniyorsa receipts tablosuna gitmeliyiz (İLERİ SEVİYE)
                # Şimdilik pas geçiyoruz.
            conn.commit()
            st.success("Tüm değişiklikler veritabanına işlendi!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")
            
    conn.close()

elif selected_page == "📤 Fiş Yükle":
    st.title("📤 Fiş Yükleme Merkezi")
    st.markdown("""
    Buradan PDF formatındaki fişlerinizi yükleyebilirsiniz. 
    İsterseniz dosyaları doğrudan `data/inbox` klasörüne de atabilirsiniz, sistem otomatik algılar.
    """)
    
    uploaded_files = st.file_uploader("PDF Dosyalarını Sürükleyin", accept_multiple_files=True, type=["pdf"])
    
    if st.button("🚀 İşlemi Başlat", type="primary"):
        if not uploaded_files:
            st.warning("Lütfen önce dosya seçin.")
        else:
            bar = st.progress(0)
            conn = connect()
            count = 0
            skipped = 0
            for i, f in enumerate(uploaded_files):
                path = save_uploaded_file(f)
                if path:
                    result = ingest_one(conn, path)
                    if result:
                        count += 1
                    else:
                        skipped += 1
                bar.progress((i + 1) / len(uploaded_files))
            conn.commit()
            conn.close()
            
            if count > 0:
                st.success(f"✅ {count} adet yeni fiş başarıyla işlendi!")
            if skipped > 0:
                st.info(f"ℹ️ {skipped} adet fiş zaten sistemde mevcut (atlandı).")
            if count == 0 and skipped == 0:
                st.warning("⚠️ Hiçbir fiş işlenemedi. Lütfen dosyaları kontrol edin.")
