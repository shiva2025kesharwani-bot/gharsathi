import streamlit as st
from src.db import get_pending_users, approve_user, reject_user

def render_admin():
    st.header("Admin - Verification Panel")
    pending = get_pending_users()
    if not pending:
        st.info("Koi pending verification nahi")
        return
    for u in pending:
        with st.expander(f"{u[1]} - {u[3].upper()} - {u[2]}"):
            st.write(f"Masked Aadhaar: {u[4]}")
            st.write(f"Address: {u[5]}")
            st.caption(f"Consent at: {u[7]}")
            c1, c2 = st.columns(2)
            if c1.button("Approve", key=f"a{u[0]}"):
                approve_user(u[0]); st.rerun()
            with c2:
                reason = st.text_input("Reason (reject)", key=f"rr{u[0]}")
                if st.button("Reject", key=f"r{u[0]}", disabled=not reason):
                    reject_user(u[0], reason); st.rerun()
