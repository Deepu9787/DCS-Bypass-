import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
st.set_page_config(page_title="DCS BYPASS", layout="wide")
st_autorefresh(interval=10000, key="global_sync")

# --- DB CONNECTION ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.title("🛡️ DCS Bypass Management")

# --- FORM ---
with st.form("request_form"):
    st.subheader("📝 New Bypass Authorization")
    c1, c2 = st.columns(2)
    tag = c1.text_input("Equipment Tag")
    area = c2.selectbox("Area", ["Cement Mill 1", "Cement Mill 2", "Packing Plant", "Kiln"])
    dept = c1.selectbox("Department", ["Mechanical", "Production", "Packing O&M", "E&I"])
    b_type = c2.selectbox("Bypass Type", ["Temporary", "Permanent"])
    risk = c1.selectbox("Risk Level", ["Low", "Medium", "High"])
    reason = st.text_area("Reason (Mandatory)")
    
    # Handle dates carefully
    start = datetime.now().isoformat()
    end = None
    
    if st.form_submit_button("Submit for Approval"):
        if tag and reason:
            try:
                # INSERT DATA
                data_to_insert = {
                    "tag": tag, 
                    "area": area, 
                    "dept": dept, 
                    "type": b_type,
                    "risk": risk, 
                    "reason": reason, 
                    "status": "Pending Concerned HOD",
                    "start_time": start,
                    "end_time": end
                }
                
                supabase.table("requests").insert(data_to_insert).execute()
                st.success("✅ Success! Request submitted.")
                st.rerun()
                
            except Exception as e:
                # THIS WILL SHOW THE REAL ERROR
                st.error("❌ DATABASE ERROR:")
                st.write(str(e))
        else:
            st.warning("Please fill Tag and Reason.")
