import pandas as pd

def load_data():
    df = pd.read_csv("data/raw/sales_data.csv")
    df['date'] = pd.to_datetime(df['date'])
    return df

if __name__ == "__main__":
    df = load_data()
    print(df)
