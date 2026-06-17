import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ----------------------------
# 1. VERİYİ OKU VE TEMİZLE
# ----------------------------
@st.cache_data
def load_data():
    df = pd.read_excel('data/20260506_2_REV5.xlsx', sheet_name='Sayfa2')
    df.columns = df.columns.str.strip()
    df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(df['MERKEZDEN GEMİYE BİNİŞ'], format='mixed', errors='coerce')
    df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])
    df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
    df['Saat_Dilimi'] = df['Saat'].apply(lambda x: f"{x:02d}:00–{x:02d}:59")
    df['YÖN'] = df['YÖN'].str.strip()
    return df

df = load_data()

# ----------------------------
# 2. SİDEBAR - NAVİGASYON
# ----------------------------
st.set_page_config(page_title="Vapur Yolcu Analizi", layout="wide")
st.sidebar.title("🚢 Navigasyon")
secenek = st.sidebar.radio(
    "Gitmek istediğiniz sayfayı seçin:",
    ["📊 Dashboard", "🔮 Tahmin Aracı", "📈 Veri Analizi"]
)

# ----------------------------
# 3. DASHBOARD SAYFASI
# ----------------------------
if secenek == "📊 Dashboard":
    st.title("🚢 Üsküdar – Beşiktaş Vapur Hattı Yolcu Analiz Dashboard")
    st.markdown("---")
    
    # Yön seçimi
    yon = st.selectbox("Yön seçin:", df['YÖN'].unique())
    df_yon = df[df['YÖN'] == yon]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam Biniş", f"{df_yon.shape[0]:,}")
    with col2:
        ortalama = df_yon.shape[0] / 24
        st.metric("Ortalama / Saat", f"{ortalama:.1f}")
    with col3:
        gitmeyen = df_yon[df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0].shape[0]
        st.metric("Aktarma Yapmayan", f"{gitmeyen:,}")
    with col4:
        giden = df_yon[df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1].shape[0]
        st.metric("Aktarma Yapan", f"{giden:,}")
    
    st.markdown("---")
    
    # Grafik 1: Saatlik biniş
    st.subheader("Saat Dilimine Göre Biniş Sayısı")
    saatlik = df_yon.groupby('Saat_Dilimi').size().reset_index(name='Toplam')
    fig, ax = plt.subplots(figsize=(12, 4))
    sns.barplot(data=saatlik, x='Saat_Dilimi', y='Toplam', palette='Blues_d', ax=ax)
    ax.set_xlabel('Saat Dilimi')
    ax.set_ylabel('Kişi Sayısı')
    ax.tick_params(axis='x', rotation=45)
    st.pyplot(fig)
    
    # Grafik 2: Nereden geldi (en çok 10)
    st.subheader("En Çok Gelinilen Hatlar (Top 10)")
    gelis = df_yon[df_yon['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
    gelis = gelis[gelis['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
    gelis_top = gelis.groupby('MERKEZE GELDİĞİ ARACIN HATTI').size().nlargest(10).reset_index(name='Kisi')
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=gelis_top, y='MERKEZE GELDİĞİ ARACIN HATTI', x='Kisi', palette='Greens_d', ax=ax)
    ax.set_xlabel('Kişi Sayısı')
    ax.set_ylabel('Geliş Hattı')
    st.pyplot(fig)
    
    # Grafik 3: Nereye gidiyor (tüm yerler)
    st.subheader("İndikten Sonra Gidilen Yerler")
    giden_df = df_yon[
        (df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].notna() & 
         df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip().notna() & 
         (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR'))
    ]
    gidis = giden_df.groupby('İNDİKTEN SONRA NEREYE GİTTİ').size().reset_index(name='Kisi')
    gidis = gidis.sort_values('Kisi', ascending=False)
    st.dataframe(gidis, use_container_width=True)
    
    # Gitmeyenlerin saatlik dağılımı
    st.subheader("Aktarma Yapmayanların Saatlik Dağılımı")
    gitmeyen_df = df_yon[
        (df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].isna()) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() == '') |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'] == 'BİLİNMİYOR')
    ]
    gitmeyen_saat = gitmeyen_df.groupby('Saat_Dilimi').size().reset_index(name='Gitmeyen')
    fig, ax = plt.subplots(figsize=(12, 4))
    sns.barplot(data=gitmeyen_saat, x='Saat_Dilimi', y='Gitmeyen', palette='Reds_d', ax=ax)
    ax.set_xlabel('Saat Dilimi')
    ax.set_ylabel('Gitmeyen Kişi Sayısı')
    ax.tick_params(axis='x', rotation=45)
    st.pyplot(fig)

# ----------------------------
# 4. TAHMİN ARACI
# ----------------------------
elif secenek == "🔮 Tahmin Aracı":
    st.title("🔮 Yolcu Tahmin Aracı")
    st.markdown("Bu bölümde, seçtiğiniz yön, saat ve varış yerine göre tahmini yolcu sayısını hesaplayabilirsiniz.")
    
    # Kullanıcı seçimleri
    yon = st.selectbox("Yön seçin:", df['YÖN'].unique())
    df_yon = df[df['YÖN'] == yon]
    
    # Varış yeri seçimi
    giden_df = df_yon[
        (df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].notna() & 
         df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip().notna() & 
         (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR'))
    ]
    yerler = ['Hepsi'] + sorted(giden_df['İNDİKTEN SONRA NEREYE GİTTİ'].unique().tolist())
    varis = st.selectbox("Gidilecek yer (isteğe bağlı):", yerler)
    
    saat = st.slider("Saat (0-23):", 0, 23, 8)
    
    # Tahmin butonu
    if st.button("Tahmin Yap"):
        st.subheader("📊 Tahmin Sonuçları")
        
        # Veriyi hazırla
        if varis == 'Hepsi':
            model_df = giden_df.copy()
        else:
            model_df = giden_df[giden_df['İNDİKTEN SONRA NEREYE GİTTİ'] == varis].copy()
        
        if model_df.empty:
            st.warning("Bu kriterlere uygun veri bulunamadı. Lütfen farklı seçimler yapın.")
        else:
            # Saat bazında ortalama tahmin (basit ortalama)
            saatlik_ortalama = model_df.groupby('Saat').size().reset_index(name='Kisi')
            # Eksik saatleri doldur
            tum_saatler = pd.DataFrame({'Saat': range(24)})
            saatlik_ortalama = tum_saatler.merge(saatlik_ortalama, on='Saat', how='left').fillna(0)
            
            # Tahmini bul
            tahmin = saatlik_ortalama[saatlik_ortalama['Saat'] == saat]['Kisi'].values[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tahmini Yolcu Sayısı", f"{int(tahmin)}")
                st.caption(f"{yon} yönünde, saat {saat:02d}:00 civarında")
                if varis != 'Hepsi':
                    st.caption(f"Hedef: {varis}")
                else:
                    st.caption("Tüm hedefler dahil")
            
            with col2:
                # Geçmiş veriyi göster
                st.write("**Geçmiş Saatlik Veriler**")
                st.dataframe(saatlik_ortalama)
            
            # Grafik
            fig, ax = plt.subplots(figsize=(10, 4))
            sns.barplot(data=saatlik_ortalama, x='Saat', y='Kisi', palette='viridis', ax=ax)
            ax.axvline(x=saat, color='red', linestyle='--', label='Tahmin Saati')
            ax.set_xlabel('Saat')
            ax.set_ylabel('Kişi Sayısı')
            ax.legend()
            st.pyplot(fig)

# ----------------------------
# 5. VERİ ANALİZİ SAYFASI
# ----------------------------
elif secenek == "📈 Veri Analizi":
    st.title("📈 Detaylı Veri Analizi")
    st.markdown("Tüm veri seti ve ham veriler.")
    
    st.subheader("Veri Seti Önizleme")
    st.dataframe(df.head(100))
    
    st.subheader("Veri Hakkında Bilgi")
    st.write("Toplam satır:", df.shape[0])
    st.write("Sütunlar:", df.columns.tolist())
    st.write("Eksik veri durumu:")
    st.dataframe(df.isnull().sum().reset_index(name='Eksik_Sayisi'))
    
    # İki yön için karşılaştırmalı grafik
    st.subheader("Yön Karşılaştırması")
    yon_saat = df.groupby(['YÖN', 'Saat']).size().reset_index(name='Kisi')
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.lineplot(data=yon_saat, x='Saat', y='Kisi', hue='YÖN', marker='o', ax=ax)
    ax.set_title('Saatlik Yolcu Sayısı (Yön Karşılaştırması)')
    ax.set_xlabel('Saat')
    ax.set_ylabel('Kişi Sayısı')
    st.pyplot(fig)

# ----------------------------
# 6. FOOTER
# ----------------------------
st.sidebar.markdown("---")
st.sidebar.info("📅 Veri: 2026-04-15\n📊 Güncel analiz")
