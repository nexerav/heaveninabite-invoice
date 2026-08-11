import sqlite3
import os

DB_PATH = 'data/database.db'

def init_db():
    os.makedirs('data', exist_ok=True)
    os.makedirs('data/exports', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Invoices Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT,
            client_phone TEXT,
            items TEXT NOT NULL, -- JSON formatted array: [{"description": "", "qty": 1, "price": 0.0}]
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Unpaid', -- 'Paid' or 'Unpaid'
            special_notes TEXT
        )
    ''')
    
    # Pre-populate sample invoice if table is empty
    cursor.execute('SELECT COUNT(*) FROM invoices')
    if cursor.fetchone()[0] == 0:
        import json
        sample_items = json.dumps([
            {"description": "Bespoke 3-Tier Chocolate Wedding Cake", "qty": 1, "price": 1450.00},
            {"description": "Gourmet Savory Platter Array", "qty": 2, "price": 380.00}
        ])
        cursor.execute('''
            INSERT INTO invoices (invoice_number, date, client_name, client_email, client_phone, items, total_amount, status, special_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'INV-2026-0001',
            '2026-08-10',
            'Sipho Khumalo',
            'sipho@example.co.za',
            '+27 82 555 1234',
            sample_items,
            2210.00,
            'Unpaid',
            'Delivery to Boksburg Central by 11:00 AM'
        ))
        conn.commit()
        print("Sample data populated.")

    conn.close()
    print("SQLite database successfully initialized at:", DB_PATH)

if __name__ == '__main__':
    init_db()
