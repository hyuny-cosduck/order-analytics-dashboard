# Brand Management - handles brand CRUD operations and authentication

import json
import os
import secrets
import string
from typing import Optional, Dict, Tuple
import config
import sheets_manager


def _load_brands() -> Dict:
    """Load brands from Google Sheet (persistent storage)."""
    return sheets_manager.load_brands_from_sheet()


def _save_brands(brands: Dict) -> None:
    """Save brands to Google Sheet (persistent storage)."""
    sheets_manager.save_brands_to_sheet(brands)


def generate_password(brand_name: str = "") -> str:
    """Generate a password: brandname + special char + 2 digits."""
    brand_part = brand_name.lower() if brand_name else "brand"
    random_nums = ''.join(secrets.choice(string.digits) for _ in range(2))

    password = brand_part + secrets.choice('#$@!') + random_nums
    return password


def get_all_brands() -> Dict:
    """Get all brands."""
    return _load_brands()


def get_brand(brand_name: str) -> Optional[Dict]:
    """Get a specific brand by name (case-insensitive)."""
    brands = _load_brands()
    brand_lower = brand_name.lower()
    for name, data in brands.items():
        if name.lower() == brand_lower:
            return {**data, 'name': name}
    return None


def authenticate_brand(brand_name: str, password: str) -> Optional[Dict]:
    """
    Authenticate a brand login.
    Returns brand data if successful, None otherwise.
    """
    brand = get_brand(brand_name)
    if brand and brand.get('password') == password:
        return brand
    return None


def authenticate_admin(password: str) -> bool:
    """Authenticate admin login (password only)."""
    return password == config.ADMIN_PASSWORD


def add_brand(brand_name: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Add a new brand - creates Google Sheet and stores credentials.
    Returns (brand_data, error_message).
    """
    brands = _load_brands()

    # Check if brand already exists
    if any(name.lower() == brand_name.lower() for name in brands.keys()):
        return None, f"Brand '{brand_name}' already exists"

    # Create Google Sheet for the brand
    try:
        sheet_id, sheet_url = sheets_manager.create_brand_sheet(brand_name)
    except Exception as e:
        return None, f"Failed to create sheet: {str(e)}"

    # Generate password with brand name
    password = generate_password(brand_name)

    # Store brand data
    brand_data = {
        'sheet_id': sheet_id,
        'sheet_url': sheet_url,
        'password': password
    }

    brands[brand_name] = brand_data
    _save_brands(brands)

    return {**brand_data, 'name': brand_name}, None


def update_brand_password(brand_name: str, new_password: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Update/reset a brand's password.
    If new_password is None, generates a new one.
    Returns (new_password, error_message).
    """
    brands = _load_brands()

    # Find brand (case-insensitive)
    actual_name = None
    for name in brands.keys():
        if name.lower() == brand_name.lower():
            actual_name = name
            break

    if actual_name is None:
        return None, f"Brand '{brand_name}' not found"

    if new_password is None:
        new_password = generate_password(actual_name)

    brands[actual_name]['password'] = new_password
    _save_brands(brands)

    return new_password, None


def delete_brand(brand_name: str, delete_sheet: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Delete a brand.
    Optionally deletes the Google Sheet as well.
    Returns (success, error_message).
    """
    brands = _load_brands()

    # Find brand (case-insensitive)
    actual_name = None
    for name in brands.keys():
        if name.lower() == brand_name.lower():
            actual_name = name
            break

    if actual_name is None:
        return False, f"Brand '{brand_name}' not found"

    # Optionally delete the sheet
    if delete_sheet:
        sheet_id = brands[actual_name].get('sheet_id')
        if sheet_id:
            success, error = sheets_manager.delete_sheet(sheet_id)
            if not success:
                return False, f"Failed to delete sheet: {error}"

    # Remove from brands
    del brands[actual_name]
    _save_brands(brands)

    return True, None


def import_existing_sheet(brand_name: str, sheet_id: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Import an existing Google Sheet for a brand.
    Returns (brand_data, error_message).
    """
    brands = _load_brands()

    # Check if brand already exists
    if any(name.lower() == brand_name.lower() for name in brands.keys()):
        return None, f"Brand '{brand_name}' already exists"

    # Verify the sheet exists and is accessible
    spreadsheet = sheets_manager.get_sheet_by_id(sheet_id)
    if spreadsheet is None:
        return None, "Sheet not found or not accessible. Make sure it's shared with the service account."

    # Generate password with brand name
    password = generate_password(brand_name)

    # Store brand data
    brand_data = {
        'sheet_id': sheet_id,
        'sheet_url': f"https://docs.google.com/spreadsheets/d/{sheet_id}",
        'password': password
    }

    brands[brand_name] = brand_data
    _save_brands(brands)

    return {**brand_data, 'name': brand_name}, None


def migrate_from_json_file() -> Tuple[int, Optional[str]]:
    """
    Migrate brands from the local JSON file to Google Sheet storage.
    This is a one-time migration for existing local setups.
    Returns (brands_migrated, error_message).
    """
    # Check if JSON file exists
    if not os.path.exists(config.BRANDS_FILE):
        return 0, None

    # Load brands from JSON file
    try:
        with open(config.BRANDS_FILE, 'r') as f:
            json_brands = json.load(f)
    except Exception as e:
        return 0, f"Failed to read JSON file: {str(e)}"

    if not json_brands:
        return 0, None

    # Load existing brands from sheet
    sheet_brands = _load_brands()

    # Merge - only add brands that don't already exist in sheet
    brands_added = 0
    for name, data in json_brands.items():
        if not any(n.lower() == name.lower() for n in sheet_brands.keys()):
            sheet_brands[name] = data
            brands_added += 1

    # Save merged brands to sheet
    if brands_added > 0:
        _save_brands(sheet_brands)

    return brands_added, None
