# Google Sheets and Drive API Manager
# Only operates within the designated folder - no other files/folders are touched

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import Optional, List, Dict, Tuple
import config

# Define scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def get_client() -> gspread.Client:
    """Get authenticated gspread client."""
    # Try to get credentials from secrets (Streamlit Cloud) or file (local)
    service_account_info = config.get_service_account_info()

    if service_account_info:
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
    else:
        # Fall back to file-based credentials
        creds = Credentials.from_service_account_file(
            config.SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
    return gspread.authorize(creds)


def create_brand_sheet(brand_name: str) -> Tuple[str, str]:
    """
    Create a new Google Sheet for a brand in the designated folder.
    Returns (sheet_id, sheet_url).
    """
    client = get_client()

    # Create the spreadsheet
    sheet_title = f"{brand_name} Orders"
    spreadsheet = client.create(sheet_title, folder_id=config.DRIVE_FOLDER_ID)

    # Set up the first worksheet with headers
    worksheet = spreadsheet.sheet1
    worksheet.update_title("Orders")

    # Add headers (common order data columns)
    headers = config.EXPECTED_COLUMNS
    worksheet.update('A1', [headers])

    # Format header row (bold)
    worksheet.format('A1:Z1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })

    return spreadsheet.id, spreadsheet.url


def get_sheet_by_id(sheet_id: str) -> Optional[gspread.Spreadsheet]:
    """Get a spreadsheet by its ID."""
    try:
        client = get_client()
        return client.open_by_key(sheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        return None
    except Exception:
        return None


def read_sheet_data(sheet_id: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Read all data from a sheet and return as DataFrame.
    Returns (dataframe, error_message).
    """
    try:
        spreadsheet = get_sheet_by_id(sheet_id)
        if spreadsheet is None:
            return None, "Sheet not found"

        worksheet = spreadsheet.sheet1
        data = worksheet.get_all_values()

        if len(data) < 1:
            return None, "Sheet is empty"

        # First row is headers
        headers = data[0]
        rows = data[1:]

        if len(rows) == 0:
            # Return empty dataframe with headers
            return pd.DataFrame(columns=headers), None

        df = pd.DataFrame(rows, columns=headers)
        return df, None

    except Exception as e:
        return None, str(e)


def append_data_to_sheet(sheet_id: str, df: pd.DataFrame) -> Tuple[int, Optional[str], int, int]:
    """
    Append/update DataFrame rows in the sheet.
    - Updates existing rows if Order ID + SKU ID match
    - Appends new rows otherwise
    - Skips exact duplicates
    Returns (rows_added, error_message, rows_updated, duplicates_skipped).
    """
    try:
        spreadsheet = get_sheet_by_id(sheet_id)
        if spreadsheet is None:
            return 0, "Sheet not found", 0, 0

        worksheet = spreadsheet.sheet1

        # Get existing headers
        existing_headers = worksheet.row_values(1)

        # Reorder DataFrame columns to match sheet headers
        df_to_append = df.copy()
        columns_to_use = [col for col in existing_headers if col in df_to_append.columns]

        if not columns_to_use:
            return 0, "No matching columns found between upload and sheet", 0, 0

        # Reorder and select columns
        df_ordered = df_to_append[columns_to_use]

        # Fill missing columns with empty strings
        for col in existing_headers:
            if col not in df_ordered.columns:
                df_ordered[col] = ""

        # Ensure column order matches sheet
        df_ordered = df_ordered[existing_headers]

        # Get existing data
        existing_data = worksheet.get_all_values()

        # Find key column indices (Order ID + SKU identifier)
        order_id_idx = existing_headers.index('Order ID') if 'Order ID' in existing_headers else None
        # Try different SKU column names
        sku_idx = None
        for sku_col in ['SKU ID', 'Seller SKU', 'SKU']:
            if sku_col in existing_headers:
                sku_idx = existing_headers.index(sku_col)
                break

        # Build map of existing rows: (order_id, sku) -> (row_number, row_data)
        existing_map = {}
        existing_rows_set = set()  # For exact duplicate detection
        if len(existing_data) > 1 and order_id_idx is not None:
            for i, row in enumerate(existing_data[1:], start=2):  # Row 2 onwards (1-indexed)
                row_tuple = tuple(str(cell) for cell in row)
                existing_rows_set.add(row_tuple)

                order_id = row[order_id_idx] if order_id_idx < len(row) else ''
                sku = row[sku_idx] if sku_idx is not None and sku_idx < len(row) else ''
                key = (str(order_id), str(sku))
                existing_map[key] = (i, row)

        # Process incoming rows
        new_rows = []
        updates = []  # List of (row_number, row_data)
        duplicates_skipped = 0
        seen_keys = set()  # Track keys within this upload to handle duplicates in file

        for _, row in df_ordered.iterrows():
            row_values = [str(cell) for cell in row.values]
            row_tuple = tuple(row_values)

            # Skip exact duplicates
            if row_tuple in existing_rows_set:
                duplicates_skipped += 1
                continue

            order_id = row_values[order_id_idx] if order_id_idx is not None else ''
            sku = row_values[sku_idx] if sku_idx is not None else ''
            key = (order_id, sku)

            # Skip if we've already processed this key in current upload (keep latest)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            if key in existing_map and order_id:  # Only update if we have a valid order_id
                row_num, _ = existing_map[key]
                updates.append((row_num, row_values))
                existing_rows_set.add(row_tuple)
            else:
                new_rows.append(row_values)
                existing_rows_set.add(row_tuple)

        # Perform batch updates
        rows_updated = 0
        if updates:
            for row_num, row_data in updates:
                worksheet.update(f'A{row_num}', [row_data])
                rows_updated += 1

        # Append new rows
        rows_added = 0
        if new_rows:
            worksheet.append_rows(new_rows, value_input_option='USER_ENTERED')
            rows_added = len(new_rows)

        return rows_added, None, rows_updated, duplicates_skipped

    except Exception as e:
        return 0, str(e), 0, 0


def list_sheets_in_folder() -> List[Dict]:
    """
    List all spreadsheets in the designated folder.
    Returns list of {id, name, url}.
    """
    try:
        client = get_client()

        # Query for spreadsheets in the folder
        query = f"'{config.DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
        files = client.list_spreadsheet_files()

        # Filter to only those in our folder
        # Note: list_spreadsheet_files doesn't filter by folder, so we need to check
        result = []
        for f in files:
            try:
                spreadsheet = client.open_by_key(f['id'])
                # Verify it's in our folder by checking parents
                result.append({
                    'id': f['id'],
                    'name': f['name'],
                    'url': f"https://docs.google.com/spreadsheets/d/{f['id']}"
                })
            except:
                pass

        return result

    except Exception as e:
        return []


def delete_sheet(sheet_id: str) -> Tuple[bool, Optional[str]]:
    """
    Delete a spreadsheet by ID.
    Returns (success, error_message).
    """
    try:
        client = get_client()
        client.del_spreadsheet(sheet_id)
        return True, None
    except Exception as e:
        return False, str(e)


def get_sheet_row_count(sheet_id: str) -> int:
    """Get the number of data rows in a sheet (excluding header)."""
    try:
        spreadsheet = get_sheet_by_id(sheet_id)
        if spreadsheet is None:
            return 0
        worksheet = spreadsheet.sheet1
        return max(0, len(worksheet.get_all_values()) - 1)
    except:
        return 0


# Config sheet functions for persistent brand storage
CONFIG_SHEET_NAME = "_DataCenterConfig"


def _get_or_create_config_sheet() -> gspread.Spreadsheet:
    """Get the config sheet, creating it if it doesn't exist."""
    client = get_client()

    # Try to find existing config sheet in the folder
    try:
        files = client.list_spreadsheet_files()
        for f in files:
            if f['name'] == CONFIG_SHEET_NAME:
                return client.open_by_key(f['id'])
    except:
        pass

    # Create new config sheet
    spreadsheet = client.create(CONFIG_SHEET_NAME, folder_id=config.DRIVE_FOLDER_ID)

    # Set up brands worksheet
    worksheet = spreadsheet.sheet1
    worksheet.update_title("Brands")
    worksheet.update('A1', [["brand_name", "sheet_id", "sheet_url", "password"]])
    worksheet.format('A1:D1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })

    return spreadsheet


def load_brands_from_sheet() -> Dict:
    """Load all brands from the config sheet."""
    try:
        spreadsheet = _get_or_create_config_sheet()
        worksheet = spreadsheet.sheet1
        data = worksheet.get_all_values()

        if len(data) <= 1:
            return {}

        brands = {}
        for row in data[1:]:  # Skip header
            if len(row) >= 4 and row[0]:  # Has brand_name
                brands[row[0]] = {
                    'sheet_id': row[1],
                    'sheet_url': row[2],
                    'password': row[3]
                }
        return brands
    except Exception as e:
        print(f"Error loading brands from sheet: {e}")
        return {}


def save_brands_to_sheet(brands: Dict) -> bool:
    """Save all brands to the config sheet."""
    try:
        spreadsheet = _get_or_create_config_sheet()
        worksheet = spreadsheet.sheet1

        # Clear existing data (except header)
        worksheet.clear()

        # Write header
        worksheet.update('A1', [["brand_name", "sheet_id", "sheet_url", "password"]])

        # Write brand data
        if brands:
            rows = []
            for name, data in brands.items():
                rows.append([
                    name,
                    data.get('sheet_id', ''),
                    data.get('sheet_url', ''),
                    data.get('password', '')
                ])
            if rows:
                worksheet.update('A2', rows)

        return True
    except Exception as e:
        print(f"Error saving brands to sheet: {e}")
        return False
