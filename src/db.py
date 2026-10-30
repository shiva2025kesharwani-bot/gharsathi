import sqlite3, os
from datetime import datetime
from src.config import DB_PATH

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL, role TEXT NOT NULL,
        masked_aadhaar TEXT, address TEXT,
        consent_given INTEGER DEFAULT 0, consent_at TEXT,
        status TEXT DEFAULT 'pending', rejection_reason TEXT,
        verified_at TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS helpers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
        skills TEXT, daily_rate INTEGER, monthly_rate INTEGER,
        area TEXT, rating REAL DEFAULT 0.0,
        FOREIGN KEY(user_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER, helper_id INTEGER, booking_type TEXT,
        slot TEXT, start_date TEXT, end_date TEXT, total_days INTEGER,
        amount INTEGER, status TEXT DEFAULT 'active', created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS skips(
        id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER,
        skip_date TEXT, created_at TEXT)""")
    conn.commit(); conn.close()

def get_user(phone):
    conn = get_conn()
    r = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    conn.close(); return r

def get_helper_by_user(user_id):
    conn = get_conn()
    r = conn.execute("SELECT * FROM helpers WHERE user_id=?", (user_id,)).fetchone()
    conn.close(); return r

def is_helper_busy_range(helper_id, sd, ed, slot):
    conn = get_conn()
    r = conn.execute("""SELECT 1 FROM bookings WHERE helper_id=? AND slot=?
                        AND status='active' AND start_date <= ? AND end_date >= ?""",
                     (helper_id, slot, ed, sd)).fetchone()
    conn.close(); return bool(r)

def create_user(name, phone, role, masked_aadhaar, address,
                skills="", daily_rate=0, monthly_rate=0, area=""):
    conn = get_conn()
    try:
        cur = conn.execute("""INSERT INTO users(name,phone,role,masked_aadhaar,address,
                            consent_given,consent_at,status,created_at)
                            VALUES(?,?,?,?,?,?,?,?,?)""",
                         (name, phone, role, masked_aadhaar, address, 1,
                          datetime.now().isoformat(), "pending",
                          datetime.now().isoformat()))
        uid = cur.lastrowid
        if role == "helper":
            conn.execute("""INSERT INTO helpers(user_id,skills,daily_rate,monthly_rate,area)
                            VALUES(?,?,?,?,?)""",
                         (uid, skills, daily_rate, monthly_rate, area))
        conn.commit()
        return True, f"Signup ho gaya! Masked Aadhaar: {masked_aadhaar}"
    except sqlite3.IntegrityError:
        return False, "Ye phone already registered hai"
    finally:
        conn.close()

def create_booking(customer_id, helper_id, btype, slot, sd, ed, days, amount):
    conn = get_conn()
    conn.execute("""INSERT INTO bookings(customer_id,helper_id,booking_type,slot,
                    start_date,end_date,total_days,amount,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                 (customer_id, helper_id, btype, slot, sd, ed, days, amount,
                  datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_verified_helpers():
    conn = get_conn()
    rows = conn.execute("""SELECT h.id, u.name, h.skills, h.daily_rate, h.monthly_rate,
                           h.area, h.rating FROM helpers h
                           JOIN users u ON u.id=h.user_id
                           WHERE u.status='verified'""").fetchall()
    conn.close(); return rows

def get_customer_bookings(customer_id):
    conn = get_conn()
    rows = conn.execute("""SELECT b.id,b.booking_type,b.slot,b.start_date,b.end_date,
                           b.total_days,b.amount,b.status,u.name
                           FROM bookings b JOIN helpers h ON h.id=b.helper_id
                           JOIN users u ON u.id=h.user_id
                           WHERE b.customer_id=? ORDER BY b.id DESC""",
                        (customer_id,)).fetchall()
    conn.close(); return rows

def get_helper_bookings(helper_id):
    conn = get_conn()
    rows = conn.execute("""SELECT b.id,b.booking_type,b.slot,b.start_date,b.end_date,
                           b.amount,b.status,u.name FROM bookings b
                           JOIN users u ON u.id=b.customer_id
                           WHERE b.helper_id=? ORDER BY b.id DESC""",
                        (helper_id,)).fetchall()
    conn.close(); return rows

def get_skip_count(booking_id):
    conn = get_conn()
    r = conn.execute("SELECT COUNT(*) FROM skips WHERE booking_id=?",
                     (booking_id,)).fetchone()[0]
    conn.close(); return r

def add_skip(booking_id, skip_date):
    conn = get_conn()
    dup = conn.execute("SELECT 1 FROM skips WHERE booking_id=? AND skip_date=?",
                       (booking_id, skip_date)).fetchone()
    if dup:
        conn.close(); return False, "Ye date pehle skip ho chuki hai"
    conn.execute("INSERT INTO skips(booking_id,skip_date,created_at) VALUES(?,?,?)",
                 (booking_id, skip_date, datetime.now().isoformat()))
    conn.commit(); conn.close()
    return True, "Skip ho gaya"

def get_pending_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users WHERE status='pending'").fetchall()
    conn.close(); return rows

def approve_user(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET status='verified', verified_at=? WHERE id=?",
                 (datetime.now().isoformat(), user_id))
    conn.commit(); conn.close()

def reject_user(user_id, reason):
    conn = get_conn()
    conn.execute("UPDATE users SET status='rejected', rejection_reason=? WHERE id=?",
                 (reason, user_id))
    conn.commit(); conn.close()
