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
    st.stop()  # Stop further execution until login is successful

# ================================
# MANAGER DASHBOARD
# ================================
st.title(f"📋 Manager Dashboard - {st.session_state.outlet_name}")

# Load data from Google Sheets
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Filter only for the logged-in outlet
df = df[df["Outlet"].str.lower() == st.session_state.outlet_name.lower()]

# Convert 'Date Submitted' to datetime.date
if "Date Submitted" in df.columns:
    df["Date Submitted"] = pd.to_datetime(df["Date Submitted"], errors='coerce').dt.date

# ================================
# SIDEBAR FILTERS
# ================================
st.sidebar.header("Filters")

# Form Type filter
if "Form Type" in df.columns:
    form_types = df["Form Type"].dropna().unique().tolist()
    selected_form_types = st.sidebar.multiselect("Form Type", form_types, default=form_types)
    df = df[df["Form Type"].isin(selected_form_types)]

# Date filter
if "Date Submitted" in df.columns:
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("From", min(df["Date Submitted"].dropna(), default=datetime.today().date()))
    end_date = col2.date_input("To", max(df["Date Submitted"].dropna(), default=datetime.today().date()))
    df = df[(df["Date Submitted"] >= start_date) & (df["Date Submitted"] <= end_date)]

# Search filter
search_query = st.sidebar.text_input("Search in table")
if search_query:
    df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)]

# ================================
# DISPLAY DATA
# ================================
if df.empty:
    st.info("No records match the filters.")
else:
    for i, row in df.iterrows():
        st.markdown(f"### {row.get('Item Name', '')}  |  Qty: {row.get('Qty', '')}")
        st.markdown(f"- **Form Type:** {row.get('Form Type', '')}")
        st.markdown(f"- **Staff Name:** {row.get('Staff Name', '')}")
        st.markdown(f"- **Expiry Date:** {row.get('Expiry', 'N/A')}")
        st.markdown(f"- **Action Took:** {row.get('Action Took', '')}")
        st.markdown(f"- **Date Submitted:** {row.get('Date Submitted', '')}")
        st.markdown("---")
