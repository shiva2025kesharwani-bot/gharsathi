import streamlit as st
import sqlite3
import os
import re
from datetime import datetime, date, timedelta

# --- SETUP & CONFIG ---
st.set_page_config(page_title="GharSathi", page_icon=":house:", layout="wide")
DB_PATH = "gharsathi_live.db"
ADMIN_PASSWORD = "admin123"

# --- DB FUNCTIONS ---
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT UNIQUE, role TEXT,
        masked_aadhaar TEXT, address TEXT, consent_given INTEGER, status TEXT DEFAULT 'pending', rejection_reason TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS helpers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, skills TEXT,
        daily_rate INTEGER, monthly_rate INTEGER, area TEXT, rating REAL DEFAULT 0.0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, helper_id INTEGER,
        booking_type TEXT, slot TEXT, start_date TEXT, end_date TEXT, total_days INTEGER,
        amount INTEGER, status TEXT DEFAULT 'active')""")
    c.execute("""CREATE TABLE IF NOT EXISTS skips(
        id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, skip_date TEXT)""")
    conn.commit(); conn.close()

init_db()

def get_user(phone):
    conn = get_conn(); r = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone(); conn.close(); return r

def get_helper_by_user(user_id):
    conn = get_conn(); r = conn.execute("SELECT * FROM helpers WHERE user_id=?", (user_id,)).fetchone(); conn.close(); return r

def is_helper_busy_range(helper_id, sd, ed, slot):
    conn = get_conn()
    r = conn.execute("SELECT 1 FROM bookings WHERE helper_id=? AND slot=? AND status='active' AND start_date <= ? AND end_date >= ?", (helper_id, slot, ed, sd)).fetchone()
    conn.close(); return bool(r)

def create_user(name, phone, role, masked_aadhaar, address, skills="", dr=0, mr=0, area=""):
    conn = get_conn()
    try:
        cur = conn.execute("INSERT INTO users(name,phone,role,masked_aadhaar,address,consent_given) VALUES(?,?,?,?,?,1)", (name, phone, role, masked_aadhaar, address))
        uid = cur.lastrowid
        if role == "helper":
            conn.execute("INSERT INTO helpers(user_id,skills,daily_rate,monthly_rate,area) VALUES(?,?,?,?,?)", (uid, skills, dr, mr, area))
        conn.commit(); return True, f"Signup done! Masked Aadhaar: {masked_aadhaar}"
    except sqlite3.IntegrityError: return False, "Phone already registered."
    finally: conn.close()

def create_booking(customer_id, helper_id, btype, slot, sd, ed, days, amount):
    conn = get_conn()
    conn.execute("INSERT INTO bookings(customer_id,helper_id,booking_type,slot,start_date,end_date,total_days,amount) VALUES(?,?,?,?,?,?,?,?)", (customer_id, helper_id, btype, slot, sd, ed, days, amount))
    conn.commit(); conn.close()

def get_verified_helpers():
    conn = get_conn(); rows = conn.execute("SELECT h.id, u.name, h.skills, h.daily_rate, h.monthly_rate, h.area, h.rating FROM helpers h JOIN users u ON u.id=h.user_id WHERE u.status='verified'").fetchall(); conn.close(); return rows

def get_customer_bookings(customer_id):
    conn = get_conn(); rows = conn.execute("SELECT b.id,b.booking_type,b.slot,b.start_date,b.end_date,b.total_days,b.amount,b.status,u.name FROM bookings b JOIN helpers h ON h.id=b.helper_id JOIN users u ON u.id=h.user_id WHERE b.customer_id=? ORDER BY b.id DESC", (customer_id,)).fetchall(); conn.close(); return rows

def get_helper_bookings(helper_id):
    conn = get_conn(); rows = conn.execute("SELECT b.id,b.booking_type,b.slot,b.start_date,b.end_date,b.amount,b.status,u.name FROM bookings b JOIN users u ON u.id=b.customer_id WHERE b.helper_id=? ORDER BY b.id DESC", (helper_id,)).fetchall(); conn.close(); return rows

def get_skip_count(booking_id):
    conn = get_conn(); r = conn.execute("SELECT COUNT(*) FROM skips WHERE booking_id=?", (booking_id,)).fetchone()[0]; conn.close(); return r

def add_skip(booking_id, skip_date):
    conn = get_conn()
    dup = conn.execute("SELECT 1 FROM skips WHERE booking_id=? AND skip_date=?", (booking_id, skip_date)).fetchone()
    if dup: conn.close(); return False, "Already skipped."
    conn.execute("INSERT INTO skips(booking_id,skip_date) VALUES(?,?)", (booking_id, skip_date))
    conn.commit(); conn.close(); return True, "Skipped!"

# --- VALIDATORS (Verhoeff) ---
_V_D = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],[6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0]]
_V_P = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],[2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]
def _verhoeff_valid(num):
    c = 0
    for i, ch in enumerate(reversed(num)): c = _V_D[c][_V_P[i % 8][int(ch)]]
    return c == 0

def validate_phone(phone):
    if not phone: return False, "", "Empty"
    cleaned = re.sub(r"\D", "", phone)
    if len(cleaned) != 10: return False, cleaned, "Must be 10 digits"
    if cleaned[0] not in "6789": return False, cleaned, "Must start with 6-9"
    return True, cleaned, ""

def validate_aadhaar(aadhaar):
    if not aadhaar: return False, "", "", "Empty"
    cleaned = re.sub(r"\D", "", aadhaar)
    if len(cleaned) != 12: return False, cleaned, "", "Must be 12 digits"
    if cleaned[0] in "01": return False, cleaned, "", "Cannot start with 0 or 1"
    if not _verhoeff_valid(cleaned): return False, cleaned, "", "Invalid Aadhaar checksum"
    return True, cleaned, f"XXXX XXXX {cleaned[-4:]}", ""

# --- APP UI ---
if "phone" not in st.session_state: st.session_state.phone = None
if "admin" not in st.session_state: st.session_state.admin = False

with st.sidebar:
    st.title("GharSathi")
    if st.session_state.admin:
        st.success("Admin logged in")
        if st.button("Logout"): st.session_state.admin = False; st.rerun()
    elif st.session_state.phone:
        u = get_user(st.session_state.phone)
        st.success(f"{u[1]} ({u[3]})")
        if st.button("Logout"): st.session_state.phone = None; st.rerun()

if st.session_state.admin:
    st.header("Admin - Verification Panel")
    conn = get_conn()
    pending = conn.execute("SELECT * FROM users WHERE status='pending'").fetchall()
    conn.close()
    if not pending: st.info("No pending verifications.")
    for u in pending:
        with st.expander(f"{u[1]} - {u[3].upper()} - {u[2]}"):
            st.write(f"Masked Aadhaar: {u[4]} | Address: {u[5]}")
            c1, c2 = st.columns(2)
            if c1.button("Approve", key=f"a{u[0]}"):
                conn = get_conn(); conn.execute("UPDATE users SET status='verified' WHERE id=?", (u[0],)); conn.commit(); conn.close(); st.rerun()
            with c2:
                reason = st.text_input("Reason", key=f"r{u[0]}")
                if st.button("Reject", key=f"rb{u[0]}", disabled=not reason):
                    conn = get_conn(); conn.execute("UPDATE users SET status='rejected', rejection_reason=? WHERE id=?", (reason, u[0])); conn.commit(); conn.close(); st.rerun()
    st.stop()

if st.session_state.phone:
    me = get_user(st.session_state.phone)
    st.header(f"Hi {me[1]}")
    
    # 🟢 YAHAN INDEX FIX KIYA HAI (me[7] status hai, me[8] rejection reason)
    if me[7] != "verified":
        st.warning(f"Status: {me[7]}. Please wait for Admin approval.")
        if me[8]: st.error(f"Reason: {me[8]}")
        st.stop()
        
    if me[3] == "customer":
        st.subheader("Verified Helpers")
        helpers = get_verified_helpers()
        if not helpers: st.info("No helpers available right now.")
        for h in helpers:
            st.markdown(f"### {h[1]} - {h[5]}")
            st.caption(f"Daily Rs {h[3]} | Monthly Rs {h[4]}")
            with st.form(f"book_{h[0]}"):
                btype = st.radio("Type", ["daily", "monthly"], horizontal=True)
                slot = st.selectbox("Slot", ["7-9 AM", "5-7 PM"])
                d = st.date_input("Start Date", min_value=date.today())
                if st.form_submit_button("Book Now"):
                    ed = d + timedelta(days=29) if btype == "monthly" else d
                    if is_helper_busy_range(h[0], d.isoformat(), ed.isoformat(), slot):
                        st.error("Slot Busy!")
                    else:
                        create_booking(me[0], h[0], btype, slot, d.isoformat(), ed.isoformat(), 30 if btype=="monthly" else 1, h[4] if btype=="monthly" else h[3])
                        st.success("Booked successfully!"); st.rerun()
        
        st.divider(); st.subheader("My Bookings")
        for b in get_customer_bookings(me[0]):
            st.write(f"**#{b[0]}** {b[1].upper()} - {b[8]} - {b[2]} - Rs {b[6]} - {b[7]}")
            if b[1] == "monthly" and b[7] == "active":
                st.caption(f"Skips used: {get_skip_count(b[0])}/4")
                with st.form(f"skip_{b[0]}"):
                    sk = st.date_input("Skip Date", min_value=date.fromisoformat(b[3]), max_value=date.fromisoformat(b[4]))
                    if st.form_submit_button("Skip"):
                        if get_skip_count(b[0]) >= 4: st.error("Limit over")
                        else: add_skip(b[0], sk.isoformat()); st.rerun()
                        
    else: # HELPER
        h = get_helper_by_user(me[0])
        st.subheader("My Bookings")
        total = 0
        for b in get_helper_bookings(h[0]):
            st.write(f"**#{b[0]}** {b[1]} - {b[2]} - {b[3]} to {b[4]} - Rs {b[5]} - Customer: {b[7]}")
            if b[6] == "active": total += b[5]
        st.metric("Expected Earnings", f"Rs {total}")
    st.stop()

# AUTHENTICATION
tab1, tab2, tab3 = st.tabs(["Login", "Signup", "Admin"])
with tab1:
    phone = st.text_input("Phone", key="l_p")
    if st.button("Login"):
        p_ok, p_clean, p_err = validate_phone(phone) # FIX: Cleaning phone number
        if not p_ok:
            st.error(p_err)
        elif get_user(p_clean): 
            st.session_state.phone = p_clean
            st.rerun()
        else: 
            st.error("Not found. Please signup.")

with tab2:
    with st.form("signup_form"):
        st.subheader("Create Account")
        r = st.radio("Role", ["customer", "helper"], horizontal=True)
        name = st.text_input("Name")
        ph = st.text_input("Phone")
        aadh = st.text_input("Aadhaar (e.g. 234123412346)")
        addr = st.text_input("Address")
        consent = st.checkbox("I agree to share documents (DPDP Act)")
        skills=""; dr=0; mr=0; area=""
        if r == "helper":
            skills = st.text_input("Skills"); dr = st.number_input("Daily Rate", 100); mr = st.number_input("Monthly Rate", 1000); area = st.text_input("Area")
        
        if st.form_submit_button("Signup"):
            p_ok, p_clean, p_err = validate_phone(ph)
            a_ok, _, a_mask, a_err = validate_aadhaar(aadh)
            if not p_ok: st.error(p_err)
            elif not a_ok: st.error(a_err)
            elif not consent: st.error("Consent required")
            else:
                ok, msg = create_user(name, p_clean, r, a_mask, addr, skills, dr, mr, area)
                if ok: st.success(msg + " Wait for admin approval.")
                else: st.error(msg)

with tab3:
    pw = st.text_input("Admin Password", type="password")
    if st.button("Login Admin"):
        if pw == ADMIN_PASSWORD: st.session_state.admin = True; st.rerun()
        else: st.error("Wrong password")