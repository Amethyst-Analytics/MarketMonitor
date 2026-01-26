"""Instrument management page."""

import streamlit as st
import requests

st.title("Instrument Management")

st.subheader("Bulk ISIN Upload")
uploaded = st.file_uploader("Upload CSV with ISIN column", type=["csv"])
if uploaded:
    # TODO: parse and call POST /isin/bulk
    st.info("Uploaded.")

st.subheader("Subscribed Instruments")
# TODO: fetch from GET /instruments/subscribed
st.info("Instrument list will be displayed here once backend is connected.")
