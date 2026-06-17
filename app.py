import pandas as pd
import numpy as np
import os

# ------------------------------
# 1. VERİYİ OKU
# ------------------------------
file_path = '20260506_2_REV5.xlsx'

if not os.path.exists(file_path):
    print(f"❌ Hata: '{file_path}' dosyası bulunamadı.")
    exit()

df = pd.read_excel(file_path, sheet_name='Sayfa2')
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

print(f"✅ Veri yüklendi: {df.shape[0]} satır")

# ------------------------------
# 2. YÖNLERE GÖRE AYIR
# ------------------------------
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

# ------------------------------
# 3. ANALİZ FONKSİYONU
# ------------------------------
def analiz_yap(df_yon):
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
# 4. ANALİZLER
# ------------------------------
binme_u, gelis_u, gidis_u, gitmeyen_u = analiz_yap(df_uskudar)
binme_b, gelis_b, gidis_b, gitmeyen_b = analiz_yap(df_besiktas)

# ------------------------------
# 5. TAHMİN VERİSİ
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
tahmin_df.rename(columns={'İNDİKTEN SONRA NEREYE GİTTİ': 'Hedef'}, inplace=True)

# Tüm kombinasyonları oluştur
tum_hedefler = tahmin_df['Hedef'].unique()
tum_yonler = tahmin_df['YÖN'].unique()
tum_saatler = list(range(24))

tum_kombinasyon = []
for yon in tum_yonler:
    for hedef in tum_hedefler:
        for saat in tum_saatler:
            tum_kombinasyon.append({'YÖN': yon, 'Hedef': hedef, 'Saat': saat})

tum_kombinasyon_df = pd.DataFrame(tum_kombinasyon)
tahmin_full = tum_kombinasyon_df.merge(
    tahmin_df, on=['YÖN', 'Hedef', 'Saat'], how='left'
)
tahmin_full['Tahmini_Yolcu_Sayisi'] = tahmin_full['Tahmini_Yolcu_Sayisi'].fillna(0).astype(int)

# ------------------------------
# 6. PİVOT TABLOLAR
# ------------------------------
gidis_u_pivot = gidis_u.pivot(index='Gidilen_Yer', columns='Saat_Dilimi', values='Kisi_Sayisi').fillna(0)
gidis_b_pivot = gidis_b.pivot(index='Gidilen_Yer', columns='Saat_Dilimi', values='Kisi_Sayisi').fillna(0)

# ------------------------------
# 7. ÖZET
# ------------------------------
ozet = pd.DataFrame({
    'Yön': ['Üsküdar → Beşiktaş', 'Beşiktaş → Üsküdar'],
    'Toplam_Biniş': [len(df_uskudar), len(df_besiktas)],
    'Aktarma_Yapan': [gidis_u['Kisi_Sayisi'].sum(), gidis_b['Kisi_Sayisi'].sum()],
    'Gitmeyen': [gitmeyen_u['Gitmeyen_Sayisi'].sum(), gitmeyen_b['Gitmeyen_Sayisi'].sum()],
    'Ortalama_Biniş/Saat': [round(len(df_uskudar)/24, 1), round(len(df_besiktas)/24, 1)]
})

# ------------------------------
# 8. EXCEL'E YAZ (openpyxl)
# ------------------------------
output_file = 'vapur_tam_analiz.xlsx'
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    binme_u.to_excel(writer, sheet_name='Uskudar_Binme', index=False)
    gelis_u.to_excel(writer, sheet_name='Uskudar_Gelis', index=False)
    gidis_u.to_excel(writer, sheet_name='Uskudar_Gidis', index=False)
    gitmeyen_u.to_excel(writer, sheet_name='Uskudar_Gitmeyen', index=False)
    
    binme_b.to_excel(writer, sheet_name='Besiktas_Binme', index=False)
    gelis_b.to_excel(writer, sheet_name='Besiktas_Gelis', index=False)
    gidis_b.to_excel(writer, sheet_name='Besiktas_Gidis', index=False)
    gitmeyen_b.to_excel(writer, sheet_name='Besiktas_Gitmeyen', index=False)
    
    tahmin_full.to_excel(writer, sheet_name='Tahmin_Verisi', index=False)
    gidis_u_pivot.reset_index().to_excel(writer, sheet_name='Uskudar_Gidis_Pivot', index=False)
    gidis_b_pivot.reset_index().to_excel(writer, sheet_name='Besiktas_Gidis_Pivot', index=False)
    ozet.to_excel(writer, sheet_name='Ozet', index=False)

# Sütun genişliklerini ayarla
try:
    from openpyxl import load_workbook
    wb = load_workbook(output_file)
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    max_len = max(max_len, len(str(cell.value)))
                except:
                    pass
            ws.column_dimensions[col_letter].width = min(max_len + 2, 40)
    wb.save(output_file)
except:
    pass

print(f"\n✅ Excel dosyası oluşturuldu: {output_file}")
print("\n📊 ÖZET:")
print(ozet.to_string(index=False))
