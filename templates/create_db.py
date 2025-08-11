import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "bmi.db")  # ระบุ path ที่แน่นอน

def create_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            dob TEXT,
            gender TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bmi_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            height REAL,
            weight REAL,
            bmi REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✔ สร้างฐานข้อมูลและตารางเรียบร้อยแล้วที่", DB_PATH)

if __name__ == "__main__":
    create_db()
