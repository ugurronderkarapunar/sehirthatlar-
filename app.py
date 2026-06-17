import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Vapur Hattı Analizi", layout="wide")
st.title("🚢 Üsküdar – Beşiktaş Vapur Hattı Analiz ve Tahmin Aracı")

uploaded_file = st.file_uploader("📂 Excel dosyasını yükleyin", type=["xlsx"])

if uploaded_file is None:
    st.warning("Lütfen bir Excel dosyası yükleyin.")
    st.stop()

# Veriyi oku
df = pd.read_excel(uploaded_file, sheet_name='Sayfa2')
df.columns = df.columns.str.strip()
df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(df['MERKEZDEN GEMİYE BİNİŞ'], format='mixed', errors='coerce')
df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])
df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
df['Saat_Dilimi'] = df['Saat'].apply(lambda x: f"{x:02d}:00–{x:02d}:59")
df['YÖN'] = df['YÖN'].str.strip()

st.success(f"✅ Veri yüklendi: {df.shape[0]} satır")

# Yönlere göre filtrele
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

st.subheader("📊 Üsküdar → Beşiktaş")
col1, col2 = st.columns(2)
col1.metric("Toplam Biniş", df_uskudar.shape[0])
col2.metric("Ortalama Biniş/Saat", round(df_uskudar.shape[0]/24, 1))

# Saatlik biniş grafiği
binme_uskudar = df_uskudar.groupby('Saat_Dilimi').size().reset_index(name='Yolcu')
fig1 = px.bar(binme_uskudar, x='Saat_Dilimi', y='Yolcu', title='Saatlik Biniş (Üsküdar→Beşiktaş)')
st.plotly_chart(fig1, use_container_width=True)

st.subheader("📊 Beşiktaş → Üsküdar")
col3, col4 = st.columns(2)
col3.metric("Toplam Biniş", df_besiktas.shape[0])
col4.metric("Ortalama Biniş/Saat", round(df_besiktas.shape[0]/24, 1))

binme_besiktas = df_besiktas.groupby('Saat_Dilimi').size().reset_index(name='Yolcu')
fig2 = px.bar(binme_besiktas, x='Saat_Dilimi', y='Yolcu', title='Saatlik Biniş (Beşiktaş→Üsküdar)')
st.plotly_chart(fig2, use_container_width=True)

# Tahmin
st.header("🔮 Tahmin Aracı")
col5, col6, col7 = st.columns(3)
with col5:
    yon = st.selectbox("Yön", ['ÜSKÜDAR → BEŞİKTAŞ', 'BEŞİKTAŞ → ÜSKÜDAR'])
with col6:
    hedef = st.selectbox("Gidilecek Yer", ['KADIKÖY', 'TAKSİM', 'SARIYER', 'BEŞİKTAŞ', 'ÜSKÜDAR'])
with col7:
    saat = st.slider("Saat", 0, 23, 8)

# Tahmini hesapla (basit)
tahmin = df[(df['YÖN'] == yon) & (df['Saat'] == saat)]
if not tahmin.empty:
    st.success(f"Tahmini yolcu sayısı: {len(tahmin)} kişi")
else:
    st.info("Bu saatte veri bulunamadı.")
