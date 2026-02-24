import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# 1. Setup
st.set_page_config(page_title="Team Sync", layout="centered")
st_autorefresh(interval=5000, key="sync")

# 2. Connection
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("📲 Team Central Portal")

# --- SECTION 1: SUBMIT ---
with st.expander("➕ NEW REQUEST"):
    u_name = st.text_input("Name")
    u_req = st.text_area("Request")
    if st.button("Submit Request"):
        if u_name and u_req:
            try:
                # INSERT DATA
                supabase.table("requests").insert({
                    "name": u_name, 
                    "request": u_req, 
                    "status": "Pending"
                }).execute()
                st.success("Sent successfully!")
                st.rerun()
            except Exception as e:
                st.error("Error: Ensure RLS is disabled in Supabase Policies.")
                st.write(str(e))

# --- SECTION 2: VIEW ---
st.subheader("📋 Active Dashboard")
try:
    # FETCH DATA
    res = supabase.table("requests").select("*").order("id", desc=True).execute()
    rows = res.data
    
    if not rows:
        st.info("No requests yet. Try adding one above!")
    else:
        for row in rows:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{row['name']}**: {row['request']}")
                
                if row.get('status') == "Pending":
                    if col2.button("Approve", key=f"btn_{row['id']}"):
                        supabase.table("requests").update({"status": "Approved ✅"}).eq("id", row['id']).execute()
                        st.rerun()
                else:
                    col2.write(f"**{row.get('status', 'Approved ✅')}**")
except Exception as e:
    st.warning("Database connection starting...")
