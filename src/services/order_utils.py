import pandas as pd
from datetime import datetime
import os

ORDERS_FILE = "data/orders.csv"

def save_order(buyer_type, buyer_name, region, crop, variety, season, quantity_quintal):
    # Load existing orders
    if os.path.exists(ORDERS_FILE):
        df = pd.read_csv(ORDERS_FILE)
    else:
        df = pd.DataFrame(columns=[
            "order_id", "buyer_type", "buyer_name", "region",
            "crop", "variety", "season", "quantity_quintal", "booking_date"
        ])

    # Generate order ID
    order_id = f"ORD{len(df) + 1:04d}"

    # Create new order row
    new_order = {
        "order_id": order_id,
        "buyer_type": buyer_type,
        "buyer_name": buyer_name,
        "region": region,
        "crop": crop,
        "variety": variety,
        "season": season,
        "quantity_quintal": quantity_quintal,
        "booking_date": datetime.now().strftime("%Y-%m-%d")
    }

    # Append and save
    df = pd.concat([df, pd.DataFrame([new_order])], ignore_index=True)
    df.to_csv(ORDERS_FILE, index=False)

    return order_id
