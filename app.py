"""Enige Streamlit-entrypoint: streamlit run app.py."""

import streamlit as st

st.set_page_config(page_title="MinorAdviseur AI", page_icon="🎓", layout="wide")
navigation = st.navigation([
    st.Page("pages/1_Chatbot.py", title="Chatbot", icon="💬", default=True),
    st.Page("pages/2_Testing_Diagnostics.py", title="Testing & Diagnostics", icon="🔎"),
])
navigation.run()
