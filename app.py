import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & INDUSTRIAL THEME ---
st.set_page_config(page_title="DCS BYPASS | Operational Portal", layout="wide")
st_autorefresh(interval=10000, key="global_sync")

st.markdown("""
    <style>
    .stApp { background-color: #0A0E14; color: #E0E0E0; }
    .status-card { padding: 15px; border-radius: 8px; background: #161B22; border: 1px solid #30363D; margin-bottom: 10px; border-left: 5px solid #3A86FF; }
    .stButton>button { width: 100%; font-weight: bold; border-radius: 4px; height: 3em; }
    .kpi { text-align: center; background: #1B222C; padding: 10px; border-radius: 5px; border: 1px solid #2D3748; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DB CONNECTION ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- 3. ACCESS CONTROL WITH LOGIN BUTTON ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.sidebar.title("🔐 PLANT ACCESS")
user_role = st.sidebar.selectbox("Your Role", ["Requester", "HOD", "DCS Admin"])
user_dept = st.sidebar.selectbox("Your Department", ["Mechanical", "Production", "E&I", "Packing O&M"])
pin = st.sidebar.text_input("Security Pin", type="password")

if st.sidebar.button("Login"):
    if pin == "123":
        st.session_state.logged_in = True
        st.sidebar.success("Access Granted")
    else:
        st.sidebar.error("Invalid Pin")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- 4. DATA FETCH & KPI ---
res = supabase.table("requests").select("*").execute()
df = pd.DataFrame(res.data)

st.title("🛡️ DCS Bypass Authorization System")

# Fix: Use "Pending" to match your database screenshot
if not df.empty:
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi'>PENDING<br><h2 style='color:#FFD600'>{len(df[df['status'].str.contains('Pending', na=False)])}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi'>ACTIVE<br><h2 style='color:#00E676'>{len(df[df['status'] == 'Active'])}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi'>REMOVAL<br><h2 style='color:#FFA500'>{len(df[df['status'].str.contains('Removal', na=False)])}</h2></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi'>READY<br><h2 style='color:#AA00FF'>{len(df[df['status'].str.contains('Ready', na=False)])}</h2></div>", unsafe_allow_html=True)

st.divider()

# --- 5. WORKFLOW ENGINE (Corrected Status Strings) ---
def get_next_step(current_status, req_dept, is_removal=False):
    pref = "Removal Pending:" if is_removal else "Pending"
    ready = "Ready for Removal Execution" if is_removal else "Ready for Execution"
    
    if "Concerned HOD" in current_status:
        if req_dept == "Mechanical": return f"{pref} Production HOD"
        if req_dept == "Production": return f"{pref} Mechanical HOD"
        return f"{pref} Production HOD"

    if "Production HOD" in current_status:
        if req_dept == "Mechanical": return f"{pref} E&I HOD"
        return f"{pref} Mechanical HOD"

    if "Mechanical HOD" in current_status:
        return f"{pref} E&I HOD"

    if "E&I HOD" in current_status:
        return ready
    
    return "Rejected"

# --- 6. ROLE INTERFACES ---

if st.session_state.logged_in:
    if user_role == "Requester":
        col1, col2 = st.columns(2)
        with col1:
            with st.form("new_request"):
                st.subheader("➕ New Bypass Request")
                tag = st.text_input("Equipment Tag")
                area = st.selectbox("Plant Area", ["Cement Mill 1", "Cement Mill 2", "Packing", "Kiln", "Utility"])
                b_type = st.selectbox("Type", ["Temporary", "Permanent"])
                reason = st.text_area("Reason")
                if st.form_submit_button("SUBMIT"):
                    if tag and reason:
                        supabase.table("requests").insert({"tag": tag, "area": area, "dept": user_dept, "type": b_type, "reason": reason, "status": "Pending Concerned HOD"}).execute()
                        st.rerun()

        with col2:
            st.subheader("🔓 Active - Request Removal")
            my_actives = df[(df['status'] == "Active") & (df['dept'] == user_dept)]
            for _, row in my_actives.iterrows():
                if st.button(f"Request Removal: {row['tag']}", key=f"rem_{row['id']}"):
                    supabase.table("requests").update({"status": "Removal Pending: Concerned HOD"}).eq("id", row['id']).execute()
                    st.rerun()

    elif user_role == "HOD":
        # Match HOD's dept to targets
        if user_dept == "Mechanical": targets = ["Pending Mechanical HOD", "Removal Pending: Mechanical HOD"]
        elif user_dept == "Production": targets = ["Pending Production HOD", "Removal Pending: Production HOD"]
        elif user_dept == "E&I": targets = ["Pending E&I HOD", "Removal Pending: E&I HOD"]
        else: targets = []
        
        hod_tasks = df[ (df['status'].isin(targets)) | 
                        ((df['status'].str.contains("Concerned HOD")) & (df['dept'] == user_dept)) ]

        st.subheader(f"📥 Approval Queue: {user_dept} HOD")
        for _, row in hod_tasks.iterrows():
            is_rem = "Removal" in row['status']
            st.markdown(f"""<div class='status-card' style='border-left-color: {"#FFA500" if is_rem else "#3A86FF"}'>
                <b>{"REMOVAL" if is_rem else "BYPASS"} REQUEST</b> | TAG: {row['tag']}<br>
                <b>REASON:</b> {row['reason']}
            </div>""", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button(f"✅ Approve {row['tag']}", key=f"a_{row['id']}"):
                new_stat = get_next_step(row['status'], row['dept'], is_removal=is_rem)
                supabase.table("requests").update({"status": new_stat}).eq("id", row['id']).execute()
                st.rerun()
            if c2.button(f"❌ Reject", key=f"r_{row['id']}"):
                supabase.table("requests").update({"status": "Rejected"}).eq("id", row['id']).execute()
                st.rerun()

    elif user_role == "DCS Admin":
        st.subheader("⚙️ DCS Operational Desk")
        ready_b = df[df['status'] == "Ready for Execution"]
        ready_r = df[df['status'] == "Ready for Removal Execution"]
        
        if ready_b.empty and ready_r.empty:
            st.info("No items ready for execution yet.")
        
        for _, row in ready_b.iterrows():
            st.info(f"⚡ BYPASS READY: {row['tag']}")
            if st.button("CONFIRM BYPASS", key=f"ex_b_{row['id']}"):
                supabase.table("requests").update({"status": "Active"}).eq("id", row['id']).execute()
                st.rerun()

        for _, row in ready_r.iterrows():
            st.success(f"🔓 REMOVAL READY: {row['tag']}")
            if st.button("CONFIRM RESUME", key=f"ex_r_{row['id']}"):
                supabase.table("requests").update({"status": "Resumed (Normal)"}).eq("id", row['id']).execute()
                st.rerun()

else:
    st.warning("Please Login to access operational features.")

# --- 7. AUDIT LOG ---
st.subheader("📜 System Audit History")
if not df.empty:
    st.dataframe(df, use_container_width=True)
