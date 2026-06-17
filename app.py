import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor

# Sayfa ayarları
st.set_page_config(
    page_title="🚢 Vapur Hattı Analiz Dashboard",
    page_icon="⛴️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS ile renk ve stil iyileştirmeleri
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

# Sidebar - Dosya yükleme
with st.sidebar:
    st.header("📂 Veri Yükle")
    uploaded_file = st.file_uploader("Excel dosyasını yükleyin", type=["xlsx"])
    
    if uploaded_file is None:
        st.warning("Lütfen bir Excel dosyası yükleyin.")
        st.stop()

# Veriyi oku ve temizle
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
    
    # Kart tipini temizle
    df['KART_TIPI'] = df['KART TİPİ'].str.strip() if 'KART TİPİ' in df.columns else df['KART TİPİ'].str.strip()
    df['KART_TIPI'] = df['KART_TIPI'].fillna('BİLİNMİYOR')
    
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
    
    # Kart tipi filtresi
    kart_list = df['KART_TIPI'].unique()
    kart_list = sorted([k for k in kart_list if k and k != 'None'])
    kart_filter = st.multiselect(
        "Kart Tipi (Opsiyonel)",
        options=kart_list,
        default=[]
    )
    
    # Hedef filtresi
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

col1, col2, col3, col4, col5 = st.columns(5)

total = len(filtered_df)
total_uskudar = len(filtered_df[filtered_df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ'])
total_besiktas = len(filtered_df[filtered_df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR'])

# En çok kullanılan kart tipi
en_cok_kart = filtered_df['KART_TIPI'].value_counts().index[0] if not filtered_df.empty else "Yok"
en_cok_kart_sayi = filtered_df['KART_TIPI'].value_counts().iloc[0] if not filtered_df.empty else 0

col1.metric("Toplam Yolcu", f"{total:,}")
col2.metric("Üsküdar→Beşiktaş", f"{total_uskudar:,}")
col3.metric("Beşiktaş→Üsküdar", f"{total_besiktas:,}")
col4.metric("En Çok Kart Tipi", f"{en_cok_kart}", delta=f"{en_cok_kart_sayi:,} kişi")
col5.metric("Kart Tipi Sayısı", f"{filtered_df['KART_TIPI'].nunique():,}")

# ------------------------------
# KART TİPİ DAĞILIMI (Plotly)
# ------------------------------
st.subheader("💳 Kart Tipi Dağılımı")

col_k1, col_k2 = st.columns(2)

with col_k1:
    # Kart tipi - yön bazında
    kart_yon = filtered_df.groupby(['YÖN', 'KART_TIPI']).size().reset_index(name='Kisi')
    fig_kart = px.bar(kart_yon, x='KART_TIPI', y='Kisi', color='YÖN',
                      title='Kart Tipi Dağılımı (Yön Bazında)',
                      labels={'Kisi':'Kişi Sayısı', 'KART_TIPI':'Kart Tipi'},
                      barmode='group',
                      color_discrete_map={'ÜSKÜDAR → BEŞİKTAŞ': '#1E88E5',
                                          'BEŞİKTAŞ → ÜSKÜDAR': '#FF9800'})
    fig_kart.update_layout(legend_title_text='Yön')
    st.plotly_chart(fig_kart, use_container_width=True)

with col_k2:
    # Kart tipi - saatlik dağılım (en çok kullanılan 5 kart)
    top_kartlar = filtered_df['KART_TIPI'].value_counts().nlargest(5).index.tolist()
    kart_saat = filtered_df[filtered_df['KART_TIPI'].isin(top_kartlar)]
    kart_saat_ozet = kart_saat.groupby(['Saat', 'KART_TIPI']).size().reset_index(name='Kisi')
    fig_kart_saat = px.line(kart_saat_ozet, x='Saat', y='Kisi', color='KART_TIPI',
                            title='En Çok Kullanılan 5 Kart Tipi (Saatlik)',
                            markers=True)
    fig_kart_saat.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
    st.plotly_chart(fig_kart_saat, use_container_width=True)

# ------------------------------
# SAATLİK BİNİŞ GRAFİKLERİ (Plotly)
# ------------------------------
st.subheader("📈 Saatlik Biniş Dağılımı")

col1, col2 = st.columns(2)

with col1:
    df_u = filtered_df[filtered_df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
    binme_u = df_u.groupby('Saat').size().reset_index(name='Yolcu')
    fig_u = px.bar(binme_u, x='Saat', y='Yolcu',
                   title='Üsküdar → Beşiktaş',
                   color_discrete_sequence=['#1E88E5'])
    if not binme_u.empty:
        max_saat = binme_u.loc[binme_u['Yolcu'].idxmax(), 'Saat']
        fig_u.add_vline(x=max_saat, line_dash="dash", line_color="red",
                       annotation_text="Tepe Saat", annotation_position="top right")
    fig_u.update_xaxes(dtick=1)
    st.plotly_chart(fig_u, use_container_width=True)

with col2:
    df_b = filtered_df[filtered_df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']
    binme_b = df_b.groupby('Saat').size().reset_index(name='Yolcu')
    fig_b = px.bar(binme_b, x='Saat', y='Yolcu',
                   title='Beşiktaş → Üsküdar',
                   color_discrete_sequence=['#FF9800'])
    if not binme_b.empty:
        max_saat_b = binme_b.loc[binme_b['Yolcu'].idxmax(), 'Saat']
        fig_b.add_vline(x=max_saat_b, line_dash="dash", line_color="red",
                       annotation_text="Tepe Saat", annotation_position="top right")
    fig_b.update_xaxes(dtick=1)
    st.plotly_chart(fig_b, use_container_width=True)

# ------------------------------
# TAHMİN ARACI (Mevcut, ML içermeyen versiyonu korundu)
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
    tahmin_df = df[
        (df['YÖN'] == tahmin_yon) &
        (df['Hedef_Temiz'] == tahmin_hedef) &
        (df['Saat'] == tahmin_saat)
    ]
    tahmin_sayisi = len(tahmin_df)
    
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
    col_r4.metric("📌 Toplam Yolcu", f"{df[(df['YÖN'] == tahmin_yon) & (df['Hedef_Temiz'] == tahmin_hedef)].shape[0]:,} kişi")
    
    trend_df = df[
        (df['YÖN'] == tahmin_yon) &
        (df['Hedef_Temiz'] == tahmin_hedef)
    ].groupby('Saat').size().reset_index(name='Yolcu')
    
    if not trend_df.empty:
        fig_trend = px.line(trend_df, x='Saat', y='Yolcu', markers=True,
                            title=f'{tahmin_yon} - {tahmin_hedef} Saatlik Yolcu Trendi')
        fig_trend.add_vline(x=tahmin_saat, line_dash="dash", line_color="red",
                           annotation_text="Seçilen Saat")
        fig_trend.update_xaxes(dtick=1)
        st.plotly_chart(fig_trend, use_container_width=True)
else:
    if tahmin_hedef == 'Veri Yok':
        st.info("Bu yön için hedef verisi bulunamadı. Lütfen başka bir yön seçin.")

# ------------------------------
# YENİ: Makine Öğrenmesi Özellikleri (K-Means Segmentasyon)
# ------------------------------
st.header("🧠 Makine Öğrenmesi Analizleri")

# K-Means segmentasyonu için veri hazırlığı ve model eğitimi (cache)
@st.cache_resource
def train_segmentation(df):
    seg = df.groupby(['Saat', 'YÖN']).agg(
        Toplam_Yolcu = ('MERKEZDEN GEMİYE BİNİŞ', 'count'),
        Aktarma_Orani = ('İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)', lambda x: x.mean() if x.notna().any() else 0),
        Kart_Cesidi = ('KART_TIPI', 'nunique'),
        EnCokKart_Orani = ('KART_TIPI', lambda x: x.value_counts(normalize=True).max())
    ).reset_index()
    
    hedef_c = df.groupby(['Saat', 'YÖN'])['Hedef_Temiz'].nunique().reset_index(name='Hedef_Cesidi')
    seg = seg.merge(hedef_c, on=['Saat','YÖN'], how='left')
    seg['Hedef_Cesidi'] = seg['Hedef_Cesidi'].fillna(0)
    
    X = seg[['Toplam_Yolcu', 'Aktarma_Orani', 'Kart_Cesidi', 'EnCokKart_Orani', 'Hedef_Cesidi']].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=4, random_state=42, n_init='auto')
    seg['Segment'] = kmeans.fit_predict(X_scaled)
    
    # Merkezleri orijinal ölçeğe dön
    centers = scaler.inverse_transform(kmeans.cluster_centers_)
    centers_df = pd.DataFrame(centers, columns=X.columns)
    centers_df['Segment'] = range(len(centers_df))
    
    return seg, kmeans, scaler, centers_df

seg_df, kmeans_model, scaler_model, centers_df = train_segmentation(df)

# Segmentasyon görselleri
st.subheader("👥 Yolcu Segmentleri (K-Means)")
col_seg1, col_seg2 = st.columns([3, 2])

with col_seg1:
    # Saatlik segment dağılımını gösteren scatter plot
    fig_seg = px.scatter(seg_df, x='Toplam_Yolcu', y='Aktarma_Orani', 
                         color=seg_df['Segment'].astype(str),
                         hover_data=['Saat', 'YÖN'],
                         title='Saatlik Yolcu Profillerinin Segmentasyonu',
                         labels={'Toplam_Yolcu': 'Toplam Yolcu', 'Aktarma_Orani': 'Aktarma Oranı',
                                 'color': 'Segment'})
    st.plotly_chart(fig_seg, use_container_width=True)

with col_seg2:
    st.markdown("**Segment Merkezleri (Özellik Ortalamaları)**")
    st.dataframe(centers_df.style.format("{:.2f}"))
    
    # Segment isimlendirme önerisi (manuel yorum)
    st.caption("""
    **Örnek Yorum:**  
    Segment 0: Sabah yoğun, düşük aktarma  
    Segment 1: Akşam orta yoğun, yüksek kart çeşidi  
    Segment 2: Gün içi düşük yolcu, yüksek hedef çeşidi  
    Segment 3: Yoğun, çok aktarma (aktarma merkezi)
    """)

# Kullanıcının mevcut filtreleriyle en yakın segmenti bulma
if not filtered_df.empty:
    simdi_profil = filtered_df.groupby('Saat').agg(
        Toplam_Yolcu = ('MERKEZDEN GEMİYE BİNİŞ', 'count'),
        Aktarma_Orani = ('İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)', lambda x: x.mean() if x.notna().any() else 0),
        Kart_Cesidi = ('KART_TIPI', 'nunique'),
        EnCokKart_Orani = ('KART_TIPI', lambda x: x.value_counts(normalize=True).max()),
        Hedef_Cesidi = ('Hedef_Temiz', 'nunique')
    ).reset_index()
    if len(simdi_profil) > 0:
        profil_ort = simdi_profil[['Toplam_Yolcu', 'Aktarma_Orani', 'Kart_Cesidi', 'EnCokKart_Orani', 'Hedef_Cesidi']].mean().values.reshape(1, -1)
        profil_ort = pd.DataFrame(profil_ort, columns=['Toplam_Yolcu', 'Aktarma_Orani', 'Kart_Cesidi', 'EnCokKart_Orani', 'Hedef_Cesidi'])
        profil_scaled = scaler_model.transform(profil_ort)
        en_yakin_segment = kmeans_model.predict(profil_scaled)[0]
        st.info(f"🔎 Seçili filtrelere göre en yakın segment: **Segment {en_yakin_segment}**")

# ------------------------------
# YENİ: Dönem Karşılaştırma (RandomForest Anomali Tespiti)
# ------------------------------
st.header("📆 ML Destekli Dönem Karşılaştırma")

# Model eğitimi (tüm veri üzerinde)
@st.cache_resource
def train_forecast_model(df):
    df_model = df.copy()
    df_model['Tarih'] = df_model['MERKEZDEN GEMİYE BİNİŞ'].dt.date
    df_model['Gun_hafta'] = df_model['MERKEZDEN GEMİYE BİNİŞ'].dt.dayofweek
    df_model['Saat'] = df_model['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
    df_model['Ay'] = df_model['MERKEZDEN GEMİYE BİNİŞ'].dt.month
    
    # Saat-yön-gün bazında toplam
    daily = df_model.groupby(['Tarih','YÖN','Saat','Gun_hafta','Ay']).size().reset_index(name='Yolcu')
    
    le = LabelEncoder()
    daily['YON_enc'] = le.fit_transform(daily['YÖN'])
    
    X = daily[['Saat','Gun_hafta','Ay','YON_enc']]
    y = daily['Yolcu']
    
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X, y)
    return model, le, daily[['Tarih','YÖN','Saat','Gun_hafta','Ay','Yolcu']]

forecast_model, le_forecast, daily_data = train_forecast_model(df)

# Tarih seçimi
col_d1, col_d2 = st.columns(2)
with col_d1:
    tarih1_bas = st.date_input("1. Dönem Başlangıç", df['MERKEZDEN GEMİYE BİNİŞ'].min().date())
    tarih1_bit = st.date_input("1. Dönem Bitiş", df['MERKEZDEN GEMİYE BİNİŞ'].max().date())
with col_d2:
    tarih2_bas = st.date_input("2. Dönem Başlangıç", df['MERKEZDEN GEMİYE BİNİŞ'].min().date())
    tarih2_bit = st.date_input("2. Dönem Bitiş", df['MERKEZDEN GEMİYE BİNİŞ'].max().date())

if st.button("🔍 Dönemleri Karşılaştır (Anomali Analizi)"):
    def donem_sapma(df, model, le, start, end):
        mask = (df['MERKEZDEN GEMİYE BİNİŞ'].dt.date >= start) & (df['MERKEZDEN GEMİYE BİNİŞ'].dt.date <= end)
        sub = df[mask].copy()
        if sub.empty:
            return pd.DataFrame()
        sub['Gun_hafta'] = sub['MERKEZDEN GEMİYE BİNİŞ'].dt.dayofweek
        sub['Saat'] = sub['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
        sub['Ay'] = sub['MERKEZDEN GEMİYE BİNİŞ'].dt.month
        sub['YON_enc'] = le.transform(sub['YÖN'])
        X_sub = sub[['Saat','Gun_hafta','Ay','YON_enc']]
        sub['Tahmin'] = model.predict(X_sub)
        # Gerçek sayıları grupla
        actual = sub.groupby(['Saat','YÖN']).size().reset_index(name='Gerçek')
        pred = sub.groupby(['Saat','YÖN'])['Tahmin'].mean().reset_index(name='Tahmin')
        comp = actual.merge(pred, on=['Saat','YÖN'])
        comp['Fark'] = comp['Gerçek'] - comp['Tahmin']
        comp['Mutlak_Fark'] = comp['Fark'].abs()
        comp['Dönem'] = f"{start} - {end}"
        return comp.sort_values('Mutlak_Fark', ascending=False)
    
    comp1 = donem_sapma(df, forecast_model, le_forecast, tarih1_bas, tarih1_bit)
    comp2 = donem_sapma(df, forecast_model, le_forecast, tarih2_bas, tarih2_bit)
    
    if comp1.empty or comp2.empty:
        st.warning("Seçilen dönemlerden birinde veri yok.")
    else:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.write("**Dönem 1 – En Büyük Sapmalar (Gerçek - Tahmin)**")
            st.dataframe(comp1.head(10)[['Saat','YÖN','Gerçek','Tahmin','Fark']])
        with col_c2:
            st.write("**Dönem 2 – En Büyük Sapmalar**")
            st.dataframe(comp2.head(10)[['Saat','YÖN','Gerçek','Tahmin','Fark']])
        
        # Karşılaştırma grafiği (ilk 20 en büyük sapma için)
        comp_all = pd.concat([comp1.nlargest(10, 'Mutlak_Fark'), 
                              comp2.nlargest(10, 'Mutlak_Fark')])
        comp_all['Etiket'] = comp_all['Saat'].astype(str) + ' ' + comp_all['YÖN']
        fig_comp = px.bar(comp_all, x='Etiket', y='Fark', color='Dönem',
                          title='Dönemlere Göre Saatlik Sapmalar (Tahmin - Gerçek)',
                          barmode='group')
        fig_comp.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_comp, use_container_width=True)
        
        # Anomali vurgusu
        yuksek_sapma = comp_all[comp_all['Mutlak_Fark'] > 20]  # eşik örnek
        if not yuksek_sapma.empty:
            st.warning(f"🚨 {len(yuksek_sapma)} adet yüksek sapmalı saat/yön tespit edildi! Detaylar yukarıdaki tabloda.")

# ------------------------------
# DETAYLI TABLOLAR (Mevcut, ufak Plotly eklemeleriyle)
# ------------------------------
st.subheader("📋 Detaylı Veri Tabloları")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📍 Nereden Geldi?", 
    "🎯 Nereye Gitti?", 
    "💳 Kart Tipi Dağılımı",
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
        
        top_gelis = gelis_ozet.groupby('MERKEZE GELDİĞİ ARACIN HATTI')['Kisi'].sum().nlargest(10).reset_index()
        fig_gelis = px.bar(top_gelis, x='Kisi', y='MERKEZE GELDİĞİ ARACIN HATTI',
                          orientation='h', title='En Çok Gelinilen 10 Hat',
                          color_discrete_sequence=['#4CAF50'])
        st.plotly_chart(fig_gelis, use_container_width=True)
    else:
        st.info("Geliş hattı verisi bulunamadı.")

with tab2:
    gidis_data = filtered_df[filtered_df['Hedef_Temiz'].notna()]
    if not gidis_data.empty:
        gidis_ozet = gidis_data.groupby(['YÖN', 'Hedef_Temiz']).size().reset_index(name='Kisi')
        gidis_ozet = gidis_ozet.sort_values('Kisi', ascending=False)
        st.dataframe(gidis_ozet, use_container_width=True)
        
        top_gidis = gidis_ozet.groupby('Hedef_Temiz')['Kisi'].sum().nlargest(10).reset_index()
        fig_gidis = px.bar(top_gidis, x='Kisi', y='Hedef_Temiz',
                          orientation='h', title='En Çok Gidilen 10 Yer',
                          color_discrete_sequence=['#FF5722'])
        st.plotly_chart(fig_gidis, use_container_width=True)
    else:
        st.info("Gidiş verisi bulunamadı.")

with tab3:
    kart_detay = filtered_df.groupby(['YÖN', 'KART_TIPI']).size().reset_index(name='Kisi')
    kart_detay = kart_detay.sort_values('Kisi', ascending=False)
    st.dataframe(kart_detay, use_container_width=True)
    
    # Tüm kartların saatlik dağılımı (Plotly)
    kart_saat_tum = filtered_df.groupby(['Saat', 'KART_TIPI']).size().reset_index(name='Kisi')
    fig_kart_tum = px.line(kart_saat_tum, x='Saat', y='Kisi', color='KART_TIPI',
                          title='Tüm Kart Tiplerinin Saatlik Dağılımı')
    fig_kart_tum.update_xaxes(dtick=1)
    st.plotly_chart(fig_kart_tum, use_container_width=True)

with tab4:
    gitmeyen_data = filtered_df[
        (filtered_df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
        (filtered_df['Hedef_Temiz'].isna())
    ]
    if not gitmeyen_data.empty:
        gitmeyen_ozet = gitmeyen_data.groupby(['YÖN', 'KART_TIPI']).size().reset_index(name='Kisi')
        gitmeyen_ozet = gitmeyen_ozet.sort_values('Kisi', ascending=False)
        st.dataframe(gitmeyen_ozet, use_container_width=True)
        st.metric("Toplam Gitmeyen", f"{len(gitmeyen_data):,}")
    else:
        st.info("Gitmeyen verisi bulunamadı.")

with tab5:
    st.dataframe(filtered_df.head(200), use_container_width=True)
    st.caption(f"Toplam {len(filtered_df):,} satır gösteriliyor (ilk 200).")

st.markdown("---")
st.caption("⛴️ Vapur Hattı Analiz Dashboard | Veri: 20260506_2_REV5.xlsx | ML entegrasyonu ile geliştirilmiştir.")
