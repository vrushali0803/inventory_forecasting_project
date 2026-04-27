import random
from db import get_connection

# ---------------------------
# Config
# ---------------------------
YEARS = [2022, 2023, 2024]
REGIONS = ["Maharashtra", "Gujarat", "Madhya Pradesh", "Telangana", "Karnataka"]

PRODUCTS = [
    {"crop": "Soybean", "variety": "SB-101", "season": "Kharif"},
    {"crop": "Soybean", "variety": "SB-202", "season": "Kharif"},
    {"crop": "Cotton", "variety": "CT-101", "season": "Kharif"},
    {"crop": "Cotton", "variety": "CT-202", "season": "Kharif"},
    {"crop": "Maize", "variety": "MZ-101", "season": "Rabi"},
    {"crop": "Maize", "variety": "MZ-202", "season": "Rabi"},
]

# region preference multipliers to simulate realistic patterns
REGION_FACTOR = {
    "Maharashtra": 1.3,
    "Gujarat": 1.2,
    "Madhya Pradesh": 1.1,
    "Telangana": 0.9,
    "Karnataka": 0.8,
}

BASE_DEMAND = {
    "Soybean": 350,
    "Cotton": 280,
    "Maize": 180
}

# ---------------------------
# Seed Function
# ---------------------------
def seed_data():
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing synthetic data (optional but useful for re-running)
    cursor.execute("DELETE FROM sales_history;")
    cursor.execute("DELETE FROM products;")
    cursor.execute("DELETE FROM forecast_data;")

    # ---------------------------
    # Insert Products
    # ---------------------------
    for p in PRODUCTS:
        cursor.execute(
            """
            INSERT INTO products (crop, variety, season)
            VALUES (%s,%s,%s)
            """,
            (p["crop"], p["variety"], p["season"])
        )

    # ---------------------------
    # Generate Sales History
    # ---------------------------
    rows_inserted = 0

    for year in YEARS:
        for region in REGIONS:
            for p in PRODUCTS:
                crop = p["crop"]
                variety = p["variety"]
                season = p["season"]

                base = BASE_DEMAND[crop]
                region_factor = REGION_FACTOR[region]

                # yearly growth trend
                growth = 1 + (year - 2022) * 0.08

                quantity = int(base * region_factor * growth * random.uniform(0.8, 1.2))

                cursor.execute(
                    """
                    INSERT INTO sales_history (crop, variety, season, year, region, quantity)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    (crop, variety, season, year, region, quantity)
                )

                rows_inserted += 1

    # ---------------------------
    # Generate Forecast Data
    # ---------------------------
    for crop, base in BASE_DEMAND.items():
        forecast = int(base * random.uniform(1.2, 1.6))
        cursor.execute(
            """
            INSERT INTO forecast_data (crop, forecast_quantity)
            VALUES (%s,%s)
            """,
            (crop, forecast)
        )

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Inserted {rows_inserted} sales records successfully.")


if __name__ == "__main__":
    seed_data()