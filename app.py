import pandas as pd
import numpy as np
from datetime import datetime

# ------------------------------
# 1. VERİYİ OKU VE TEMİZLE
# ------------------------------
file_path = '20260506_2_REV5.xlsx'
df = pd.read_excel(file_path, sheet_name='Sayfa2')

# Sütun adlarını temizle
df.columns = df.columns.str.strip()

# Tarih/saat dönüşümü (milisaniye sorununu çözer)
df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(
    df['MERKEZDEN GEMİYE BİNİŞ'], 
    format='mixed', 
    errors='coerce'
)
df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])

# Saat ve saat dilimi
df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
df['Saat_Dilimi'] = df['Saat'].apply(lambda x: f"{x:02d}:00–{x:02d}:59")

# Yön temizle
df['YÖN'] = df['YÖN'].str.strip()

# ------------------------------
# 2. İKİ YÖN İÇİN AYRI DATAFRAME'LER
# ------------------------------
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ'].copy()
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR'].copy()

# ------------------------------
# 3. FONKSİYONLAR (Analizleri tekrar kullanmak için)
# ------------------------------
def analiz_yap(df_yon, yon_adi):
    """
    Verilen yön DataFrame'i için tüm analizleri yapar ve sonuçları sözlük olarak döndürür.
    """
    # a) Saat dilimine göre binme
    binme = df_yon.groupby('Saat_Dilimi').size().reset_index(name='Toplam_Binme')
    
    # b) Geliş hatları (nereden geldi)
    gelis_df = df_yon[df_yon['MERKEZE GELDİĞİ ARACIN HATTI'].notna()]
    gelis_df = gelis_df[gelis_df['MERKEZE GELDİĞİ ARACIN HATTI'] != '']
    gelis = gelis_df.groupby(
        ['Saat_Dilimi', 'MERKEZE GELDİĞİ ARACIN HATTI']
    ).size().reset_index(name='Kisi_Sayisi')
    gelis.rename(columns={'MERKEZE GELDİĞİ ARACIN HATTI': 'Gelis_Hatti'}, inplace=True)
    
    # c) İndikten sonra gidilen yerler (aktarma yapanlar)
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
    
    # d) İndikten sonra hiçbir yere gitmeyenler
    gitmeyen_df = df_yon[
        (df_yon['İNDİKTEN SONRA AKTARMA YAPTIMI(0=HAYIR,1=EVET)'] == 0) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].isna()) |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'].str.strip() == '') |
        (df_yon['İNDİKTEN SONRA NEREYE GİTTİ'] == 'BİLİNMİYOR')
    ]
    gitmeyen = gitmeyen_df.groupby('Saat_Dilimi').size().reset_index(name='Gitmeyen_Sayisi')
    
    # e) Genel özet
    toplam = df_yon.shape[0]
    ortalama = toplam / 24  # yaklaşık saat başı
    en_cok_yer = gidis.groupby('Gidilen_Yer')['Kisi_Sayisi'].sum().idxmax() if not gidis.empty else 'Yok'
    
    return {
        'binme': binme,
        'gelis': gelis,
        'gidis': gidis,
        'gitmeyen': gitmeyen,
        'toplam': toplam,
        'ortalama': ortalama,
        'en_cok_yer': en_cok_yer
    }

# ------------------------------
# 4. ANALİZLERİ ÇALIŞTIR
# ------------------------------
sonuc_uskudar = analiz_yap(df_uskudar, 'Üsküdar→Beşiktaş')
sonuc_besiktas = analiz_yap(df_besiktas, 'Beşiktaş→Üsküdar')

# ------------------------------
# 5. TAHMİN İÇİN VERİ HAZIRLA (Ortalama ve Mod)
# ------------------------------
# Saat dilimlerini sıralı hale getir
saat_sirasi = {f"{i:02d}:00–{i:02d}:59": i for i in range(24)}

# Üsküdar yönü için tahmin tablosu
tahmin_uskudar = sonuc_uskudar['binme'].copy()
tahmin_uskudar['Ortalama'] = tahmin_uskudar['Toplam_Binme']  # basitçe o saatteki toplam (zaten saatlik)
# En çok gidilen yeri ekle
# Her saat dilimi için en çok gidilen yeri bul
uskudar_gidis_saat = sonuc_uskudar['gidis'].copy()
mod_uskudar = uskudar_gidis_saat.groupby('Saat_Dilimi').apply(
    lambda x: x.loc[x['Kisi_Sayisi'].idxmax(), 'Gidilen_Yer'] if not x.empty else 'Yok'
).reset_index(name='En_Cok_Gidilen_Yer')
tahmin_uskudar = tahmin_uskudar.merge(mod_uskudar, on='Saat_Dilimi', how='left')
tahmin_uskudar['Saat_Sirasi'] = tahmin_uskudar['Saat_Dilimi'].map(saat_sirasi)
tahmin_uskudar = tahmin_uskudar.sort_values('Saat_Sirasi').drop('Saat_Sirasi', axis=1)

# Beşiktaş yönü için tahmin tablosu
tahmin_besiktas = sonuc_besiktas['binme'].copy()
tahmin_besiktas['Ortalama'] = tahmin_besiktas['Toplam_Binme']
besiktas_gidis_saat = sonuc_besiktas['gidis'].copy()
mod_besiktas = besiktas_gidis_saat.groupby('Saat_Dilimi').apply(
    lambda x: x.loc[x['Kisi_Sayisi'].idxmax(), 'Gidilen_Yer'] if not x.empty else 'Yok'
).reset_index(name='En_Cok_Gidilen_Yer')
tahmin_besiktas = tahmin_besiktas.merge(mod_besiktas, on='Saat_Dilimi', how='left')
tahmin_besiktas['Saat_Sirasi'] = tahmin_besiktas['Saat_Dilimi'].map(saat_sirasi)
tahmin_besiktas = tahmin_besiktas.sort_values('Saat_Sirasi').drop('Saat_Sirasi', axis=1)

# ------------------------------
# 6. EXCEL'E YAZ (MODERN DASHBOARD)
# ------------------------------
output_file = 'dashboard_prof.xlsx'

with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    workbook = writer.book
    
    # ---- VERİ SAYFALARI ----
    # Üsküdar yönü
    sonuc_uskudar['binme'].to_excel(writer, sheet_name='Uskudar_Binme', index=False)
    sonuc_uskudar['gelis'].to_excel(writer, sheet_name='Uskudar_Gelis', index=False)
    sonuc_uskudar['gidis'].to_excel(writer, sheet_name='Uskudar_Gidis', index=False)
    sonuc_uskudar['gitmeyen'].to_excel(writer, sheet_name='Uskudar_Gitmeyen', index=False)
    
    # Beşiktaş yönü
    sonuc_besiktas['binme'].to_excel(writer, sheet_name='Besiktas_Binme', index=False)
    sonuc_besiktas['gelis'].to_excel(writer, sheet_name='Besiktas_Gelis', index=False)
    sonuc_besiktas['gidis'].to_excel(writer, sheet_name='Besiktas_Gidis', index=False)
    sonuc_besiktas['gitmeyen'].to_excel(writer, sheet_name='Besiktas_Gitmeyen', index=False)
    
    # Tahmin tabloları
    tahmin_uskudar.to_excel(writer, sheet_name='Tahmin_Uskudar', index=False)
    tahmin_besiktas.to_excel(writer, sheet_name='Tahmin_Besiktas', index=False)
    
    # ---- DASHBOARD SAYFALARI ----
    def create_dashboard(sheet_name, yon_adi, sonuc, tahmin_df):
        dashboard = workbook.add_worksheet(sheet_name)
        
        # Stiller
        title_style = workbook.add_format({
            'bold': True, 'font_size': 18, 'font_color': '#1E88E5',
            'align': 'center', 'valign': 'vcenter'
        })
        header_style = workbook.add_format({
            'bold': True, 'font_size': 12, 'bg_color': '#1E88E5',
            'font_color': 'white', 'align': 'center', 'valign': 'vcenter'
        })
        card_style = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#F5F5F5',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        value_style = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#E3F2FD',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        
        # Başlık
        dashboard.merge_range('A1:F1', f'🚢 {yon_adi} Yolcu Analiz Dashboard', title_style)
        
        # Özet kartlar
        dashboard.write('A3', '📊 Özet İstatistikler', header_style)
        dashboard.merge_range('A4:B4', 'Toplam Biniş', card_style)
        dashboard.merge_range('C4:D4', f'{sonuc["toplam"]:,}', value_style)
        dashboard.merge_range('E4:F4', 'Ortalama Biniş/Saat', card_style)
        dashboard.merge_range('G4:H4', f'{sonuc["ortalama"]:.1f}', value_style)
        
        dashboard.merge_range('A5:B5', '🚫 Gitmeyen (Aktarma Yok)', card_style)
        dashboard.merge_range('C5:D5', f'{sonuc["gitmeyen"]["Gitmeyen_Sayisi"].sum():,}', value_style)
        dashboard.merge_range('E5:F5', '🏆 En Çok Gidilen Yer', card_style)
        dashboard.merge_range('G5:H5', f'{sonuc["en_cok_yer"]}', value_style)
        
        # Grafik 1: Saatlik Biniş (Sütun)
        chart1 = workbook.add_chart({'type': 'column'})
        binme_data = sonuc['binme']
        if not binme_data.empty:
            start_row = binme_data.index[0] + 2
            end_row = binme_data.index[-1] + 2
            categories = f"='{sheet_name.replace('Dashboard_', '')}_Binme'!$A${start_row}:$A${end_row}"
            values = f"='{sheet_name.replace('Dashboard_', '')}_Binme'!$B${start_row}:$B${end_row}"
            chart1.add_series({
                'name': 'Toplam Biniş',
                'categories': categories,
                'values': values,
            })
            chart1.set_title({'name': 'Saat Dilimine Göre Biniş Sayısı'})
            chart1.set_x_axis({'name': 'Saat Dilimi'})
            chart1.set_y_axis({'name': 'Kişi Sayısı'})
            chart1.set_legend({'position': 'none'})
            chart1.set_size({'width': 720, 'height': 400})
            dashboard.insert_chart('A7', chart1)
        
        # Grafik 2: En Çok Gidilen Yerler (Pasta) - Tüm yerler, ama en büyük 10 gösterelim
        gidis_data = sonuc['gidis']
        if not gidis_data.empty:
            top_yerler = gidis_data.groupby('Gidilen_Yer')['Kisi_Sayisi'].sum().nlargest(10).reset_index()
            # Verileri dashboard'a yaz
            dashboard.write('A30', '🏆 En Çok Gidilen Yerler (Top 10)', header_style)
            dashboard.write('A31', 'Yer', header_style)
            dashboard.write('B31', 'Kişi Sayısı', header_style)
            for idx, row in enumerate(top_yerler.itertuples()):
                dashboard.write(f'A{32+idx}', row.Gidilen_Yer)
                dashboard.write(f'B{32+idx}', row.Kisi_Sayisi)
            
            chart2 = workbook.add_chart({'type': 'pie'})
            chart2.add_series({
                'name': 'Gidilen Yerler',
                'categories': '=Dashboard!$A$32:$A$41',
                'values': '=Dashboard!$B$32:$B$41',
            })
            chart2.set_title({'name': 'En Çok Gidilen 10 Yer'})
            chart2.set_legend({'position': 'right'})
            chart2.set_size({'width': 500, 'height': 400})
            dashboard.insert_chart('E30', chart2)
        
        # Tablo: Tüm gidilen yerler (saat dilimine göre) - Pivot ayrı sayfada
        dashboard.write('A50', '📋 Tüm Gidilen Yerler (Saat Dilimine Göre)', header_style)
        dashboard.write('A51', 'Detaylı pivot tablo için "Gidis_Pivot" sayfasına bakınız.', workbook.add_format({'italic': True}))
        
        # Sütun genişlikleri
        dashboard.set_column('A:A', 25)
        dashboard.set_column('B:B', 15)
        dashboard.set_column('C:C', 15)
        dashboard.set_column('D:D', 15)
        dashboard.set_column('E:E', 25)
        dashboard.set_column('F:F', 15)
        dashboard.set_column('G:G', 15)
        dashboard.set_column('H:H', 15)
    
    # Dashboard sayfalarını oluştur
    create_dashboard('Dashboard_Uskudar', 'Üsküdar → Beşiktaş', sonuc_uskudar, tahmin_uskudar)
    create_dashboard('Dashboard_Besiktas', 'Beşiktaş → Üsküdar', sonuc_besiktas, tahmin_besiktas)
    
    # ---- TAHMİN SAYFASI ----
    tahmin_sheet = workbook.add_worksheet('Tahmin')
    title_style = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#1E88E5', 'align': 'center'})
    header_style = workbook.add_format({'bold': True, 'bg_color': '#1E88E5', 'font_color': 'white'})
    input_style = workbook.add_format({'bg_color': '#FFF9C4', 'border': 1})
    result_style = workbook.add_format({'bold': True, 'font_size': 14, 'bg_color': '#E8F5E9', 'border': 1})
    
    tahmin_sheet.merge_range('A1:C1', '🔮 Yolcu Tahmin Aracı', title_style)
    tahmin_sheet.write('A3', 'Yön Seçiniz:', header_style)
    tahmin_sheet.write('B3', 'Üsküdar→Beşiktaş', input_style)
    tahmin_sheet.write('C3', 'veya Beşiktaş→Üsküdar', input_style)
    tahmin_sheet.write('A4', 'Saat (0-23):', header_style)
    tahmin_sheet.write('B4', 8, input_style)
    
    tahmin_sheet.write('A6', 'Tahmini Sonuçlar:', header_style)
    tahmin_sheet.write('A7', 'Ortalama Yolcu Sayısı:', header_style)
    tahmin_sheet.write('B7', '', result_style)
    tahmin_sheet.write('A8', 'En Çok Gidilen Yer:', header_style)
    tahmin_sheet.write('B8', '', result_style)
    
    # Veri doğrulama (dropdown) ekle
    tahmin_sheet.data_validation('B3', {
        'validate': 'list',
        'source': ['Üsküdar→Beşiktaş', 'Beşiktaş→Üsküdar']
    })
    tahmin_sheet.data_validation('B4', {
        'validate': 'integer',
        'criteria': 'between',
        'minimum': 0,
        'maximum': 23
    })
    
    tahmin_sheet.set_column('A:A', 25)
    tahmin_sheet.set_column('B:B', 20)
    tahmin_sheet.set_column('C:C', 20)
    
    # Pivot tabloları ayrı sayfalara yaz (gidis pivot)
    for yon, suffix in [('Uskudar', 'Üsküdar→Beşiktaş'), ('Besiktas', 'Beşiktaş→Üsküdar')]:
        gidis_pivot = sonuc_uskudar['gidis'].pivot(index='Gidilen_Yer', columns='Saat_Dilimi', values='Kisi_Sayisi').fillna(0)
        gidis_pivot.reset_index().to_excel(writer, sheet_name=f'{yon}_Gidis_Pivot', index=False)

print(f"✅ Profesyonel dashboard oluşturuldu: {output_file}")
print("📌 Tahmin sayfasında B3 ve B4 hücrelerine veri girerek tahmin alabilirsiniz.")
print("⚠️ Not: Tahmin sonuçları Excel formülleri ile otomatik gelmeyecektir. İsterseniz VBA veya manuel DÜŞEYARA ekleyin.")
