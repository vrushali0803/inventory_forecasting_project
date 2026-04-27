import pandas as pd
from prophet import Prophet

def prophet_forecast():
    df = pd.read_csv("data/raw/sales_data.csv")
    df['date'] = pd.to_datetime(df['date'])

    # Prophet expects columns: ds (date), y (value)
    prophet_df = df.groupby('date')['sales'].sum().reset_index()
    prophet_df.columns = ['ds', 'y']

    model = Prophet()
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=5)
    forecast = model.predict(future)

    print("Prophet Forecast (Next 5 days):")
    print(forecast[['ds', 'yhat']].tail(5))

if __name__ == "__main__":
    prophet_forecast()
