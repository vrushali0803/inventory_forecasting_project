import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

def arima_forecast():
    df = pd.read_csv("data/raw/sales_data.csv")
    df['date'] = pd.to_datetime(df['date'])

    # Aggregate sales by date
    ts = df.groupby('date')['sales'].sum()

    model = ARIMA(ts, order=(1,1,1))
    model_fit = model.fit()

    forecast = model_fit.forecast(steps=5)
    print("ARIMA Forecast (Next 5 days):")
    print(forecast)

if __name__ == "__main__":
    arima_forecast()
