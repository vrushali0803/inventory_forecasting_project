from db import get_connection

conn = get_connection()
print("Database connected successfully!")

conn.close()
