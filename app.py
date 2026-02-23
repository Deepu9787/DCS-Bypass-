import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Team System", layout="centered")

# Auto-refresh every 10 seconds
st_autorefresh(interval=10000, key="datarefresh")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # We try to read the data. If it fails, we show a helpful message.
        return conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        st.error(f"⚠️ Sheet Error: Make sure your Google Sheet tab is named 'Sheet1' and you have headers (ID, Name, Request, Status)")
        st.info("Check your Streamlit Secrets for the correct URL.")
        return pd.DataFrame()

df = get_data()

st.title("📲 Team Central Portal")

if not df.empty:
    # --- USER REQUEST ---
    with st.expander("➕ NEW REQUEST"):
        name = st.text_input("Your Name")
        request = st.text_area("Request Details")
        
        if st.button("Submit Request"):
            if name and request:
                new_row = pd.DataFrame([{"ID": len(df) + 1, "Name": name, "Request": request, "Status": "Pending"}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("Sent!")
                st.rerun()

    st.divider()

    # --- DASHBOARD ---
    st.subheader("📋 Active Requests")
    for index, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{row['Name']}**: {row['Request']}")
            if str(row['Status']) == "Pending":
                if col2.button("Approve", key=f"app_{index}"):
                    df.at[index, 'Status'] = "Approved ✅"
                    conn.update(worksheet="Sheet1", data=df)
                    st.rerun()
            else:
                col2.write(row['Status'])
else:
    st.warning("Database is offline. Please check your Google Sheet and Secrets.")
