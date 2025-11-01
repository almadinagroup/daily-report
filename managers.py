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

if not sheets_connected:
    st.stop()

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
# LOAD DATA FROM SHEET
# ================================
data = sheet.get_all_records()
df = pd.DataFrame(data)
st.session_state.df = df.copy()

# Only show items for this outlet
outlet_name = st.session_state.outlet_name
outlet_df = st.session_state.df[
    st.session_state.df["Outlet"].str.lower() == outlet_name.lower()
]

# ================================
# DASHBOARD PAGES
# ================================
page = st.sidebar.radio("Go to:", ["Main Dashboard", "Edit Dashboard"])

# ---------------- Main Dashboard ----------------
if page == "Main Dashboard":
    st.title(f"📋 Main Dashboard - {outlet_name}")

    # Only show items where Action Took is empty
    main_df = outlet_df[outlet_df["Action Took"].isna() | (outlet_df["Action Took"] == "")]

    if main_df.empty:
        st.info("No pending items for action.")
    else:
        # Sidebar filters
        st.sidebar.header("Filters")
        form_types = main_df["Form Type"].dropna().unique().tolist()
        selected_form_types = st.sidebar.multiselect("Form Type", form_types, default=form_types)
        search_query = st.sidebar.text_input("Search")

        filtered_df = main_df[main_df["Form Type"].isin(selected_form_types)]
        if search_query:
            filtered_df = filtered_df[
                filtered_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)
            ]

        for i, row in filtered_df.iterrows():
            st.markdown(f"### {row['Item Name']}  | Qty: {row['Qty']}")
            st.markdown(f"**Form Type:** {row.get('Form Type', 'N/A')}  |  **Expiry Date:** {row.get('Expiry Date', 'N/A')}  |  **Staff:** {row.get('Staff Name', 'N/A')}  |  **Barcode:** {row.get('Barcode', 'N/A')}")

            action_val = st.text_input("Action Took", value="", key=f"action_main_{i}")

            def submit_action(i=i, action_val=action_val):
                if not action_val.strip():
                    st.warning("Please enter an Action Took value")
                    return
                try:
                    all_values = sheet.get_all_values()
                    headers = all_values[0]
                    # Add Action Took Date column if missing
                    if "Action Took Date" not in headers:
                        sheet.add_cols(1)
                        sheet.update_cell(1, len(headers)+1, "Action Took Date")
                        headers.append("Action Took Date")

                    action_idx = headers.index("Action Took")
                    date_idx = headers.index("Action Took Date")

                    # Update the correct row
                    for j, sheet_row in enumerate(all_values[1:], start=2):
                        if sheet_row[headers.index("Item Name")] == row["Item Name"] and sheet_row[headers.index("Outlet")].lower() == outlet_name.lower():
                            sheet.update_cell(j, action_idx+1, action_val)
                            sheet.update_cell(j, date_idx+1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            st.success(f"✅ Action Took updated for {row['Item Name']}")
                            break
                    st.session_state.df = pd.DataFrame(sheet.get_all_records())
                except Exception as e:
                    st.error(f"❌ Error updating sheet: {e}")

            st.button("Submit Action Took", on_click=submit_action, key=f"submit_main_{i}")

# ---------------- Edit Dashboard ----------------
if page == "Edit Dashboard":
    st.title(f"✏️ Edit Dashboard - {outlet_name}")

    # Only show items where Action Took is filled
    edit_df = outlet_df[~(outlet_df["Action Took"].isna() | (outlet_df["Action Took"] == ""))]

    if edit_df.empty:
        st.info("No items to edit.")
    else:
        search_query = st.text_input("Search in Edit Dashboard")
        filtered_edit = edit_df
        if search_query:
            filtered_edit = edit_df[
                edit_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)
            ]

        for i, row in filtered_edit.iterrows():
            st.markdown(f"### {row['Item Name']}  | Qty: {row['Qty']}")
            st.markdown(f"**Form Type:** {row.get('Form Type', 'N/A')}  |  **Expiry Date:** {row.get('Expiry Date', 'N/A')}  |  **Staff:** {row.get('Staff Name', 'N/A')}  |  **Barcode:** {row.get('Barcode', 'N/A')}  |  **Action Took Date:** {row.get('Action Took Date', 'N/A')}")

            action_val = st.text_input("Action Took", value=row["Action Took"], key=f"action_edit_{i}")

            def edit_action(i=i, action_val=action_val):
                if not action_val.strip():
                    st.warning("Please enter an Action Took value")
                    return
                try:
                    all_values = sheet.get_all_values()
                    headers = all_values[0]
                    action_idx = headers.index("Action Took")
                    date_idx = headers.index("Action Took Date")

                    # Update the correct row
                    for j, sheet_row in enumerate(all_values[1:], start=2):
                        if sheet_row[headers.index("Item Name")] == row["Item Name"] and sheet_row[headers.index("Outlet")].lower() == outlet_name.lower():
                            sheet.update_cell(j, action_idx+1, action_val)
                            sheet.update_cell(j, date_idx+1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            st.success(f"✅ Action Took updated for {row['Item Name']}")
                            break
                    st.session_state.df = pd.DataFrame(sheet.get_all_records())
                except Exception as e:
                    st.error(f"❌ Error updating sheet: {e}")

            st.button("Update Action Took", on_click=edit_action, key=f"submit_edit_{i}")
