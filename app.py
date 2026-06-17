import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Vapur Hattı Analizi", layout="wide")
st.title("🚢 Üsküdar – Beşiktaş Vapur Hattı Analiz ve Tahmin Aracı")

# Dosya yükle
uploaded_file = st.file_uploader("📂 Excel dosyasını yükleyin (20260506_2_REV5.xlsx)", type=["xlsx"])

if uploaded_file is None:
    st.warning("Lütfen Excel dosyasını yükleyin.")
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

# Yönlere ayır
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

# Özet kartlar
col1, col2, col3, col4 = st.columns(4)
col1.metric("Üsküdar→Beşiktaş Toplam", f"{df_uskudar.shape[0]:,}")
col2.metric("Üsküdar→Beşiktaş Ort/Saat", f"{df_uskudar.shape[0]/24:.1f}")
col3.metric("Beşiktaş→Üsküdar Toplam", f"{df_besiktas.shape[0]:,}")
col4.metric("Beşiktaş→Üsküdar Ort/Saat", f"{df_besiktas.shape[0]/24:.1f}")

# Grafikler (matplotlib)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Üsküdar grafiği
binme_u = df_uskudar.groupby('Saat').size().reset_index(name='Yolcu')
axes[0].bar(binme_u['Saat'], binme_u['Yolcu'], color='#1E88E5', edgecolor='black')
axes[0].set_title('Üsküdar → Beşiktaş (Saatlik Biniş)', fontsize=14)
axes[0].set_xlabel('Saat', fontsize=12)
axes[0].set_ylabel('Yolcu Sayısı', fontsize=12)
axes[0].grid(True, alpha=0.3)
axes[0].set_xticks(range(0, 24))

# Beşiktaş grafiği
binme_b = df_besiktas.groupby('Saat').size().reset_index(name='Yolcu')
axes[1].bar(binme_b['Saat'], binme_b['Yolcu'], color='#FF9800', edgecolor='black')
axes[1].set_title('Beşiktaş → Üsküdar (Saatlik Biniş)', fontsize=14)
axes[1].set_xlabel('Saat', fontsize=12)
axes[1].set_ylabel('Yolcu Sayısı', fontsize=12)
axes[1].grid(True, alpha=0.3)
axes[1].set_xticks(range(0, 24))

plt.tight_layout()
st.pyplot(fig)

# ------------------------------
# TAHMİN ARACI
# ------------------------------
st.header("🔮 Tahmin Aracı")

col5, col6, col7 = st.columns(3)
with col5:
    yon = st.selectbox("Yön Seçiniz", ['ÜSKÜDAR → BEŞİKTAŞ', 'BEŞİKTAŞ → ÜSKÜDAR'])
with col6:
    # Hedefleri listele
    hedef_list = df[df['İNDİKTEN SONRA NEREYE GİTTİ'].notna()]['İNDİKTEN SONRA NEREYE GİTTİ'].unique()
    hedef_list = [h for h in hedef_list if h not in ['', 'BİLİNMİYOR']]
    hedef = st.selectbox("Gidilecek Yer Seçiniz", sorted(hedef_list))
with col7:
    saat = st.slider("Saat Seçiniz (0-23)", 0, 23, 8)

# Tahmin hesapla
tahmin = df[
    (df['YÖN'] == yon) & 
    (df['Saat'] == saat) & 
    (df['İNDİKTEN SONRA NEREYE GİTTİ'] == hedef)
]
tahmin_sayisi = len(tahmin)

st.metric("📊 Tahmini Yolcu Sayısı", f"{tahmin_sayisi} kişi")

# ------------------------------
# DETAYLI TABLOLAR (Expander)
# ------------------------------
with st.expander("📋 Üsküdar → Beşiktaş - Nereden Geldi?"):
    gelis_u = df_uskudar[df_uskudar['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
    gelis_u = gelis_u[gelis_u['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
    st.dataframe(gelis_u.groupby('MERKEZE GELDİĞİ ARACIN HATTI').size().reset_index(name='Kisi'), use_container_width=True)

with st.expander("📋 Üsküdar → Beşiktaş - Nereye Gitti?"):
    gidis_u = df_uskudar[
        (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'].notna()) &
        (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'] != '') &
        (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR')
    ]
    st.dataframe(gidis_u.groupby('İNDİKTEN SONRA NEREYE GİTTİ').size().reset_index(name='Kisi'), use_container_width=True)

with st.expander("📋 Beşiktaş → Üsküdar - Nereden Geldi?"):
    gelis_b = df_besiktas[df_besiktas['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
    gelis_b = gelis_b[gelis_b['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
    st.dataframe(gelis_b.groupby('MERKEZE GELDİĞİ ARACIN HATTI').size().reset_index(name='Kisi'), use_container_width=True)

with st.expander("📋 Beşiktaş → Üsküdar - Nereye Gitti?"):
    gidis_b = df_besiktas[
        (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'].notna()) &
        (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'] != '') &
        (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR')
    ]
    st.dataframe(gidis_b.groupby('İNDİKTEN SONRA NEREYE GİTTİ').size().reset_index(name='Kisi'), use_container_width=True)

with st.expander("🚫 Gitmeyenler (Aktarma Yapmayanlar)"):
    gitmeyen = df[df['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0]
    st.dataframe(gitmeyen.groupby('YÖN').size().reset_index(name='Kisi'), use_container_width=True)

st.success("✅ Tüm analizler hazır! Yukarıdaki sekmeleri kullanarak detaylara bakabilirsiniz.")
