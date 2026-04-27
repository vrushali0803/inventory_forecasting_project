import pandas as pd
from db import get_connection

# Read Excel file
df = pd.read_excel("sales_history.xlsx")

conn = get_connection()
cursor = conn.cursor()

for _, row in df.iterrows():
    cursor.execute(
        """
        INSERT INTO sales_history (crop, variety, season, year, region, quantity)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            row["crop"],
            row["variety"],
            row["season"],
            int(row["year"]),
            row["region"],
            int(row["quantity"])
        )
    )

conn.commit()
cursor.close()
conn.close()

print("Sales data imported successfully!")