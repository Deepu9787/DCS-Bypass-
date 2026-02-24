import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Team Portal", layout="centered")
st_autorefresh(interval=10000, key="datarefresh")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # This will now show the EXACT technical error message
        data = conn.read(worksheet="Sheet1", ttl=0)
        return data
    except Exception as e:
        st.error(f"❌ Connection Error: {str(e)}")
        st.info("Check your Streamlit Secrets for the correct 'url' and ensure the Sheet tab is 'Sheet1'")
        return None

df = load_data()

st.title("📲 Team Central Portal")

if df is not None:
    # Check if headers exist
    expected_cols = ['ID', 'Name', 'Request', 'Status']
    if all(col in df.columns for col in expected_cols):
        with st.expander("➕ NEW REQUEST"):
            u_name = st.text_input("Name")
            u_req = st.text_area("Request")
            if st.button("Submit"):
                if u_name and u_req:
                    new_row = pd.DataFrame([{"ID": len(df)+1, "Name": u_name, "Request": u_req, "Status": "Pending"}])
                    updated = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated)
                    st.success("Done!")
                    st.rerun()

        st.subheader("📋 Active Requests")
        for i, row in df.iloc[::-1].iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['Name']}**: {row['Request']}")
                if str(row['Status']) == "Pending":
                    if c2.button("Approve", key=f"a_{i}"):
                        df.at[i, 'Status'] = "Approved ✅"
                        conn.update(worksheet="Sheet1", data=df)
                        st.rerun()
                else:
                    c2.write(row['Status'])
    else:
        st.warning(f"Columns not found. Found: {list(df.columns)}")
        st.info("Ensure Row 1 has: ID, Name, Request, Status")

# Manual Sync
if st.button("🔄 Sync"):
    st.rerun()
