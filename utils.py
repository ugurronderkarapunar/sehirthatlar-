import pandas as pd
import networkx as nx
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime

def load_data(file):
    df = pd.read_excel("ÜSKÜDAR BEŞİKTAŞ YÖNÜ.xlsx")
    # tarih ve saati birleştir
    df['datetime'] = pd.to_datetime(df['Tarih'].astype(str) + ' ' + df['Saat'].astype(str))
    return df

def build_graph(df):
    G = nx.Graph()
    # Her benzersiz biniş-iniş çifti için bir kenar ekle
    for _, row in df.iterrows():
        G.add_edge(row['Biniş_İskelesi'], row['İniş_İskelesi'], weight=1)  # veya sefer süresi
    return G

def find_alternative_route(G, origin, dest, exclude_edge):
    # exclude_edge'ı geçici olarak çıkar
    G_temp = G.copy()
    if exclude_edge in G_temp.edges:
        G_temp.remove_edge(*exclude_edge)
    try:
        path = nx.shortest_path(G_temp, origin, dest)
        return path
    except nx.NetworkXNoPath:
        return None

def train_model(df):
    # Özellik mühendisliği
    df['hour'] = df['datetime'].dt.hour
    df['dayofweek'] = df['datetime'].dt.dayofweek
    df['month'] = df['datetime'].dt.month
    # Her iskele için ayrı model veya tümünü kapsayan bir model
    X = df[['hour','dayofweek','month']]
    y = df['Yolcu_Sayısı']
    model = RandomForestRegressor(n_estimators=100)
    model.fit(X, y)
    return model

def predict_passengers(model, iskele, date, hour):
    # Gerçekte iskele bazlı filtreleme yapılmalı, burada basitçe örnek
    dayofweek = date.weekday()
    month = date.month
    X_pred = pd.DataFrame([[hour, dayofweek, month]], columns=['hour','dayofweek','month'])
    return model.predict(X_pred)[0]
