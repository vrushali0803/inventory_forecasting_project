import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    print("DB PASSWORD:", os.getenv("DB_PASSWORD"))
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    return conn
    print("DB PASSWORD:", os.getenv("DB_PASSWORD"))