import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# -------------------------------
# Page config
# -------------------------------
st.set_page_config(page_title="Outlet Manager Dashboard", layout="wide")

# -------------------------------
# Outlet credentials
# -------------------------------
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

# -------------------------------
# Google Sheets setup
# -------------------------------
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

# -------------------------------
# Session state initialization
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "outlet_name" not in st.session_state:
    st.session_state.outlet_name = None
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

# -------------------------------
# Login page
# -------------------------------
if not st.session_state.logged_in:
    st.title("🔐 Outlet Manager Login")
    outlet = st.selectbox("Select your Outlet", list(outlet_passwords.keys()))
    password = st.text_input("Enter Password", type="password")

    if st.button("Login"):
        if outlet_passwords.get(outlet) == password:
            st.session_state.logged_in = True
            st.session_state.outlet_name = outlet
            st.success(f"✅ Logged in as {outlet}")
            st.experimental_rerun()
        else:
            st.error("❌ Invalid password")
else:
    # Logout button
    st.sidebar.title(f"Welcome, {st.session_state.outlet_name}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.outlet_name = None
        st.experimental_rerun()

    st.title(f"📊 Manager Dashboard - {st.session_state.outlet_name}")

    # -------------------------------
    # Load sheet data
    # -------------------------------
    if sheets_connected:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        st.session_state.df = df.copy()
    else:
        st.stop()

    # -------------------------------
    # Filter by outlet
    # -------------------------------
    outlet_name = st.session_state.outlet_name
    df_outlet = st.session_state.df[df["Outlet"].str.lower() == outlet_name.lower()]

    # -------------------------------
    # Sidebar filters
    # -------------------------------
    st.sidebar.header("Filters")
    form_types = df_outlet["Form Type"].dropna().unique().tolist()
    selected_form_types = st.sidebar.multiselect("Form Type", form_types, default=form_types)

    search_query = st.sidebar.text_input("Search in table")

    # Apply filters
    filtered_df = df_outlet[df_outlet["Form Type"].isin(selected_form_types)]
    if search_query:
        filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)]

    st.subheader("📋 Filtered Records")
    
    # -------------------------------
    # Editable Action Took
    # -------------------------------
    if not filtered_df.empty:
        for i, row in filtered_df.iterrows():
            st.write(f"**{row['Item Name']} - Qty: {row['Qty']}**")
            action = st.text_input(
                "Action Took", 
                value=row.get("Action Took", ""), 
                key=f"action_{i}"
            )
            filtered_df.at[i, "Action Took"] = action

        # Save button
        if st.button("💾 Save Action Took to Google Sheets"):
            try:
                all_values = sheet.get_all_values()
                headers = all_values[0]
                action_idx = headers.index("Action Took")
                outlet_idx = headers.index("Outlet")
                item_idx = headers.index("Item Name")

                # Update rows in Google Sheets
                for i, row in filtered_df.iterrows():
                    # Find the correct row in the sheet
                    for j, sheet_row in enumerate(all_values[1:], start=2):
                        if sheet_row[item_idx] == row["Item Name"] and sheet_row[outlet_idx].lower() == outlet_name.lower():
                            sheet.update_cell(j, action_idx + 1, row["Action Took"])
                st.success("✅ Updated successfully in Google Sheets!")
            except Exception as e:
                st.error(f"❌ Failed to update: {e}")

    else:
        st.info("No records to show for your outlet and selected filters.")
