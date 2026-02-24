import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration
st.set_page_config(page_title="Team Portal", layout="centered")

# Auto-refresh every 5 seconds to sync data between users
st_autorefresh(interval=5000, key="sync")

# 2. Connect to Supabase
# Ensure these names match EXACTLY what you put in Streamlit Secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📲 Team Central Portal")

# --- SECTION 1: SUBMIT NEW REQUEST (Mobile) ---
with st.expander("➕ NEW REQUEST"):
    u_name = st.text_input("Your Name")
    u_req = st.text_area("Details")
    if st.button("Submit Request"):
        if u_name and u_req:
            try:
                # Insert data into your 'requests' table
                supabase.table("requests").insert({
                    "name": u_name, 
                    "request": u_req, 
                    "status": "Pending"
                }).execute()
                st.success("Sent to team!")
                st.rerun()
            except Exception as e:
                st.error(f"Error submitting: {e}")

# --- SECTION 2: VIEW & APPROVE (Dashboard) ---
st.subheader("📋 Live Requests")

try:
    # Fetch all rows from the 'requests' table
    response = supabase.table("requests").select("*").order("id", desc=True).execute()
    rows = response.data

    if not rows:
        st.info("No requests yet.")
    else:
        for row in rows:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['name']}**: {row['request']}")
                
                if row['status'] == "Pending":
                    # Approval button
                    if c2.button("Approve", key=f"btn_{row['id']}"):
                        supabase.table("requests").update
