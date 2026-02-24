import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 1. Setup
st.set_page_config(page_title="Team Sync", layout="centered")
st_autorefresh(interval=10000, key="datarefresh")

# YOUR DIRECT LINK (Bypasses the broken Secrets box)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1xbvGH7-wpvhSoeYUYArwSQvz4AmTZ-Du_-7zrxBUMCY/edit?usp=sharing"

# 2. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # We pass the URL directly here
        return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
    except Exception as e:
        st.error(f"❌ Connection Failed: {str(e)}")
        return pd.DataFrame()

df = load_data()

st.title("📲 Team Central Portal")

if not df.empty and 'Name' in df.columns:
    # --- ADD NEW ---
    with st.expander("➕ NEW REQUEST"):
        u_name = st.text_input("Name")
        u_req = st.text_area("Request")
        if st.button("Submit"):
            if u_name and u_req:
                new_row = pd.DataFrame([{"ID": len(df)+1, "Name": u_name, "Request": u_req, "Status": "Pending"}])
                updated = pd.concat([df, new_row], ignore_index=True)
                # We update using the direct URL too
                conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated)
                st.success("Sent!")
                st.rerun()

    # --- DISPLAY ---
    st.subheader("📋 Active Requests")
    for i, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{row['Name']}**: {row['Request']}")
            if str(row['Status']) == "Pending":
                if c2.button("Approve", key=f"btn_{i}"):
                    df.at[i, 'Status'] = "Approved ✅"
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)
                    st.rerun()
            else:
                c2.write(row['Status'])
else:
    st.warning("Still waiting for Google Sheets connection. If you see this, make sure row 1 of your sheet has headers: ID, Name, Request, Status")
