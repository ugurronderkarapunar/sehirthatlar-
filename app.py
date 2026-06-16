import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_data, build_graph, find_alternative_route, train_model, predict_passengers

st.set_page_config(page_title="Vapur Optimizasyonu", layout="wide")

st.title("🚢 Üsküdar-Beşiktaş Hattı Analiz ve Optimizasyon")

# 1. Veri yükleme
uploaded_file = st.file_uploader("Excel dosyasını yükleyin", type=["xlsx"])
if uploaded_file:
    df = load_data(uploaded_file)
    st.dataframe(df.head())
    
    # 2. Graf oluştur
    G = build_graph(df)  # iskeleler arası bağlantılar
    st.success("Graf başarıyla oluşturuldu.")
    
    # 3. Alternatif rota bulma
    col1, col2 = st.columns(2)
    with col1:
        origin = st.selectbox("Biniş İskelesi", df['Biniş_İskelesi'].unique())
    with col2:
        dest = st.selectbox("İniş İskelesi", df['İniş_İskelesi'].unique())
    
    if st.button("Rota Öner"):
        alt_route = find_alternative_route(G, origin, dest, exclude_edge=("Üsküdar","Beşiktaş"))
        if alt_route:
            st.write(f"✅ Alternatif rota: {' -> '.join(alt_route)}")
        else:
            st.write("❌ Alternatif rota bulunamadı, mevcut rotayı kullanmalısınız.")
    
    # 4. Makine öğrenmesi tahmini (eğitim ve tahmin)
    # Modeli eğit (veya kaydedilmiş modeli yükle)
    model = train_model(df)  # bu fonksiyon içinde veriyi hazırlayıp modeli eğit
    # Kullanıcıdan tahmin için girdi al
    st.subheader("Yolcu Sayısı Tahmini")
    date_input = st.date_input("Tarih")
    hour_input = st.slider("Saat", 0, 23, 12)
    iskele_input = st.selectbox("İskele", df['İniş_İskelesi'].unique())
    if st.button("Tahmin Et"):
        pred = predict_passengers(model, iskele_input, date_input, hour_input)
        st.metric("Tahmini Yolcu Sayısı", int(pred))
    
    # 5. Dashboard – Zaman serisi grafikleri
    st.subheader("Zaman İçinde Yolcu Dağılımı")
    fig = px.line(df.groupby(['Tarih','Saat']).sum('Yolcu_Sayısı').reset_index(),
                  x='Tarih', y='Yolcu_Sayısı', title="Günlük Toplam Yolcu")
    st.plotly_chart(fig)
    
    # İskele bazında kırılım
    fig2 = px.bar(df.groupby('İniş_İskelesi').sum('Yolcu_Sayısı').reset_index(),
                  x='İniş_İskelesi', y='Yolcu_Sayısı', title="İskelelere Göre İnen Yolcu Sayısı")
    st.plotly_chart(fig2)
