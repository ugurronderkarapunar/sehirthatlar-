import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

# Sayfa yapılandırması
st.set_page_config(
    page_title="Vapur Hattı Analiz Dashboard", 
    page_icon="🚢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS ile özel stiller
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1E88E5; text-align: center; }
    .sub-header { font-size: 1.2rem; color: #555; text-align: center; margin-bottom: 2rem; }
    .metric-card { background: #f8f9fa; padding: 1rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .metric-value { font-size: 2rem; font-weight: bold; color: #1E88E5; }
    .metric-label { font-size: 0.9rem; color: #666; }
    .insight-box { background: #E3F2FD; padding: 1rem; border-radius: 10px; border-left: 5px solid #1E88E5; margin: 0.5rem 0; }
</style>
""", unsafe_allow_html=True)

# Başlık
st.markdown('<div class="main-header">🚢 Üsküdar – Beşiktaş Vapur Hattı</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Yolcu Analiz ve Tahmin Dashboardu</div>', unsafe_allow_html=True)

# ------------------------------
# DOSYA YÜKLEME
# ------------------------------
uploaded_file = st.file_uploader("📂 Excel dosyasını yükleyin", type=["xlsx"])

if uploaded_file is None:
    st.info("📌 Lütfen veri dosyasını yükleyin.")
    st.stop()

# ------------------------------
# VERİ OKUMA VE TEMİZLEME
# ------------------------------
@st.cache_data
def load_data(file):
    df = pd.read_excel(file, sheet_name='Sayfa2')
    df.columns = df.columns.str.strip()
    df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(df['MERKEZDEN GEMİYE BİNİŞ'], format='mixed', errors='coerce')
    df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])
    df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
    df['Saat_Dilimi'] = df['Saat'].apply(lambda x: f"{x:02d}:00")
    df['YÖN'] = df['YÖN'].str.strip()
    return df

df = load_data(uploaded_file)
st.success(f"✅ Veri başarıyla yüklendi! Toplam {df.shape[0]:,} yolcu kaydı.")

# ------------------------------
# VERİYİ HAZIRLA
# ------------------------------
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

# Gidilen yerleri temizle
df['Hedef_Temiz'] = df['İNDİKTEN SONRA NEREYE GİTTİ'].fillna('')
df['Hedef_Temiz'] = df['Hedef_Temiz'].apply(lambda x: str(x).strip() if x not in ['', 'BİLİNMİYOR'] else '')
df['Hedef_Temiz'] = df['Hedef_Temiz'].replace('', 'Belirtilmemiş')

# ------------------------------
# SIDEBAR - FİLTRELEME
# ------------------------------
st.sidebar.header("🔍 Filtreler")
selected_yon = st.sidebar.selectbox(
    "Yön Seçiniz", 
    ['Tümü', 'ÜSKÜDAR → BEŞİKTAŞ', 'BEŞİKTAŞ → ÜSKÜDAR']
)

# Saat aralığı seçimi
saat_araligi = st.sidebar.slider(
    "Saat Aralığı Seçiniz",
    min_value=0, max_value=23, value=(6, 22)
)

# Filtrele
filtre_df = df.copy()
if selected_yon != 'Tümü':
    filtre_df = filtre_df[filtre_df['YÖN'] == selected_yon]
filtre_df = filtre_df[(filtre_df['Saat'] >= saat_araligi[0]) & (filtre_df['Saat'] <= saat_araligi[1])]

# ------------------------------
# METRİK KARTLARI
# ------------------------------
st.subheader("📊 Özet İstatistikler")

col1, col2, col3, col4, col5 = st.columns(5)

toplam = len(filtre_df)
ortalama = toplam / 24 if toplam > 0 else 0
aktarma = len(filtre_df[filtre_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1])
gitmeyen = toplam - aktarma

# En yoğun saat
if toplam > 0:
    en_yogun_saat = filtre_df.groupby('Saat').size().idxmax()
    en_yogun_saat_dilimi = f"{en_yogun_saat:02d}:00"
else:
    en_yogun_saat_dilimi = "-"

# En çok gidilen yer
if toplam > 0:
    en_cok_yer = filtre_df['Hedef_Temiz'].value_counts().idxmax()
else:
    en_cok_yer = "-"

col1.metric("📌 Toplam Yolcu", f"{toplam:,}")
col2.metric("⏱️ Ortalama/Saat", f"{ortalama:.1f}")
col3.metric("🔄 Aktarma Yapan", f"{aktarma:,} (%{aktarma/toplam*100:.0f})" if toplam > 0 else "0")
col4.metric("🚫 Gitmeyen", f"{gitmeyen:,} (%{gitmeyen/toplam*100:.0f})" if toplam > 0 else "0")
col5.metric("🏆 En Yoğun Saat", en_yogun_saat_dilimi)

# ------------------------------
# GRAFİKLER
# ------------------------------
st.subheader("📈 Zaman Serisi ve Dağılım Analizleri")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Saatlik Biniş", "🎯 Gidilen Yerler", "📍 Nereden Geldi", "🔄 Aktarma Analizi"])

with tab1:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Üsküdar yönü
    binme_u = df_uskudar.groupby('Saat').size().reset_index(name='Yolcu')
    axes[0].bar(binme_u['Saat'], binme_u['Yolcu'], color='#1E88E5', edgecolor='black', alpha=0.8)
    axes[0].set_title('Üsküdar → Beşiktaş', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Saat')
    axes[0].set_ylabel('Yolcu Sayısı')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xticks(range(0, 24))
    axes[0].axvline(x=saat_araligi[0], color='red', linestyle='--', alpha=0.5)
    axes[0].axvline(x=saat_araligi[1], color='red', linestyle='--', alpha=0.5)
    
    # Beşiktaş yönü
    binme_b = df_besiktas.groupby('Saat').size().reset_index(name='Yolcu')
    axes[1].bar(binme_b['Saat'], binme_b['Yolcu'], color='#FF9800', edgecolor='black', alpha=0.8)
    axes[1].set_title('Beşiktaş → Üsküdar', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Saat')
    axes[1].set_ylabel('Yolcu Sayısı')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xticks(range(0, 24))
    axes[1].axvline(x=saat_araligi[0], color='red', linestyle='--', alpha=0.5)
    axes[1].axvline(x=saat_araligi[1], color='red', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    st.pyplot(fig)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption("Üsküdar → Beşiktaş - En Çok Gidilen Yerler")
        gidis_u = df_uskudar[df_uskudar['Hedef_Temiz'] != 'Belirtilmemiş']
        if not gidis_u.empty:
            top_u = gidis_u['Hedef_Temiz'].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(8, 6))
            top_u.plot(kind='barh', ax=ax, color='#1E88E5')
            ax.set_xlabel('Kişi Sayısı')
            ax.set_title('Top 10 Gidilen Yer')
            st.pyplot(fig)
        else:
            st.info("Veri bulunamadı.")
    
    with col2:
        st.caption("Beşiktaş → Üsküdar - En Çok Gidilen Yerler")
        gidis_b = df_besiktas[df_besiktas['Hedef_Temiz'] != 'Belirtilmemiş']
        if not gidis_b.empty:
            top_b = gidis_b['Hedef_Temiz'].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(8, 6))
            top_b.plot(kind='barh', ax=ax, color='#FF9800')
            ax.set_xlabel('Kişi Sayısı')
            ax.set_title('Top 10 Gidilen Yer')
            st.pyplot(fig)
        else:
            st.info("Veri bulunamadı.")

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption("Üsküdar → Beşiktaş - Geliş Hatları")
        gelis_u = df_uskudar[df_uskudar['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
        gelis_u = gelis_u[gelis_u['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
        if not gelis_u.empty:
            top_gelis_u = gelis_u['MERKEZE GELDİĞİ ARACIN HATTI'].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(8, 6))
            top_gelis_u.plot(kind='barh', ax=ax, color='#1E88E5')
            ax.set_xlabel('Kişi Sayısı')
            ax.set_title('Top 10 Geliş Hattı')
            st.pyplot(fig)
        else:
            st.info("Veri bulunamadı.")
    
    with col2:
        st.caption("Beşiktaş → Üsküdar - Geliş Hatları")
        gelis_b = df_besiktas[df_besiktas['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
        gelis_b = gelis_b[gelis_b['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
        if not gelis_b.empty:
            top_gelis_b = gelis_b['MERKEZE GELDİĞİ ARACIN HATTI'].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(8, 6))
            top_gelis_b.plot(kind='barh', ax=ax, color='#FF9800')
            ax.set_xlabel('Kişi Sayısı')
            ax.set_title('Top 10 Geliş Hattı')
            st.pyplot(fig)
        else:
            st.info("Veri bulunamadı.")

with tab4:
    col1, col2 = st.columns(2)
    
    with col1:
        # Aktarma oranı - Üsküdar
        aktarma_u = len(df_uskudar[df_uskudar['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1])
        gitmeyen_u = len(df_uskudar) - aktarma_u
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pie([aktarma_u, gitmeyen_u], labels=['Aktarma Yapan', 'Gitmeyen'], 
               autopct='%1.1f%%', colors=['#4CAF50', '#FF5722'], startangle=90)
        ax.set_title('Üsküdar → Beşiktaş - Aktarma Oranı')
        st.pyplot(fig)
    
    with col2:
        # Aktarma oranı - Beşiktaş
        aktarma_b = len(df_besiktas[df_besiktas['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1])
        gitmeyen_b = len(df_besiktas) - aktarma_b
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pie([aktarma_b, gitmeyen_b], labels=['Aktarma Yapan', 'Gitmeyen'], 
               autopct='%1.1f%%', colors=['#4CAF50', '#FF5722'], startangle=90)
        ax.set_title('Beşiktaş → Üsküdar - Aktarma Oranı')
        st.pyplot(fig)

# ------------------------------
# ISI HARİTASI (Saat x Hedef)
# ------------------------------
st.subheader("🔥 Isı Haritası - Saat x Gidilen Yer (Üsküdar → Beşiktaş)")

# Pivot tablo oluştur
if not df_uskudar.empty:
    pivot_data = df_uskudar[df_uskudar['Hedef_Temiz'] != 'Belirtilmemiş']
    if not pivot_data.empty:
        pivot = pd.crosstab(pivot_data['Hedef_Temiz'], pivot_data['Saat'])
        # En çok gidilen 10 yer ile sınırla
        top_hedefler = pivot.sum(axis=1).nlargest(10).index
        pivot = pivot.loc[top_hedefler]
        
        fig, ax = plt.subplots(figsize=(14, 8))
        sns.heatmap(pivot, annot=True, fmt='d', cmap='Blues', ax=ax, cbar_kws={'label': 'Yolcu Sayısı'})
        ax.set_title('Saat × Gidilen Yer (Üsküdar → Beşiktaş)', fontsize=14)
        ax.set_xlabel('Saat')
        ax.set_ylabel('Gidilen Yer')
        st.pyplot(fig)
    else:
        st.info("Isı haritası için yeterli veri yok.")
else:
    st.info("Bu yönde veri bulunamadı.")

# ------------------------------
# TAHMİN ARACI (PROFESYONEL)
# ------------------------------
st.subheader("🔮 Akıllı Tahmin Aracı")

st.markdown("""
<div class="insight-box">
    💡 <b>Nasıl çalışır?</b> Seçtiğiniz yön, hedef ve saat için geçmiş verilere göre 
    tahmini yolcu sayısını hesaplar. Ayrıca o saatteki genel yoğunluk ve trend bilgisi sunar.
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    tahmin_yon = st.selectbox(
        "📍 Yön", 
        ['ÜSKÜDAR → BEŞİKTAŞ', 'BEŞİKTAŞ → ÜSKÜDAR'],
        key='tahmin_yon'
    )

# Hedef listesini güncelle (NaN sorunu çözüldü)
hedef_series = df[df['İNDİKTEN SONRA NEREYE GİTTİ'].notna()]['İNDİKTEN SONRA NEREYE GİTTİ']
hedef_series = hedef_series[hedef_series != '']
hedef_series = hedef_series[hedef_series != 'BİLİNMİYOR']
hedef_list = sorted([str(h) for h in hedef_series.unique() if pd.notna(h) and str(h).strip()])

with col2:
    tahmin_hedef = st.selectbox("🎯 Gidilecek Yer", hedef_list, key='tahmin_hedef')

with col3:
    tahmin_saat = st.slider("⏰ Saat", 0, 23, 8, key='tahmin_saat')

# Tahmin hesapla
tahmin_data = df[
    (df['YÖN'] == tahmin_yon) &
    (df['Saat'] == tahmin_saat) &
    (df['İNDİKTEN SONRA NEREYE GİTTİ'] == tahmin_hedef)
]
tahmin_sayisi = len(tahmin_data)

# Aynı saatteki toplam biniş
toplam_saat = df[(df['YÖN'] == tahmin_yon) & (df['Saat'] == tahmin_saat)].shape[0]

# Tahmin metrikleri
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

col1.metric("🎯 Tahmini Yolcu", f"{tahmin_sayisi} kişi", 
            delta=f"%{(tahmin_sayisi/toplam_saat*100) if toplam_saat > 0 else 0:.0f} of total" if toplam_saat > 0 else None)

col2.metric("📊 Toplam Biniş (Bu Saat)", f"{toplam_saat} kişi")

# Son 3 saatin ortalaması (trend)
onceki_saatler = df[(df['YÖN'] == tahmin_yon) & (df['Saat'].between(max(0, tahmin_saat-2), tahmin_saat-1))]
onceki_ortalama = onceki_saatler.groupby('Saat').size().mean() if not onceki_saatler.empty else 0
col3.metric("📈 Trend (Önceki 3 Saat)", f"{onceki_ortalama:.1f} kişi/ort")

# En yoğun saat
yogun_saat = df[df['YÖN'] == tahmin_yon].groupby('Saat').size().idxmax() if not df[df['YÖN'] == tahmin_yon].empty else 0
col4.metric("🏆 En Yoğun Saat", f"{yogun_saat:02d}:00")

# Tahmin detay grafiği
st.markdown("---")
st.caption("📊 Seçilen saatteki güncel dağılım")

# Seçilen saatteki tüm hedefler
saat_hedefler = df[
    (df['YÖN'] == tahmin_yon) & 
    (df['Saat'] == tahmin_saat) & 
    (df['İNDİKTEN SONRA NEREYE GİTTİ'].notna()) &
    (df['İNDİKTEN SONRA NEREYE GİTTİ'] != '') &
    (df['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR')
]
saat_hedefler['Hedef_Temiz'] = saat_hedefler['İNDİKTEN SONRA NEREYE GİTTİ']

if not saat_hedefler.empty:
    hedef_dist = saat_hedefler['Hedef_Temiz'].value_counts().head(10)
    fig, ax = plt.subplots(figsize=(10, 6))
    hedef_dist.plot(kind='barh', ax=ax, color='#1E88E5')
    ax.set_xlabel('Kişi Sayısı')
    ax.set_title(f'{tahmin_yon} - {tahmin_saat:02d}:00 Saatindeki Hedef Dağılımı')
    ax.axvline(x=tahmin_sayisi, color='red', linestyle='--', linewidth=2, label='Tahmininiz')
    ax.legend()
    st.pyplot(fig)
else:
    st.info("Bu saatte aktarma yapan yolcu verisi bulunamadı.")

# ------------------------------
# DETAYLI TABLOLAR
# ------------------------------
with st.expander("📋 Detaylı Veri Tabloları"):
    tab1, tab2, tab3, tab4 = st.tabs(["Üsküdar→Beşiktaş", "Beşiktaş→Üsküdar", "Geliş Hatları", "Gitmeyenler"])
    
    with tab1:
        st.dataframe(df_uskudar.head(100), use_container_width=True)
    
    with tab2:
        st.dataframe(df_besiktas.head(100), use_container_width=True)
    
    with tab3:
        gelis_df = df[df['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
        gelis_df = gelis_df[gelis_df['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
        st.dataframe(gelis_df.groupby(['YÖN', 'MERKEZE GELDİĞİ ARACIN HATTI']).size().reset_index(name='Kisi'), use_container_width=True)
    
    with tab4:
        gitmeyen_df = df[df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0]
        st.dataframe(gitmeyen_df.groupby('YÖN').size().reset_index(name='Kisi'), use_container_width=True)

# ------------------------------
# FOOTER
# ------------------------------
st.markdown("---")
st.caption(f"📅 Son Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Veri: {df.shape[0]:,} kayıt")
