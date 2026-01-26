"""Tick data viewer page."""

import streamlit as st
import requests
from src.common.logging import configure_logging
from datetime import datetime, timedelta

st.title("Tick Data Viewer")

# Simple ISIN selector
isin = st.text_input("Enter ISIN")
if not isin:
    st.stop()

start = st.date_input("Start", value=datetime.now().date() - timedelta(days=1))
end = st.date_input("End", value=datetime.now().date())

if st.button("Fetch"):
    # TODO: call GET /ticks/history?isin=...&start=...&end=...
    st.info("Historical data fetching not yet implemented.")

# Latest price placeholder
st.subheader("Latest Price")
# TODO: call GET /ticks/latest?isin=...
st.info("Latest price will be shown here.")
