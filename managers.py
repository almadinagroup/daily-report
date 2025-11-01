import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(page_title="Outlet Manager Dashboard", layout="wide")

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
# LOAD DATA
# ================================
st.title(f"📋 Manager Dashboard - {st.session_state.outlet_name}")

data = sheet.get_all_records()
df = pd.DataFrame(data)

# Filter only for logged-in outlet
df = df[df["Outlet"].str.lower() == st.session_state.outlet_name.lower()]

# Convert dates to datetime.date
if "Date Submitted" in df.columns:
    df["Date Submitted"] = pd.to_datetime(df["Date Submitted"], errors='coerce').dt.date
if "Expiry" in df.columns:
    df["Expiry"] = pd.to_datetime(df["Expiry"], errors='coerce').dt.date

# ================================
# SIDEBAR FILTERS
# ================================
st.sidebar.header("Filters")

# Form Type dropdown (single selection)
form_types = df["Form Type"].dropna().unique().tolist()
form_types.sort()
form_types.insert(0, "All")  # Add "All" option
selected_form_type = st.sidebar.selectbox("Form Type", form_types)
if selected_form_type != "All":
    df = df[df["Form Type"] == selected_form_type]

# Date filter column selection
date_column = st.sidebar.selectbox("Filter by Date Column", ["Date Submitted", "Expiry"])
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("From", value=datetime.today().date())
end_date = col2.date_input("To", value=datetime.today().date())
df = df[(df[date_column] >= start_date) & (df[date_column] <= end_date)]

# Search filter
search_query = st.sidebar.text_input("Search")
if search_query:
    df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)]

# ================================
# EDITABLE ACTION TOOK TABLE
# ================================
if df.empty:
    st.info("No records match the filters.")
else:
    st.markdown(f"**Showing records from {start_date} to {end_date} ({date_column})**")

    # Reorder columns to show "Action Took" first
    columns_order = ["Action Took"] + [col for col in df.columns if col != "Action Took"]
    df = df[columns_order]

    # Editable table
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Action Took": st.column_config.TextColumn(
                "Action Took",
                help="Edit the action took for this item",
                max_chars=200,
            )
        },
        hide_index=True
    )

    # ================================
    # SAVE FUNCTION
    # ================================
    def save_action_took():
        try:
            # Use the latest edited_df returned by st.data_editor
            all_values = sheet.get_all_values()
            headers = all_values[0]
            action_idx = headers.index("Action Took")
            outlet_idx = headers.index("Outlet")
            item_idx = headers.index("Item Name")
            date_idx = headers.index("Action Took Date") if "Action Took Date" in headers else None

            today_date = datetime.now().strftime("%Y-%m-%d")

            for i, row in edited_df.iterrows():
                for j, sheet_row in enumerate(all_values[1:], start=2):
                    if (sheet_row[item_idx] == row["Item Name"] and
                        sheet_row[outlet_idx].lower() == st.session_state.outlet_name.lower()):
                        sheet.update_cell(j, action_idx + 1, row["Action Took"])
                        if date_idx is not None:
                            sheet.update_cell(j, date_idx + 1, today_date)

            st.success("✅ Action Took updated successfully!")

        except Exception as e:
            st.error(f"❌ Failed to update: {e}")

    st.button("💾 Submit Action Took", on_click=save_action_took)
