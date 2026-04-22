import psycopg2
import csv
from config import params

def init_db():
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pb (id SERIAL PRIMARY KEY, name TEXT, phone TEXT UNIQUE)")
    conn.commit()
    cur.close()
    conn.close()

def main():
    try:
        init_db()
        print("--- PhoneBook ---")
        name = input("Enter Name: ")
        phone = input("Enter Phone: ")
        
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute("INSERT INTO pb (name, phone) VALUES (%s, %s) ON CONFLICT DO NOTHING", (name, phone))
        conn.commit()
        
        cur.execute("SELECT * FROM pb")
        print("All contacts:", cur.fetchall())
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()