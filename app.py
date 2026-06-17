import pandas as pd
import matplotlib.pyplot as plt

# Dosyayı oku
df = pd.read_excel('20260506_2_REV5.xlsx', sheet_name='Sayfa2')
df.columns = df.columns.str.strip()
df['MERKEZDEN GEMİYE BİNİŞ'] = pd.to_datetime(df['MERKEZDEN GEMİYE BİNİŞ'], format='mixed', errors='coerce')
df = df.dropna(subset=['MERKEZDEN GEMİYE BİNİŞ'])
df['Saat'] = df['MERKEZDEN GEMİYE BİNİŞ'].dt.hour
df['YÖN'] = df['YÖN'].str.strip()

# Yönlere göre ayır
df_uskudar = df[df['YÖN'] == 'ÜSKÜDAR → BEŞİKTAŞ']
df_besiktas = df[df['YÖN'] == 'BEŞİKTAŞ → ÜSKÜDAR']

# Saatlik analiz
binme_u = df_uskudar.groupby('Saat').size().reset_index(name='Yolcu')
binme_b = df_besiktas.groupby('Saat').size().reset_index(name='Yolcu')

print("="*50)
print("Üsküdar → Beşiktaş")
print(f"Toplam: {len(df_uskudar)}")
print(f"Ortalama: {len(df_uskudar)/24:.1f}")
print("\nSaatlik Dağılım:")
print(binme_u.to_string(index=False))

print("\n" + "="*50)
print("Beşiktaş → Üsküdar")
print(f"Toplam: {len(df_besiktas)}")
print(f"Ortalama: {len(df_besiktas)/24:.1f}")
print("\nSaatlik Dağılım:")
print(binme_b.to_string(index=False))

# Grafik
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].bar(binme_u['Saat'], binme_u['Yolcu'], color='blue')
axes[0].set_title('Üsküdar→Beşiktaş')
axes[1].bar(binme_b['Saat'], binme_b['Yolcu'], color='orange')
axes[1].set_title('Beşiktaş→Üsküdar')
plt.tight_layout()
plt.savefig('vapur_grafik.png')
print("\n✅ Grafik 'vapur_grafik.png' olarak kaydedildi.")

# Excel raporu
with pd.ExcelWriter('vapur_analiz.xlsx') as writer:
    binme_u.to_excel(writer, sheet_name='Uskudar_Saatlik', index=False)
    binme_b.to_excel(writer, sheet_name='Besiktas_Saatlik', index=False)
    df_uskudar.to_excel(writer, sheet_name='Uskudar_Detay', index=False)
    df_besiktas.to_excel(writer, sheet_name='Besiktas_Detay', index=False)

print("✅ Excel raporu 'vapur_analiz.xlsx' olarak kaydedildi.")
