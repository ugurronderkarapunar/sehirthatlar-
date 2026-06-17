import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Vapur Hattı Analiz Dashboard", layout="wide")
st.title("🚢 Üsküdar – Beşiktaş Vapur Hattı Detaylı Analiz ve Tahmin Aracı")

# ------------------------------
# DOSYA YÜKLEME
# ------------------------------
uploaded_file = st.file_uploader("📂 Excel dosyasını yükleyin (20260506_2_REV5.xlsx)", type=["xlsx"])

if uploaded_file is None:
    st.warning("Lütfen Excel dosyasını yükleyin.")
    st.stop()

# ------------------------------
# VERİYİ OKU VE TEMİZLE
# ------------------------------
df = pd.read_excel(uploaded_file, sheet_name='Sayfa2')
df.columns = df.columns.str.strip()

df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(
    df['MERKEZDEN GEMİYE BİNİŞ'], 
    format='mixed', 
    errors='coerce'
)
df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])

df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
df['Saat_Dilimi'] = df['Saat'].apply(lambda x: f"{x:02d}:00–{x:02d}:59")
df['YÖN'] = df['YÖN'].str.strip()

st.success(f"✅ Veri başarıyla yüklendi! Toplam {df.shape[0]} satır.")

# ------------------------------
# YÖNLERE GÖRE AYIR
# ------------------------------
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

# ------------------------------
# FONKSİYON: DETAYLI ANALİZ
# ------------------------------
def detayli_analiz(df_yon, yon_adi):
    """Yön bazında tüm detaylı analizleri yapar"""
    
    # 1. Saatlik biniş
    binme = df_yon.groupby('Saat_Dilimi').size().reset_index(name='Toplam_Binme')
    binme['Saat'] = binme['Saat_Dilimi'].str[:2].astype(int)
    binme = binme.sort_values('Saat')
    
    # 2. Geliş hatları (nereden geldi)
    gelis_df = df_yon[df_yon['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
    gelis_df = gelis_df[gelis_df['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
    gelis = gelis_df.groupby(
        ['Saat_Dilimi', 'MERKEZE GELDİĞİ ARACIN HATTI']
    ).size().reset_index(name='Kisi_Sayisi')
    gelis.rename(columns={'MERKEZE GELDİĞİ ARACIN HATTI': 'Gelis_Hatti'}, inplace=True)
    gelis['Saat'] = gelis['Saat_Dilimi'].str[:2].astype(int)
    gelis = gelis.sort_values(['Saat', 'Gelis_Hatti'])
    
    # 3. Gidilen yerler (aktarma yapanlar)
    giden_df = df_yon[
        (df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].notna() & 
         df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip().notna() & 
         (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR'))
    ]
    gidis = giden_df.groupby(
        ['Saat_Dilimi', 'İNDİKTEN SONRA NEREYE GİTTİ']
    ).size().reset_index(name='Kisi_Sayisi')
    gidis.rename(columns={'İNDİKTEN SONRA NEREYE GİTTİ': 'Gidilen_Yer'}, inplace=True)
    gidis['Saat'] = gidis['Saat_Dilimi'].str[:2].astype(int)
    gidis = gidis.sort_values(['Saat', 'Gidilen_Yer'])
    
    # 4. Gitmeyenler (aktarma yapmayanlar)
    gitmeyen_df = df_yon[
        (df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].isna()) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() == '') |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'] == 'BİLİNMİYOR')
    ]
    gitmeyen = gitmeyen_df.groupby('Saat_Dilimi').size().reset_index(name='Gitmeyen_Sayisi')
    gitmeyen['Saat'] = gitmeyen['Saat_Dilimi'].str[:2].astype(int)
    gitmeyen = gitmeyen.sort_values('Saat')
    
    # 5. Tüm detay veriler (her bir yolcu hareketi)
    detay = df_yon[['Saat_Dilimi', 'MERKEZE GELDİĞİ ARACIN HATTI', 'İNDİKTEN SONRA NEREYE GİTTİ']].copy()
    detay.columns = ['Saat_Dilimi', 'Geldigi_Hat', 'Gittigi_Yer']
    
    return {
        'binme': binme,
        'gelis': gelis,
        'gidis': gidis,
        'gitmeyen': gitmeyen,
        'detay': detay,
        'toplam': df_yon.shape[0],
        'ortalama': df_yon.shape[0] / 24
    }

# ------------------------------
# ANALİZLERİ ÇALIŞTIR
# ------------------------------
analiz_u = detayli_analiz(df_uskudar, 'Üsküdar→Beşiktaş')
analiz_b = detayli_analiz(df_besiktas, 'Beşiktaş→Üsküdar')

# ------------------------------
# TAHMİN VERİSİ
# ------------------------------
tum_gidis = df[
    (df['İNDİKTEN SONRA NEREYE GİTTİ'].notna()) &
    (df['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip().notna()) &
    (df['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR')
].copy()
tum_gidis['Saat'] = tum_gidis['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
tahmin_df = tum_gidis.groupby(
    ['YÖN', 'İNDİKTEN SONRA NEREYE GİTTİ', 'Saat']
).size().reset_index(name='Tahmini_Yolcu_Sayisi')

# ------------------------------
# DASHBOARD - TAB'LER
# ------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Üsküdar → Beşiktaş", 
    "📊 Beşiktaş → Üsküdar", 
    "🔮 Tahmin Aracı",
    "📈 Karşılaştırma"
])

# ----- TAB 1: Üsküdar → Beşiktaş -----
with tab1:
    st.header("🚢 Üsküdar → Beşiktaş Hattı Detaylı Analiz")
    
    # Özet kartlar
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Biniş", f"{analiz_u['toplam']:,}")
    c2.metric("Ortalama/Saat", f"{analiz_u['ortalama']:.1f}")
    c3.metric("Aktarma Yapan", f"{analiz_u['gidis']['Kisi_Sayisi'].sum():,}")
    c4.metric("Gitmeyen", f"{analiz_u['gitmeyen']['Gitmeyen_Sayisi'].sum():,}")
    
    # 1. Saatlik Biniş Grafiği
    st.subheader("📊 Saat Dilimine Göre Biniş Sayısı")
    fig1 = px.bar(
        analiz_u['binme'],
        x='Saat_Dilimi',
        y='Toplam_Binme',
        title='Saatlik Biniş Dağılımı',
        labels={'Saat_Dilimi': 'Saat', 'Toplam_Binme': 'Kişi Sayısı'},
        color='Toplam_Binme',
        color_continuous_scale='Blues'
    )
    fig1.update_layout(height=400)
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. En çok gidilen yerler
    st.subheader("📍 İndikten Sonra Gidilen Yerler (Tümü)")
    top10_gidis = analiz_u['gidis'].groupby('Gidilen_Yer')['Kisi_Sayisi'].sum().nlargest(10).reset_index()
    fig2 = px.pie(
        top10_gidis,
        values='Kisi_Sayisi',
        names='Gidilen_Yer',
        title='En Çok Gidilen 10 Yer',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)
    
    # 3. Tüm gidilen yerler (saat dilimine göre)
    with st.expander("📋 Tüm Gidilen Yerler (Saat Dilimine Göre Detaylı)"):
        st.dataframe(analiz_u['gidis'], use_container_width=True)
        # Pivot tablo
        pivot_u = analiz_u['gidis'].pivot(index='Gidilen_Yer', columns='Saat_Dilimi', values='Kisi_Sayisi').fillna(0)
        st.dataframe(pivot_u, use_container_width=True)
    
    # 4. Nereden geldi (geliş hatları)
    with st.expander("🚌 Nereden Geldi (Geliş Hatları)"):
        st.dataframe(analiz_u['gelis'], use_container_width=True)
        pivot_gelis_u = analiz_u['gelis'].pivot(index='Gelis_Hatti', columns='Saat_Dilimi', values='Kisi_Sayisi').fillna(0)
        st.dataframe(pivot_gelis_u, use_container_width=True)
    
    # 5. Gitmeyenler
    with st.expander("🚫 İndikten Sonra Hiçbir Yere Gitmeyenler"):
        st.dataframe(analiz_u['gitmeyen'], use_container_width=True)
    
    # 6. Her bir yolcu hareketi (detay)
    with st.expander("🔍 Her Bir Yolcu Hareketi (Detay)"):
        st.dataframe(analiz_u['detay'].head(200), use_container_width=True)

# ----- TAB 2: Beşiktaş → Üsküdar -----
with tab2:
    st.header("🚢 Beşiktaş → Üsküdar Hattı Detaylı Analiz")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Biniş", f"{analiz_b['toplam']:,}")
    c2.metric("Ortalama/Saat", f"{analiz_b['ortalama']:.1f}")
    c3.metric("Aktarma Yapan", f"{analiz_b['gidis']['Kisi_Sayisi'].sum():,}")
    c4.metric("Gitmeyen", f"{analiz_b['gitmeyen']['Gitmeyen_Sayisi'].sum():,}")
    
    st.subheader("📊 Saat Dilimine Göre Biniş Sayısı")
    fig1 = px.bar(
        analiz_b['binme'],
        x='Saat_Dilimi',
        y='Toplam_Binme',
        title='Saatlik Biniş Dağılımı',
        labels={'Saat_Dilimi': 'Saat', 'Toplam_Binme': 'Kişi Sayısı'},
        color='Toplam_Binme',
        color_continuous_scale='Oranges'
    )
    fig1.update_layout(height=400)
    st.plotly_chart(fig1, use_container_width=True)
    
    st.subheader("📍 İndikten Sonra Gidilen Yerler (Tümü)")
    top10_gidis_b = analiz_b['gidis'].groupby('Gidilen_Yer')['Kisi_Sayisi'].sum().nlargest(10).reset_index()
    fig2 = px.pie(
        top10_gidis_b,
        values='Kisi_Sayisi',
        names='Gidilen_Yer',
        title='En Çok Gidilen 10 Yer',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)
    
    with st.expander("📋 Tüm Gidilen Yerler (Saat Dilimine Göre Detaylı)"):
        st.dataframe(analiz_b['gidis'], use_container_width=True)
        pivot_b = analiz_b['gidis'].pivot(index='Gidilen_Yer', columns='Saat_Dilimi', values='Kisi_Sayisi').fillna(0)
        st.dataframe(pivot_b, use_container_width=True)
    
    with st.expander("🚌 Nereden Geldi (Geliş Hatları)"):
        st.dataframe(analiz_b['gelis'], use_container_width=True)
        pivot_gelis_b = analiz_b['gelis'].pivot(index='Gelis_Hatti', columns='Saat_Dilimi', values='Kisi_Sayisi').fillna(0)
        st.dataframe(pivot_gelis_b, use_container_width=True)
    
    with st.expander("🚫 İndikten Sonra Hiçbir Yere Gitmeyenler"):
        st.dataframe(analiz_b['gitmeyen'], use_container_width=True)
    
    with st.expander("🔍 Her Bir Yolcu Hareketi (Detay)"):
        st.dataframe(analiz_b['detay'].head(200), use_container_width=True)

# ----- TAB 3: Tahmin Aracı -----
with tab3:
    st.header("🔮 Tahmin Aracı")
    st.info("Yön, gidilecek yer ve saat seçerek tahmini yolcu sayısını görebilirsiniz.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        yon_sec = st.selectbox("📍 Yön", ['ÜSKÜDAR → BEŞİKTAŞ', 'BEŞİKTAŞ → ÜSKÜDAR'])
    with col2:
        hedef_list = sorted(tahmin_df[tahmin_df['YÖN'] == yon_sec]['İNDİKTEN SONRA NEREYE GİTTİ'].unique())
        hedef_sec = st.selectbox("🎯 Gidilecek Yer", hedef_list)
    with col3:
        saat_sec = st.slider("⏰ Saat", 0, 23, 8)
    
    tahmin_sonuc = tahmin_df[
        (tahmin_df['YÖN'] == yon_sec) &
        (tahmin_df['İNDİKTEN SONRA NEREYE GİTTİ'] == hedef_sec) &
        (tahmin_df['Saat'] == saat_sec)
    ]
    
    if not tahmin_sonuc.empty:
        st.success(f"📊 Tahmini Yolcu Sayısı: **{tahmin_sonuc['Tahmini_Yolcu_Sayisi'].iloc[0]}** kişi")
    else:
        st.info("Bu kombinasyonda veri bulunamadı. Tahmin: 0 kişi")
    
    # Saatlik tahmin grafiği
    st.subheader("📈 Seçilen Hedef için Saatlik Tahmin")
    hedef_tahmin = tahmin_df[(tahmin_df['YÖN'] == yon_sec) & (tahmin_df['İNDİKTEN SONRA NEREYE GİTTİ'] == hedef_sec)]
    if not hedef_tahmin.empty:
        fig = px.bar(
            hedef_tahmin,
            x='Saat',
            y='Tahmini_Yolcu_Sayisi',
            title=f'{yon_sec} - {hedef_sec} için Saatlik Tahmin',
            labels={'Saat': 'Saat', 'Tahmini_Yolcu_Sayisi': 'Tahmini Yolcu Sayısı'},
            color='Tahmini_Yolcu_Sayisi',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)

# ----- TAB 4: Karşılaştırma -----
with tab4:
    st.header("📈 İki Yönün Karşılaştırması")
    
    # Özet karşılaştırma
    karsilastirma = pd.DataFrame({
        'Yön': ['Üsküdar→Beşiktaş', 'Beşiktaş→Üsküdar'],
        'Toplam_Biniş': [analiz_u['toplam'], analiz_b['toplam']],
        'Aktarma_Yapan': [analiz_u['gidis']['Kisi_Sayisi'].sum(), analiz_b['gidis']['Kisi_Sayisi'].sum()],
        'Gitmeyen': [analiz_u['gitmeyen']['Gitmeyen_Sayisi'].sum(), analiz_b['gitmeyen']['Gitmeyen_Sayisi'].sum()],
        'Aktarma_Oranı': [
            analiz_u['gidis']['Kisi_Sayisi'].sum() / analiz_u['toplam'] * 100,
            analiz_b['gidis']['Kisi_Sayisi'].sum() / analiz_b['toplam'] * 100
        ]
    })
    karsilastirma['Aktarma_Oranı'] = karsilastirma['Aktarma_Oranı'].round(1)
    st.dataframe(karsilastirma, use_container_width=True)
    
    # Karşılaştırma grafiği
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=karsilastirma['Yön'],
        y=karsilastirma['Toplam_Biniş'],
        name='Toplam Biniş',
        marker_color='blue'
    ))
    fig.add_trace(go.Bar(
        x=karsilastirma['Yön'],
        y=karsilastirma['Aktarma_Yapan'],
        name='Aktarma Yapan',
        marker_color='green'
    ))
    fig.add_trace(go.Bar(
        x=karsilastirma['Yön'],
        y=karsilastirma['Gitmeyen'],
        name='Gitmeyen',
        marker_color='red'
    ))
    fig.update_layout(
        title='İki Yönün Karşılaştırması',
        barmode='group',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    # Zaman serisi karşılaştırma (saatlik)
    st.subheader("⏰ Saatlik Karşılaştırma")
    saat_karsilastirma = pd.merge(
        analiz_u['binme'][['Saat', 'Toplam_Binme']],
        analiz_b['binme'][['Saat', 'Toplam_Binme']],
        on='Saat',
        suffixes=('_Uskudar', '_Besiktas')
    )
    fig2 = px.line(
        saat_karsilastirma,
        x='Saat',
        y=['Toplam_Binme_Uskudar', 'Toplam_Binme_Besiktas'],
        title='Saatlik Biniş Karşılaştırması',
        labels={'value': 'Kişi Sayısı', 'variable': 'Yön'},
        color_discrete_map={
            'Toplam_Binme_Uskudar': 'blue',
            'Toplam_Binme_Besiktas': 'orange'
        }
    )
    st.plotly_chart(fig2, use_container_width=True)

st.success("✅ Tüm analizler tamamlandı! Yukarıdaki sekmeleri kullanarak detayları inceleyebilirsiniz.")
