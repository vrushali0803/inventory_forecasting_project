from db import get_db_connection
import pandas as pd
from sklearn.linear_model import LinearRegression

def predict_demand(region):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT product_name, COUNT(*) as demand,
               EXTRACT(MONTH FROM created_at) as month
        FROM orders
        WHERE region = %s
        GROUP BY product_name, month
    """, (region,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=['crop_name', 'quantity', 'month'])

    # Convert Decimal → float
    df['quantity'] = df['quantity'].astype(float)
    df['month'] = df['month'].astype(float)

    if df.empty:
        return {"crop": "No Data", "demand": 0}

    results = []

    for crop in df["crop_name"].unique():

        crop_df = df[df["crop_name"] == crop]

        X = crop_df[["month"]]
        y = crop_df["quantity"]

        if len(X) < 2:
            continue

        model = LinearRegression()
        model.fit(X, y)

        # ✅ FIXED: correct next month logic
        next_month_value = crop_df["month"].max() + 1

        next_month_df = pd.DataFrame([[next_month_value]], columns=['month'])

        predicted = model.predict(next_month_df)[0]  # ✅ get number

        results.append((crop, predicted))

    if not results:
        return {"crop": "No Data", "demand": 0}

    best_crop = max(results, key=lambda x: x[1])

    return {
        "crop": best_crop[0],
        "demand": int(best_crop[1])
    }