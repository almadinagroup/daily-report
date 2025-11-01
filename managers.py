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
if "page" not in st.session_state:
    st.session_state.page = "Main"

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
# NAVIGATION
# ================================
st.sidebar.title("Navigation")
page_selection = st.sidebar.radio("Go to:", ["Main Dashboard", "Edit Action Took"])
st.session_state.page = page_selection

if not sheets_connected:
    st.stop()

# ================================
# LOAD DATA FROM GOOGLE SHEETS
# ================================
def load_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # Ensure Action Took Date column exists
    if "Action Took Date" not in df.columns:
        df["Action Took Date"] = ""
    return df

st.session_state.df = load_data()
df = st.session_state.df

# Filter for the logged-in outlet
outlet_name = st.session_state.outlet_name
df_outlet = df[df["Outlet"].str.lower() == outlet_name.lower()]

# Sidebar Filters
form_types = df_outlet["Form Type"].dropna().unique().tolist()
selected_form_types = st.sidebar.multiselect("Form Type", form_types, default=form_types)
search_query = st.sidebar.text_input("Search")

# Apply filters
filtered_df = df_outlet[df_outlet["Form Type"].isin(selected_form_types)]
if search_query:
    filtered_df = filtered_df[
        filtered_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)
    ]

# ================================
# MAIN DASHBOARD
# ================================
if st.session_state.page == "Main Dashboard":
    st.title(f"📊 Main Dashboard - {outlet_name}")

    # Only show rows where Action Took is empty
    display_df = filtered_df[filtered_df["Action Took"].isnull() | (filtered_df["Action Took"] == "")]

    if not display_df.empty:
        for i, row in display_df.iterrows():
            st.write(f"**{row['Item Name']} - Qty: {row['Qty']} - Staff: {row.get('Staff Name','')} - Barcode: {row.get('Barcode','')}**")
            action = st.text_input(
                "Action Took",
                value="",
                key=f"action_main_{i}"
            )
            submit_button = st.button("Submit Action Took", key=f"submit_main_{i}")

            if submit_button and action.strip() != "":
                # Update Google Sheet
                all_values = sheet.get_all_values()
                headers = all_values[0]
                action_idx = headers.index("Action Took")
                date_idx = headers.index("Action Took Date") if "Action Took Date" in headers else None
                outlet_idx = headers.index("Outlet")
                item_idx = headers.index("Item Name")

                # Find row in sheet
                for j, sheet_row in enumerate(all_values[1:], start=2):
                    if sheet_row[item_idx] == row["Item Name"] and sheet_row[outlet_idx].lower() == outlet_name.lower():
                        sheet.update_cell(j, action_idx + 1, action)
                        if date_idx is None:
                            # Add Action Took Date column if missing
                            sheet.update_cell(1, len(headers)+1, "Action Took Date")
                            date_idx = len(headers)
                        sheet.update_cell(j, date_idx + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        st.success(f"✅ Action Took updated for {row['Item Name']}")
                        break
                st.experimental_rerun()
    else:
        st.info("No pending items to show.")

# ================================
# EDIT ACTION TOOK PAGE
# ================================
elif st.session_state.page == "Edit Action Took":
    st.title(f"✏️ Edit Action Took - {outlet_name}")

    # Only show rows where Action Took is not empty
    edit_df = filtered_df[filtered_df["Action Took"].notnull() & (filtered_df["Action Took"] != "")]

    if not edit_df.empty:
        for i, row in edit_df.iterrows():
            st.write(f"**{row['Item Name']} - Qty: {row['Qty']} - Staff: {row.get('Staff Name','')} - Barcode: {row.get('Barcode','')}**")
            action = st.text_input(
                "Action Took",
                value=row.get("Action Took", ""),
                key=f"action_edit_{i}"
            )
            submit_button = st.button("Update Action Took", key=f"submit_edit_{i}")

            if submit_button and action.strip() != "":
                # Update Google Sheet
                all_values = sheet.get_all_values()
                headers = all_values[0]
                action_idx = headers.index("Action Took")
                date_idx = headers.index("Action Took Date") if "Action Took Date" in headers else None
                outlet_idx = headers.index("Outlet")
                item_idx = headers.index("Item Name")

                for j, sheet_row in enumerate(all_values[1:], start=2):
                    if sheet_row[item_idx] == row["Item Name"] and sheet_row[outlet_idx].lower() == outlet_name.lower():
                        sheet.update_cell(j, action_idx + 1, action)
                        if date_idx is not None:
                            sheet.update_cell(j, date_idx + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        st.success(f"✅ Action Took updated for {row['Item Name']}")
                        break
                st.experimental_rerun()
    else:
        st.info("No Action Took entries to edit.")
