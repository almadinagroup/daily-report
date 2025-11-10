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
    "Shams salem": "shams123",
    "Shams Liwan": "liwan123",
    "Superstore": "super123",
    "Tay Tay": "taytay123",
    "Safa oudmehta": "oud123",
    "Port saeed": "port123",
    "Logistics": "1234512345"  # ✅ Added logistics user
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

# Filter only for outlet users
if st.session_state.outlet_name.lower() != "logistics":
    df = df[df["Outlet"].str.lower() == st.session_state.outlet_name.lower()]

# Convert dates
if "Date Submitted" in df.columns:
    df["Date Submitted"] = pd.to_datetime(df["Date Submitted"], errors='coerce').dt.date
if "Expiry" in df.columns:
    df["Expiry"] = pd.to_datetime(df["Expiry"], errors='coerce').dt.date
if "Action Took Date" in df.columns:
    df["Action Took Date"] = pd.to_datetime(df["Action Took Date"], errors='coerce').dt.date

# ================================
# SIDEBAR FILTERS
# ================================
st.sidebar.header("Filters")

form_types = df["Form Type"].dropna().unique().tolist()
form_types.sort()
form_types.insert(0, "All")
selected_form_type = st.sidebar.selectbox("Form Type", form_types)
if selected_form_type != "All":
    df = df[df["Form Type"] == selected_form_type]

date_column = st.sidebar.selectbox("Filter by Date Column", ["Date Submitted", "Expiry"])
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("From", value=datetime.today().date())
end_date = col2.date_input("To", value=datetime.today().date())
df = df[(df[date_column] >= start_date) & (df[date_column] <= end_date)]

search_query = st.sidebar.text_input("Search")
if search_query:
    df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)]

# ================================
# EDITABLE TABLES
# ================================
if df.empty:
    st.info("No records match the filters.")
else:
    st.markdown(f"**Showing records from {start_date} to {end_date} ({date_column})**")

    # Remove "Action Took Date" for outlets
    view_df = df.copy()
    if st.session_state.outlet_name.lower() != "logistics":
        if "Action Took Date" in view_df.columns:
            view_df = view_df.drop(columns=["Action Took Date"], errors="ignore")

    # Editable columns based on user
    if st.session_state.outlet_name.lower() == "logistics":
        # Logistics can edit Supplier Name
        editable_cols = {
            "Supplier Name": st.column_config.TextColumn("Supplier Name", help="Edit supplier name"),
        }
    else:
        # Outlets can edit only Action Took
        editable_cols = {
            "Action Took": st.column_config.TextColumn("Action Took", help="Edit action took for this item"),
        }

    edited_df = st.data_editor(
        view_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config=editable_cols,
        hide_index=True
    )

    # ================================
    # SAVE BUTTONS
    # ================================
    def save_changes():
        try:
            all_values = sheet.get_all_values()
            headers = all_values[0]
            outlet_idx = headers.index("Outlet")
            item_idx = headers.index("Item Name")

            today_date = datetime.now().strftime("%Y-%m-%d")

            if st.session_state.outlet_name.lower() == "logistics":
                supplier_idx = headers.index("Supplier Name")
                for i, row in edited_df.iterrows():
                    for j, sheet_row in enumerate(all_values[1:], start=2):
                        if sheet_row[item_idx] == row["Item Name"]:
                            sheet.update_cell(j, supplier_idx + 1, row["Supplier Name"])
                st.success("✅ Supplier Name updated successfully!")
            else:
                action_idx = headers.index("Action Took")
                date_idx = headers.index("Action Took Date") if "Action Took Date" in headers else None
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

    st.button("💾 Submit Changes", on_click=save_changes)
