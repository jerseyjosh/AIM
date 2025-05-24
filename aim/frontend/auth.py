"""UNUSED CODE"""

import os
import logging
import streamlit as st

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

def login():
    """
    If user is not logged in, display the login form.
    If credentials match, set session_state to True and rerun.
    Returns a boolean indicating whether the user is logged in.
    """

    # Attempt to load credentials just once, or use st.secrets
    # (You can keep your dotenv logic here too if you like)
    STREAMLIT_USER = os.getenv("STREAMLIT_USER") or st.secrets.get("STREAMLIT_USER", "")
    STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD") or st.secrets.get("STREAMLIT_PASSWORD", "")

    # Initialize session_state for login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.subheader("Please log in")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if username == STREAMLIT_USER and password == STREAMLIT_PASSWORD:
                st.session_state.logged_in = True
                st.success("Logged in successfully.")
                # Force a rerun so that the rest of your page can load
                st.rerun()
            else:
                st.error("Invalid username or password.")

        # User not logged in yet, so return False
        return False

    # If we reach here, it means user is already logged in
    return True
