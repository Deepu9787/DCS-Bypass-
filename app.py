import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="DCS BYPASS - Secure Workflow", layout="wide")
st_autorefresh(interval=10000, key="sync")

st.markdown("""
    <style>
    .stApp { background-color: #0A0E14; color: #E0E0E0; }
    .status-card { padding: 15px; border-radius: 8px; background: #161B22; border: 1px solid #30363D; margin-bottom: 10px; }
    .stButton>button { width: 100%; font-weight: bold; }
    .active-tag { color: #00E676; border: 1px solid #00E676; padding: 2px 8px; border-radius: 4px; }
    .removal-tag { color: #FFA500; border: 1px solid #FFA500; padding: 2px 8px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DB ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- 3. AUTH SIDEBAR ---
st.sidebar.title("🔐 WORKFLOW AUTH")
user_role = st.sidebar.selectbox("Select Role", ["Viewer", "Requester", "Concerned HOD", "Mechanical HOD", "Production HOD", "E&I HOD", "DCS Admin"])
user_dept = st.sidebar.selectbox("Your Dept", ["Mechanical", "Production", "Packing O&M", "E&I"])
password = st.sidebar.text_input("Security Pin", type="password")
authorized = (password == "123")

# --- 4. DATA ---
res = supabase.table("requests").select("*").execute()
df = pd.DataFrame(res.data)

st.title("🛡️ DCS Bypass & Normalization Control")

# --- 5. SMART WORKFLOW ENGINE ---
def get_next_status(current_status, req_dept, is_removal=False):
    prefix = "Removal Approval:" if is_removal else "Pending"
    final_step = "Ready for Removal Execution" if is_removal else "Ready for Execution"
    
    # Step 1: Concerned
    if current_status in ["Pending Concerned HOD", "Removal Approval: Concerned"]:
        if req_dept == "Mechanical": return f"{prefix} Production HOD"
        return f"{prefix} Mechanical HOD"

    # Step 2: Intermediate
    if current_status in ["Pending Production HOD", "Removal Approval: Production HOD"]:
        if req_dept == "Mechanical": return f"{prefix} E&I HOD"
        return f"{prefix} Mechanical HOD" # Case for E&I or Prod or Pack

    if current_status in ["Pending Mechanical HOD", "Removal Approval: Mechanical HOD"]:
        return f"{prefix} E&I HOD"

    # Step 3: Final
    if current_status in ["Pending E&I HOD", "Removal Approval: E&I HOD"]:
        return final_step

    return "Rejected"

# --- 6. INTERFACES ---

# A. REQUESTER: Submit New OR Request Removal
if authorized and user_role == "Requester":
    col_a, col_b = st.columns(2)
    
    with col_a:
        with st.form("new_request"):
            st.subheader("➕ New Bypass Request")
            tag = st.text_input("Equipment Tag")
            area = st.selectbox("Area", ["Cement Mill 1", "Cement Mill 2", "Packing", "Kiln"])
            b_type = st.selectbox("Type", ["Temporary", "Permanent"])
            reason = st.text_area("Bypass Reason")
            if st.form_submit_button("SUBMIT"):
                supabase.table("requests").insert({"tag": tag, "area": area, "dept": user_dept, "type": b_type, "reason": reason, "status": "Pending Concerned HOD"}).execute()
                st.rerun()

    with col_b:
        st.subheader("🔄 Active - Request Removal")
        active_items = df[(df['status'] == "Active") & (df['dept'] == user_dept)]
        if active_items.empty:
            st.info("No active bypasses for your dept.")
        else:
            for _, row in active_items.iterrows():
                if st.button(f"Request Removal: {row['tag']}", key=f"rem_{row['id']}"):
                    supabase.table("requests").update({"status": "Removal Approval: Concerned"}).eq("id", row['id']).execute()
                    st.rerun()

# B. HOD APPROVALS (Handles both Bypass and Removal)
elif authorized and "HOD" in user_role:
    # Logic to identify which status this HOD is looking for
    hod_map = {
        "Concerned HOD": ["Pending Concerned HOD", "Removal Approval: Concerned"],
        "Mechanical HOD": ["Pending Mechanical HOD", "Removal Approval: Mechanical HOD"],
        "Production HOD": ["Pending Production HOD", "Removal Approval: Production HOD"],
        "E&I HOD": ["Pending E&I HOD", "Removal Approval: E&I HOD"]
    }
    
    targets = hod_map[user_role]
    # Filter tasks
    if user_role == "Concerned HOD":
        tasks = df[df['status'].isin(targets) & (df['dept'] == user_dept)]
    else:
        tasks = df[df['status'].isin(targets)]

    st.subheader(f"📥 Approval Queue: {user_role}")
    for _, row in tasks.iterrows():
        is_rem = "Removal" in row['status']
        label = "REMOVAL REQUEST" if is_rem else "BYPASS REQUEST"
        
        with st.container():
            st.markdown(f"""<div class='status-card'>
                <span style='color: {"#FFA500" if is_rem else "#3A86FF"}'><b>{label}</b></span><br>
                <b>TAG:</b> {row['tag']} | <b>DEPT:</b> {row['dept']} | <b>TYPE:</b> {row['type']}<br>
                <b>REASON:</b> {row['reason']}
            </div>""", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button(f"✅ Approve {row['tag']}", key=f"app_{row['id']}"):
                new_stat = get_next_status(row['status'], row['dept'], is_removal=is_rem)
                supabase.table("requests").update({"status": new_stat}).eq("id", row['id']).execute()
                st.rerun()
            if c2.button(f"❌ Reject", key=f"rej_{row['id']}"):
                supabase.table("requests").update({"status": "Rejected"}).eq("id", row['id']).execute()
                st.rerun()

# C. DCS ADMIN: Execute Bypass OR Execution Removal
elif authorized and user_role == "DCS Admin":
    st.subheader("⚙️ DCS Operational Desk")
    
    # Bypass Execution
    b_ready = df[df['status'] == "Ready for Execution"]
    for _, row in b_ready.iterrows():
        st.info(f"⚡ READY TO BYPASS: {row['tag']}")
        if st.button("CONFIRM BYPASS", key=f"ex_b_{row['id']}"):
            supabase.table("requests").update({"status": "Active"}).eq("id", row['id']).execute()
            st.rerun()

    # Removal Execution
    r_ready = df[df['status'] == "Ready for Removal Execution"]
    for _, row in r_ready.iterrows():
        st.success(f"🔓 READY TO REMOVE/RESUME: {row['tag']}")
        if st.button("CONFIRM NORMALIZATION", key=f"ex_r_{row['id']}"):
            supabase.table("requests").update({"status": "Resumed (Normal)"}).eq("id", row['id']).execute()
            st.rerun()

# --- 7. AUDIT LOG ---
st.subheader("📜 Global Audit Log")
if not df.empty:
    def style_status(val):
        color = "#FFFFFF"
        if "Active" in str(val): color = "#00E676"
        if "Removal" in str(val): color = "#FFA500"
        if "Resumed" in str(val): color = "#718096"
        if "Pending" in str(val): color = "#FFD600"
        return f'color: {color}; font-weight: bold'
    
    st.dataframe(df.style.applymap(style_status, subset=['status']), use_container_width=True)
