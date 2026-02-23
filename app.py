import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 1. Page Configuration
st.set_page_config(page_title="Team Request System", layout="centered")

# 2. Auto-Refresh (Sync every 10 seconds for all 20 users)
st_autorefresh(interval=10000, key="datarefresh")

# 3. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Helper function to load fresh data
def get_data():
    return conn.read(worksheet="Sheet1", ttl=0) # ttl=0 ensures it's always live

df = get_data()

st.title("📲 Team Central Portal")

# --- SECTION: USER REQUEST (Mobile View) ---
with st.expander("➕ NEW REQUEST"):
    name = st.text_input("Your Name")
    request = st.text_area("Request Details")
    
    if st.button("Submit Request"):
        if name and request:
            # Create a new row
            new_row = pd.DataFrame([{
                "ID": len(df) + 1,
                "Name": name,
                "Request": request,
                "Status": "Pending ⏳"
            }])
            # Add to current data
            updated_df = pd.concat([df, new_row], ignore_index=True)
            # Update the Google Sheet
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("Request sent to the team!")
            st.rerun()

st.divider()

# --- SECTION: DASHBOARD (Laptop/All Users View) ---
st.subheader("📋 Active Requests")

if df.empty:
    st.info("No requests found.")
else:
    # Display requests from newest to oldest
    for index, row in df.iloc[::-1].iterrows():
        # Create a nice card for each request
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**From:** {row['Name']}")
                st.write(f"**Request:** {row['Request']}")
            
            with col2:
                # If it's pending, show the Approve button (for Admin)
                if "Pending" in str(row['Status']):
                    if st.button("Approve", key=f"app_{index}"):
                        df.at[index, 'Status'] = "Approved ✅"
                        conn.update(worksheet="Sheet1", data=df)
                        st.rerun()
                else:
                    st.write(f"**{row['Status']}**")

# Manual Sync Button
if st.button("🔄 Sync Now"):
    st.rerun()
