import os
import logging
from typing import Optional, Dict, List

import streamlit as st
import pandas as pd
from streamlit.components.v1 import html
from dotenv import load_dotenv, find_dotenv

from aim.emailer.base import Email, Advert, TopImage
from aim.news.models import NewsStory

# Constants
TITLE = "News Email"
NEWS_SITES = ["BE", "JEP"]
SESSION_KEYS = ["global_email", "logged_in"]

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Configuration class for secrets and constants
class Config:
    """Handles loading and storing configuration settings."""
    def __init__(self):
        self.streamlit_user: Optional[str] = None
        self.streamlit_password: Optional[str] = None
        self.load_secrets()

    def load_secrets(self) -> None:
        """Load secrets from .env or Streamlit secrets."""
        try:
            load_dotenv(find_dotenv())
            self.streamlit_user = os.getenv("STREAMLIT_USER")
            self.streamlit_password = os.getenv("STREAMLIT_PASSWORD")
            if self.streamlit_user and self.streamlit_password:
                logger.debug("Secrets loaded from .env file")
            else:
                raise ValueError("Missing credentials in .env")
        except Exception:
            try:
                self.streamlit_user = st.secrets["STREAMLIT_USER"]
                self.streamlit_password = st.secrets["STREAMLIT_PASSWORD"]
                logger.debug("Secrets loaded from Streamlit Secrets")
            except Exception as e:
                logger.error(f"Failed to load secrets: {e}")
                raise RuntimeError("Could not load authentication credentials") from e

# Email Manager class to encapsulate email-related logic
class EmailManager:
    """Manages the Email instance and its data interactions with Streamlit."""
    def __init__(self, template_name: str = "be_template.html"):
        self.email = Email(template_name=template_name)

    def get_email(self) -> Email:
        """Retrieve the Email instance."""
        return self.email

    def update_data_from_session(self) -> None:
        """Update email data from Streamlit session state."""
        try:
            for key in self.email.data.keys():
                if key in st.session_state:
                    value = st.session_state[key]
                    if isinstance(value, pd.DataFrame):
                        value = value.to_dict(orient="records")
                    self.email.update_data(key, value)
        except Exception as e:
            logger.error(f"Error updating email data: {e}")
            st.error("Failed to update email data. Check logs for details.")

    def render_data_editor(self, key: str):
        """Render a data editor for the specified key with robust error handling."""
        columns = list(NewsStory.__annotations__.keys())
        data = self.email.data.get(key, [])
        
        try:
            if not data:
                df = pd.DataFrame(columns=columns)
            else:
                if isinstance(data, dict):
                    data = [data]  # Handle single dict case
                
                # Normalize data to match expected columns
                normalized_data = []
                for item in data:
                    # Ensure item is a dict and only include expected columns
                    if not isinstance(item, dict):
                        logger.warning(f"Unexpected data type in {key}: {type(item)}")
                        continue
                    # Create a new dict with only the expected columns, filling missing ones with None
                    normalized_item = {col: item.get(col, None) for col in columns}
                    normalized_data.append(normalized_item)
                
                df = pd.DataFrame(normalized_data, columns=columns)
                
                if "order" in df.columns:
                    # Handle potential non-numeric order values
                    df["order"] = pd.to_numeric(df["order"], errors="coerce").fillna(0)
                    df.sort_values("order", inplace=True)
                    df = df[["order"] + [col for col in columns if col != "order"]]
        except Exception as e:
            logger.error(f"Error creating DataFrame for {key}: {e}")
            df = pd.DataFrame(columns=columns)  # Fallback to empty DataFrame

        return st.data_editor(
            df,
            key=key,
            num_rows="dynamic",
            use_container_width=True,
            on_change=self.update_data_from_session,
        )

# Main application logic
def main():
    """Main entry point for the Streamlit application."""
    # Initialize session state
    for key in SESSION_KEYS:
        if key not in st.session_state:
            st.session_state[key] = False if key == "logged_in" else EmailManager()

    config = Config()
    email_manager: EmailManager = st.session_state["global_email"]

    # Login handling
    if not st.session_state["logged_in"]:
        st.title(TITLE)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == config.streamlit_user and password == config.streamlit_password:
                st.session_state["logged_in"] = True
                st.success("Logged in.")
                st.rerun()
            else:
                st.error("Invalid username or password")
        return

    # Main UI
    st.title(TITLE)

    # Email parameters
    num_stories = st.number_input("Number of News Stories", min_value=1, max_value=20, value=7, step=1)
    num_business = st.number_input("Number of Business Stories", min_value=1, max_value=20, value=1, step=1)
    num_sports = st.number_input("Number of Sports Stories", min_value=1, max_value=20, value=1, step=1)

    # Top image inputs
    st.text_input("Top Image URL", key="top_image_url", on_change=email_manager.update_data_from_session)
    st.text_input("Top Image Title", key="top_image_title", on_change=email_manager.update_data_from_session)
    st.text_input("Top Image Author", key="top_image_author", on_change=email_manager.update_data_from_session)

    # Vertical adverts
    st.title("Vertical Adverts")
    st.data_editor(
        pd.DataFrame(email_manager.get_email().data.get("vertical_adverts", []), columns=Advert.__annotations__.keys()),
        key="vertical_adverts",
        num_rows="dynamic",
        use_container_width=True,
        on_change=email_manager.update_data_from_session,
    )

    # Fetch stories
    if st.button("Fetch Stories"):
        with st.spinner("Fetching Stories..."):
            try:
                email_manager.get_email().get_data(num_stories, num_business, num_sports)
                st.success("Stories fetched successfully!")
            except Exception as e:
                logger.error(f"Error fetching stories: {e}")
                st.error("Failed to fetch stories. Check logs for details.")

    # Instructions
    st.info(
        """
        **Story Ordering Instructions:**
        - Stories are displayed in ascending order based on the 'order' column (1,2,3,...).
        - You can reorder stories by changing the numbers in the 'order' column.
        - Stories with order=0 will not appear.
        """
    )

    # Data editors
    for key in ["news_stories", "business_stories", "sport_stories"]:
        email_manager.render_data_editor(key)

    # Render email
    if st.button("Render Email"):
        try:
            rendered_html = email_manager.get_email().render()
            html(rendered_html, height=800, scrolling=True)
            if st.download_button("Save Email", rendered_html, file_name="email.html", mime="text/html"):
                st.success("Email saved successfully")
        except Exception as e:
            logger.error(f"Error rendering email: {e}")
            st.error("Failed to render email. Check logs for details.")

if __name__ == "__main__":
    main()