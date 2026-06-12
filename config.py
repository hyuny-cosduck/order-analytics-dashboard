# Configuration settings for Order Analytics Dashboard

import os
import json
import streamlit as st

# Check if running on Streamlit Cloud (secrets available)
def _get_secret(key: str, default: str = None):
    """Get secret from Streamlit secrets, env vars, or return default."""
    # 1. Streamlit secrets (Streamlit Cloud)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # 2. Environment variables (Railway / other platforms)
    env_val = os.environ.get(key)
    if env_val:
        return env_val
    return default

# Google Cloud Settings
# For local development: use JSON file
# For deployed environments: use secrets / env vars
SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(__file__),
    "data-center-dashboard-3266303edecc.json"
)

def get_service_account_info():
    """Get service account credentials from secrets, env var, or file."""
    # 1. Streamlit secrets (Streamlit Cloud)
    try:
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass

    # 2. Environment variable as JSON string (Railway / other platforms)
    env_sa = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if env_sa:
        return json.loads(env_sa)

    # 3. Fall back to local file (development)
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            return json.load(f)

    return None

# Folder where all brand sheets are stored
# Only this folder will be accessed - no other files/folders will be touched
DRIVE_FOLDER_ID = _get_secret("DRIVE_FOLDER_ID", "1RjrHjI7ZRWmRQHJU6cWZbfgy7Z0G8Rv7")

# Admin credentials (password only) - MUST be set via env var or secrets in production
ADMIN_PASSWORD = _get_secret("ADMIN_PASSWORD")

# Config sheet ID — the single _DataCenterConfig sheet that stores brand data.
CONFIG_SHEET_ID = _get_secret("CONFIG_SHEET_ID", "1F_zmxbIkIEBAEA8Nw09_KydXp7DQXgeyhOmtET1z_n0")

# Brand passwords will be stored in a brands.json file managed by the app
BRANDS_FILE = os.path.join(os.path.dirname(__file__), "brands.json")

# Sheet structure - columns expected in order data
EXPECTED_COLUMNS = [
    "Order ID", "Order Status", "Order Substatus", "Order Amount",
    "Created Time", "Seller SKU", "Product Name", "Quantity",
    "Payment Method", "Tracking ID", "Cancel By", "Cancel Reason",
    "Warehouse Name", "Fulfillment Type", "Shipping Provider Name"
]
