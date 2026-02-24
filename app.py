import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- 1. INDUSTRIAL THEME & CONFIG ---
st.set_page_config(page_title="DCS BYPASS SYSTEM", layout="wide")
st_autorefresh(interval=10000, key="global_sync")

# Modern Industrial CSS
st.markdown("""
    <style>
    .stApp { background-color: #0A0E14; color: #E0E0E0; }
    .status-card { padding: 20px; border-radius: 8px; background: #161B22; border-left: 5px solid #3A86FF; margin-bottom: 15px; }
    .kpi-box { text-align: center; padding: 10px; background: #1B222C; border-radius: 5px; border: 1px solid #2D3748; }
    h1, h2, h3 { color: #3A86FF; font-family: 'Segoe UI', sans-serif; }
    .stButton>button { width: 100%; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DB CONNECTION ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- 3. LOGIN SYSTEM ---
st.sidebar.title("🔐 ACCESS CONTROL")
user_role = st.sidebar.selectbox("Select Your Role", [
    "Viewer (History Only)", 
    "Requester", 
    "Concerned HOD", 
    "Mechanical HOD", 
    "Production HOD", 
    "Packing O&M HOD", 
    "E&I HOD", 
    "DCS Admin"
])
password = st.sidebar.text_input("Enter Password", type="password")

if password != "123":
    st.warning("Please enter the correct password in the sidebar to access management features.")
    authorized = False
else:
    authorized = True
    st.sidebar.success(f"Logged in as: {user_role}")

# --- 4. DATA LOADING & KPI ---
res = supabase.table("requests").select("*").execute()
df = pd.DataFrame(res.data)

def get_status_color(status):
    colors = {
        "Active": "#00E676", "Expired": "#FF4B4B", "Rejected": "#718096",
        "Ready for Execution": "#AA00FF", "Pending": "#FFD600"
    }
    for key, color in colors.items():
        if key in status: return color
    return "#3A86FF"

# Top KPI Bar (Visible to everyone)
st.title("🛡️ DCS Bypass Management Portal")
if not df.empty:
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f"<div class='kpi-box'><h4>ACTIVE</h4><h2>{len(df[df['status'] == 'Active'])}</h2></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='kpi-box'><h4>PENDING</h4><h2>{len(df[df['status'].str.contains('Pending')])}</h2></div>", unsafe_allow_html=True)
    with k3: st.markdown(f"<div class='kpi-box'><h4>READY</h4><h2>{len(df[df['status'] == 'Ready for Execution'])}</h2></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='kpi-box'><h4>EXPIRED</h4><h2>{len(df[df['status'] == 'Expired'])}</h2></div>", unsafe_allow_html=True)

st.divider()

# --- 5. ROLE-BASED INTERFACE ---

# --- A. REQUESTER ---
if authorized and user_role == "Requester":
    with st.form("new_request"):
        st.subheader("📝 New Bypass Authorization")
        c1, c2 = st.columns(2)
        tag = c1.text_input("Equipment Tag (e.g. 421BE01)")
        area = c2.selectbox("Area", ["Cement Mill 1", "Cement Mill 2", "Packing Plant", "Kiln", "Utility"])
        dept = c1.selectbox("Department", ["Mechanical", "Production", "Packing O&M", "E&I"])
        risk = c2.selectbox("Risk Level", ["Low", "Medium", "High"])
        b_type = c1.selectbox("Bypass Type", ["Temporary", "Permanent"])
        reason = st.text_area("Reason for Bypass (Mandatory)")
        
        if st.form_submit_button("SUBMIT REQUEST"):
            if tag and reason:
                supabase.table("requests").insert({
                    "tag": tag, "area": area, "dept": dept, "risk": risk, "type": b_type,
                    "reason": reason, "status": "Pending Concerned HOD", "requested_by": "User"
                }).execute()
                st.success("Request Submitted Successfully!")
                st.rerun()

# --- B. HOD APPROVALS ---
elif authorized and "HOD" in user_role:
    status_filter = {
        "Concerned HOD": "Pending Concerned HOD",
        "Mechanical HOD": "Pending Mechanical",
        "Production HOD": "Pending Production",
        "Packing O&M HOD": "Pending Packing O&M",
        "E&I HOD": "Pending E&I"
    }
    
    pending_tasks = df[df['status'] == status_filter[user_role]]
    st.subheader(f"📥 Pending Approvals: {user_role}")
    
    if pending_tasks.empty:
        st.info("No requests currently require your approval.")
    else:
        for _, row in pending_tasks.iterrows():
            with st.container():
                st.markdown(f"""<div class='status-card'>
                    <b>TAG:</b> {row['tag']} | <b>AREA:</b> {row['area']} | <b>RISK:</b> {row['risk']}<br>
                    <b>REASON:</b> {row['reason']}
                </div>""", unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button(f"✅ Approve {row['tag']}", key=f"app_{row['id']}"):
                    # Workflow Logic
                    next_status = "Rejected"
                    if user_role == "Concerned HOD": next_status = "Pending Mechanical"
                    elif user_role == "Mechanical HOD": next_status = "Pending Production"
                    elif user_role == "Production HOD":
                        next_status = "Pending Packing O&M" if row['area'] == "Packing Plant" else "Pending E&I"
                    elif user_role == "Packing O&M HOD": next_status = "Pending E&I"
                    elif user_role == "E&I HOD": next_status = "Ready for Execution"
                    
                    supabase.table("requests").update({"status": next_status}).eq("id", row['id']).execute()
                    st.rerun()
                
                if c2.button(f"❌ Reject {row['tag']}", key=f"rej_{row['id']}"):
                    supabase.table("requests").update({"status": "Rejected"}).eq("id", row['id']).execute()
                    st.rerun()

# --- C. DCS ADMIN EXECUTION ---
elif authorized and user_role == "DCS Admin":
    st.subheader("⚡ DCS Execution Desk")
    ready = df[df['status'] == "Ready for Execution"]
    if ready.empty:
        st.info("No requests ready for DCS execution.")
    else:
        for _, row in ready.iterrows():
            st.warning(f"ACTION REQUIRED: Execute Bypass for {row['tag']}")
            if st.button(f"CONFIRM EXECUTION: {row['tag']}", key=f"exec_{row['id']}"):
                supabase.table("requests").update({"status": "Active", "executed_by": "DCS_Admin"}).eq("id", row['id']).execute()
                st.rerun()

# --- 6. HISTORY PAGE (Visible to All) ---
st.subheader("📜 Global Bypass Audit Log")
if not df.empty:
    # Color code the rows based on status
    st.dataframe(df.style.applymap(lambda x: f"color: {get_status_color(str(x))}" if x in df['status'].values else "", subset=['status']), use_container_width=True)

    # Expandable Details
    with st.expander("🔍 View Detailed Request Data"):
        selected_tag = st.selectbox("Select Tag to view history", df['tag'].unique())
        detail = df[df['tag'] == selected_tag].iloc[0]
        st.json(detail.to_dict())
