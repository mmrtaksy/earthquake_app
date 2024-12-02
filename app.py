from flask import Flask, jsonify, render_template
import requests
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C
from pmdarima import auto_arima
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error
from flask_caching import Cache

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Veri çekme ve temizleme
def fetch_earthquake_data():
    try:
        response = requests.get("https://api.orhanaydogdu.com.tr/deprem/kandilli/live")
        response.raise_for_status()
        data = response.json().get('result', [])

        if not data:
            print("API'den veri alınamadı.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['date_time'] = pd.to_datetime(df['date_time'], errors='coerce')
        df.dropna(subset=['date_time'], inplace=True)
        df.set_index('date_time', inplace=True)
        df = df.sort_index()
        df = df[df['mag'] >= 1.0]

        if df.empty:
            print("Filtreleme sonrası DataFrame boş.")
            return pd.DataFrame()

        print("Veri başarıyla çekildi ve temizlendi.")
        return df

    except requests.exceptions.RequestException as e:
        print(f"API hatası: {e}")
        return pd.DataFrame()

# Veri ön işleme
def preprocess_data(df):
    # Alternatif frekans kullanımı
    df = df.asfreq('h')  # Saatlik frekans
    
    # Zaman farklarını hesapla
    df['time_diff'] = df.index.to_series().diff().dt.total_seconds()
    



    # Eksik değerleri doldur
    df['time_diff'] = df['time_diff'].bfill().ffill()
    
    # Sabit seriler için rastgele gürültü eklemek (isteğe bağlı)
    if df['time_diff'].std() == 0:
        print("Zaman serisi hala sabit.")
        df['time_diff'] += np.random.normal(0, 0.1, len(df))
    
    return df

def arima_forecast(df):
    try:
        df = preprocess_data(df)

        if df['time_diff'].std() == 0:
            print("Zaman serisi sabit, ARIMA tahmini yapılamıyor.")
            return None

        # ARIMA optimizasyonu
        model = auto_arima(df['time_diff'], seasonal=False, stepwise=True, trace=True, suppress_warnings=True)
        
        if model.order == (0, 0, 0):
            print("ARIMA anlamlı bir model bulamadı, sabit bir değer döndürülüyor.")
            return 0.5  # Saat cinsinden örnek bir varsayılan tahmin

        forecast = model.predict(n_periods=1)
        return forecast[0] / 3600  # Saat cinsinden
    except Exception as e:
        print(f"ARIMA hatası: {e}")
        return None



# Gaussian Process tahmini
def gaussian_forecast(df):
    try:
        df = preprocess_data(df)

        X = np.arange(len(df)).reshape(-1, 1)
        y = df['time_diff'].values

        # Gaussian kernel parametrelerini genişlet
        kernel = C(1.0, (1e-4, 1e3)) * RBF(1, (1e-4, 1e3)) + RBF(length_scale=10.0, length_scale_bounds=(1e-4, 1e6))
        # gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, alpha=1e-2)
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, alpha=1e-1)
        gp.fit(X, y)

        next_index = np.array([[len(df)]])
        y_pred, sigma = gp.predict(next_index, return_std=True)
        return y_pred[0] / 3600, sigma[0] / 3600  # Saat cinsinden tahmin ve belirsizlik
    except Exception as e:
        print(f"Gaussian Process hatası: {e}")
        return None, None


# Performans değerlendirme
def evaluate_predictions(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"MAE: {mae}, RMSE: {rmse}")
    return mae, rmse

# Tahmin grafiği
def plot_predictions(df, predictions):
    plt.figure(figsize=(10, 6))
    plt.plot(df.index[-len(predictions):], predictions, label="Tahmin")
    plt.plot(df.index, df['time_diff'], label="Gerçek")
    plt.legend()
    plt.show()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/earthquake_data')
@cache.cached(timeout=300)
def earthquake_data():
    df = fetch_earthquake_data()
    
    if df.isnull().values.any():
        print("Veri setinde eksik değerler tespit edildi.")


    if df.empty:
        return jsonify({"error": "No earthquake data available"}), 404

    try:
        latest_earthquake = df.iloc[-1]
        average_magnitude = df['mag'].mean()

        # ARIMA tahmini
        arima_prediction_hours = arima_forecast(df)

        if arima_prediction_hours is None:
            next_earthquake_time = "Tahmin yapılamadı"

        next_earthquake_time = None
        if arima_prediction_hours is not None:
            next_earthquake_time = (datetime.now() + pd.Timedelta(hours=arima_prediction_hours)).isoformat()

        # Gaussian tahmini
        gp_prediction, gp_sigma = gaussian_forecast(df)

        # JSON yanıtı oluştur
        return jsonify({
            "average_magnitude": average_magnitude,
            "next_earthquake": next_earthquake_time,
            "earthquake_depth": latest_earthquake.get("depth", "Unknown"),
            "earthquake_location": latest_earthquake.get("title", "Unknown"),
            "earthquake_magnitude": latest_earthquake["mag"],
            "recent_earthquake_count": len(df),
            "last_update": datetime.now().isoformat(),
            "today_date": datetime.now().isoformat(),
            "closest_cities": latest_earthquake.get('location_properties', {}).get('closestCities', [])
        })

    except Exception as e:
        print(f"Error processing earthquake data: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
