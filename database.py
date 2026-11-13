# -*- coding: utf-8 -*-
"""
Database configuration - Clean slate with NO mock numbers.
User enters all data themselves on localhost.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "minhan_sales.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(reset_all=False):
    conn = get_connection()
    cur = conn.cursor()

    # 1. Bảng sản phẩm & giá niêm yết
    cur.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit TEXT NOT NULL,
        unit_price REAL NOT NULL,
        stock_qty INTEGER NOT NULL DEFAULT 0,
        lead_time_days INTEGER NOT NULL DEFAULT 7,
        warranty_months INTEGER NOT NULL DEFAULT 12,
        description TEXT
    )
    ''')

    # 2. Bảng Nhân viên Kinh doanh (6 NVKD Minh An)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sales_reps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        current_leads INTEGER DEFAULT 0,
        specialty TEXT
    )
    ''')

    # 3. Bảng Hồ sơ Cơ hội
    cur.execute('''
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        client_name TEXT,
        client_company TEXT,
        client_email TEXT,
        client_phone TEXT,
        raw_request TEXT NOT NULL,
        status TEXT NOT NULL, 
        is_info_sufficient INTEGER DEFAULT 1,
        missing_info_notes TEXT,
        assigned_rep_id INTEGER,
        assigned_rep_name TEXT,
        requested_budget REAL DEFAULT 0,
        requested_deadline TEXT,
        feasible_deadline TEXT,
        deadline_status TEXT, 
        total_original_price REAL DEFAULT 0,
        requested_discount_pct REAL DEFAULT 0,
        approved_discount_pct REAL DEFAULT 0,
        total_final_price REAL DEFAULT 0,
        requires_manager_approval INTEGER DEFAULT 0,
        approval_status TEXT DEFAULT 'NOT_REQUIRED', 
        manager_notes TEXT,
        proposal_email_draft TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_rep_id) REFERENCES sales_reps (id)
    )
    ''')

    # 4. Bảng Chi tiết Hạng mục
    cur.execute('''
    CREATE TABLE IF NOT EXISTS opportunity_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER NOT NULL,
        product_id INTEGER,
        matched_sku TEXT,
        matched_name TEXT,
        requested_name TEXT,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        stock_available INTEGER NOT NULL,
        is_stock_sufficient INTEGER NOT NULL,
        item_lead_time_days INTEGER DEFAULT 0,
        FOREIGN KEY (opportunity_id) REFERENCES opportunities (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')

    # 5. Bảng To-Do Tasks (Không chèn sẵn số liệu giả)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        emoji TEXT DEFAULT '📋',
        due_info TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 6. Bảng Hoạt động (Không chèn sẵn số liệu giả)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        icon_type TEXT DEFAULT 'check',
        time_ago TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 7. Cài đặt hệ thống
    cur.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    conn.commit()

    if reset_all:
        cur.execute('DELETE FROM opportunities')
        cur.execute('DELETE FROM opportunity_items')
        cur.execute('DELETE FROM tasks')
        cur.execute('DELETE FROM activities')
        cur.execute('UPDATE sales_reps SET current_leads = 0')
        # Đưa các chỉ số về 0 để người dùng tự nhập
        clean_settings = [
            ('custom_kpi_done', '0'),
            ('custom_kpi_progress', '0'),
            ('custom_kpi_completed', '0'),
            ('custom_kpi_focus', '0h'),
            ('user_name', 'Quản trị viên'),
            ('user_greeting', 'Nhấn vào đây để nhập lời chào hoặc mục tiêu của bạn ✨'),
            ('chart_data', '{"labels": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"], "values": [0, 0, 0, 0, 0, 0, 0], "badge": "Nhấp để đổi ghi chú"}')
        ]
        for k, v in clean_settings:
            cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (k, v))
        conn.commit()

    conn.close()

def clear_mock_data():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM opportunities')
    cur.execute('DELETE FROM opportunity_items')
    cur.execute('DELETE FROM tasks')
    cur.execute('DELETE FROM activities')
    cur.execute('UPDATE sales_reps SET current_leads = 0')
    
    clean_settings = [
        ('custom_kpi_done', '0'),
        ('custom_kpi_progress', '0'),
        ('custom_kpi_completed', '0'),
        ('custom_kpi_focus', '0h'),
        ('user_name', 'Quản trị viên'),
        ('user_greeting', 'Nhấn vào đây để nhập lời chào hoặc mục tiêu của bạn ✨'),
        ('chart_data', '{"labels": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"], "values": [0, 0, 0, 0, 0, 0, 0], "badge": "Nhấp để đổi ghi chú"}')
    ]
    for k, v in clean_settings:
        cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (k, v))
    conn.commit()
    conn.close()
    print("All mock data cleared! Metrics set to 0. Database is now 100% clean for user input.")

if __name__ == "__main__":
    init_db(reset_all=True)
    clear_mock_data()
