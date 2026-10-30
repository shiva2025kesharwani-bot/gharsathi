import streamlit as st
from src.db import get_helper_by_user, get_helper_bookings

def render_helper(me):
    st.header(f"Hi {me[1]}")
    if me[8] != "verified":
        st.warning(f"Status: {me[8]}. Verified hone tak kaam nahi milega.")
        if me[9]: st.error(f"Rejection reason: {me[9]}")
        return
    h = get_helper_by_user(me[0])
    if not h:
        st.error("Helper record nahi mila")
        return
    st.subheader("My bookings")
    bks = get_helper_bookings(h[0])
    total = 0
    for b in bks:
        st.markdown(f"**#{b[0]}** {b[1]} - {b[2]} - {b[3]} to {b[4]} - Rs {b[5]} - Customer: {b[7]} - {b[6]}")
        if b[6] == "active":
            total += b[5]
    st.metric("Expected earnings (active)", f"Rs {total}")
