import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter

st.set_page_config(page_title="Vapur Hattı Analiz Dashboard", layout="wide")
st.title("🚢 Üsküdar – Beşiktaş Vapur Hattı Detaylı Analiz ve Aktarma Optimizasyonu")

# ------------------------------
# DOSYA YÜKLEME
# ------------------------------
uploaded_file = st.file_uploader("📂 Excel dosyasını yükleyin", type=["xlsx"])

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

# ------------------------------
# YÖNLERE GÖRE AYIR
# ------------------------------
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

# ------------------------------
# AKTARMA ANALİZİ (GELİŞ-GİDİŞ EŞLEŞTİRMESİ)
# ------------------------------
st.header("🔄 Aktarma Optimizasyonu Analizi")

# Sadece aktarma yapanları al (gidiş yeri bilinenler)
aktarma_df = df[
    (df['İNDİKTEN SONRA NEREYE GİTTİ'].notna()) &
    (df['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() != '') &
    (df['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR') &
    (df['MERKEZE GELDİĞİ ARACIN HATTI'].notna()) &
    (df['MERKEZE GELDİĞİ ARACIN HATTI'].str.strip() != '')
]

# Geliş-Gidiş çiftlerini oluştur
aktarma_df['GELIS_GIDIS'] = aktarma_df['MERKEZE GELDİĞİ ARACIN HATTI'] + " → " + aktarma_df['İNDİKTEN SONRA NEREYE GİTTİ']

# En sık tekrarlanan rotalar
rota_sayac = Counter(aktarma_df['GELIS_GIDIS'])
top_rotalar = rota_sayac.most_common(20)

rota_df = pd.DataFrame(top_rotalar, columns=['Rota', 'Yolcu_Sayisi'])

if not rota_df.empty:
    st.subheader("📊 En Sık Yapılan Aktarmalar (Top 20)")
    st.dataframe(rota_df, use_container_width=True)
    
    # Grafik
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(rota_df['Rota'], rota_df['Yolcu_Sayisi'], color='teal')
    ax.set_xlabel('Yolcu Sayısı')
    ax.set_title('En Sık Yapılan Aktarmalar')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig)
    
    # Özet
    toplam_aktarma = len(aktarma_df)
    benzersiz_rota = len(rota_sayac)
    st.info(f"📌 Toplam {toplam_aktarma} aktarma hareketi, {benzersiz_rota} farklı rota var. En yoğun rota: **{rota_df.iloc[0]['Rota']}** ({rota_df.iloc[0]['Yolcu_Sayisi']} kişi)")
    
    # Müdüre özel öneri
    st.subheader("💡 Müdüre Özel Analiz")
    st.write("Aşağıdaki rotalar, yolcuların Üsküdar/Beşiktaş'a gelip başka bir yere gitmesini gösteriyor. Bu rotalarda doğrudan hat oluşturulabilir mi?")
    
    # En yoğun 5 rota için öneri
    for i, row in rota_df.head(5).iterrows():
        rota = row['Rota']
        kisi = row['Yolcu_Sayisi']
        st.write(f"🔹 **{rota}** → {kisi} kişi. Bu rota için direkt hat düşünülebilir.")
else:
    st.warning("Aktarma verisi bulunamadı.")

# ------------------------------
# SAATLİK AKTARMA ANALİZİ
# ------------------------------
st.header("⏰ Saat Dilimlerine Göre Aktarmalar")

aktarma_saat = aktarma_df.groupby(['Saat_Dilimi', 'GELIS_GIDIS']).size().reset_index(name='Kisi_Sayisi')
aktarma_saat = aktarma_saat.sort_values(['Saat_Dilimi', 'Kisi_Sayisi'], ascending=[True, False])

# En yoğun saat dilimleri
en_yogun_saat = aktarma_df.groupby('Saat_Dilimi').size().reset_index(name='Toplam_Aktarma')
en_yogun_saat = en_yogun_saat.sort_values('Toplam_Aktarma', ascending=False)

st.subheader("📈 En Yoğun Aktarma Saatleri")
st.dataframe(en_yogun_saat, use_container_width=True)

fig2, ax2 = plt.subplots(figsize=(10, 4))
ax2.bar(en_yogun_saat['Saat_Dilimi'].head(10), en_yogun_saat['Toplam_Aktarma'].head(10), color='coral')
ax2.set_xlabel('Saat Dilimi')
ax2.set_ylabel('Aktarma Sayısı')
ax2.set_title('En Yoğun 10 Saat Dilimi (Aktarma)')
ax2.tick_params(axis='x', rotation=45)
plt.tight_layout()
st.pyplot(fig2)

# ------------------------------
# DASHBOARD 1: ÜSKÜDAR → BEŞİKTAŞ (DETAYLI)
# ------------------------------
st.header("📊 Dashboard 1: Üsküdar → Beşiktaş")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Toplam Biniş", f"{len(df_uskudar):,}")
col2.metric("Aktarma Yapan", f"{len(df_uskudar[df_uskudar['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1]):,}")
col3.metric("Gitmeyen (Aktarma Yok)", f"{len(df_uskudar[df_uskudar['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0]):,}")
col4.metric("Ortalama Biniş/Saat", f"{len(df_uskudar)/24:.1f}")

# Saatlik biniş
binme_u = df_uskudar.groupby('Saat').size().reset_index(name='Yolcu')
fig3, ax3 = plt.subplots(figsize=(10, 4))
ax3.bar(binme_u['Saat'], binme_u['Yolcu'], color='#1E88E5')
ax3.set_xlabel('Saat')
ax3.set_ylabel('Yolcu Sayısı')
ax3.set_title('Üsküdar → Beşiktaş Saatlik Biniş')
ax3.grid(True, alpha=0.3)
plt.tight_layout()
st.pyplot(fig3)

# Nereden geldi?
gelis_u = df_uskudar[df_uskudar['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
gelis_u = gelis_u[gelis_u['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
gelis_u_count = gelis_u.groupby('MERKEZE GELDİĞİ ARACIN HATTI').size().reset_index(name='Kisi_Sayisi')
gelis_u_count = gelis_u_count.sort_values('Kisi_Sayisi', ascending=False)

st.subheader("🚌 Üsküdar → Beşiktaş: Yolcular Nereden Geldi?")
st.dataframe(gelis_u_count, use_container_width=True)

# Nereye gitti?
gidis_u = df_uskudar[
    (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'].notna()) &
    (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() != '') &
    (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR')
]
gidis_u_count = gidis_u.groupby('İNDİKTEN SONRA NEREYE GİTTİ').size().reset_index(name='Kisi_Sayisi')
gidis_u_count = gidis_u_count.sort_values('Kisi_Sayisi', ascending=False)

st.subheader("📍 Üsküdar → Beşiktaş: Yolcular Nereye Gitti?")
st.dataframe(gidis_u_count, use_container_width=True)

# Gitmeyenler
gitmeyen_u = df_uskudar[
    (df_uskudar['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
    (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'].isna()) |
    (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() == '') |
    (df_uskudar['İNDİKTEN SONRA NEREYE GİTTİ'] == 'BİLİNMİYOR')
]
st.subheader("🚫 Üsküdar → Beşiktaş: Gitmeyenler (Aktarma Yapmayanlar)")
st.metric("Toplam Gitmeyen", f"{len(gitmeyen_u):,}")

# ------------------------------
# DASHBOARD 2: BEŞİKTAŞ → ÜSKÜDAR (DETAYLI)
# ------------------------------
st.header("📊 Dashboard 2: Beşiktaş → Üsküdar")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Toplam Biniş", f"{len(df_besiktas):,}")
col6.metric("Aktarma Yapan", f"{len(df_besiktas[df_besiktas['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1]):,}")
col7.metric("Gitmeyen (Aktarma Yok)", f"{len(df_besiktas[df_besiktas['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0]):,}")
col8.metric("Ortalama Biniş/Saat", f"{len(df_besiktas)/24:.1f}")

# Saatlik biniş
binme_b = df_besiktas.groupby('Saat').size().reset_index(name='Yolcu')
fig4, ax4 = plt.subplots(figsize=(10, 4))
ax4.bar(binme_b['Saat'], binme_b['Yolcu'], color='#FF9800')
ax4.set_xlabel('Saat')
ax4.set_ylabel('Yolcu Sayısı')
ax4.set_title('Beşiktaş → Üsküdar Saatlik Biniş')
ax4.grid(True, alpha=0.3)
plt.tight_layout()
st.pyplot(fig4)

# Nereden geldi?
gelis_b = df_besiktas[df_besiktas['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
gelis_b = gelis_b[gelis_b['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
gelis_b_count = gelis_b.groupby('MERKEZE GELDİĞİ ARACIN HATTI').size().reset_index(name='Kisi_Sayisi')
gelis_b_count = gelis_b_count.sort_values('Kisi_Sayisi', ascending=False)

st.subheader("🚌 Beşiktaş → Üsküdar: Yolcular Nereden Geldi?")
st.dataframe(gelis_b_count, use_container_width=True)

# Nereye gitti?
gidis_b = df_besiktas[
    (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'].notna()) &
    (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() != '') &
    (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR')
]
gidis_b_count = gidis_b.groupby('İNDİKTEN SONRA NEREYE GİTTİ').size().reset_index(name='Kisi_Sayisi')
gidis_b_count = gidis_b_count.sort_values('Kisi_Sayisi', ascending=False)

st.subheader("📍 Beşiktaş → Üsküdar: Yolcular Nereye Gitti?")
st.dataframe(gidis_b_count, use_container_width=True)

# Gitmeyenler
gitmeyen_b = df_besiktas[
    (df_besiktas['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
    (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'].isna()) |
    (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() == '') |
    (df_besiktas['İNDİKTEN SONRA NEREYE GİTTİ'] == 'BİLİNMİYOR')
]
st.subheader("🚫 Beşiktaş → Üsküdar: Gitmeyenler (Aktarma Yapmayanlar)")
st.metric("Toplam Gitmeyen", f"{len(gitmeyen_b):,}")

# ------------------------------
# KARŞILAŞTIRMALI TABLO
# ------------------------------
st.header("📈 Karşılaştırmalı Özet")
karsilastirma = pd.DataFrame({
    'Metrik': ['Toplam Biniş', 'Aktarma Yapan', 'Gitmeyen', 'Ortalama/Saat'],
    'Üsküdar→Beşiktaş': [
        len(df_uskudar),
        len(df_uskudar[df_uskudar['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1]),
        len(gitmeyen_u),
        round(len(df_uskudar)/24, 1)
    ],
    'Beşiktaş→Üsküdar': [
        len(df_besiktas),
        len(df_besiktas[df_besiktas['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1]),
        len(gitmeyen_b),
        round(len(df_besiktas)/24, 1)
    ]
})
st.dataframe(karsilastirma, use_container_width=True)

# ------------------------------
# VERİ ÖNİZLEME
# ------------------------------
with st.expander("🔍 Ham Veri Önizleme (İlk 100 Satır)"):
    st.dataframe(df.head(100), use_container_width=True)

st.success("✅ Tüm analizler tamamlandı!")
