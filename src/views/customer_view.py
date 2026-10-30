import streamlit as st
from datetime import date, timedelta
from src.config import MONTHLY_DAYS, SKIP_LIMIT_MONTHLY
from src.db import (get_verified_helpers, is_helper_busy_range, create_booking,
                    get_customer_bookings, get_skip_count, add_skip)

def render_customer(me):
    st.header(f"Hi {me[1]}")
    if me[8] != "verified":
        st.warning(f"Status: {me[8]}. Verified hone tak booking nahi kar sakte.")
        if me[9]: st.error(f"Rejection reason: {me[9]}")
        return
    _render_helper_list(me)
    _render_my_bookings(me)

def _render_helper_list(me):
    st.subheader("Available verified helpers")
    helpers = get_verified_helpers()
    if not helpers:
        st.info("Abhi koi verified helper nahi. Admin se approve karwao.")
        return
    for h in helpers:
        hid, hname, skills, dr, mr, area, rating = h
        st.markdown(f"### {hname} - {area}")
        st.caption(f"Skills: {skills} | Daily Rs {dr} | Monthly Rs {mr} | {rating} star")
        btype = st.radio("Booking type", ["daily", "monthly"],
                         key=f"bt{hid}", horizontal=True)
        slot = st.selectbox("Slot", ["7-9 AM", "9-11 AM", "5-7 PM"], key=f"sl{hid}")
        if btype == "daily":
            d = st.date_input("Date", min_value=date.today(), key=f"d{hid}")
            if st.button(f"Book daily with {hname}", key=f"bd{hid}"):
                if is_helper_busy_range(hid, d.isoformat(), d.isoformat(), slot):
                    st.error("Ye slot busy hai")
                else:
                    create_booking(me[0], hid, "daily", slot,
                                   d.isoformat(), d.isoformat(), 1, dr)
                    st.success(f"Booking done! WhatsApp -> helper: daily {d} {slot} Rs {dr}")
                    st.rerun()
        else:
            sd = st.date_input("Start date", min_value=date.today(), key=f"sd{hid}")
            ed = sd + timedelta(days=MONTHLY_DAYS - 1)
            st.caption(f"End date: {ed}")
            if st.button(f"Book monthly with {hname}", key=f"bm{hid}"):
                if is_helper_busy_range(hid, sd.isoformat(), ed.isoformat(), slot):
                    st.error("Is range me slot busy hai")
                else:
                    create_booking(me[0], hid, "monthly", slot,
                                   sd.isoformat(), ed.isoformat(), MONTHLY_DAYS, mr)
                    st.success(f"Monthly booking! WhatsApp -> helper: {sd} to {ed} {slot} Rs {mr}")
                    st.rerun()

def _render_my_bookings(me):
    st.divider()
    st.subheader("My bookings")
    bks = get_customer_bookings(me[0])
    if not bks:
        st.info("Abhi koi booking nahi")
        return
    for b in bks:
        bid, btype, slot, sd, ed, td, amt, st_, hname = b
        skip_count = get_skip_count(bid)
        st.markdown(f"**#{bid}** {btype.upper()} - {hname} - {slot} - {sd} to {ed} - Rs {amt} - {st_}")
        if btype == "monthly" and st_ == "active":
            st.caption(f"Skips used: {skip_count}/{SKIP_LIMIT_MONTHLY}")
            sk = st.date_input("Skip date", min_value=date.fromisoformat(sd),
                               max_value=date.fromisoformat(ed), key=f"sk{bid}")
            if st.button("Skip this day", key=f"skb{bid}"):
                if skip_count >= SKIP_LIMIT_MONTHLY:
                    st.error(f"{SKIP_LIMIT_MONTHLY} skip limit khatam")
                else:
                    ok, msg = add_skip(bid, sk.isoformat())
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.info(f"WhatsApp -> helper: {sk} par kaam nahi")
                        st.rerun()
