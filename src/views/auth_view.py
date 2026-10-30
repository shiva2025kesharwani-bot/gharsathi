import streamlit as st
from src.config import ADMIN_PASSWORD
from src.validators import validate_phone, validate_aadhaar
from src.db import get_user, create_user

def render_auth():
    tab1, tab2, tab3 = st.tabs(["Login", "Signup", "Admin"])
    with tab1: _render_login()
    with tab2: _render_signup()
    with tab3: _render_admin_login()

def _render_login():
    phone = st.text_input("Phone (10 digit)", key="l_phone", max_chars=10)
    ok, clean, err = validate_phone(phone)
    if phone and not ok:
        st.warning(err)
    if st.button("Login", disabled=not ok):
        u = get_user(clean)
        if u:
            st.session_state.phone = clean
            st.rerun()
        else:
            st.error("User nahi mila - pehle signup karo")

def _render_signup():
    st.subheader("Naya account")
    r = st.radio("Role", ["customer", "helper"], horizontal=True)
    name = st.text_input("Naam", key="s_name", max_chars=50)
    ph = st.text_input("Phone (10 digit)", key="s_ph", max_chars=10,
                       placeholder="9876543210")
    ph_ok, ph_clean, ph_err = validate_phone(ph)
    if ph:
        if ph_ok: st.success(f"Valid: {ph_clean}")
        else: st.warning(ph_err)

    # BUG FIX: type="password" hata diya taaki browser crash na ho
    aadh = st.text_input("Aadhaar (12 digit)", key="s_aadh", max_chars=12,
                         placeholder="234567890123")

    aad_ok, _, aad_masked, aad_err = validate_aadhaar(aadh)
    if aadh:
        if aad_ok: st.success(f"Valid - store hoga: {aad_masked}")
        else: st.warning(aad_err)
    st.caption("Poora Aadhaar store nahi hoga - sirf masked (last 4 digit)")
    addr = st.text_input("Address", key="s_addr", max_chars=200)
    consent = st.checkbox("Main apna document verification ke liye share karne ki consent deta/deti hoon (DPDP Act 2023)")
    
    skills = ""; dr = 0; mr = 0; area = ""
    if r == "helper":
        skills = st.text_input("Skills (jhadu,bartan,cooking)", key="s_sk")
        dr = st.number_input("Daily rate", 100, 2000, 300, key="s_dr")
        mr = st.number_input("Monthly rate", 1000, 15000, 3000, key="s_mr")
        area = st.text_input("Area", key="s_area")
        
    form_valid = bool(name and ph_ok and aad_ok and consent and addr.strip())
    if st.button("Signup", disabled=not form_valid):
        ok, msg = create_user(name.strip(), ph_clean, r, aad_masked, addr,
                              skills, dr, mr, area)
        (st.success if ok else st.error)(msg)
    if not form_valid:
        st.caption("Sab fields sahi bharo, tab hi button enable hoga")

def _render_admin_login():
    pw = st.text_input("Admin password", type="password")
    if st.button("Login as admin"):
        if pw == ADMIN_PASSWORD:
            st.session_state.admin = True
            st.rerun()
        else:
            st.error("Galat password")
