import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Team Portal", layout="centered")

# Auto-refresh every 10 seconds to sync phone and computer
st_autorefresh(interval=10000, key="datarefresh")

# Create connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # We use a very simple read command
        return conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        st.error(f"❌ Connection Error: {str(e)}")
        return pd.DataFrame()

df = load_data()

st.title("📲 Team Central Portal")

# Only show the app if data loaded correctly
if not df.empty and 'Name' in df.columns:
    # --- ADD NEW REQUEST ---
    with st.expander("➕ NEW REQUEST"):
        user = st.text_input("Your Name")
        task = st.text_area("What do you need?")
        if st.button("Submit to Team"):
            if user and task:
                new_row = pd.DataFrame([{"ID": len(df)+1, "Name": user, "Request": task, "Status": "Pending"}])
                df_updated = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df_updated)
                st.success("Request sent!")
                st.rerun()

    st.subheader("📋 Live Dashboard")
    # Display newest requests first
    for i, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{row['Name']}**: {row['Request']}")
            
            # Status / Approval logic
            if str(row['Status']) == "Pending":
                if col2.button("Approve", key=f"btn_{i}"):
                    df.at[i, 'Status'] = "Approved ✅"
                    conn.update(worksheet="Sheet1", data=df)
                    st.rerun()
            else:
                col2.write(f"**{row['Status']}**")
else:
    st.info("Waiting for Google Sheets connection... Please ensure Secrets are saved and app is rebooted.")
