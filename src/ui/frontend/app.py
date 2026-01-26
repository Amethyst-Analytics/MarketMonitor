"""Streamlit UI for MarketMonitor."""

from __future__ import annotations

import streamlit as st
from pages import auth, instruments, ticks

st.set_page_config(page_title="MarketMonitor", layout="wide")

pg = st.navigation(
    [
        st.Page(auth, title="Auth"),
        st.Page(instruments, title="Instruments"),
        st.Page(ticks, title="Ticks"),
    ]
)

pg.run()
