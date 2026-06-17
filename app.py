import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from datetime import datetime

# ------------------------------
# Sayfa ayarları
# ------------------------------
st.set_page_config(
    page_title="🚢 Vapur Hattı Analiz Dashboard",
    page_icon="⛴️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# CSS
# ------------------------------
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 1rem;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">⛴️ Üsküdar – Beşiktaş Vapur Hattı Analiz ve Tahmin Aracı</div>', unsafe_allow_html=True)

# ------------------------------
# Sidebar - Dosya yükleme
# ------------------------------
with st.sidebar:
    st.header("📂 Veri Yükle")
    uploaded_file = st.file_uploader("Excel dosyasını yükleyin", type=["xlsx"])
    
    if uploaded_file is None:
        st.warning("Lütfen bir Excel dosyası yükleyin.")
        st.stop()

# ------------------------------
# VERİ YÜKLEME VE TEMİZLEME
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
    df['KART_TIPI'] = df['KART TİPİ'].str.strip() if 'KART TİPİ' in df.columns else 'Bilinmiyor'
    
    # Hedef temizleme
    df['Hedef_Temiz'] = df['İNDİKTEN SONRA NEREYE GİTTİ'].apply(
        lambda x: str(x).strip() if pd.notna(x) and str(x).strip() not in ['', 'BİLİNMİYOR', 'nan'] else None
    )
    
    return df

df = load_data(uploaded_file)
st.success(f"✅ Veri başarıyla yüklendi! Toplam {df.shape[0]:,} satır.")

# ------------------------------
# Sidebar - Filtreler
# ------------------------------
with st.sidebar:
    st.header("🔍 Filtreler")
    
    yon_filter = st.multiselect(
        "Yön Seçiniz",
        options=df['YÖN'].unique(),
        default=df['YÖN'].unique()
    )
    
    saat_range = st.slider(
        "Saat Aralığı",
        min_value=0, max_value=23,
        value=(6, 22)
    )
    
    kart_tipleri = df['KART_TIPI'].unique()
    kart_tipleri = [k for k in kart_tipleri if k and k != 'Bilinmiyor']
    kart_filter = st.multiselect(
        "Kart Tipi (Opsiyonel)",
        options=sorted(kart_tipleri),
        default=[]
    )
    
    hedef_list = df[df['Hedef_Temiz'].notna()]['Hedef_Temiz'].unique()
    hedef_list = sorted([h for h in hedef_list if h and h != 'None'])
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
if kart_filter:
    filtered_df = filtered_df[filtered_df['KART_TIPI'].isin(kart_filter)]
if hedef_filter:
    filtered_df = filtered_df[filtered_df['Hedef_Temiz'].isin(hedef_filter)]

# ------------------------------
# METRİK KARTLAR
# ------------------------------
st.subheader("📊 Özet İstatistikler")

total = len(filtered_df)
total_uskudar = len(filtered_df[filtered_df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ'])
total_besiktas = len(filtered_df[filtered_df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR'])

aktarma = len(filtered_df[filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1])
gitmeyen = len(filtered_df[
    (filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
    (filtered_df['Hedef_Temiz'].isna())
])

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Toplam Yolcu", f"{total:,}")
col2.metric("Üsküdar→Beşiktaş", f"{total_uskudar:,}")
col3.metric("Beşiktaş→Üsküdar", f"{total_besiktas:,}")
col4.metric("Aktarma Yapan", f"{aktarma:,}", delta=f"%{aktarma/total*100:.1f}" if total > 0 else "0%")
col5.metric("Gitmeyen (Aktarma Yok)", f"{gitmeyen:,}", delta=f"%{gitmeyen/total*100:.1f}" if total > 0 else "0%")

# ------------------------------
# SAATLİK BİNİŞ GRAFİKLERİ
# ------------------------------
st.subheader("📈 Saatlik Biniş Dağılımı")

fig, axes = plt.subplots(1, 2, figsize=(16, 5))

df_u = filtered_df[filtered_df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
binme_u = df_u.groupby('Saat').size().reset_index(name='Yolcu')
axes[0].bar(binme_u['Saat'], binme_u['Yolcu'], color='#1E88E5', edgecolor='white', alpha=0.8)
axes[0].set_title('Üsküdar → Beşiktaş', fontsize=14, fontweight='bold')
axes[0].set_xlabel('Saat', fontsize=12)
axes[0].set_ylabel('Yolcu Sayısı', fontsize=12)
axes[0].grid(True, alpha=0.3)
axes[0].set_xticks(range(0, 24))
if not binme_u.empty:
    max_idx = binme_u['Yolcu'].idxmax()
    axes[0].axvline(binme_u.loc[max_idx, 'Saat'], color='red', linestyle='--', alpha=0.5, label='Tepe Saat')
    axes[0].legend()

df_b = filtered_df[filtered_df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']
binme_b = df_b.groupby('Saat').size().reset_index(name='Yolcu')
axes[1].bar(binme_b['Saat'], binme_b['Yolcu'], color='#FF9800', edgecolor='white', alpha=0.8)
axes[1].set_title('Beşiktaş → Üsküdar', fontsize=14, fontweight='bold')
axes[1].set_xlabel('Saat', fontsize=12)
axes[1].set_ylabel('Yolcu Sayısı', fontsize=12)
axes[1].grid(True, alpha=0.3)
axes[1].set_xticks(range(0, 24))
if not binme_b.empty:
    max_idx = binme_b['Yolcu'].idxmax()
    axes[1].axvline(binme_b.loc[max_idx, 'Saat'], color='red', linestyle='--', alpha=0.5, label='Tepe Saat')
    axes[1].legend()

plt.tight_layout()
st.pyplot(fig)

# ------------------------------
# KART TİPİ ANALİZİ
# ------------------------------
st.subheader("🎫 Kart Tipi Dağılımı")

kart_df = filtered_df[filtered_df['KART_TIPI'].notna()]
if not kart_df.empty:
    kart_ozet = kart_df.groupby(['YÖN', 'KART_TIPI']).size().reset_index(name='Kisi')
    fig_kart, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=kart_ozet, x='KART_TIPI', y='Kisi', hue='YÖN', ax=ax, palette=['#1E88E5', '#FF9800'])
    ax.set_title('Kart Tipine Göre Yolcu Dağılımı', fontsize=14)
    ax.set_xlabel('Kart Tipi')
    ax.set_ylabel('Kişi Sayısı')
    ax.legend(title='Yön')
    st.pyplot(fig_kart)
    
    with st.expander("📋 Kart Tipi Detaylı Tablo"):
        st.dataframe(kart_ozet, use_container_width=True)

# ------------------------------
# TAHMİN ARACI
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
        hedef_list_tahmin = sorted([h for h in hedef_list_tahmin if h and h != 'None'])
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
    tahmin_sayisi = len(df[
        (df['YÖN'] == tahmin_yon) &
        (df['Hedef_Temiz'] == tahmin_hedef) &
        (df['Saat'] == tahmin_saat)
    ])
    
    saatlik_ortalama = df[
        (df['YÖN'] == tahmin_yon) &
        (df['Hedef_Temiz'] == tahmin_hedef)
    ].groupby('Saat').size().mean()
    
    en_yogun = df[
        (df['YÖN'] == tahmin_yon) &
        (df['Hedef_Temiz'] == tahmin_hedef)
    ].groupby('Saat').size().idxmax() if not df.empty else None
    
    st.markdown("---")
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    col_r1.metric("📊 Tahmini Yolcu", f"{tahmin_sayisi} kişi")
    col_r2.metric("📈 Saatlik Ortalama", f"{saatlik_ortalama:.1f} kişi")
    col_r3.metric("🔥 En Yoğun Saat", f"{en_yogun}:00" if en_yogun is not None else "-")
    col_r4.metric("📌 Toplam (Tüm Saatler)", 
                  f"{df[(df['YÖN'] == tahmin_yon) & (df['Hedef_Temiz'] == tahmin_hedef)].shape[0]:,} kişi")
    
    trend_df = df[
        (df['YÖN'] == tahmin_yon) &
        (df['Hedef_Temiz'] == tahmin_hedef)
    ].groupby('Saat').size().reset_index(name='Yolcu')
    
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
else:
    if tahmin_hedef == 'Veri Yok':
        st.info("Bu yön için hedef verisi bulunamadı. Lütfen başka bir yön seçin.")

# ------------------------------
# DETAYLI TABLOLAR (Harita Tab'ı Kaldırıldı)
# ------------------------------
st.subheader("📋 Detaylı Veri Tabloları")

tab1, tab2, tab3, tab4 = st.tabs([
    "📍 Nereden Geldi?", 
    "🎯 Nereye Gitti?",
    "🚫 Gitmeyenler", 
    "📊 Tüm Veri"
])

with tab1:
    gelis_data = filtered_df[filtered_df['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
    gelis_data = gelis_data[gelis_data['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
    if not gelis_data.empty:
        gelis_ozet = gelis_data.groupby(['YÖN', 'MERKEZE GELDİĞİ ARACIN HATTI']).size().reset_index(name='Kisi')
        gelis_ozet = gelis_ozet.sort_values('Kisi', ascending=False)
        st.dataframe(gelis_ozet, use_container_width=True)
        
        fig_gelis, ax = plt.subplots(figsize=(10, 4))
        top_gelis = gelis_ozet.groupby('MERKEZE GELDİĞİ ARACIN HATTI')['Kisi'].sum().nlargest(10).reset_index()
        ax.barh(top_gelis['MERKEZE GELDİĞİ ARACIN HATTI'], top_gelis['Kisi'], color='#4CAF50')
        ax.set_title('En Çok Gelinilen 10 Hat', fontsize=14)
        ax.set_xlabel('Kişi Sayısı')
        st.pyplot(fig_gelis)
    else:
        st.info("Geliş hattı verisi bulunamadı.")

with tab2:
    gidis_data_tab2 = filtered_df[filtered_df['Hedef_Temiz'].notna()]
    if not gidis_data_tab2.empty:
        gidis_ozet = gidis_data_tab2.groupby(['YÖN', 'Hedef_Temiz']).size().reset_index(name='Kisi')
        gidis_ozet = gidis_ozet.sort_values('Kisi', ascending=False)
        st.dataframe(gidis_ozet, use_container_width=True)
        
        fig_gidis, ax = plt.subplots(figsize=(10, 4))
        top_gidis = gidis_ozet.groupby('Hedef_Temiz')['Kisi'].sum().nlargest(10).reset_index()
        ax.barh(top_gidis['Hedef_Temiz'], top_gidis['Kisi'], color='#FF5722')
        ax.set_title('En Çok Gidilen 10 Yer', fontsize=14)
        ax.set_xlabel('Kişi Sayısı')
        st.pyplot(fig_gidis)
    else:
        st.info("Gidiş verisi bulunamadı.")

with tab3:
    gitmeyen_data = filtered_df[
        (filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
        (filtered_df['Hedef_Temiz'].isna())
    ]
    if not gitmeyen_data.empty:
        gitmeyen_ozet = gitmeyen_data.groupby(['YÖN']).size().reset_index(name='Kisi')
        st.dataframe(gitmeyen_ozet, use_container_width=True)
        st.metric("Toplam Gitmeyen", f"{len(gitmeyen_data):,}")
    else:
        st.info("Gitmeyen verisi bulunamadı.")

with tab4:
    st.dataframe(filtered_df.head(200), use_container_width=True)
    st.caption(f"Toplam {len(filtered_df):,} satır gösteriliyor (ilk 200).")

# ------------------------------
# ALT BİLGİ
# ------------------------------
st.markdown("---")
st.caption("⛴️ Vapur Hattı Analiz Dashboard | Veri: 20260506_2_REV5.xlsx | Tüm hakları saklıdır.")
