import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Outlet Dashboard", layout="wide")

# --- Outlet credentials ---
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

# --- Google Sheets connection ---
conn = st.connection("gsheets", type=GSheetsConnection)
sheet_url = "https://docs.google.com/spreadsheets/d/1MK5WDETIFCRes-c8X16JjrNdrlEpHwv9vHvb96VVtM0/edit?gid=0"

# --- Login section ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "outlet_name" not in st.session_state:
    st.session_state.outlet_name = None

if not st.session_state.logged_in:
    st.title("🔐 Outlet Manager Login")

    outlet = st.selectbox("Select your Outlet", list(outlet_passwords.keys()))
    password = st.text_input("Enter Password", type="password")

    if st.button("Login"):
        if outlet_passwords.get(outlet) == password:
            st.session_state.logged_in = True
            st.session_state.outlet_name = outlet
            st.success(f"✅ Logged in as {outlet}")
            st.rerun()
        else:
            st.error("❌ Invalid password. Please try again.")
else:
    st.sidebar.title(f"Welcome, {st.session_state.outlet_name}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.outlet_name = None
        st.rerun()

    st.title(f"📊 Dashboard - {st.session_state.outlet_name}")

    # --- Load data from Google Sheets ---
    df = conn.read(spreadsheet=sheet_url, worksheet="Items", ttl=5)
    df = df.dropna(how="all")

    # --- Filter data by outlet ---
    outlet_name = st.session_state.outlet_name
    df_outlet = df[df["Outlet"].str.lower() == outlet_name.lower()]

    # --- Filter options ---
    st.sidebar.header("Filters")
    unique_forms = df_outlet["Form Type"].dropna().unique().tolist()
    form_filter = st.sidebar.multiselect("Select Form Type", unique_forms, default=unique_forms)

    # Date filter (if Date column exists)
    if "Date" in df_outlet.columns:
        min_date = pd.to_datetime(df_outlet["Date"], errors='coerce').min()
        max_date = pd.to_datetime(df_outlet["Date"], errors='coerce').max()
        date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])
    else:
        date_range = []

    # Search bar
    search_query = st.text_input("🔍 Search any text in the table")

    # --- Apply filters ---
    filtered_df = df_outlet[df_outlet["Form Type"].isin(form_filter)]

    if len(date_range) == 2 and "Date" in df_outlet.columns:
        filtered_df = filtered_df[
            (pd.to_datetime(filtered_df["Date"], errors='coerce') >= pd.to_datetime(date_range[0])) &
            (pd.to_datetime(filtered_df["Date"], errors='coerce') <= pd.to_datetime(date_range[1]))
        ]

    if search_query:
        filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)]

    # --- Display Data ---
    st.subheader("📋 Filtered Records")
    st.dataframe(filtered_df, use_container_width=True)

    st.write(f"Total Records: **{len(filtered_df)}**")

    # Download option
    st.download_button(
        label="⬇️ Download Filtered Data as CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name=f"{outlet_name}_filtered_data.csv",
        mime="text/csv"
    )
