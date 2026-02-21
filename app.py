import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 1. USER REGISTRY (No Passwords)
# ==========================================
USER_REGISTRY = {
    "suresh": {"role": "Requester", "name": "Suresh"},
    "vaibhav": {"role": "E&I HOD", "name": "Vaibhav"},
    "amit": {"role": "Plant Head", "name": "Amit"}, 
    "deepak": {"role": "DCS Admin", "name": "Deepak"}
}

# ==========================================
# 2. DATABASE INITIALIZATION
# ==========================================
if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=[
        "ID", "Tag", "Status", "Requester", "Reason", "T_Req", 
        "T_HOD_Appr", "T_PH_Appr", "T_Applied",
        "T_Rest_Req", "T_Rest_H_Appr", "T_Rest_PH_Appr", "T_Restored"
    ])

def update_status(req_id, new_status, time_col=None):
    idx = st.session_state.db.index[st.session_state.db['ID'] == req_id].tolist()[0]
    st.session_state.db.at[idx, 'Status'] = new_status
    if time_col:
        st.session_state.db.at[idx, time_col] = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.success(f"Action Successfully Confirmed!")
    st.rerun()

# ==========================================
# 3. LOGIN PAGE
# ==========================================
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🛡️ SecureBypass OS")
    choice = st.selectbox("Select User Profile", ["--- Choose Name ---"] + list(USER_REGISTRY.keys()))
    if st.button("Enter System", use_container_width=True):
        if choice != "--- Choose Name ---":
            st.session_state.authenticated = True
            st.session_state.user = USER_REGISTRY[choice]
            st.rerun()
    st.stop()

# ==========================================
# 4. MAIN APP
# ==========================================
user = st.session_state.user
db = st.session_state.db

st.sidebar.title(f"👤 {user['name']}")
st.sidebar.info(f"Role: {user['role']}")
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

st.title("⚡ Action Center")
t1, t2 = st.tabs(["⚡ Pending Tasks", "📜 Audit Trail"])

with t1:
    # --- ROLE: REQUESTER (SURESH) ---
    if user["role"] == "Requester":
        st.subheader("Create New Request")
        with st.form("new_req", clear_on_submit=True):
            tag = st.text_input("Instrument Tag Number")
            reason = st.text_area("Reason/Justification")
            if st.form_submit_button("Submit Request"):
                if tag and reason:
                    new_id = 1000 + len(db) + 1
                    new_row = {
                        "ID": new_id, "Tag": tag.upper(), "Status": "Wait: HOD Approval", 
                        "Requester": user["name"], "Reason": reason, 
                        "T_Req": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([new_row])], ignore_index=True)
                    st.rerun()

        st.divider()
        st.subheader("Request Restoration")
        active = db[db["Status"] == "BYPASS ACTIVE"]
        for _, row in active.iterrows():
            with st.expander(f"🔴 Tag: {row['Tag']} is currently ACTIVE"):
                st.write(f"Applied on: {row['T_Applied']}")
                with st.popover("Request Restoration"):
                    st.write("Do you want to request restoration?")
                    if st.button("OK", key=f"re_ok_{row['ID']}"):
                        update_status(row['ID'], "Wait: Restor. HOD Approval", "T_Rest_Req")

    # --- ROLE: E&I HOD (VAIBHAV) ---
    elif user["role"] == "E&I HOD":
        # New Bypass Queue
        q1 = db[db["Status"] == "Wait: HOD Approval"]
        if not q1.empty:
            st.subheader("Pending Technical Approvals")
            for _, row in q1.iterrows():
                with st.container(border=True):
                    st.write(f"**Tag:** {row['Tag']} | **ID:** {row['ID']}")
                    st.write(f"**Requester:** {row['Requester']} | **Created:** {row['T_Req']}")
                    st.write(f"**Reason:** {row['Reason']}")
                    with st.popover("Approve"):
                        st.write("Do you want to approve?")
                        if st.button("OK", key=f"v_ok_{row['ID']}"):
                            update_status(row['ID'], "Wait: PH Approval", "T_HOD_Appr")

        # Restoration Queue
        q2 = db[db["Status"] == "Wait: Restor. HOD Approval"]
        if not q2.empty:
            st.subheader("Restoration Clearances")
            for _, row in q2.iterrows():
                with st.container(border=True):
                    st.write(f"**Tag:** {row['Tag']} (Restoration Request)")
                    st.write(f"**Requester:** {row['Requester']} | **Request Time:** {row['T_Rest_Req']}")
                    with st.popover("Approve Restoration"):
                        st.write("Do you want to approve?")
                        if st.button("OK", key=f"vr_ok_{row['ID']}"):
                            update_status(row['ID'], "Wait: Restor. PH Approval", "T_Rest_H_Appr")
        
        if q1.empty and q2.empty: st.info("No tasks pending for Vaibhav.")

    # --- ROLE: PLANT HEAD (AMIT) ---
    elif user["role"] == "Plant Head":
        # New Bypass Queue
        q1 = db[db["Status"] == "Wait: PH Approval"]
        if not q1.empty:
            st.subheader("Management Authorizations")
            for _, row in q1.iterrows():
                with st.container(border=True):
                    st.write(f"**Tag:** {row['Tag']} | **Requester:** {row['Requester']}")
                    st.write(f"**Created:** {row['T_Req']} | **HOD Cleared:** {row['T_HOD_Appr']}")
                    st.write(f"**Reason:** {row['Reason']}")
                    with st.popover("Authorize"):
                        st.write("Do you want to approve?")
                        if st.button("OK", key=f"a_ok_{row['ID']}"):
                            update_status(row['ID'], "Wait: DCS Implementation", "T_PH_Appr")

        # Restoration Queue
        q2 = db[db["Status"] == "Wait: Restor. PH Approval"]
        if not q2.empty:
            st.subheader("Restoration Authorizations")
            for _, row in q2.iterrows():
                with st.container(border=True):
                    st.write(f"**Tag:** {row['Tag']} (Restoration)")
                    st.write(f"**HOD Restore Clearance:** {row['T_Rest_H_Appr']}")
                    with st.popover("Authorize Restoration"):
                        st.write("Do you want to approve?")
                        if st.button("OK", key=f"ar_ok_{row['ID']}"):
                            update_status(row['ID'], "Wait: DCS Restoration", "T_Rest_PH_Appr")

        if q1.empty and q2.empty: st.info("No tasks pending for Amit.")

    # --- ROLE: DCS ADMIN (DEEPAK) ---
    elif user["role"] == "DCS Admin":
        # Apply Task
        q1 = db[db["Status"] == "Wait: DCS Implementation"]
        if not q1.empty:
            st.subheader("DCS Implementation Tasks")
            for _, row in q1.iterrows():
                with st.container(border=True):
                    st.write(f"**Tag:** {row['Tag']} | **Reason:** {row['Reason']}")
                    st.write(f"**PH Authorized at:** {row['T_PH_Appr']}")
                    with st.popover("Complete Implementation"):
                        st.write("Do you want to approve?")
                        if st.button("OK", key=f"da_ok_{row['ID']}"):
                            update_status(row['ID'], "BYPASS ACTIVE", "T_Applied")

        # Restore Task
        q2 = db[db["Status"] == "Wait: DCS Restoration"]
        if not q2.empty:
            st.subheader("DCS Restoration Tasks")
            for _, row in q2.iterrows():
                with st.container(border=True):
                    st.write(f"**Tag:** {row['Tag']} | **PH Authorized at:** {row['T_Rest_PH_Appr']}")
                    with st.popover("Complete Restoration"):
                        st.write("Do you want to approve?")
                        if st.button("OK", key=f"dr_ok_{row['ID']}"):
                            update_status(row['ID'], "RESTORED", "T_Restored")

        if q1.empty and q2.empty: st.info("No active DCS tasks.")

# --- TAB: AUDIT TRAIL ---
with t2:
    st.subheader("System History Log")
    st.dataframe(st.session_state.db, hide_index=True)