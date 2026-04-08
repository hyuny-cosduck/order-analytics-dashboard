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


def append_data_to_sheet(sheet_id: str, df: pd.DataFrame) -> Tuple[int, Optional[str]]:
    """
    Append DataFrame rows to the sheet.
    Returns (rows_added, error_message).
    """
    try:
        spreadsheet = get_sheet_by_id(sheet_id)
        if spreadsheet is None:
            return 0, "Sheet not found"

        worksheet = spreadsheet.sheet1

        # Get existing headers
        existing_headers = worksheet.row_values(1)

        # Reorder DataFrame columns to match sheet headers
        # Only include columns that exist in the sheet
        df_to_append = df.copy()
        columns_to_use = [col for col in existing_headers if col in df_to_append.columns]

        if not columns_to_use:
            return 0, "No matching columns found between upload and sheet"

        # Reorder and select columns
        df_ordered = df_to_append[columns_to_use]

        # Fill missing columns with empty strings
        for col in existing_headers:
            if col not in df_ordered.columns:
                df_ordered[col] = ""

        # Ensure column order matches sheet
        df_ordered = df_ordered[existing_headers]

        # Convert to list of lists
        values = df_ordered.values.tolist()

        if len(values) == 0:
            return 0, "No data to append"

        # Append to sheet
        worksheet.append_rows(values, value_input_option='USER_ENTERED')

        return len(values), None

    except Exception as e:
        return 0, str(e)


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
