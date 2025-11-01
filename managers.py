import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(page_title="Manager Dashboard", layout="wide")

# ================================
# OUTLET PASSWORDS
# ================================
outlet_passwords = {
    "Hilal": "hilal123",
    "Safa Super": "safa123",
    "Azhar HP": "azharhp123",
    "Azhar": "azhar123",
    "Blue Pearl": "blue123",
    "Fida": "fida123",
    "Hadeqat": "hadeqat123",
    "Jais": "jais123",
    "Sabah": "sabah123",
    "Sahat": "sahat123",
    "Shams salem": "salem123",
    "Shams Liwan": "liwan123",
    "Superstore": "super123",
    "Tay Tay": "taytay123",
    "Safa oudmehta": "oud123",
    "Port saeed": "port123"
}

# ================================
# GOOGLE SHEETS SETUP
# ================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MK5WDETIFCRes-c8X16JjrNdrlEpHwv9vHvb96VVtM0/edit#gid=0"
SHEET_NAME = "Items"

try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)
    sheets_connected = True
except Exception as e:
    st.error(f"⚠️ Google Sheets connection error: {e}")
    sheets_connected = False

# ================================
# SESSION STATE INIT
# ================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "outlet_name" not in st.session_state:
    st.session_state.outlet_name = None
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

# ================================
# LOGIN PAGE
# ================================
if not st.session_state.logged_in:
    st.title("🔐 Outlet Manager Login")
    outlet = st.selectbox("Select your Outlet", list(outlet_passwords.keys()))
    password = st.text_input("Enter Password", type="password")

    def login_callback():
        if outlet_passwords.get(outlet) == password:
            st.session_state.logged_in = True
            st.session_state.outlet_name = outlet
            st.success(f"✅ Logged in as {outlet}")
        else:
            st.error("❌ Invalid password")

    st.button("Login", on_click=login_callback)
    st.stop()

# ================================
# LOAD DATA FROM GOOGLE SHEETS
# ================================
if sheets_connected:
    data = sheet.get_all_records()
    st.session_state.df = pd.DataFrame(data)

df = st.session_state.df
outlet_name = st.session_state.outlet_name
df_outlet = df[df["Outlet"].str.lower() == outlet_name.lower()]

# ================================
# SIDEBAR FOR PAGE SELECTION
# ================================
page = st.sidebar.selectbox("Select Page", ["Main Dashboard", "Edit Action Took"])

# ================================
# MAIN DASHBOARD - SHOW ONLY EMPTY ACTION TOOK
# ================================
if page == "Main Dashboard":
    st.title(f"📋 Main Dashboard - {outlet_name}")
    main_df = df_outlet[df_outlet["Action Took"].isna() | (df_outlet["Action Took"].str.strip() == "")]
    
    if main_df.empty:
        st.info("No items pending Action Took.")
    else:
        st.subheader("Pending Items")
        for i, row in main_df.iterrows():
            st.markdown(f"### {row['Item Name']}  | Qty: {row['Qty']}")
            st.markdown(f"**Form Type:** {row['Form Type']}  |  **Expiry Date:** {row.get('Expiry Date', 'N/A')}  |  **Staff:** {row.get('Staff Name', 'N/A')}")
            
            action = st.text_input("Action Took", value="", key=f"action_main_{i}")
            
            def submit_action(i=i, action_val=action):
                try:
                    all_values = sheet.get_all_values()
                    headers = all_values[0]
                    if "Action Took Date" not in headers:
                        sheet.add_cols(1)
                        sheet.update_cell(1, len(headers)+1, "Action Took Date")
                        headers.append("Action Took Date")
                    
                    action_idx = headers.index("Action Took")
                    action_date_idx = headers.index("Action Took Date")
                    
                    # Find row in sheet
                    for j, sheet_row in enumerate(all_values[1:], start=2):
                        if sheet_row[headers.index("Item Name")] == row["Item Name"] and sheet_row[headers.index("Outlet")].lower() == outlet_name.lower():
                            sheet.update_cell(j, action_idx+1, action_val)
                            sheet.update_cell(j, action_date_idx+1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            st.success(f"✅ Action Took updated for {row['Item Name']}")
                            break
                    
                    # Refresh session df
                    st.session_state.df = pd.DataFrame(sheet.get_all_records())
                except Exception as e:
                    st.error(f"❌ Error updating sheet: {e}")
            
            st.button("Submit Action Took", on_click=submit_action)

# ================================
# EDIT DASHBOARD - SHOW ONLY FILLED ACTION TOOK
# ================================
if page == "Edit Action Took":
    st.title(f"✏️ Edit Action Took - {outlet_name}")
    edit_df = df_outlet[df_outlet["Action Took"].notna() & (df_outlet["Action Took"].str.strip() != "")]
    
    if edit_df.empty:
        st.info("No submitted Action Took records to edit.")
    else:
        st.subheader("Submitted Items")
        for i, row in edit_df.iterrows():
            st.markdown(f"### {row['Item Name']}  | Qty: {row['Qty']}")
            st.markdown(f"**Form Type:** {row['Form Type']}  |  **Expiry Date:** {row.get('Expiry Date', 'N/A')}  |  **Staff:** {row.get('Staff Name', 'N/A')}")
            
            action = st.text_input("Action Took", value=row["Action Took"], key=f"action_edit_{i}")
            
            def edit_action(i=i, action_val=action):
                try:
                    all_values = sheet.get_all_values()
                    headers = all_values[0]
                    if "Action Took Date" not in headers:
                        sheet.add_cols(1)
                        sheet.update_cell(1, len(headers)+1, "Action Took Date")
                        headers.append("Action Took Date")
                    
                    action_idx = headers.index("Action Took")
                    action_date_idx = headers.index("Action Took Date")
                    
                    for j, sheet_row in enumerate(all_values[1:], start=2):
                        if sheet_row[headers.index("Item Name")] == row["Item Name"] and sheet_row[headers.index("Outlet")].lower() == outlet_name.lower():
                            sheet.update_cell(j, action_idx+1, action_val)
                            sheet.update_cell(j, action_date_idx+1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            st.success(f"✅ Action Took updated for {row['Item Name']}")
                            break
                    st.session_state.df = pd.DataFrame(sheet.get_all_records())
                except Exception as e:
                    st.error(f"❌ Error updating sheet: {e}")
            
            st.button("Update Action Took", on_click=edit_action)
