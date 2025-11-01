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
    st.stop()  # Stop further execution until login is successful

# ================================
# MANAGER DASHBOARD
# ================================
st.title(f"📊 Manager Dashboard - {st.session_state.outlet_name}")

if not sheets_connected:
    st.stop()

# Load data from Google Sheets
data = sheet.get_all_records()
df = pd.DataFrame(data)
st.session_state.df = df.copy()

# Ensure date columns are datetime
if 'Date' in df.columns:
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
if 'Expiry' in df.columns:
    df['Expiry'] = pd.to_datetime(df['Expiry'], errors='coerce')

# ================================
# Sidebar Navigation
# ================================
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Main Dashboard", "Edit Dashboard", "View All Details"])

# ================================
# FILTERS
# ================================
st.sidebar.header("Filters")
# Form Type
form_types = df["Form Type"].dropna().unique().tolist()
selected_form_types = st.sidebar.multiselect("Form Type", form_types, default=form_types)

# Date Range Filter
if 'Date' in df.columns:
    start_date, end_date = st.sidebar.date_input(
        "Select Date Range",
        value=[df['Date'].min(), df['Date'].max()]
    )
else:
    start_date = end_date = None

# Search
search_query = st.sidebar.text_input("Search")

# Filter by outlet for main & edit dashboards
outlet_name = st.session_state.outlet_name
df_outlet = df[df["Outlet"].str.lower() == outlet_name.lower()]

# Apply Form Type filter
df_outlet = df_outlet[df_outlet["Form Type"].isin(selected_form_types)]

# Apply Date filter
if start_date and end_date and 'Date' in df_outlet.columns:
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    df_outlet = df_outlet[(df_outlet['Date'] >= start_date) & (df_outlet['Date'] <= end_date)]

# Apply Search
if search_query:
    df_outlet = df_outlet[df_outlet.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)]

# ================================
# MAIN DASHBOARD (Action Took empty)
# ================================
if page == "Main Dashboard":
    st.subheader("📝 Items Pending Action Took")
    main_df = df_outlet[df_outlet["Action Took"].isna() | (df_outlet["Action Took"] == "")]

    if not main_df.empty:
        for i, row in main_df.iterrows():
            st.markdown(f"### {row['Item Name']} - Qty: {row['Qty']}")
            st.markdown(f"**Staff:** {row.get('Staff Name', '')} | **Form Type:** {row.get('Form Type', '')} | **Expiry:** {row.get('Expiry', 'N/A')}")
            action_input = st.text_input(
                "Action Took",
                value="",
                key=f"action_{i}"
            )

            # Submit Button
            def submit_action(idx=i, action_val=action_input):
                try:
                    all_values = sheet.get_all_values()
                    headers = all_values[0]
                    action_idx = headers.index("Action Took")
                    date_idx = None
                    if "Action Took Date" in headers:
                        date_idx = headers.index("Action Took Date")
                    else:
                        # Add new column for date if not exists
                        sheet.update_cell(1, len(headers)+1, "Action Took Date")
                        date_idx = len(headers)
                    
                    outlet_idx = headers.index("Outlet")
                    item_idx = headers.index("Item Name")

                    # Update Google Sheet
                    for j, sheet_row in enumerate(all_values[1:], start=2):
                        if sheet_row[item_idx] == row["Item Name"] and sheet_row[outlet_idx].lower() == outlet_name.lower():
                            sheet.update_cell(j, action_idx+1, action_val)
                            sheet.update_cell(j, date_idx+1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    st.success(f"✅ Action Took updated for {row['Item Name']}")
                except Exception as e:
                    st.error(f"❌ Failed to update: {e}")

            st.button("Submit Action Took", on_click=submit_action, key=f"submit_{i}")
            st.markdown("---")
    else:
        st.info("No pending items for your outlet.")

# ================================
# EDIT DASHBOARD (Action Took filled)
# ================================
elif page == "Edit Dashboard":
    st.subheader("✏️ Items with Action Took")
    edit_df = df_outlet[~df_outlet["Action Took"].isna() & (df_outlet["Action Took"] != "")]
    if not edit_df.empty:
        st.dataframe(edit_df)
    else:
        st.info("No items with Action Took yet.")

# ================================
# VIEW ALL DETAILS PAGE
# ================================
elif page == "View All Details":
    st.subheader("📂 All Details")
    if not df_outlet.empty:
        st.dataframe(df_outlet)
    else:
        st.info("No records to show.")
