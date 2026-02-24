import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

# 1. Setup
st.set_page_config(page_title="Team Sync", layout="centered")
st_autorefresh(interval=10000, key="datarefresh")

# CLEAN URL (No extra characters at the end)
SHEET_ID = "1xbvGH7-wpvhSoeYUYArwSQvz4AmTZ-Du_-7zrxBUMCY"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
NORMAL_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"

# 2. Connection Object (needed for writing/approving)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # We use standard pandas to READ (more stable)
        return pd.read_csv(CSV_URL)
    except Exception as e:
        st.error(f"❌ Read Error: {str(e)}")
        return pd.DataFrame()

df = load_data()

st.title("📲 Team Central Portal")

if not df.empty and 'Name' in df.columns:
    # --- SUBMIT NEW REQUEST ---
    with st.expander("➕ NEW REQUEST"):
        u_name = st.text_input("Name")
        u_req = st.text_area("Request")
        if st.button("Submit"):
            if u_name and u_req:
                new_row = pd.DataFrame([{"ID": len(df)+1, "Name": u_name, "Request": u_req, "Status": "Pending"}])
                updated = pd.concat([df, new_row], ignore_index=True)
                # Write back to Google
                conn.update(spreadsheet=NORMAL_URL, worksheet="Sheet1", data=updated)
                st.success("Request sent!")
                st.rerun()

    # --- DISPLAY LIST ---
    st.subheader("📋 Active Requests")
    for i, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{row['Name']}**: {row['Request']}")
            
            curr_status = str(row['Status'])
            if curr_status == "Pending" or curr_status == "nan":
                if c2.button("Approve", key=f"btn_{i}"):
                    df.at[i, 'Status'] = "Approved ✅"
                    conn.update(spreadsheet=NORMAL_URL, worksheet="Sheet1", data=df)
                    st.rerun()
            else:
                c2.write(curr_status)
else:
    st.info("The app is starting up... if you see this for more than 10 seconds, check your Google Sheet row 1 for: ID, Name, Request, Status")
