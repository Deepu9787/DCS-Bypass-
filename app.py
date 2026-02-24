import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- INDUSTRIAL THEME CONFIGURATION ---
st.set_page_config(page_title="DCS BYPASS | Industrial Portal", layout="wide")
st_autorefresh(interval=10000, key="global_sync")

# Custom CSS for Industrial Dark UI
st.markdown("""
    <style>
    .stApp { background-color: #0A0E14; color: #E0E0E0; }
    [data-testid="stMetricValue"] { color: #3A86FF; font-family: 'Roboto Mono', monospace; }
    .stButton>button { background-color: #1E3A8A; color: white; border: none; }
    .status-card { padding: 15px; border-radius: 5px; border-left: 5px solid #3A86FF; background: #161B22; margin-bottom: 10px; }
    .expired-alert { color: #FF4B4B; font-weight: bold; border: 1px solid #FF4B4B; padding: 10px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- HELPERS ---
DEPARTMENTS = ["Mechanical", "Production", "Packing O&M", "E&I"]
AREAS = ["Cement Mill 1", "Cement Mill 2", "Packing Plant", "Utility", "Raw Mill", "Kiln"]
RISK_LEVELS = ["Low", "Medium", "High"]

def get_status_color(status):
    if "Pending" in status: return "#FFD600"
    if "Active" in status: return "#00E676"
    if "Expired" in status: return "#FF4B4B"
    if "Ready" in status: return "#AA00FF"
    return "#3A86FF"

# --- APP LOGIC ---
st.sidebar.title("🏭 DCS CONTROL")
role = st.sidebar.selectbox("Current Role Selection", 
    ["Requester", "Concerned HOD", "Mechanical HOD", "Production HOD", "Packing O&M HOD", "E&I HOD", "DCS Admin", "View Only"])

# --- DASHBOARD SECTION ---
res = supabase.table("requests").select("*").execute()
df = pd.DataFrame(res.data)

st.title("🛡️ Authorized Bypass Management")

# KPI Summary
if not df.empty:
    # Expiry Logic Calculation
    df['is_expired'] = (df['type'] == 'Temporary') & (pd.to_datetime(df['end_time']) < datetime.now()) & (df['status'] == 'Active')
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("ACTIVE BYPASS", len(df[df['status'] == 'Active']))
    kpi2.metric("PENDING APPROVAL", len(df[df['status'].str.contains('Pending')]))
    kpi3.metric("READY FOR DCS", len(df[df['status'] == 'Ready for Execution']))
    kpi4.metric("HIGH RISK ACTIVE", len(df[(df['risk'] == 'High') & (df['status'] == 'Active')]))

# --- VIEW: REQUEST FORM ---
if role == "Requester":
    with st.form("request_form"):
        st.subheader("📝 New Bypass Authorization")
        c1, c2 = st.columns(2)
        tag = c1.text_input("Equipment Tag (e.g., 421-BE1)")
        area = c2.selectbox("Area", AREAS)
        dept = c1.selectbox("Requesting Department", DEPARTMENTS)
        b_type = c2.selectbox("Bypass Type", ["Temporary", "Permanent"])
        
        risk = c1.selectbox("Risk Level", RISK_LEVELS)
        reason = st.text_area("Reason for Bypass (Mandatory)")
        
        start = end = None
        if b_type == "Temporary":
            cc1, cc2 = st.columns(2)
            start = cc1.datetime_input("Expected Start")
            end = cc2.datetime_input("Expected End")
            
        if st.form_submit_button("Submit for Approval"):
            if tag and reason:
                supabase.table("requests").insert({
                    "tag": tag, "area": area, "dept": dept, "type": b_type,
                    "risk": risk, "reason": reason, "status": "Pending Concerned HOD",
                    "start_time": str(start), "end_time": str(end)
                }).execute()
                st.success("Request initiated. Routed to Concerned HOD.")
                st.rerun()

# --- VIEW: APPROVAL CENTER ---
elif "HOD" in role:
    st.subheader(f"📥 Pending Approvals for {role}")
    # Logic to show only requests relevant to current step
    status_map = {
        "Concerned HOD": "Pending Concerned HOD",
        "Mechanical HOD": "Pending Mechanical",
        "Production HOD": "Pending Production",
        "Packing O&M HOD": "Pending Packing O&M",
        "E&I HOD": "Pending E&I"
    }
    
    pending = df[df['status'] == status_map[role]]
    if pending.empty:
        st.info("No items in your approval queue.")
    else:
        for idx, row in pending.iterrows():
            with st.container():
                st.markdown(f"""<div class='status-card'>
                    <h4>TAG: {row['tag']} | RISK: {row['risk']}</h4>
                    <p><b>Area:</b> {row['area']} | <b>Reason:</b> {row['reason']}</p>
                </div>""", unsafe_allow_html=True)
                
                comment = st.text_input("Approval Comment", key=f"com_{row['id']}")
                c1, c2 = st.columns(2)
                
                if c1.button("✅ APPROVE", key=f"app_{row['id']}"):
                    # Move to next step logic
                    next_status = ""
                    if role == "Concerned HOD": next_status = "Pending Mechanical"
                    elif role == "Mechanical HOD": next_status = "Pending Production"
                    elif role == "Production HOD": 
                        next_status = "Pending Packing O&M" if row['area'] == "Packing Plant" else "Pending E&I"
                    elif role == "Packing O&M HOD": next_status = "Pending E&I"
                    elif role == "E&I HOD": next_status = "Ready for Execution"
                    
                    supabase.table("requests").update({"status": next_status}).eq("id", row['id']).execute()
                    st.rerun()
                
                if c2.button("❌ REJECT", key=f"rej_{row['id']}"):
                    supabase.table("requests").update({"status": "Rejected"}).eq("id", row['id']).execute()
                    st.rerun()

# --- VIEW: DCS ADMIN ---
elif role == "DCS Admin":
    st.subheader("⚡ DCS Execution Desk")
    ready = df[df['status'] == "Ready for Execution"]
    for idx, row in ready.iterrows():
        st.warning(f"READY: {row['tag']} ({row['area']})")
        if st.button(f"Confirm Execution: {row['tag']}", key=f"exec_{row['id']}"):
            supabase.table("requests").update({"status": "Active"}).eq("id", row['id']).execute()
            st.rerun()

# --- VIEW: HISTORY ---
else:
    st.subheader("📜 Global Bypass History")
    if not df.empty:
        # Displaying with high contrast colors
        st.dataframe(df.style.applymap(lambda x: f'background-color: {get_status_color(str(x))}' if x in df['status'].values else '', subset=['status']))

# Expired Alert Banner
if not df.empty and df['is_expired'].any():
    st.markdown("<div class='expired-alert'>⚠️ ATTENTION: ONE OR MORE TEMPORARY BYPASSES HAVE EXPIRED</div>", unsafe_allow_html=True)
