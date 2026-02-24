import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# 1. Page Config
st.set_page_config(page_title="Team Portal", layout="centered")

# Auto-refresh every 5 seconds to sync users
st_autorefresh(interval=5000, key="sync")

# 2. Connect to Supabase
# These come from your Streamlit Secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📲 Team Central Portal")

# --- SECTION 1: SUBMIT NEW REQUEST ---
with st.expander("➕ NEW REQUEST"):
    u_name = st.text_input("Your Name")
    u_req = st.text_area("Details")
    if st.button("Submit Request"):
        if u_name and u_req:
            # Insert into Supabase table 'requests'
            supabase.table("requests").insert({
                "name": u_name, 
                "request": u_req, 
                "status": "Pending"
            }).execute()
            st.success("Sent to team!")
            st.rerun()

# --- SECTION 2: VIEW & APPROVE ---
st.subheader("📋 Live Requests")

# Fetch all requests from the 'requests' table
response = supabase.table("requests").select("*").order("id", desc=True).execute()
rows = response.data

if not rows:
    st.info("No requests yet.")
else:
    for row in rows:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{row['name']}**: {row['request']}")
            
            # Check if status is Pending to show Approve button
            if row['status'] == "Pending":
                if col2.button("Approve", key=f"btn_{row['id']}"):
                    supabase.table("requests").update({"status": "Approved ✅"}).eq("id", row['id']).execute()
                    st.rerun()
            else:
                col2.write(f"**{row['status']}**")
