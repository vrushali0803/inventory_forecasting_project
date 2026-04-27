import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet

def load_data():
    df = pd.read_csv("data/raw/sales_data.csv")
    df['date'] = pd.to_datetime(df['date'])
    return df

def arima_forecast(ts):
    model = ARIMA(ts, order=(1,1,1))
    fit = model.fit()
    return fit.forecast(steps=5)

def prophet_forecast(df):
    p_df = df.groupby('date')['sales'].sum().reset_index()
    p_df.columns = ['ds', 'y']
    model = Prophet()
    model.fit(p_df)
    future = model.make_future_dataframe(periods=5)
    forecast = model.predict(future)
    return forecast[['ds', 'yhat']].tail(5)

if __name__ == "__main__":
    df = load_data()
    ts = df.groupby('date')['sales'].sum()

    arima = arima_forecast(ts).reset_index()
    arima.columns = ['date', 'arima_forecast']

    prophet = prophet_forecast(df)
    prophet.columns = ['date', 'prophet_forecast']

    result = pd.merge(arima, prophet, on='date')
    print(result)

    result.to_csv("data/processed/forecast_comparison.csv", index=False)
