import psycopg2

def get_db_connection():
    conn = psycopg2.connect(
    host="localhost",
    database="seed_erp",
    user="postgres",
    password="vrush123",
    port="5433"
)
    return conn
