import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Sayfa ayarları
st.set_page_config(
    page_title="🚢 Vapur Hattı Analiz Dashboard",
    page_icon="⛴️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS ile modern stil
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem;
        background: linear-gradient(90deg, #E3F2FD, #BBDEFB);
        border-radius: 10px;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #1E88E5;
        transition: 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.3rem;
    }
    .metric-delta {
        font-size: 0.85rem;
        color: #4CAF50;
    }
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 20px;
        background-color: #f0f2f6;
        border-radius: 6px 6px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E88E5;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">⛴️ Üsküdar – Beşiktaş Vapur Hattı Analiz ve Tahmin Aracı</div>', unsafe_allow_html=True)

# ------------------------------
# SIDEBAR - Dosya Yükleme ve Filtreler
# ------------------------------
with st.sidebar:
    st.header("📂 Veri Yükle")
    uploaded_file = st.file_uploader("Excel dosyasını yükleyin (20260506_2_REV5.xlsx)", type=["xlsx"])
    
    if uploaded_file is None:
        st.warning("Lütfen bir Excel dosyası yükleyin.")
        st.stop()

# ------------------------------
# VERİYİ OKU VE TEMİZLE
# ------------------------------
@st.cache_data
def load_data(file):
    df = pd.read_excel(file, sheet_name='Sayfa2')
    df.columns = df.columns.str.strip()
    
    # Tarih dönüşümü
    df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(
        df['MERKEZDEN GEMİYE BİNİŞ'], 
        format='mixed', 
        errors='coerce'
    )
    df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])
    
    df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
    df['Saat_Dilimi'] = df['Saat'].apply(lambda x: f"{x:02d}:00–{x:02d}:59")
    df['YÖN'] = df['YÖN'].str.strip()
    
    # Hedef temizleme - ÇOK ÖNEMLİ: NaN, boş, BİLİNMİYOR hepsini filtrele
    def temizle_hedef(x):
        if pd.isna(x):
            return None
        val = str(x).strip()
        if val in ['', 'BİLİNMİYOR', 'nan', 'None']:
            return None
        return val
    
    df['Hedef_Temiz'] = df['İNDİKTEN SONRA NEREYE GİTTİ'].apply(temizle_hedef)
    
    # Aktarma durumunu netleştir (0=Gitmedi, 1=Gitti)
    # Eğer hedef varsa ve aktarma=0 ise düzelt
    df.loc[(df['Hedef_Temiz'].notna()) & (df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0), 'İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] = 1
    
    return df

df = load_data(uploaded_file)
st.success(f"✅ Veri başarıyla yüklendi! Toplam {df.shape[0]:,} satır.")

# ------------------------------
# SIDEBAR - Filtreler
# ------------------------------
with st.sidebar:
    st.header("🔍 Filtreler")
    
    # Yön seçimi
    yon_filter = st.multiselect(
        "Yön Seçiniz",
        options=df['YÖN'].unique(),
        default=df['YÖN'].unique()
    )
    
    # Saat aralığı
    saat_range = st.slider(
        "Saat Aralığı",
        min_value=0, max_value=23,
        value=(6, 22)
    )
    
    # Hedef filtresi
    hedef_list = df[df['Hedef_Temiz'].notna()]['Hedef_Temiz'].unique()
    hedef_list = sorted([h for h in hedef_list if h])
    hedef_filter = st.multiselect(
        "Hedef Yer (Opsiyonel)",
        options=hedef_list,
        default=[]
    )

# Veriyi filtrele
filtered_df = df[
    (df['YÖN'].isin(yon_filter)) &
    (df['Saat'] >= saat_range[0]) &
    (df['Saat'] <= saat_range[1])
]
if hedef_filter:
    filtered_df = filtered_df[filtered_df['Hedef_Temiz'].isin(hedef_filter)]

# ------------------------------
# METRİK KARTLAR
# ------------------------------
st.subheader("📊 Özet İstatistikler")

# Hesaplamalar
total = len(filtered_df)
total_uskudar = len(filtered_df[filtered_df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ'])
total_besiktas = len(filtered_df[filtered_df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR'])

# AKTARMA: 1 olanlar (gidenler)
aktarma = len(filtered_df[filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1])
# GİTMEYEN: 0 olanlar veya hedefi olmayanlar
gitmeyen = len(filtered_df[filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0])

# Detaylı kontrol - HEDEFİ OLAN ama AKTARMA=0 olanları düzelt
# (Yukarıda zaten düzelttik ama emin olalım)
yanlis = filtered_df[(filtered_df['Hedef_Temiz'].notna()) & (filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0)]
if not yanlis.empty:
    aktarma += len(yanlis)
    gitmeyen -= len(yanlis)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{total:,}</div>
        <div class="metric-label">Toplam Yolcu</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #1E88E5;">
        <div class="metric-value" style="color:#1E88E5;">{total_uskudar:,}</div>
        <div class="metric-label">Üsküdar → Beşiktaş</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #FF9800;">
        <div class="metric-value" style="color:#FF9800;">{total_besiktas:,}</div>
        <div class="metric-label">Beşiktaş → Üsküdar</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    pct = (aktarma/total*100) if total > 0 else 0
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #4CAF50;">
        <div class="metric-value" style="color:#4CAF50;">{aktarma:,}</div>
        <div class="metric-label">🔄 Aktarma Yapan</div>
        <div class="metric-delta">%{pct:.1f} (Toplamın)</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    pct = (gitmeyen/total*100) if total > 0 else 0
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #F44336;">
        <div class="metric-value" style="color:#F44336;">{gitmeyen:,}</div>
        <div class="metric-label">🚫 Gitmeyen (Aktarma Yok)</div>
        <div class="metric-delta">%{pct:.1f} (Toplamın)</div>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------
# İKİ YÖN İÇİN GRAFİKLER
# ------------------------------
st.subheader("📈 Saatlik Biniş Dağılımı")

fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# Üsküdar yönü
df_u = filtered_df[filtered_df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
binme_u = df_u.groupby('Saat').size().reset_index(name='Yolcu')
if not binme_u.empty:
    axes[0].bar(binme_u['Saat'], binme_u['Yolcu'], color='#1E88E5', edgecolor='white', alpha=0.8)
    axes[0].set_title('Üsküdar → Beşiktaş', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Saat', fontsize=12)
    axes[0].set_ylabel('Yolcu Sayısı', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xticks(range(0, 24))
    max_idx = binme_u['Yolcu'].idxmax()
    axes[0].axvline(binme_u.loc[max_idx, 'Saat'], color='red', linestyle='--', alpha=0.7, label=f"Tepe: {binme_u.loc[max_idx, 'Saat']}:00")
    axes[0].legend()

# Beşiktaş yönü
df_b = filtered_df[filtered_df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']
binme_b = df_b.groupby('Saat').size().reset_index(name='Yolcu')
if not binme_b.empty:
    axes[1].bar(binme_b['Saat'], binme_b['Yolcu'], color='#FF9800', edgecolor='white', alpha=0.8)
    axes[1].set_title('Beşiktaş → Üsküdar', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Saat', fontsize=12)
    axes[1].set_ylabel('Yolcu Sayısı', fontsize=12)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xticks(range(0, 24))
    max_idx = binme_b['Yolcu'].idxmax()
    axes[1].axvline(binme_b.loc[max_idx, 'Saat'], color='red', linestyle='--', alpha=0.7, label=f"Tepe: {binme_b.loc[max_idx, 'Saat']}:00")
    axes[1].legend()

plt.tight_layout()
st.pyplot(fig)

# ------------------------------
# GELİŞMİŞ TAHMİN ARACI
# ------------------------------
st.header("🔮 Gelişmiş Tahmin Aracı")

with st.container():
    col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 1])
    
    with col_a:
        tahmin_yon = st.selectbox(
            "📍 Yön Seçiniz",
            options=['ÜSKÜDAR → BEŞİKTAŞ', 'BEŞİKTAŞ → ÜSKÜDAR'],
            key="tahmin_yon"
        )
    
    with col_b:
        hedef_list_tahmin = df[df['YÖN'] == tahmin_yon]['Hedef_Temiz'].dropna().unique()
        hedef_list_tahmin = sorted([h for h in hedef_list_tahmin if h])
        tahmin_hedef = st.selectbox(
            "🎯 Gidilecek Yer",
            options=hedef_list_tahmin if len(hedef_list_tahmin) > 0 else ['Veri Yok'],
            key="tahmin_hedef"
        )
    
    with col_c:
        tahmin_saat = st.slider(
            "⏰ Saat Seçiniz",
            min_value=0, max_value=23, value=8,
            key="tahmin_saat"
        )
    
    with col_d:
        st.write("")
        st.write("")
        tahmin_button = st.button("🚀 Tahmin Yap", use_container_width=True)

if tahmin_button and tahmin_hedef != 'Veri Yok':
    # Seçilen kriterlere göre filtrele
    tahmin_df = df[
        (df['YÖN'] == tahmin_yon) &
        (df['Hedef_Temiz'] == tahmin_hedef) &
        (df['Saat'] == tahmin_saat)
    ]
    tahmin_sayisi = len(tahmin_df)
    
    # Aynı hedef için saatlik ortalama
    saatlik_df = df[
        (df['YÖN'] == tahmin_yon) &
        (df['Hedef_Temiz'] == tahmin_hedef)
    ]
    saatlik_ortalama = saatlik_df.groupby('Saat').size().mean()
    en_yogun = saatlik_df.groupby('Saat').size().idxmax() if not saatlik_df.empty else None
    
    # Sonuçları göster
    st.markdown("---")
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    col_r1.metric("📊 Tahmini Yolcu", f"{tahmin_sayisi} kişi", delta=f"Seçilen saat için")
    col_r2.metric("📈 Saatlik Ortalama", f"{saatlik_ortalama:.1f} kişi", delta="Tüm saatler")
    col_r3.metric("🔥 En Yoğun Saat", f"{en_yogun}:00" if en_yogun is not None else "-", delta="Bu hedef için")
    col_r4.metric("📌 Toplam Yolcu (Tüm Saatler)", 
                  f"{saatlik_df.shape[0]:,} kişi")
    
    # Hedefin saatlik trend grafiği
    trend_df = saatlik_df.groupby('Saat').size().reset_index(name='Yolcu')
    if not trend_df.empty:
        fig_trend, ax = plt.subplots(figsize=(10, 4))
        ax.plot(trend_df['Saat'], trend_df['Yolcu'], marker='o', linestyle='-', color='#1E88E5', linewidth=2, markersize=8)
        ax.axvline(tahmin_saat, color='red', linestyle='--', alpha=0.7, label='Seçilen Saat')
        ax.set_title(f'{tahmin_yon} - {tahmin_hedef} Saatlik Yolcu Trendi', fontsize=14)
        ax.set_xlabel('Saat', fontsize=12)
        ax.set_ylabel('Yolcu Sayısı', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_xticks(range(0, 24))
        st.pyplot(fig_trend)

# ------------------------------
# DETAYLI TABLOLAR - SEKME
# ------------------------------
st.subheader("📋 Detaylı Analiz Tabloları")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📍 Nereden Geldi?", 
    "🎯 Nereye Gitti?", 
    "🚫 Gitmeyenler", 
    "🔄 Aktarma Yapanlar",
    "📊 Tüm Veri"
])

# Tab 1: Nereden Geldi?
with tab1:
    gelis_data = filtered_df[filtered_df['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
    gelis_data = gelis_data[gelis_data['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
    if not gelis_data.empty:
        gelis_ozet = gelis_data.groupby(['YÖN', 'MERKEZE GELDİĞİ ARACIN HATTI']).size().reset_index(name='Kisi')
        gelis_ozet = gelis_ozet.sort_values('Kisi', ascending=False)
        st.dataframe(gelis_ozet, use_container_width=True, height=400)
        
        # Geliş hatları grafiği
        fig_gelis, ax = plt.subplots(figsize=(10, 5))
        top_gelis = gelis_ozet.groupby('MERKEZE GELDİĞİ ARACIN HATTI')['Kisi'].sum().nlargest(10).reset_index()
        ax.barh(top_gelis['MERKEZE GELDİĞİ ARACIN HATTI'], top_gelis['Kisi'], color='#4CAF50')
        ax.set_title('En Çok Gelinilen 10 Hat', fontsize=14)
        ax.set_xlabel('Kişi Sayısı')
        st.pyplot(fig_gelis)
    else:
        st.info("Geliş hattı verisi bulunamadı.")

# Tab 2: Nereye Gitti?
with tab2:
    gidis_data = filtered_df[filtered_df['Hedef_Temiz'].notna()]
    if not gidis_data.empty:
        gidis_ozet = gidis_data.groupby(['YÖN', 'Hedef_Temiz']).size().reset_index(name='Kisi')
        gidis_ozet = gidis_ozet.sort_values('Kisi', ascending=False)
        st.dataframe(gidis_ozet, use_container_width=True, height=400)
        
        # Gidiş grafiği
        fig_gidis, ax = plt.subplots(figsize=(10, 5))
        top_gidis = gidis_ozet.groupby('Hedef_Temiz')['Kisi'].sum().nlargest(10).reset_index()
        ax.barh(top_gidis['Hedef_Temiz'], top_gidis['Kisi'], color='#FF5722')
        ax.set_title('En Çok Gidilen 10 Yer', fontsize=14)
        ax.set_xlabel('Kişi Sayısı')
        st.pyplot(fig_gidis)
    else:
        st.info("Gidiş verisi bulunamadı.")

# Tab 3: Gitmeyenler (AKTARMA=0)
with tab3:
    gitmeyen_data = filtered_df[filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0]
    if not gitmeyen_data.empty:
        gitmeyen_ozet = gitmeyen_data.groupby('YÖN').size().reset_index(name='Kisi')
        st.dataframe(gitmeyen_ozet, use_container_width=True)
        
        col_g1, col_g2 = st.columns(2)
        col_g1.metric("Toplam Gitmeyen", f"{len(gitmeyen_data):,}")
        col_g2.metric("Gitmeyen Yüzdesi", f"{(len(gitmeyen_data)/len(filtered_df)*100):.1f}%")
        
        # Gitmeyenlerin saatlik dağılımı
        gitmeyen_saat = gitmeyen_data.groupby('Saat').size().reset_index(name='Kisi')
        if not gitmeyen_saat.empty:
            fig_git, ax = plt.subplots(figsize=(10, 4))
            ax.bar(gitmeyen_saat['Saat'], gitmeyen_saat['Kisi'], color='#F44336', alpha=0.7)
            ax.set_title('Gitmeyenlerin Saatlik Dağılımı', fontsize=14)
            ax.set_xlabel('Saat')
            ax.set_ylabel('Kişi Sayısı')
            ax.grid(True, alpha=0.3)
            st.pyplot(fig_git)
    else:
        st.info("Bu filtrelerde gitmeyen yolcu bulunamadı.")

# Tab 4: Aktarma Yapanlar (AKTARMA=1)
with tab4:
    aktarma_data = filtered_df[filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1]
    aktarma_data = aktarma_data[aktarma_data['Hedef_Temiz'].notna()]
    if not aktarma_data.empty:
        aktarma_ozet = aktarma_data.groupby(['YÖN', 'Hedef_Temiz']).size().reset_index(name='Kisi')
        aktarma_ozet = aktarma_ozet.sort_values('Kisi', ascending=False)
        st.dataframe(aktarma_ozet, use_container_width=True, height=400)
        
        col_a1, col_a2 = st.columns(2)
        col_a1.metric("Toplam Aktarma Yapan", f"{len(aktarma_data):,}")
        col_a2.metric("Aktarma Yüzdesi", f"{(len(aktarma_data)/len(filtered_df)*100):.1f}%")
    else:
        st.info("Bu filtrelerde aktarma yapan yolcu bulunamadı.")

# Tab 5: Ham Veri
with tab5:
    st.dataframe(filtered_df, use_container_width=True, height=500)
    st.caption(f"Toplam {len(filtered_df):,} satır gösteriliyor.")

# ------------------------------
# ALT BİLGİ
# ------------------------------
st.markdown("---")
st.caption("⛴️ Vapur Hattı Analiz Dashboard | Veri: 20260506_2_REV5.xlsx | Tüm hakları saklıdır.")
