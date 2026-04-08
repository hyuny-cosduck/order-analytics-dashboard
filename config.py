# Configuration settings for Order Analytics Dashboard

import os
import streamlit as st

# Check if running on Streamlit Cloud (secrets available)
def _get_secret(key: str, default: str = None):
    """Get secret from Streamlit secrets or return default."""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

# Google Cloud Settings
# For local development: use JSON file
# For Streamlit Cloud: use secrets
SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(__file__),
    "data-center-dashboard-3266303edecc.json"
)

# Service account info (for Streamlit Cloud deployment)
def get_service_account_info():
    """Get service account credentials from secrets or file."""
    try:
        # Try Streamlit secrets first
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass

    # Fall back to file
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        import json
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            return json.load(f)

    return None

# Folder where all brand sheets are stored
# Only this folder will be accessed - no other files/folders will be touched
DRIVE_FOLDER_ID = _get_secret("DRIVE_FOLDER_ID", "1RjrHjI7ZRWmRQHJU6cWZbfgy7Z0G8Rv7")

# Admin credentials (password only) - use secrets in production
ADMIN_PASSWORD = _get_secret("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", "phozphoz1!"))

# Brand passwords will be stored in a brands.json file managed by the app
BRANDS_FILE = os.path.join(os.path.dirname(__file__), "brands.json")

# Sheet structure - columns expected in order data
EXPECTED_COLUMNS = [
    "Order ID", "Order Status", "Order Substatus", "Order Amount",
    "Created Time", "Seller SKU", "Product Name", "Quantity",
    "Payment Method", "Tracking ID", "Cancel By", "Cancel Reason",
    "Warehouse Name", "Fulfillment Type", "Shipping Provider Name"
]
