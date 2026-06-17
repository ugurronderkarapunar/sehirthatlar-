import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Vapur Hattı Analiz Dashboard", 
    layout="wide",
    page_icon="🚢",
    initial_sidebar_state="expanded"
)

# ------------------------------
# SİDEBAR - FİLTRELER
# ------------------------------
st.sidebar.title("⚙️ Filtreler")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader(
    "📂 Excel dosyasını yükleyin", 
    type=["xlsx"],
    help="20260506_2_REV5.xlsx dosyasını yükleyin"
)

if uploaded_file is None:
    st.warning("Lütfen Excel dosyasını yükleyin.")
    st.stop()

# ------------------------------
# VERİYİ OKU
# ------------------------------
@st.cache_data
def load_data(file):
    df = pd.read_excel(file, sheet_name='Sayfa2')
    df.columns = df.columns.str.strip()
    df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(
        df['MERKEZDEN GEMİYE BİNİŞ'], format='mixed', errors='coerce'
    )
    df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])
    df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
    df['Saat_Dilimi'] = df['Saat'].apply(lambda x: f"{x:02d}:00–{x:02d}:59")
    df['YÖN'] = df['YÖN'].str.strip()
    df['Tarih'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.date
    return df

df = load_data(uploaded_file)

# Sidebar filtreler
st.sidebar.markdown("### 📍 Yön Seçimi")
yon_filter = st.sidebar.selectbox(
    "Yön", 
    options=['Tümü', 'ÜSKÜDAR → BEŞİKTAŞ', 'BEŞİKTAŞ → ÜSKÜDAR'],
    index=0
)

st.sidebar.markdown("### ⏰ Saat Aralığı")
saat_min, saat_max = st.sidebar.slider(
    "Saat aralığı seçin",
    min_value=0, max_value=23, value=(0, 23)
)

st.sidebar.markdown("### 🎯 Hedef Filtre")
hedef_list = df[df['İNDİKTEN SONRA NEREYE GİTTİ'].notna()]['İNDİKTEN SONRA NEREYE GİTTİ'].unique()
hedef_list = [h for h in hedef_list if h not in ['', 'BİLİNMİYOR']]
hedef_filter = st.sidebar.multiselect(
    "Gidilen Yerler",
    options=sorted(hedef_list),
    default=[]
)

# Filtreleme
df_filtered = df.copy()
if yon_filter != 'Tümü':
    df_filtered = df_filtered[df_filtered['YÖN'] == yon_filter]
df_filtered = df_filtered[(df_filtered['Saat'] >= saat_min) & (df_filtered['Saat'] <= saat_max)]
if hedef_filter:
    df_filtered = df_filtered[df_filtered['İNDİKTEN SONRA NEREYE GİTTİ'].isin(hedef_filter)]

# ------------------------------
# ANA SAYFA
# ------------------------------
st.title("🚢 Üsküdar – Beşiktaş Vapur Hattı Analiz Dashboard")
st.markdown(f"📅 **Veri Tarihi:** {df['Tarih'].min()} | **Toplam Kayıt:** {df.shape[0]:,}")

# Özet Kartlar
col1, col2, col3, col4, col5 = st.columns(5)

df_uskudar = df_filtered[df_filtered['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df_filtered[df_filtered['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

col1.metric(
    "🚢 Üsküdar→Beşiktaş", 
    f"{df_uskudar.shape[0]:,}",
    delta=f"{df_uskudar.shape[0]/24:.1f}/saat"
)
col2.metric(
    "🚢 Beşiktaş→Üsküdar", 
    f"{df_besiktas.shape[0]:,}",
    delta=f"{df_besiktas.shape[0]/24:.1f}/saat"
)

# Aktarma istatistikleri
aktarma_u = df_uskudar[df_uskudar['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1].shape[0]
aktarma_b = df_besiktas[df_besiktas['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1].shape[0]

col3.metric(
    "🔄 Aktarma Yapan (U→B)", 
    f"{aktarma_u:,}",
    delta=f"{aktarma_u/df_uskudar.shape[0]*100:.1f}%" if df_uskudar.shape[0] > 0 else "0%"
)
col4.metric(
    "🔄 Aktarma Yapan (B→U)", 
    f"{aktarma_b:,}",
    delta=f"{aktarma_b/df_besiktas.shape[0]*100:.1f}%" if df_besiktas.shape[0] > 0 else "0%"
)

# Gitmeyenler
gitmeyen_u = df_uskudar[df_uskudar['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0].shape[0]
gitmeyen_b = df_besiktas[df_besiktas['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0].shape[0]
col5.metric(
    "🚫 Gitmeyen (Toplam)", 
    f"{gitmeyen_u + gitmeyen_b:,}",
    delta=f"U→B: {gitmeyen_u}, B→U: {gitmeyen_b}"
)

st.markdown("---")

# ------------------------------
# GRAFİKLER
# ------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Saatlik Biniş", 
    "🗺️ Gidilen Yerler", 
    "🔥 Isı Haritası",
    "📈 Detaylı Analiz"
])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Üsküdar → Beşiktaş")
        binme_u = df_uskudar.groupby('Saat').size().reset_index(name='Yolcu')
        fig_u, ax_u = plt.subplots(figsize=(10, 5))
        ax_u.bar(binme_u['Saat'], binme_u['Yolcu'], color='#1E88E5', edgecolor='white', alpha=0.8)
        ax_u.set_xlabel('Saat', fontsize=12)
        ax_u.set_ylabel('Yolcu Sayısı', fontsize=12)
        ax_u.set_xticks(range(0, 24))
        ax_u.grid(True, alpha=0.3)
        ax_u.set_title(f'Toplam: {df_uskudar.shape[0]:,} yolcu', fontsize=14)
        st.pyplot(fig_u)
    
    with col2:
        st.subheader("Beşiktaş → Üsküdar")
        binme_b = df_besiktas.groupby('Saat').size().reset_index(name='Yolcu')
        fig_b, ax_b = plt.subplots(figsize=(10, 5))
        ax_b.bar(binme_b['Saat'], binme_b['Yolcu'], color='#FF9800', edgecolor='white', alpha=0.8)
        ax_b.set_xlabel('Saat', fontsize=12)
        ax_b.set_ylabel('Yolcu Sayısı', fontsize=12)
        ax_b.set_xticks(range(0, 24))
        ax_b.grid(True, alpha=0.3)
        ax_b.set_title(f'Toplam: {df_besiktas.shape[0]:,} yolcu', fontsize=14)
        st.pyplot(fig_b)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Üsküdar → Beşiktaş - En Çok Gidilen Yerler")
        gidis_u = df_uskudar[df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'].notna()]
        gidis_u = gidis_u[gidis_u['İNDİKTEN SONRA NEREYE GİTTİ'] != '']
        gidis_u = gidis_u[gidis_u['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR']
        
        if not gidis_u.empty:
            top_u = gidis_u.groupby('İNDİKTEN SONRA NEREYE GİTTİ').size().nlargest(10).reset_index(name='Kisi')
            fig_u, ax_u = plt.subplots(figsize=(10, 5))
            colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(top_u)))[::-1]
            ax_u.barh(top_u['İNDİKTEN SONRA NEREYE GİTTİ'], top_u['Kisi'], color=colors)
            ax_u.set_xlabel('Kişi Sayısı', fontsize=12)
            ax_u.set_title('En Çok Gidilen 10 Yer', fontsize=14)
            st.pyplot(fig_u)
        else:
            st.info("Bu yönde gidilen yer verisi yok.")
    
    with col2:
        st.subheader("Beşiktaş → Üsküdar - En Çok Gidilen Yerler")
        gidis_b = df_besiktas[df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'].notna()]
        gidis_b = gidis_b[gidis_b['İNDİKTEN SONRA NEREYE GİTTİ'] != '']
        gidis_b = gidis_b[gidis_b['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR']
        
        if not gidis_b.empty:
            top_b = gidis_b.groupby('İNDİKTEN SONRA NEREYE GİTTİ').size().nlargest(10).reset_index(name='Kisi')
            fig_b, ax_b = plt.subplots(figsize=(10, 5))
            colors = plt.cm.Oranges(np.linspace(0.3, 0.9, len(top_b)))[::-1]
            ax_b.barh(top_b['İNDİKTEN SONRA NEREYE GİTTİ'], top_b['Kisi'], color=colors)
            ax_b.set_xlabel('Kişi Sayısı', fontsize=12)
            ax_b.set_title('En Çok Gidilen 10 Yer', fontsize=14)
            st.pyplot(fig_b)
        else:
            st.info("Bu yönde gidilen yer verisi yok.")

with tab3:
    st.subheader("🔥 Saat - Hedef Isı Haritası")
    
    # Isı haritası için pivot
    gidis_all = df_filtered[df_filtered['İNDİKTEN SONRA NEREYE GİTTİ'].notna()]
    gidis_all = gidis_all[gidis_all['İNDİKTEN SONRA NEREYE GİTTİ'] != '']
    gidis_all = gidis_all[gidis_all['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR']
    
    if not gidis_all.empty:
        # Top 10 hedef seç
        top_hedefler = gidis_all.groupby('İNDİKTEN SONRA NEREYE GİTTİ').size().nlargest(10).index
        gidis_top = gidis_all[gidis_all['İNDİKTEN SONRA NEREYE GİTTİ'].isin(top_hedefler)]
        
        pivot = gidis_top.groupby(['Saat', 'İNDİKTEN SONRA NEREYE GİTTİ']).size().unstack(fill_value=0)
        
        fig, ax = plt.subplots(figsize=(14, 8))
        im = ax.imshow(pivot.values, cmap='YlOrRd', aspect='auto')
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha='right')
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
        ax.set_xlabel('Gidilen Yer', fontsize=12)
        ax.set_ylabel('Saat', fontsize=12)
        ax.set_title('Saat - Hedef Yoğunluk Haritası', fontsize=14)
        plt.colorbar(im, ax=ax, label='Yolcu Sayısı')
        st.pyplot(fig)
    else:
        st.info("Isı haritası için yeterli veri yok.")

with tab4:
    st.subheader("📈 Detaylı Analiz")
    
    # Saatlik yoğunluk tablosu
    st.markdown("### 📊 Saatlik Yoğunluk")
    saatlik = df_filtered.groupby(['Saat', 'YÖN']).size().reset_index(name='Yolcu')
    saatlik_pivot = saatlik.pivot(index='Saat', columns='YÖN', values='Yolcu').fillna(0)
    saatlik_pivot['Toplam'] = saatlik_pivot.sum(axis=1)
    st.dataframe(saatlik_pivot, use_container_width=True)
    
    # En yoğun saatler
    st.markdown("### ⏰ En Yoğun Saatler")
    en_yogun = saatlik_pivot.nlargest(5, 'Toplam')[['Toplam']]
    st.dataframe(en_yogun, use_container_width=True)
    
    # Hedef istatistikleri
    st.markdown("### 🎯 Hedef İstatistikleri")
    hedef_istatistik = df_filtered[df_filtered['İNDİKTEN SONRA NEREYE GİTTİ'].notna()]
    hedef_istatistik = hedef_istatistik[hedef_istatistik['İNDİKTEN SONRA NEREYE GİTTİ'] != '']
    hedef_istatistik = hedef_istatistik[hedef_istatistik['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR']
    
    if not hedef_istatistik.empty:
        hedef_ozet = hedef_istatistik.groupby(['YÖN', 'İNDİKTEN SONRA NEREYE GİTTİ']).size().reset_index(name='Kisi')
        hedef_ozet = hedef_ozet.sort_values(['YÖN', 'Kisi'], ascending=[True, False])
        st.dataframe(hedef_ozet, use_container_width=True)
    else:
        st.info("Hedef verisi bulunamadı.")

# ------------------------------
# TAHMİN ARACI (GELİŞMİŞ)
# ------------------------------
st.markdown("---")
st.header("🔮 Gelişmiş Tahmin Aracı")

col_pred1, col_pred2, col_pred3 = st.columns(3)

with col_pred1:
    pred_yon = st.selectbox(
        "📍 Yön Seçiniz",
        options=['ÜSKÜDAR → BEŞİKTAŞ', 'BEŞİKTAŞ → ÜSKÜDAR'],
        key='pred_yon'
    )

with col_pred2:
    pred_hedef_list = df[df['YÖN'] == pred_yon]['İNDİKTEN SONRA NEREYE GİTTİ'].unique()
    pred_hedef_list = [h for h in pred_hedef_list if h not in ['', 'BİLİNMİYOR']]
    pred_hedef = st.selectbox(
        "🎯 Gidilecek Yer Seçiniz",
        options=sorted(pred_hedef_list),
        key='pred_hedef'
    )

with col_pred3:
    pred_saat = st.slider(
        "⏰ Saat Seçiniz",
        min_value=0, max_value=23, value=8, key='pred_saat'
    )

# Tahmin hesapla
if pred_hedef:
    # Seçilen kriterler için veri
    pred_data = df[
        (df['YÖN'] == pred_yon) &
        (df['Saat'] == pred_saat) &
        (df['İNDİKTEN SONRA NEREYE GİTTİ'] == pred_hedef)
    ]
    
    # Tüm saatler için ortalama
    all_hours_data = df[
        (df['YÖN'] == pred_yon) &
        (df['İNDİKTEN SONRA NEREYE GİTTİ'] == pred_hedef)
    ]
    
    pred_count = len(pred_data)
    avg_count = len(all_hours_data) / 24 if len(all_hours_data) > 0 else 0
    max_count = all_hours_data.groupby('Saat').size().max() if len(all_hours_data) > 0 else 0
    min_count = all_hours_data.groupby('Saat').size().min() if len(all_hours_data) > 0 else 0
    
    # Yoğunluk seviyesi
    if pred_count >= 5:
        level = "🔴 Çok Yoğun"
        color = "#FF4444"
    elif pred_count >= 3:
        level = "🟡 Orta"
        color = "#FFA500"
    elif pred_count >= 1:
        level = "🟢 Düşük"
        color = "#44AA44"
    else:
        level = "⚪ Boş"
        color = "#888888"
    
    # Sonuçları göster
    st.markdown("---")
    st.subheader("📊 Tahmin Sonuçları")
    
    col_res1, col_res2, col_res3, col_res4, col_res5 = st.columns(5)
    col_res1.metric("📊 Tahmini Yolcu", f"{pred_count} kişi", delta=f"Saat {pred_saat}:00")
    col_res2.metric("📈 Günlük Ortalama", f"{avg_count:.1f} kişi")
    col_res3.metric("📈 Maksimum (Saatlik)", f"{max_count} kişi")
    col_res4.metric("📉 Minimum (Saatlik)", f"{min_count} kişi")
    col_res5.metric("🚦 Yoğunluk", level)
    
    # Saatlik dağılım grafiği (tahmin için)
    if len(all_hours_data) > 0:
        st.markdown("### 📈 Saatlik Dağılım (Tüm Gün)")
        saatlik_dagilim = all_hours_data.groupby('Saat').size().reset_index(name='Yolcu')
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.bar(saatlik_dagilim['Saat'], saatlik_dagilim['Yolcu'], color='#1E88E5', alpha=0.7)
        ax.axvline(x=pred_saat, color='red', linestyle='--', linewidth=2, label='Seçilen Saat')
        ax.set_xlabel('Saat', fontsize=12)
        ax.set_ylabel('Yolcu Sayısı', fontsize=12)
        ax.set_xticks(range(0, 24))
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    
    # Detaylı tablo
    with st.expander("📋 Detaylı Tahmin Verileri"):
        st.dataframe(all_hours_data[['Saat', 'MERKEZDEN GEMİYE BİNİŞ', 'YÖN']].head(20), use_container_width=True)

# ------------------------------
# FOOTER
# ------------------------------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
    🚢 Üsküdar – Beşiktaş Vapur Hattı Analiz Dashboard | Veri Tarihi: {}
    </div>
    """.format(df['Tarih'].min()),
    unsafe_allow_html=True
)
