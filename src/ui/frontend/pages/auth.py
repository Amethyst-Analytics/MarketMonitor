"""Authentication status page."""

import os
import streamlit as st

st.title("Authentication")

token = os.getenv("UPSTOX_ACCESS_TOKEN")
if token:
    st.success("Access token is configured.")
    st.code(token[:20] + "...")
else:
    st.warning("No access token found.")
    st.info("Run the auth service to obtain a token and set UPSTOX_ACCESS_TOKEN.")
