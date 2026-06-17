import pandas as pd
import numpy as np

# ------------------------------
# VERİYİ OKU (DOSYA AYNI KLASÖRDE OLMALI)
# ------------------------------
file_path = '20260506_2_REV5.xlsx'
try:
    df = pd.read_excel(file_path, sheet_name='Sayfa2')
    print("✅ Dosya okundu.")
except FileNotFoundError:
    print("❌ Dosya bulunamadı! Lütfen '20260506_2_REV5.xlsx' dosyasını bu klasöre koyun.")
    exit()

# Temizlik
df.columns = df.columns.str.strip()
df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(df['MERKEZDEN GEMİYE BİNİŞ'], format='mixed', errors='coerce')
df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])
df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
df['Saat_Dilimi'] = df['Saat'].apply(lambda x: f"{x:02d}:00–{x:02d}:59")
df['YÖN'] = df['YÖN'].str.strip()

# ------------------------------
# ANALİZ FONKSİYONU
# ------------------------------
def analiz_yap(df_yon, yon_adi):
    binme = df_yon.groupby('Saat_Dilimi').size().reset_index(name='Toplam_Binme')
    
    gelis_df = df_yon[df_yon['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
    gelis_df = gelis_df[gelis_df['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
    gelis = gelis_df.groupby(['Saat_Dilimi', 'MERKEZE GELDİĞİ ARACIN HATTI']).size().reset_index(name='Kisi_Sayisi')
    gelis.rename(columns={'MERKEZE GELDİĞİ ARACIN HATTI': 'Gelis_Hatti'}, inplace=True)
    
    giden_df = df_yon[
        (df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 1) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].notna() & 
         df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip().notna() & 
         (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'] != 'BİLİNMİYOR'))
    ]
    gidis = giden_df.groupby(['Saat_Dilimi', 'İNDİKTEN SONRA NEREYE GİTTİ']).size().reset_index(name='Kisi_Sayisi')
    gidis.rename(columns={'İNDİKTEN SONRA NEREYE GİTTİ': 'Gidilen_Yer'}, inplace=True)
    
    gitmeyen_df = df_yon[
        (df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].isna()) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() == '') |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'] == 'BİLİNMİYOR')
    ]
    gitmeyen = gitmeyen_df.groupby('Saat_Dilimi').size().reset_index(name='Gitmeyen_Sayisi')
    
    return binme, gelis, gidis, gitmeyen

# ------------------------------
# ANALİZLERİ ÇALIŞTIR
# ------------------------------
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

binme_u, gelis_u, gidis_u, gitmeyen_u = analiz_yap(df_uskudar, 'Üsküdar')
binme_b, gelis_b, gidis_b, gitmeyen_b = analiz_yap(df_besiktas, 'Beşiktaş')

# Tahmin verisi
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
# EXCEL'E YAZ
# ------------------------------
with pd.ExcelWriter('vapur_analiz_dashboard.xlsx', engine='openpyxl') as writer:
    # Üsküdar yönü
    binme_u.to_excel(writer, sheet_name='Uskudar_Binme', index=False)
    gelis_u.to_excel(writer, sheet_name='Uskudar_Gelis', index=False)
    gidis_u.to_excel(writer, sheet_name='Uskudar_Gidis', index=False)
    gitmeyen_u.to_excel(writer, sheet_name='Uskudar_Gitmeyen', index=False)
    
    # Beşiktaş yönü
    binme_b.to_excel(writer, sheet_name='Besiktas_Binme', index=False)
    gelis_b.to_excel(writer, sheet_name='Besiktas_Gelis', index=False)
    gidis_b.to_excel(writer, sheet_name='Besiktas_Gidis', index=False)
    gitmeyen_b.to_excel(writer, sheet_name='Besiktas_Gitmeyen', index=False)
    
    # Tahmin verisi
    tahmin_df.to_excel(writer, sheet_name='Tahmin_Verisi', index=False)
    
    # Özet
    ozet = pd.DataFrame({
        'Yön': ['Üsküdar→Beşiktaş', 'Beşiktaş→Üsküdar'],
        'Toplam_Biniş': [df_uskudar.shape[0], df_besiktas.shape[0]],
        'Aktarma_Yapan': [gidis_u['Kisi_Sayisi'].sum(), gidis_b['Kisi_Sayisi'].sum()],
        'Gitmeyen': [gitmeyen_u['Gitmeyen_Sayisi'].sum(), gitmeyen_b['Gitmeyen_Sayisi'].sum()]
    })
    ozet.to_excel(writer, sheet_name='Ozet', index=False)

print("✅ Excel dashboard oluşturuldu: vapur_analiz_dashboard.xlsx")
