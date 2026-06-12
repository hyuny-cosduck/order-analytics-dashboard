import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import calendar

# Import custom modules
import config
import brands_manager
import sheets_manager

st.set_page_config(
    page_title="Order Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)


@st.cache_data(ttl=300, show_spinner=False)
def load_sheet_data(sheet_id: str):
    """Shared cached loader — both Dashboard and Bundle Analysis tabs reuse one cache entry."""
    df, error = sheets_manager.read_sheet_data(sheet_id)
    if df is not None:
        # Replace string 'nan' with 'N/A' for display
        str_cols = df.select_dtypes(include='object').columns
        df[str_cols] = df[str_cols].fillna('N/A').replace('nan', 'N/A')
    return df, error


def parse_created_time(series: pd.Series) -> pd.Series:
    # TikTok Shop exports use two different locale formats:
    # '31/12/2025 22:55:42' (DD/MM/YYYY, 24h) and '03/31/2026 8:12:46 PM' (MM/DD/YYYY, 12h).
    s = series.astype(str).str.strip()
    dt = pd.to_datetime(s, format='%d/%m/%Y %H:%M:%S', errors='coerce')
    mask = dt.isna() & s.notna() & (s != '') & (s.str.lower() != 'nan')
    if mask.any():
        fallback = pd.to_datetime(s[mask], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
        dt.loc[mask] = fallback
    return dt


CURRENCY_OPTIONS = ["Rp", "USD", "KRW"]


def fmt_money(value, currency="Rp"):
    """Format a monetary value with the given currency label."""
    if pd.isna(value):
        return "-"
    return f"{currency} {value:,.0f}"


# ===== Session State Initialization =====
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'brand_name' not in st.session_state:
    st.session_state.brand_name = None
if 'brand_data' not in st.session_state:
    st.session_state.brand_data = None

# ===== One-time migration from JSON file to Google Sheet =====
if 'migration_done' not in st.session_state:
    brands_manager.migrate_from_json_file()
    st.session_state.migration_done = True


def logout():
    """Clear session and logout."""
    st.session_state.authenticated = False
    st.session_state.is_admin = False
    st.session_state.brand_name = None
    st.session_state.brand_data = None
    st.rerun()


# ===== CHECK ADMIN ROUTE =====
def is_admin_route():
    """Check if accessing via admin route (?admin=true)"""
    try:
        admin_param = st.query_params.get("admin", "")
        # Handle both string and list returns
        if isinstance(admin_param, list):
            return "true" in admin_param
        return admin_param == "true"
    except Exception:
        return False


# ===== GLOBAL STYLES (applies to all pages) =====
def _inject_global_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp { background: #f4f4f8 !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    .stMainBlockContainer { padding-top: 2rem !important; }

    /* Typography — compact like Agency Bot */
    h1 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; color: #1e1e2e !important; font-size: 1.2rem !important; }
    h2 { font-family: 'Inter', sans-serif !important; font-weight: 600 !important; color: #1e1e2e !important; font-size: 0.95rem !important; }
    h3 { font-family: 'Inter', sans-serif !important; font-weight: 600 !important; color: #1e1e2e !important; font-size: 0.85rem !important; }
    p, li { font-size: 0.875rem !important; }

    /* Inputs */
    .stTextInput > label, .stSelectbox > label, .stDateInput label, .stFileUploader > label {
        font-weight: 500 !important; font-size: 0.8rem !important; color: #64648c !important;
    }
    .stTextInput > div > div > input {
        border: 1px solid #e2e2ea !important; border-radius: 8px !important;
        padding: 0.7rem 0.85rem !important; font-size: 0.9rem !important;
        background: white !important; color: #1e1e2e !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
    }
    .stTextInput > div > div > input::placeholder { color: #b0b0c0 !important; }
    .stSelectbox > div > div { color: #1e1e2e !important; }
    .stSelectbox [data-baseweb="select"] > div { background: white !important; border: 1px solid #e2e2ea !important; border-radius: 8px !important; }
    .stDateInput > div > div > input { background: white !important; border: 1px solid #e2e2ea !important; border-radius: 8px !important; color: #1e1e2e !important; font-weight: 500 !important; }
    .stDateInput [data-baseweb="input"] { background: white !important; border: 1px solid #e2e2ea !important; border-radius: 8px !important; }
    .stDateInput [data-baseweb="input"] div { color: #1e1e2e !important; font-weight: 500 !important; }

    /* Buttons — compact */
    .stButton > button, .stFormSubmitButton > button {
        border-radius: 8px !important; font-weight: 500 !important; font-size: 0.8rem !important;
        font-family: 'Inter', sans-serif !important; padding: 0.4rem 0.9rem !important;
    }
    .stButton > button[data-testid="stBaseButton-primary"],
    .stFormSubmitButton > button {
        background: #6366f1 !important; color: white !important; border: none !important;
    }
    .stButton > button[data-testid="stBaseButton-primary"]:hover,
    .stFormSubmitButton > button:hover { background: #4f46e5 !important; }
    .stButton > button[data-testid="stBaseButton-secondary"] {
        background: white !important; color: #1e1e2e !important;
        border: 1px solid #e2e2ea !important;
    }
    .stButton > button[data-testid="stBaseButton-secondary"]:hover {
        background: #eeeef6 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0; border-bottom: 1px solid #e2e2ea;
        background: white; border-radius: 12px 12px 0 0;
        padding: 0 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important; font-weight: 500 !important;
        color: #64648c !important; padding: 0.75rem 1.2rem !important;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #6366f1 !important; border-bottom: 2px solid #6366f1 !important;
    }

    /* Metric cards — compact */
    [data-testid="stMetric"] {
        background: white; border-radius: 10px; padding: 0.75rem 1rem;
        border: 1px solid #e2e2ea;
    }
    [data-testid="stMetric"] label { color: #64648c !important; font-size: 0.7rem !important; font-weight: 500 !important; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #1e1e2e !important; font-weight: 700 !important; font-size: 1.1rem !important; }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

    /* Expanders — compact */
    .streamlit-expanderHeader {
        font-weight: 500 !important; font-size: 0.8rem !important;
        font-family: 'Inter', sans-serif !important;
        background: white !important; border-radius: 8px !important;
        padding: 0.5rem 0.75rem !important;
    }
    details { border: 1px solid #e2e2ea !important; border-radius: 8px !important; }

    /* Alerts — compact */
    .stAlert { border-radius: 8px !important; font-family: 'Inter', sans-serif !important; font-size: 0.8rem !important; padding: 0.6rem 1rem !important; }

    /* DataFrames */
    [data-testid="stDataFrame"] { border-radius: 8px !important; overflow: hidden; }

    /* Plotly charts */
    [data-testid="stPlotlyChart"] {
        background: white; border-radius: 12px; padding: 0.5rem;
        border: 1px solid #e2e2ea; overflow-x: auto;
    }
    [data-testid="stPlotlyChart"] .js-plotly-plot { width: 100% !important; }
    [data-testid="stPlotlyChart"] .plotly { width: 100% !important; }

    /* Hide anchor links */
    a.stHeaderLink, h1 a, h2 a { display: none !important; }

    /* Dividers */
    hr { border-color: #e2e2ea !important; }

    /* Equal height columns */
    [data-testid="stHorizontalBlock"] { align-items: stretch !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div { height: 100%; }

    /* Forms */
    [data-testid="stForm"] {
        border: 1px solid #e2e2ea !important; padding: 1.5rem !important;
        background: white !important; border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }

    /* Caption / footer text */
    .stCaption, [data-testid="stCaption"] { color: #8888a0 !important; font-family: 'Inter', sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)


# ===== BRAND LOGIN PAGE =====
def show_brand_login_page():
    _inject_global_styles()
    # Extra login-page padding
    st.markdown("<style>.stMainBlockContainer { padding-top: 0 !important; }</style>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.3, 1.4, 1.3])

    with col2:
        st.markdown("<div style='height: 10vh'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <p style="font-family: 'Inter', sans-serif; font-weight: 500; font-size: 0.75rem;
                      letter-spacing: 0.15em; text-transform: uppercase; color: #8888a0;
                      margin: 0 0 0.75rem 0;">Cosduck</p>
            <h2 style="font-family: 'Inter', sans-serif; font-weight: 600;
                       font-size: 1.35rem; color: #1e1e2e; margin: 0 0 0.3rem 0;">
                Orders Dashboard
            </h2>
            <p style="font-family: 'Inter', sans-serif; font-weight: 400;
                      font-size: 0.85rem; color: #8888a0; margin: 0;">
                브랜드 비밀번호는 담당 AM에게 문의해주세요
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("brand_login_form"):
            brand_name = st.text_input("브랜드명", placeholder="브랜드명을 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

        if submitted:
            if brand_name and password:
                if brands_manager.is_brand_rate_limited(brand_name):
                    st.error("로그인 시도 횟수를 초과했습니다. 잠시 후 다시 시도하세요.")
                else:
                    brand_data = brands_manager.authenticate_brand(brand_name, password)
                    if brand_data:
                        st.session_state.authenticated = True
                        st.session_state.is_admin = False
                        st.session_state.brand_name = brand_data['name']
                        st.session_state.brand_data = brand_data
                        st.rerun()
                    else:
                        st.error("브랜드명 또는 비밀번호가 올바르지 않습니다")
            else:
                st.warning("브랜드명과 비밀번호를 입력하세요")



# ===== ADMIN LOGIN PAGE =====
def show_admin_login_page():
    _inject_global_styles()
    st.markdown("<style>.stMainBlockContainer { padding-top: 0 !important; }</style>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.3, 1.4, 1.3])

    with col2:
        st.markdown("<div style='height: 10vh'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="font-family: 'Inter', sans-serif; font-weight: 600;
                       font-size: 1.35rem; color: #1e1e2e; margin: 0 0 0.3rem 0;">
                관리자
            </h2>
            <p style="font-family: 'Inter', sans-serif; font-weight: 400;
                      font-size: 0.85rem; color: #8888a0; margin: 0;">
                비밀번호를 입력하세요
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("admin_login_form"):
            password = st.text_input("비밀번호", type="password", placeholder="관리자 비밀번호를 입력하세요")
            st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

        if submitted:
            if password:
                if brands_manager.is_admin_rate_limited():
                    st.error("로그인 시도 횟수를 초과했습니다. 잠시 후 다시 시도하세요.")
                elif brands_manager.authenticate_admin(password):
                    st.session_state.authenticated = True
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다")
            else:
                st.warning("비밀번호를 입력하세요")



# ===== ADMIN PANEL =====
def show_admin_panel():
    _inject_global_styles()

    col1, col2, col3 = st.columns([6, 1, 1])
    with col1:
        st.title("Admin Panel")
    with col2:
        st.markdown("<div style='height: 0.75rem'></div>", unsafe_allow_html=True)
        if st.button("Refresh", type="secondary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col3:
        st.markdown("<div style='height: 0.75rem'></div>", unsafe_allow_html=True)
        if st.button("Logout", type="secondary", use_container_width=True):
            logout()

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 All Brands", "➕ Add Brand", "📥 Import Existing Sheet"])

    # Tab 1: View all brands
    with tab1:
        st.subheader("Registered Brands")

        brands = brands_manager.get_all_brands()

        if not brands:
            st.info("No brands registered yet. Add a brand to get started.")
        else:
            for brand_name, data in brands.items():
                with st.expander(f"**{brand_name}**", expanded=False):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.write(f"**Sheet ID:** `{data.get('sheet_id', 'N/A')}`")
                        pwd = data.get('password', 'N/A')
                        if pwd.startswith('$2b$') or pwd.startswith('$2a$'):
                            st.write("**Password:** (hashed) — click Reset Password to set a new one")
                        else:
                            st.write(f"**Password:** `{pwd}`")
                        if data.get('sheet_url'):
                            st.write(f"[Open Google Sheet]({data.get('sheet_url')})")

                        # Row count — fetch on demand to avoid API quota issues
                        rc_key = f"row_count_{brand_name}"
                        if st.button("Check Row Count", key=f"rc_btn_{brand_name}"):
                            st.session_state[rc_key] = sheets_manager.get_sheet_row_count(data.get('sheet_id', ''))
                        if rc_key in st.session_state:
                            st.write(f"**Data Rows:** {st.session_state[rc_key]:,}")

                    with col2:
                        if st.button("Reset Password", key=f"reset_{brand_name}"):
                            new_pass, error = brands_manager.update_brand_password(brand_name)
                            if error:
                                st.error(error)
                            else:
                                st.success(f"New password: `{new_pass}`")
                                st.rerun()

                        if st.button("Delete Brand", key=f"delete_{brand_name}", type="secondary"):
                            st.session_state[f'confirm_delete_{brand_name}'] = True

                        if st.session_state.get(f'confirm_delete_{brand_name}'):
                            st.warning("Are you sure? This cannot be undone.")
                            delete_sheet = st.checkbox("Also delete Google Sheet", key=f"del_sheet_{brand_name}")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("Yes, Delete", key=f"yes_{brand_name}"):
                                    success, error = brands_manager.delete_brand(brand_name, delete_sheet)
                                    if error:
                                        st.error(error)
                                    else:
                                        st.success(f"Brand '{brand_name}' deleted")
                                        st.session_state[f'confirm_delete_{brand_name}'] = False
                                        st.rerun()
                            with col_no:
                                if st.button("Cancel", key=f"no_{brand_name}"):
                                    st.session_state[f'confirm_delete_{brand_name}'] = False
                                    st.rerun()

    # Tab 2: Add new brand
    with tab2:
        st.subheader("Add New Brand")
        st.caption("This will create a new Google Sheet for the brand automatically.")

        new_brand_name = st.text_input("Brand Name", placeholder="e.g., BEPLAIN")
        new_brand_currency = st.selectbox("Currency", CURRENCY_OPTIONS, index=0, key="new_brand_currency")

        if st.button("Create Brand", type="primary"):
            if new_brand_name:
                with st.spinner("Creating brand and Google Sheet..."):
                    brand_data, error = brands_manager.add_brand(new_brand_name, currency=new_brand_currency)
                    if error:
                        st.error(error)
                    else:
                        st.success(f"Brand '{new_brand_name}' created successfully!")
                        st.info(f"""
                        **Credentials:**
                        - Username: `{new_brand_name}`
                        - Password: `{brand_data['password']}`

                        **Google Sheet:** [Open Sheet]({brand_data['sheet_url']})
                        """)
            else:
                st.warning("Please enter a brand name")

    # Tab 3: Import existing sheet
    with tab3:
        st.subheader("Import Existing Google Sheet")
        st.caption("Link an existing Google Sheet to a new brand.")

        import_brand_name = st.text_input("Brand Name", placeholder="e.g., BEPLAIN", key="import_brand")
        import_sheet_id = st.text_input(
            "Google Sheet ID",
            placeholder="e.g., 1sGARLhKbDMMLm9V4XkSl0xBt9tcCXpZXIM4R8o9F95U",
            help="The ID from the Google Sheet URL: docs.google.com/spreadsheets/d/[SHEET_ID]/edit"
        )
        import_currency = st.selectbox("Currency", CURRENCY_OPTIONS, index=0, key="import_currency")

        if st.button("Import Sheet", type="primary"):
            if import_brand_name and import_sheet_id:
                with st.spinner("Importing sheet..."):
                    brand_data, error = brands_manager.import_existing_sheet(import_brand_name, import_sheet_id, currency=import_currency)
                    if error:
                        st.error(error)
                    else:
                        st.success(f"Brand '{import_brand_name}' imported successfully!")
                        st.info(f"""
                        **Credentials:**
                        - Username: `{import_brand_name}`
                        - Password: `{brand_data['password']}`

                        **Google Sheet:** [Open Sheet]({brand_data['sheet_url']})
                        """)
            else:
                st.warning("Please enter both brand name and sheet ID")


# ===== BRAND DASHBOARD =====
def show_brand_dashboard():
    _inject_global_styles()
    brand_name = st.session_state.brand_name
    brand_data = st.session_state.brand_data
    if not brand_data:
        st.error("세션이 만료되었습니다. 다시 로그인해주세요.")
        st.stop()
    sheet_id = brand_data.get('sheet_id')
    currency = brand_data.get('currency', 'Rp')

    # Preload data count for header
    _df_preview, _err = load_sheet_data(sheet_id)
    if _df_preview is not None and not _err:
        _total = len(_df_preview[_df_preview.get('Order Amount', 0).apply(pd.to_numeric, errors='coerce') > 0]) if 'Order Amount' in _df_preview.columns else len(_df_preview)
        _samples = len(_df_preview[_df_preview.get('Order Amount', 0).apply(pd.to_numeric, errors='coerce') == 0]) if 'Order Amount' in _df_preview.columns else 0
        _data_info = f"{_total:,}행" + (f" · 샘플 {_samples:,}건" if _samples > 0 else "")
    else:
        _data_info = ""

    # Fixed header (title + logout + refresh — pure HTML)
    st.markdown(f"""
    <style>
    .brand-header {{
        position: fixed;
        top: 0; left: 0; right: 0;
        z-index: 999;
        background: white;
        border-bottom: 1px solid #e2e2ea;
        transition: box-shadow 0.2s ease;
    }}
    .brand-header-inner {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.75rem 2rem;
    }}
    .brand-header h1 {{
        font-family: 'Inter', sans-serif; font-weight: 700;
        font-size: 1.15rem; color: #1e1e2e; margin: 0;
    }}
    .brand-header-actions {{ display: flex; align-items: center; gap: 10px; }}
    .brand-header-actions a {{
        padding: 5px 14px; font-size: 0.8rem; font-family: 'Inter', sans-serif;
        color: #1e1e2e; background: white; border: 1px solid #e2e2ea;
        border-radius: 8px; cursor: pointer; text-decoration: none; font-weight: 500;
    }}
    .brand-header-actions a:hover {{ background: #f4f4f8; }}
    .brand-header-actions .data-info {{
        font-size: 0.75rem; color: #8888a0; font-family: 'Inter', sans-serif;
    }}
    .stMainBlockContainer {{ padding-top: 3.5rem !important; }}
    </style>
    <div class="brand-header" id="brand-header">
        <div class="brand-header-inner">
            <h1>{brand_name} Order Analytics</h1>
            <div class="brand-header-actions">
                <span class="data-info">{_data_info}</span>
                <a id="refresh-link">↻ 새로고침</a>
                <a id="logout-link">Logout</a>
            </div>
        </div>
    </div>
    <script>
    (function() {{
        const bh = document.getElementById('brand-header');
        if (bh) {{
            window.addEventListener('scroll', () => {{
                bh.style.boxShadow = window.scrollY > 4
                    ? '0 4px 12px rgba(0,0,0,0.06)' : 'none';
            }}, {{ passive: true }});
        }}
        document.getElementById('logout-link')?.addEventListener('click', () => {{
            window.location.search = '?action=logout';
        }});
        document.getElementById('refresh-link')?.addEventListener('click', () => {{
            window.location.search = '?action=refresh';
        }});
    }})();
    </script>
    """, unsafe_allow_html=True)

    # Handle header actions via query params
    _action = st.query_params.get("action", "")
    if _action == "logout":
        st.query_params.clear()
        logout()
    elif _action == "refresh":
        st.query_params.clear()
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            if key.startswith('main_range') or key.startswith('bundle_range') or key.startswith('_confirmed'):
                del st.session_state[key]
        st.rerun()

    # Streamlit native tabs — fully visible and functional
    tab1, tab2, tab3 = st.tabs(["📈 Dashboard", "📦 번들 분석", "📤 Upload Data"])

    with tab1:
        show_dashboard_content(sheet_id, currency)

    with tab2:
        show_bundle_analysis(sheet_id, currency)

    with tab3:
        show_upload_section(sheet_id, brand_name)


def show_bundle_analysis(sheet_id: str, currency: str = "Rp"):
    """번들 SKU별 구매/취소 분석"""
    st.subheader("번들 SKU 분석")
    st.caption("번들 상품을 선택하여 구매/취소 현황을 분석합니다.")

    with st.spinner("데이터를 불러오는 중..."):
        df, error = load_sheet_data(sheet_id)

    if error:
        st.error(f"데이터 로드 실패: {error}")
        return

    if df is None or len(df) == 0:
        st.warning("데이터가 없습니다. Upload 탭에서 데이터를 업로드해주세요.")
        return

    if 'Seller SKU' not in df.columns:
        st.error("'Seller SKU' 컬럼이 없습니다.")
        return

    # Get all unique SKUs with their product names and order counts
    sku_summary = df.groupby('Seller SKU').agg(
        product_name=('Product Name', 'first'),
        order_count=('Order ID', 'count'),
    ).reset_index().sort_values('order_count', ascending=False)

    # Auto-suggest: SKUs containing "BDL", "번들", "Bundle", "SET", "세트" or with quantity > 1 patterns
    bundle_keywords = ['BDL', '번들', 'BUNDLE', 'SET', '세트', 'COMBO', '콤보']
    suggested_skus = sku_summary[
        sku_summary['Seller SKU'].str.upper().apply(
            lambda x: any(kw.upper() in x for kw in bundle_keywords)
        ) |
        sku_summary['product_name'].fillna('').str.upper().apply(
            lambda x: any(kw.upper() in x for kw in bundle_keywords)
        )
    ]['Seller SKU'].tolist()

    # Session state key for selected bundles per sheet
    state_key = f"bundle_skus_{sheet_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = suggested_skus

    # SKU selector
    with st.expander("번들 상품 선택", expanded=len(st.session_state[state_key]) == 0):
        st.caption("번들로 분석할 SKU를 선택하세요. 자동으로 추천된 항목이 선택되어 있습니다.")

        selected_skus = st.multiselect(
            "번들 SKU 선택",
            options=sku_summary['Seller SKU'].tolist(),
            default=st.session_state[state_key],
            format_func=lambda x: f"{x} — {sku_summary[sku_summary['Seller SKU']==x]['product_name'].values[0][:40] if len(sku_summary[sku_summary['Seller SKU']==x]) > 0 else ''} ({sku_summary[sku_summary['Seller SKU']==x]['order_count'].values[0]:,}건)",
            key=f"bundle_multiselect_{sheet_id}",
        )
        st.session_state[state_key] = selected_skus

    if not selected_skus:
        st.info("번들 상품을 선택해주세요.")
        return

    bundle_df = df[df['Seller SKU'].isin(selected_skus)].copy()

    if len(bundle_df) == 0:
        st.info("선택된 번들 상품의 데이터가 없습니다.")
        return

    # Data preprocessing — only convert columns that exist
    for col in ['SKU Unit Original Price', 'Order Amount', 'Quantity']:
        if col in bundle_df.columns:
            bundle_df[col] = pd.to_numeric(bundle_df[col], errors='coerce')
        else:
            bundle_df[col] = 0

    # Exclude samples (Order Amount = 0)
    bundle_df = bundle_df[bundle_df['Order Amount'] > 0].copy()

    if 'Created Time' in bundle_df.columns:
        bundle_df['Created Date'] = parse_created_time(bundle_df['Created Time']).dt.date

    # ===== Date Filter (applied before KPIs so metrics respect selection) =====
    if 'Created Date' in bundle_df.columns:
        st.subheader("📅 기간 선택")
        valid_dates = bundle_df['Created Date'].dropna()
        if len(valid_dates) > 0:
            min_date = pd.to_datetime(valid_dates.min()).date()
            max_date = pd.to_datetime(valid_dates.max()).date()

            # Promote any pending range (set by buttons on the previous run)
            # into the widget key before the widget renders.
            if '_pending_bundle_range' in st.session_state:
                st.session_state['bundle_range'] = st.session_state.pop('_pending_bundle_range')

            bundle_df['Year-Month'] = bundle_df['Created Date'].apply(
                lambda x: x.strftime('%Y-%m') if pd.notna(x) else None
            )
            available_months = sorted(bundle_df['Year-Month'].dropna().unique(), reverse=True)

            col_month, col_range = st.columns([1, 2])
            with col_month:
                month_options = ["전체 기간"] + list(available_months)
                selected_month = st.selectbox(
                    "월 선택", options=month_options, index=0, key="bundle_month"
                )

            if selected_month != "전체 기간":
                year, month = map(int, selected_month.split('-'))
                last_day = calendar.monthrange(year, month)[1]
                default_start = max(pd.Timestamp(year, month, 1).date(), min_date)
                default_end = min(pd.Timestamp(year, month, last_day).date(), max_date)
            else:
                default_start = min_date
                default_end = max_date

            with col_range:
                date_range = st.date_input(
                    "기간",
                    value=(default_start, default_end),
                    min_value=min_date,
                    max_value=max_date,
                    key="bundle_range",
                )

            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = default_start, default_end

            st.write("빠른 선택:")
            q1, q2, q3, q4 = st.columns(4)

            def _queue_bundle_range(start, end):
                st.session_state['_pending_bundle_range'] = (start, end)
                st.rerun()

            with q1:
                if st.button("최근 7일", key="bundle_q7"):
                    _queue_bundle_range(max_date - datetime.timedelta(days=6), max_date)
            with q2:
                if st.button("최근 14일", key="bundle_q14"):
                    _queue_bundle_range(max_date - datetime.timedelta(days=13), max_date)
            with q3:
                if st.button("최근 30일", key="bundle_q30"):
                    _queue_bundle_range(max_date - datetime.timedelta(days=29), max_date)
            with q4:
                if st.button("전체", key="bundle_qall"):
                    _queue_bundle_range(min_date, max_date)

            bundle_df = bundle_df[(bundle_df['Created Date'] >= start_date) & (bundle_df['Created Date'] <= end_date)]
            st.info(f"선택된 기간: **{start_date}** ~ **{end_date}** ({len(bundle_df):,}건)")

        st.markdown("---")

    st.info(f"번들 상품 총 {len(bundle_df):,}건 (SKU {bundle_df['Seller SKU'].nunique()}개)")
    st.markdown("---")

    # ===== KPI Summary =====
    total_bundle = len(bundle_df)
    canceled_bundle = len(bundle_df[bundle_df['Order Status'].isin(('Canceled', 'Cancelled'))])
    cancel_rate = canceled_bundle / total_bundle * 100 if total_bundle > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("번들 총 주문", f"{total_bundle:,}건")
    with col2:
        st.metric("취소 건수", f"{canceled_bundle:,}건")
    with col3:
        st.metric("취소율", f"{cancel_rate:.1f}%")
    with col4:
        shipped = len(bundle_df[bundle_df['Order Status'] == 'Shipped'])
        completed = len(bundle_df[bundle_df['Order Status'] == 'Completed'])
        st.metric("정상 출고/완료", f"{shipped + completed:,}건")

    st.markdown("---")

    # ===== SKU별 분석 =====
    st.subheader("번들 SKU별 취소율")

    sku_stats = bundle_df.groupby('Seller SKU').agg({
        'SKU Unit Original Price': 'first',
        'Product Name': 'first',
        'Order ID': 'count',
        'Quantity': 'sum',
        'Order Status': lambda x: (x.isin(('Canceled', 'Cancelled'))).sum()
    }).reset_index()
    sku_stats.columns = ['SKU', '단가', 'Product Name', '전체 주문(order ID)', '전체 주문(quantity)', '취소 주문(order ID)']
    canceled_qty = bundle_df[bundle_df['Order Status'].isin(('Canceled', 'Cancelled'))].groupby('Seller SKU')['Quantity'].sum()
    sku_stats['취소 주문(quantity)'] = sku_stats['SKU'].map(canceled_qty).fillna(0).astype(int)
    sku_stats['취소율(%)'] = (sku_stats['취소 주문(order ID)'] / sku_stats['전체 주문(order ID)'] * 100).round(1)
    sku_stats = sku_stats.sort_values('전체 주문(order ID)', ascending=False)

    # Build a short display name: strip BEPLAIN / MUNG BEAN prefix, volume specs,
    # and anything after a pipe/comma, then title-case.
    import re
    def _short_name(name: str) -> str:
        s = str(name)
        s = re.split(r'\s*[\|,]\s*', s, maxsplit=1)[0]
        s = re.sub(r'^\s*BEPLAIN(\s+MUNG\s+BEAN)?\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*\d+\s*ml(\s*\*\s*\d+)?', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+', ' ', s).strip()
        return s.title() if s else str(name)

    sku_stats['상품명'] = sku_stats['Product Name'].apply(_short_name)
    # Numbered labels (#1, #2, ...) by order volume for compact x-axis
    sku_stats = sku_stats.reset_index(drop=True)
    sku_stats['번호'] = ['#' + str(i + 1) for i in range(len(sku_stats))]

    col1, col2 = st.columns(2)

    with col1:
        fig_sku = px.bar(
            sku_stats, x='번호', y=['전체 주문(order ID)', '취소 주문(order ID)'],
            title='번들 상품별 주문/취소 현황',
            barmode='group',
            color_discrete_map={'전체 주문(order ID)': '#4CAF50', '취소 주문(order ID)': '#f44336'},
            hover_data={'상품명': True, 'Product Name': True, 'SKU': True, '번호': False},
        )
        fig_sku.update_layout(xaxis_title='번들 번호', xaxis={'categoryorder': 'array', 'categoryarray': sku_stats['번호'].tolist()})
        st.plotly_chart(fig_sku, use_container_width=True)

    with col2:
        fig_cancel = px.bar(
            sku_stats, x='번호', y='취소율(%)',
            title='번들 상품별 취소율',
            color='취소율(%)', color_continuous_scale='RdYlGn_r',
            hover_data={'상품명': True, 'Product Name': True, 'SKU': True, '번호': False},
        )
        fig_cancel.update_layout(xaxis_title='번들 번호', xaxis={'categoryorder': 'array', 'categoryarray': sku_stats['번호'].tolist()})
        st.plotly_chart(fig_cancel, use_container_width=True)

    with st.expander("번들 번호 ↔ 상품 매칭 / 상세 데이터", expanded=True):
        display_df = sku_stats[['번호', 'Product Name', 'SKU', '단가', '전체 주문(order ID)', '전체 주문(quantity)', '취소 주문(order ID)', '취소 주문(quantity)', '취소율(%)']].copy()
        display_df['단가'] = display_df['단가'].apply(lambda x: fmt_money(x, currency) if pd.notna(x) and x > 0 else "-")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ===== 가격대별 분석 =====
    st.subheader("💰 가격대별 취소율")

    bundle_df['Price Range'] = pd.cut(
        bundle_df['SKU Unit Original Price'],
        bins=[0, 500000, 800000, 1200000, 1600000, float('inf')],
        labels=['~500K', '500K~800K', '800K~1.2M', '1.2M~1.6M', '1.6M+']
    )

    price_stats = bundle_df.groupby('Price Range', observed=True).agg({
        'Order ID': 'count',
        'Order Status': lambda x: (x.isin(('Canceled', 'Cancelled'))).sum()
    }).reset_index()
    price_stats.columns = ['가격대', '전체건수', '취소건수']
    price_stats['전체건수'] = pd.to_numeric(price_stats['전체건수'], errors='coerce').fillna(0)
    price_stats['취소건수'] = pd.to_numeric(price_stats['취소건수'], errors='coerce').fillna(0)
    price_stats['취소율(%)'] = (price_stats['취소건수'] / price_stats['전체건수'].replace(0, 1) * 100).round(1)

    col1, col2 = st.columns(2)

    with col1:
        fig_price = px.bar(
            price_stats, x='가격대', y='전체건수',
            title='가격대별 주문 분포',
            color='취소율(%)', color_continuous_scale='RdYlGn_r',
            text='전체건수'
        )
        fig_price.update_traces(textposition='outside')
        st.plotly_chart(fig_price, use_container_width=True)

    with col2:
        fig_price_cancel = px.bar(
            price_stats, x='가격대', y='취소율(%)',
            title='가격대별 취소율',
            color='취소율(%)', color_continuous_scale='RdYlGn_r',
            text='취소율(%)'
        )
        fig_price_cancel.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_price_cancel, use_container_width=True)

    st.markdown("---")

    # ===== 번들 특성별 분석 =====
    st.subheader("번들 특성별 분석")

    # 번들 특성 분류 (Product Name 기반)
    def classify_bundle(name):
        name_lower = str(name).lower()
        if 'twinpack' in name_lower:
            return 'TWINPACK'
        elif 'duo' in name_lower:
            return 'DUO'
        elif 'trio' in name_lower:
            return 'TRIO'
        elif 'set' in name_lower:
            return 'SET'
        else:
            return 'OTHER'

    bundle_df['Bundle Type'] = bundle_df['Product Name'].apply(classify_bundle)

    type_stats = bundle_df.groupby('Bundle Type').agg({
        'Order ID': 'count',
        'Order Status': lambda x: (x.isin(('Canceled', 'Cancelled'))).sum(),
        'SKU Unit Original Price': 'mean'
    }).reset_index()
    type_stats.columns = ['번들유형', '전체건수', '취소건수', '평균가격']
    type_stats['취소율(%)'] = (type_stats['취소건수'] / type_stats['전체건수'] * 100).round(1)
    type_stats = type_stats.sort_values('전체건수', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_type = px.pie(
            type_stats, values='전체건수', names='번들유형',
            title='번들 유형별 주문 분포',
            hole=0.4
        )
        fig_type.update_traces(textposition='inside', textinfo='percent+label')
        fig_type.update_layout(legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5), margin=dict(t=40, b=40))
        st.plotly_chart(fig_type, use_container_width=True)

    with col2:
        fig_type_cancel = px.bar(
            type_stats, x='번들유형', y='취소율(%)',
            title='번들 유형별 취소율',
            color='취소율(%)', color_continuous_scale='RdYlGn_r',
            text='취소율(%)'
        )
        fig_type_cancel.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_type_cancel, use_container_width=True)

    with st.expander("번들 유형별 상세 데이터"):
        type_display = type_stats.copy()
        type_display['평균가격'] = type_display['평균가격'].apply(lambda x: fmt_money(x, currency) if pd.notna(x) else "-")
        st.dataframe(type_display, use_container_width=True)

    st.markdown("---")

    # ===== 날짜별 추이 =====
    if 'Created Date' in bundle_df.columns:
        st.subheader("📅 날짜별 번들 취소율 추이")

        daily_stats = bundle_df.groupby('Created Date').agg({
            'Order ID': 'count',
            'Order Status': lambda x: (x.isin(('Canceled', 'Cancelled'))).sum()
        }).reset_index()
        daily_stats.columns = ['Date', '전체건수', '취소건수']
        daily_stats['취소율(%)'] = (daily_stats['취소건수'] / daily_stats['전체건수'] * 100).round(1)

        fig_daily = make_subplots(specs=[[{"secondary_y": True}]])
        fig_daily.add_trace(
            go.Bar(name='전체 주문', x=daily_stats['Date'], y=daily_stats['전체건수'],
                   marker_color='#4CAF50', opacity=0.7), secondary_y=False
        )
        fig_daily.add_trace(
            go.Bar(name='취소', x=daily_stats['Date'], y=daily_stats['취소건수'],
                   marker_color='#f44336', opacity=0.7), secondary_y=False
        )
        fig_daily.add_trace(
            go.Scatter(name='취소율(%)', x=daily_stats['Date'], y=daily_stats['취소율(%)'],
                       mode='lines+markers', line=dict(color='#FF9800', width=2),
                       hovertemplate='%{x}<br>취소율 %{y:.1f}%<extra></extra>'), secondary_y=True
        )
        fig_daily.update_layout(
            barmode='overlay', height=400, title='날짜별 번들 주문/취소 추이',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
            margin=dict(t=40, b=30, l=50, r=50),
        )
        fig_daily.update_yaxes(title_text="주문 수", secondary_y=False)
        fig_daily.update_yaxes(title_text="취소율 (%)", secondary_y=True)
        st.plotly_chart(fig_daily, use_container_width=True)

        with st.expander("날짜별 상세 데이터"):
            st.dataframe(daily_stats, use_container_width=True)


def show_upload_section(sheet_id: str, brand_name: str):
    st.subheader("📤 Upload Order Data")
    st.caption("Upload an Excel or CSV file to append data to the Google Sheet.")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['xlsx', 'xls', 'csv'],
        help="Upload order data in Excel or CSV format"
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)

            st.success(f"File loaded: **{uploaded_file.name}**")
            st.write(f"**Rows:** {len(df_upload):,} | **Columns:** {len(df_upload.columns)}")

            # Preview
            with st.expander("Preview Data (first 10 rows)"):
                st.dataframe(df_upload.head(10), use_container_width=True)

            # Column mapping info
            with st.expander("Column Mapping"):
                st.write("**Columns in uploaded file:**")
                st.write(", ".join(df_upload.columns.tolist()))

            # Upload button
            if st.button("📤 Append to Google Sheet", type="primary"):
                with st.spinner("Uploading data... (checking for duplicates)"):
                    rows_added, error, rows_updated, duplicates_skipped = sheets_manager.append_data_to_sheet(sheet_id, df_upload)
                    if error:
                        st.error(f"Upload failed: {error}")
                    else:
                        if rows_added > 0:
                            st.success(f"Added **{rows_added:,}** new rows")
                        if rows_updated > 0:
                            st.success(f"Updated **{rows_updated:,}** existing rows")
                        if duplicates_skipped > 0:
                            st.info(f"Skipped **{duplicates_skipped:,}** unchanged rows")
                        if rows_added == 0 and rows_updated == 0:
                            st.warning("No changes - all data already up to date.")
                        st.cache_data.clear()
                        # Reset date range so 전체 기간 picks up new data
                        for key in list(st.session_state.keys()):
                            if key.startswith('main_range') or key.startswith('bundle_range') or key.startswith('_confirmed'):
                                del st.session_state[key]
                        if rows_added > 0 or rows_updated > 0:
                            st.balloons()

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")


def show_dashboard_content(sheet_id: str, currency: str = "Rp"):

    with st.spinner("데이터를 불러오는 중..."):
        df, error = load_sheet_data(sheet_id)

    if error:
        st.error(f"데이터 로드 실패: {error}")
        return

    if df is None or len(df) == 0:
        st.warning("데이터가 없습니다. Upload 탭에서 데이터를 업로드해주세요.")
        return

    # Data preprocessing
    if 'Created Time' in df.columns:
        df = df[df['Created Time'] != 'Order created time.'].copy()

    if 'Order Amount' in df.columns:
        df['Order Amount'] = pd.to_numeric(df['Order Amount'], errors='coerce')
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')

    # Separate samples (Order Amount = 0, e.g. creator samples) from real sales
    samples_df = df[df['Order Amount'] == 0].copy() if 'Order Amount' in df.columns else pd.DataFrame()
    if len(samples_df) > 0:
        df = df[df['Order Amount'] > 0].copy()

    # Date conversion
    if 'Created Time' in df.columns:
        df['Created Date'] = parse_created_time(df['Created Time']).dt.date
        if len(samples_df) > 0:
            samples_df['Created Date'] = parse_created_time(samples_df['Created Time']).dt.date


    # Check for valid dates
    if 'Created Date' not in df.columns:
        st.error("'Created Time' 컬럼이 없습니다.")
        return

    valid_dates = df['Created Date'].dropna()
    if len(valid_dates) == 0:
        st.error("유효한 날짜 데이터가 없습니다.")
        return

    # Date filter setup
    min_date = pd.to_datetime(valid_dates.min()).date()
    max_date = pd.to_datetime(valid_dates.max()).date()

    df['Year-Month'] = df['Created Date'].apply(lambda x: x.strftime('%Y-%m') if pd.notna(x) else None)
    available_months = sorted(df['Year-Month'].dropna().unique(), reverse=True)

    # Apply pending month selection from quick buttons (before widget instantiation)
    if '_pending_month_sel' in st.session_state:
        st.session_state['main_month_sel'] = st.session_state.pop('_pending_month_sel')

    _period_info_placeholder = st.empty()

    # Labels row — must match control row ratios
    lbl1, lbl2, lbl_quick, _, _, _, _ = st.columns([1.5, 2.5, 0.8, 0.8, 0.8, 0.8, 0.8])
    with lbl1:
        st.markdown("<p style='font-weight:500; font-size:0.8rem; color:#64648c; margin:0 0 -1rem 0;'>월 선택</p>", unsafe_allow_html=True)
    with lbl2:
        st.markdown("<p style='font-weight:500; font-size:0.8rem; color:#64648c; margin:0 0 -1rem 0;'>기간</p>", unsafe_allow_html=True)
    with lbl_quick:
        st.markdown("<p style='font-weight:500; font-size:0.8rem; color:#64648c; margin:0 0 -1rem 0;'>빠른 선택</p>", unsafe_allow_html=True)

    # Controls row
    col_month, col_range, col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns([1.5, 2.5, 0.8, 0.8, 0.8, 0.8, 0.8])

    with col_month:
        month_options = ["전체 기간"] + list(available_months)
        selected_month = st.selectbox(
            "월 선택",
            options=month_options,
            index=0,
            key="main_month_sel",
            label_visibility="collapsed",
        )

    if selected_month != "전체 기간":
        year, month = map(int, selected_month.split('-'))
        last_day = calendar.monthrange(year, month)[1]
        default_start = max(pd.Timestamp(year, month, 1).date(), min_date)
        default_end = min(pd.Timestamp(year, month, last_day).date(), max_date)
        range_key = f"main_range_{selected_month}"
    else:
        default_start, default_end = min_date, max_date
        range_key = "main_range"
        if '_pending_main_range' in st.session_state:
            st.session_state[range_key] = st.session_state.pop('_pending_main_range')

    with col_range:
        # Only pass value= if not already set via session state (avoids conflict)
        date_kwargs = dict(
            label="기간",
            min_value=min_date,
            max_value=max_date,
            key=range_key,
            label_visibility="collapsed",
        )
        if range_key not in st.session_state:
            date_kwargs['value'] = (default_start, default_end)
        date_range = st.date_input(**date_kwargs)

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        st.session_state['_confirmed_main_range'] = (start_date, end_date)
    else:
        if '_confirmed_main_range' in st.session_state:
            start_date, end_date = st.session_state['_confirmed_main_range']
        else:
            start_date, end_date = default_start, default_end

    def _queue_range(start, end):
        st.session_state['_pending_month_sel'] = "전체 기간"
        st.session_state['_pending_main_range'] = (start, end)
        st.rerun()

    with col_q1:
        if st.button("7일", use_container_width=True):
            _queue_range(max_date - datetime.timedelta(days=6), max_date)
    with col_q2:
        if st.button("14일", use_container_width=True):
            _queue_range(max_date - datetime.timedelta(days=13), max_date)
    with col_q3:
        if st.button("30일", use_container_width=True):
            _queue_range(max_date - datetime.timedelta(days=29), max_date)
    with col_q4:
        if st.button("3개월", use_container_width=True):
            _queue_range(max_date - datetime.timedelta(days=90), max_date)
    with col_q5:
        if st.button("6개월", use_container_width=True):
            _queue_range(max_date - datetime.timedelta(days=180), max_date)

    # Keep unfiltered copies for previous period comparison
    df_all = df.copy()
    samples_all = samples_df.copy() if len(samples_df) > 0 else pd.DataFrame()

    # Apply date filter
    df = df[(df['Created Date'] >= start_date) & (df['Created Date'] <= end_date)]
    if len(samples_df) > 0 and 'Created Date' in samples_df.columns:
        samples_df = samples_df[(samples_df['Created Date'] >= start_date) & (samples_df['Created Date'] <= end_date)]

    sample_info = f" | 샘플 {len(samples_df):,}건" if len(samples_df) > 0 else ""
    _period_info_placeholder.subheader(f"📅 기간 선택 — {start_date} ~ {end_date} ({len(df):,}행{sample_info})")

    # Order-level aggregation (current period)
    df_sorted = df.sort_values('Created Time', ascending=False) if 'Created Time' in df.columns else df
    order_info = df_sorted.groupby('Order ID').agg({
        'Order Amount': 'first',
        'Order Status': 'first',
        'Created Date': 'first',
        'Payment Method': 'first' if 'Payment Method' in df.columns else lambda x: None,
        'Tracking ID': 'first' if 'Tracking ID' in df.columns else lambda x: None
    }).reset_index()

    # Previous period comparison
    period_days = (end_date - start_date).days + 1
    prev_end = start_date - datetime.timedelta(days=1)
    prev_start = prev_end - datetime.timedelta(days=period_days - 1)
    df_prev = df_all[(df_all['Created Date'] >= prev_start) & (df_all['Created Date'] <= prev_end)]

    if len(df_prev) > 0:
        df_prev_sorted = df_prev.sort_values('Created Time', ascending=False) if 'Created Time' in df_prev.columns else df_prev
        prev_order_info = df_prev_sorted.groupby('Order ID').agg({
            'Order Amount': 'first',
            'Order Status': 'first',
        }).reset_index()
        prev_total_orders = len(prev_order_info)
        prev_total_amount = prev_order_info['Order Amount'].sum()
        prev_canceled = prev_order_info[prev_order_info['Order Status'].isin(('Canceled', 'Cancelled'))]
        prev_cancel_count = len(prev_canceled)
        prev_cancel_amount = prev_canceled['Order Amount'].sum()
    else:
        prev_total_orders = prev_total_amount = prev_cancel_count = prev_cancel_amount = 0

    def _pct_change(current, previous):
        if previous == 0:
            return None
        return ((current - previous) / previous) * 100

    # ===== KPI Cards =====
    if len(df_prev) > 0:
        st.subheader("📈 주요 지표")
        st.caption(f"비교 기간: {prev_start} ~ {prev_end} ({period_days}일)")
    else:
        st.subheader("📈 주요 지표")

    total_orders = len(order_info)
    total_amount = order_info['Order Amount'].sum()
    canceled_orders = order_info[order_info['Order Status'].isin(('Canceled', 'Cancelled'))]
    cancel_count = len(canceled_orders)
    cancel_rate = cancel_count / total_orders * 100 if total_orders > 0 else 0
    cancel_amount = canceled_orders['Order Amount'].sum()

    _has_prev_period = prev_total_orders > 0
    d_orders = _pct_change(total_orders, prev_total_orders) if _has_prev_period else None
    d_amount = _pct_change(total_amount, prev_total_amount) if _has_prev_period else None
    d_cancel = _pct_change(cancel_count, prev_cancel_count) if _has_prev_period else None
    d_cancel_amt = _pct_change(cancel_amount, prev_cancel_amount) if _has_prev_period else None
    d_samples = d_samples if _has_prev_period else None

    # Sample counts for current & previous period
    sample_count = samples_df['Order ID'].nunique() if len(samples_df) > 0 else 0
    sample_qty = int(samples_df['Quantity'].sum()) if len(samples_df) > 0 and 'Quantity' in samples_df.columns else 0
    if len(samples_all) > 0 and 'Created Date' in samples_all.columns:
        prev_samples = samples_all[(samples_all['Created Date'] >= prev_start) & (samples_all['Created Date'] <= prev_end)]
        prev_sample_count = prev_samples['Order ID'].nunique() if len(prev_samples) > 0 else 0
    else:
        prev_sample_count = 0
    d_samples = _pct_change(sample_count, prev_sample_count)

    prev_cancel_rate = prev_cancel_count / prev_total_orders * 100 if prev_total_orders > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    _no_prev = "비교 기간 없음"

    with col1:
        _d = f"{d_orders:+.1f}% (이전: {prev_total_orders:,}건)" if d_orders is not None else _no_prev
        st.metric(label="총 주문 수", value=f"{total_orders:,}건", delta=_d, delta_color="off" if d_orders is None else "normal")
        st.toggle("차트", value=True, key="kpi_주문수")
    with col2:
        _d = f"{d_amount:+.1f}% (이전: {fmt_money(prev_total_amount, currency)})" if d_amount is not None else _no_prev
        st.metric(label="총 주문 금액", value=fmt_money(total_amount, currency), delta=_d, delta_color="off" if d_amount is None else "normal")
        st.toggle("차트", value=False, key="kpi_매출")
    with col3:
        _d = f"{d_cancel:+.1f}% (이전: {prev_cancel_count:,}건)" if d_cancel is not None else _no_prev
        st.metric(label="취소 주문 수", value=f"{cancel_count:,}건 ({cancel_rate:.1f}%)", delta=_d, delta_color="off" if d_cancel is None else "inverse")
        st.toggle("차트", value=True, key="kpi_취소수")
    with col4:
        _d = f"{d_cancel_amt:+.1f}% (이전: {fmt_money(prev_cancel_amount, currency)})" if d_cancel_amt is not None else _no_prev
        st.metric(label="취소 금액", value=fmt_money(cancel_amount, currency), delta=_d, delta_color="off" if d_cancel_amt is None else "inverse")
        st.toggle("차트", value=False, key="kpi_취소금액")
    with col5:
        _d = f"{d_samples:+.1f}% (이전: {prev_sample_count:,}건)" if d_samples is not None else _no_prev
        st.metric(label="샘플 발송", value=f"{sample_count:,}건 / {sample_qty:,}개", delta=_d, delta_color="off" if d_samples is None else "normal")
        st.toggle("차트", value=True, key="kpi_샘플발송")

    # ===== KPI Daily Trend Chart =====
    kpi_daily = order_info.groupby('Created Date').agg(
        주문수=('Order ID', 'count'),
        매출=('Order Amount', 'sum'),
    ).reset_index()

    kpi_canceled_daily = order_info[order_info['Order Status'].isin(('Canceled', 'Cancelled'))].groupby('Created Date').agg(
        취소수=('Order ID', 'count'),
        취소금액=('Order Amount', 'sum'),
    ).reset_index()

    kpi_daily = kpi_daily.merge(kpi_canceled_daily, on='Created Date', how='left').fillna(0)

    # Add sample data
    if len(samples_df) > 0 and 'Created Date' in samples_df.columns:
        sample_daily = samples_df.groupby('Created Date').agg(
            샘플발송=('Order ID', 'nunique'),
        ).reset_index()
        kpi_daily = kpi_daily.merge(sample_daily, on='Created Date', how='left').fillna(0)
    else:
        kpi_daily['샘플발송'] = 0

    # Build metric list from card toggles
    _toggle_map = {"주문수": "kpi_주문수", "매출": "kpi_매출", "취소수": "kpi_취소수", "취소금액": "kpi_취소금액", "샘플발송": "kpi_샘플발송"}
    kpi_metrics = [l for l, sk in _toggle_map.items() if st.session_state.get(sk)]

    if kpi_metrics:
        colors = {"주문수": "#6366f1", "매출": "#22c55e", "취소수": "#ef4444", "취소금액": "#f97316", "샘플발송": "#a855f7"}
        # Use secondary y-axis for 매출/취소금액 (different scale from counts)
        has_count = any(m in kpi_metrics for m in ["주문수", "취소수", "샘플발송"])
        has_amount = any(m in kpi_metrics for m in ["매출", "취소금액"])
        use_dual = has_count and has_amount

        fig_kpi = make_subplots(specs=[[{"secondary_y": use_dual}]])
        for m in kpi_metrics:
            secondary = use_dual and m in ("매출", "취소금액")
            fig_kpi.add_trace(
                go.Scatter(
                    name=m, x=kpi_daily['Created Date'], y=kpi_daily[m],
                    mode='lines+markers', line=dict(color=colors.get(m, '#6366f1'), width=2),
                    marker=dict(size=4),
                    hovertemplate=f'{m}: %{{y:,.0f}}<extra></extra>',
                ),
                secondary_y=secondary,
            )
        fig_kpi.update_layout(
            height=280, margin=dict(t=10, b=30, l=10, r=10),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
            hovermode='x unified',
        )
        if use_dual:
            fig_kpi.update_yaxes(title_text="건수", secondary_y=False)
            fig_kpi.update_yaxes(title_text="금액", secondary_y=True)
        elif has_amount:
            fig_kpi.update_yaxes(title_text="금액", secondary_y=False)
        else:
            fig_kpi.update_yaxes(title_text="건수", secondary_y=False)
        st.plotly_chart(fig_kpi, use_container_width=True)

    st.markdown("---")

    # ===== Sample/Creator Orders =====
    if len(samples_df) > 0:
        sample_orders = samples_df['Order ID'].nunique()
        sample_qty = int(samples_df['Quantity'].sum()) if 'Quantity' in samples_df.columns else 0
        with st.expander(f"🎁 샘플 (크리에이터 발송): {sample_orders:,}건 / {sample_qty:,}개"):
            if 'Seller SKU' in samples_df.columns:
                sample_sku = samples_df.groupby('Seller SKU').agg({
                    'Order ID': 'nunique',
                    'Quantity': 'sum',
                    'Product Name': 'first',
                }).reset_index()
                sample_sku.columns = ['SKU', '주문수', '수량', 'Product Name']
                sample_sku['SKU'] = sample_sku['SKU'].astype(str).replace('nan', 'N/A')
                sample_sku = sample_sku.sort_values('수량', ascending=False)
                st.dataframe(sample_sku, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ===== Order Status Distribution =====
    col1, col2 = st.columns(2)

    # Current period status
    status_dist = order_info.groupby('Order Status').agg({
        'Order ID': 'count',
        'Order Amount': 'sum'
    }).reset_index()
    status_dist.columns = ['Order Status', 'Count', 'Amount']

    # Previous period status
    if len(df_prev) > 0:
        df_prev_sorted = df_prev.sort_values('Created Time', ascending=False) if 'Created Time' in df_prev.columns else df_prev
        prev_oi = df_prev_sorted.groupby('Order ID').agg({
            'Order Amount': 'first', 'Order Status': 'first'
        }).reset_index()
        prev_status = prev_oi.groupby('Order Status').agg(
            Count=('Order ID', 'count'), Amount=('Order Amount', 'sum')
        ).reset_index()
    else:
        prev_status = pd.DataFrame(columns=['Order Status', 'Count', 'Amount'])

    colors = px.colors.qualitative.Set2
    all_statuses = list(status_dist['Order Status'].unique())
    color_map = {s: colors[i % len(colors)] for i, s in enumerate(all_statuses)}
    has_prev = len(prev_status) > 0

    with col1:
        _h1, _t1 = st.columns([4, 1])
        with _h1:
            st.subheader("Order Status 분포")
        with _t1:
            show_prev_pie = st.toggle("비교", value=False, key="cmp_status_pie", disabled=not has_prev)

        if show_prev_pie and has_prev:
            # Both donuts in one chart, explicit colors so nothing changes
            fig_status = go.Figure()
            # Main donut (right, full size)
            fig_status.add_trace(go.Pie(
                labels=status_dist['Order Status'], values=status_dist['Count'],
                hole=0.4, textposition='inside', textinfo='percent+label',
                marker=dict(colors=[color_map[s] for s in status_dist['Order Status']]),
                sort=False, showlegend=True,
                domain=dict(x=[0.25, 1.0], y=[0.0, 1.0]),
            ))
            # Previous donut (left-bottom, smaller)
            fig_status.add_trace(go.Pie(
                labels=prev_status['Order Status'], values=prev_status['Count'],
                hole=0.4, textposition='inside', textinfo='percent',
                marker=dict(colors=[color_map.get(s, '#ccc') for s in prev_status['Order Status']]),
                sort=False, showlegend=False,
                domain=dict(x=[0.0, 0.32], y=[0.0, 0.55]),
            ))
            fig_status.add_annotation(x=0.16, y=-0.05, text="이전", showarrow=False,
                                      font=dict(size=10, color="#64648c"))
            fig_status.update_layout(
                height=300, margin=dict(t=10, b=25, l=0, r=10),
                legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.6),
            )
        else:
            # Single donut, also explicit colors
            fig_status = go.Figure(go.Pie(
                labels=status_dist['Order Status'], values=status_dist['Count'],
                hole=0.4, textposition='inside', textinfo='percent+label',
                marker=dict(colors=[color_map[s] for s in status_dist['Order Status']]),
                sort=False,
            ))
            fig_status.update_layout(
                height=300, margin=dict(t=10, b=30, l=10, r=10),
                legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5),
            )
        st.plotly_chart(fig_status, use_container_width=True)

    with col2:
        _h2, _t2 = st.columns([4, 1])
        with _h2:
            st.subheader("💰 Status별 금액")
        with _t2:
            show_prev_bar = st.toggle("비교", value=False, key="cmp_status_bar", disabled=not has_prev)

        if show_prev_bar:
            bar_cur = status_dist[['Order Status', 'Amount']].copy()
            bar_cur['기간'] = '현재'
            bar_prev = prev_status[['Order Status', 'Amount']].copy()
            bar_prev['기간'] = '이전'
            bar_combined = pd.concat([bar_cur, bar_prev], ignore_index=True)
            fig_amount = px.bar(
                bar_combined, x='Order Status', y='Amount', color='기간',
                barmode='group', text_auto='.2s',
                color_discrete_map={'현재': '#6366f1', '이전': '#c7c7d4'}
            )
            fig_amount.update_layout(height=300, margin=dict(t=10, b=30, l=10, r=10),
                                     legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0))
        else:
            fig_amount = px.bar(
                status_dist, x='Order Status', y='Amount', color='Order Status',
                text_auto='.2s', color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_amount.update_layout(showlegend=False, height=300, margin=dict(t=10, b=30, l=10, r=10))
        st.plotly_chart(fig_amount, use_container_width=True)

    st.markdown("---")

    # ===== Daily Trends =====
    st.subheader("📅 날짜별 주문/취소 추이")

    daily_all = order_info.groupby('Created Date').agg({
        'Order ID': 'count', 'Order Amount': 'sum'
    }).rename(columns={'Order ID': '전체주문수', 'Order Amount': '전체매출'})

    daily_canceled = order_info[order_info['Order Status'].isin(('Canceled', 'Cancelled'))].groupby('Created Date').agg({
        'Order ID': 'count', 'Order Amount': 'sum'
    }).rename(columns={'Order ID': '취소주문수', 'Order Amount': '취소매출'})

    daily_summary = daily_all.join(daily_canceled).fillna(0).reset_index()
    daily_summary['취소율(%)'] = (daily_summary['취소주문수'] / daily_summary['전체주문수'] * 100).round(1)

    fig_daily = make_subplots(specs=[[{"secondary_y": True}]])
    fig_daily.add_trace(
        go.Bar(name='전체 주문', x=daily_summary['Created Date'], y=daily_summary['전체주문수'],
               marker_color='#4CAF50', opacity=0.7), secondary_y=False
    )
    fig_daily.add_trace(
        go.Bar(name='취소 주문', x=daily_summary['Created Date'], y=daily_summary['취소주문수'],
               marker_color='#f44336', opacity=0.7), secondary_y=False
    )
    fig_daily.add_trace(
        go.Scatter(name='취소율(%)', x=daily_summary['Created Date'], y=daily_summary['취소율(%)'],
                   mode='lines+markers', line=dict(color='#FF9800', width=2),
                   hovertemplate='%{x}<br>취소율 %{y:.1f}%<extra></extra>'), secondary_y=True
    )
    fig_daily.update_layout(
        barmode='overlay', height=400,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        margin=dict(t=40, b=30, l=50, r=50),
    )
    fig_daily.update_yaxes(title_text="주문 수", secondary_y=False)
    fig_daily.update_yaxes(title_text="취소율 (%)", secondary_y=True)
    st.plotly_chart(fig_daily, use_container_width=True)

    with st.expander("날짜별 상세 데이터"):
        daily_display = daily_summary.copy()
        daily_display['전체매출'] = daily_display['전체매출'].apply(lambda x: fmt_money(x, currency))
        daily_display['취소매출'] = daily_display['취소매출'].apply(lambda x: fmt_money(x, currency))
        st.dataframe(daily_display, use_container_width=True)

    st.markdown("---")

    # ===== Product Analysis =====
    if 'Seller SKU' in df.columns:
        st.subheader("제품별 주문/취소 현황")

        product_name_map = df.groupby('Seller SKU')['Product Name'].first() if 'Product Name' in df.columns else {}

        sku_all = df.groupby('Seller SKU').agg({
            'Quantity': 'sum', 'Order ID': ['nunique', 'count']
        })
        sku_all.columns = ['전체 주문(quantity)', '전체주문건수', '전체 주문(order ID)']

        canceled_df = df[df['Order Status'].isin(('Canceled', 'Cancelled'))]
        sku_canceled = canceled_df.groupby('Seller SKU').agg({
            'Quantity': 'sum', 'Order ID': 'count'
        })
        sku_canceled.columns = ['취소 주문(quantity)', '취소 주문(order ID)']

        sku_summary = sku_all.join(sku_canceled).fillna(0).reset_index()
        sku_summary['취소 주문(quantity)'] = sku_summary['취소 주문(quantity)'].astype(int)
        sku_summary['취소 주문(order ID)'] = sku_summary['취소 주문(order ID)'].astype(int)
        if len(product_name_map) > 0:
            sku_summary['Product Name'] = sku_summary['Seller SKU'].map(product_name_map)
        sku_summary['정상 주문(quantity)'] = sku_summary['전체 주문(quantity)'] - sku_summary['취소 주문(quantity)']
        sku_summary['취소율(%)'] = (sku_summary['취소 주문(quantity)'] / sku_summary['전체 주문(quantity)'] * 100).round(1)
        sku_summary = sku_summary.sort_values('전체 주문(quantity)', ascending=False)

        import re
        def _strip_brand(name):
            s = str(name) if name is not None else ''
            s = re.sub(r'\[[^\]]*\]\s*', '', s)
            s = re.sub(r'\([^)]*NOT\s*FOR\s*SALE[^)]*\)\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^\s*BEPLAIN(\s+MUNG\s+BEAN)?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'\s*\|.*$', '', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s if s else str(name)

        src = sku_summary['Product Name'] if 'Product Name' in sku_summary.columns else sku_summary['Seller SKU']
        sku_summary['Product Name Short'] = src.apply(_strip_brand)

        col1, col2 = st.columns(2)

        with col1:
            top_sku = sku_summary.head(10).reset_index(drop=True).copy()
            top_sku['번호'] = ['#' + str(i + 1) for i in range(len(top_sku))]
            fig_sku = px.bar(
                top_sku, x='번호', y=['정상 주문(quantity)', '취소 주문(quantity)'], barmode='stack',
                title='상위 10개 제품 판매 현황 (전체 판매량 기준)',
                color_discrete_map={'정상 주문(quantity)': '#4CAF50', '취소 주문(quantity)': '#f44336'},
                hover_data={'Product Name Short': False, 'Product Name': True, 'Seller SKU': True, '번호': False} if 'Product Name' in top_sku.columns else {'Product Name Short': False, '번호': False},
            )
            fig_sku.update_layout(
                xaxis_title='제품 번호', xaxis={'categoryorder': 'array', 'categoryarray': top_sku['번호'].tolist()},
                legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5),
                margin=dict(t=40, b=50, l=10, r=10),
            )
            st.plotly_chart(fig_sku, use_container_width=True)

        with col2:
            high_cancel_sku = sku_summary[sku_summary['전체 주문(quantity)'] >= 10].nlargest(10, '취소율(%)').reset_index(drop=True).copy()
            high_cancel_sku['번호'] = ['#' + str(i + 1) for i in range(len(high_cancel_sku))]
            fig_cancel_sku = px.bar(
                high_cancel_sku, x='번호', y='취소율(%)',
                title='취소율 상위 10개 제품 (최소 10개 이상 주문)',
                color='취소율(%)', color_continuous_scale='Reds',
                hover_data={'Product Name Short': False, 'Product Name': True, 'Seller SKU': True, '번호': False} if 'Product Name' in high_cancel_sku.columns else {'Product Name Short': False, '번호': False},
            )
            fig_cancel_sku.update_layout(
                xaxis_title='제품 번호', xaxis={'categoryorder': 'array', 'categoryarray': high_cancel_sku['번호'].tolist()},
                margin=dict(t=50, b=30, l=10, r=10),
            )
            st.plotly_chart(fig_cancel_sku, use_container_width=True)

        # Mapping tables so users can see which # corresponds to which product
        map_col1, map_col2 = st.columns(2)
        with map_col1:
            st.caption("상위 10개 제품 매칭")
            map_cols_top = ['번호', 'Product Name', '전체 주문(quantity)', '정상 주문(quantity)', '취소 주문(quantity)', '취소율(%)']
            st.dataframe(top_sku[[c for c in map_cols_top if c in top_sku.columns]], use_container_width=True, hide_index=True)
        with map_col2:
            st.caption("취소율 상위 10개 제품 매칭")
            st.dataframe(high_cancel_sku[[c for c in map_cols_top if c in high_cancel_sku.columns]], use_container_width=True, hide_index=True)

        with st.expander("전체 제품 상세 데이터"):
            display_cols = ['Product Name', 'Seller SKU', '전체 주문(order ID)', '전체 주문(quantity)', '정상 주문(quantity)', '취소 주문(order ID)', '취소 주문(quantity)', '취소율(%)', '전체주문건수']
            available_cols = [c for c in display_cols if c in sku_summary.columns]
            st.dataframe(sku_summary[available_cols], use_container_width=True)

        st.markdown("---")

    # ===== Canceled Orders Shipping Status =====
    if 'Tracking ID' in df.columns:
        st.subheader("🚚 취소 주문의 출고 여부 (Tracking ID 기준)")

        canceled_orders_detail = df[df['Order Status'].isin(('Canceled', 'Cancelled'))].groupby('Order ID').agg({
            'Order Amount': 'first',
            'Tracking ID': 'first',
            'Cancel By': 'first' if 'Cancel By' in df.columns else lambda x: None,
            'Cancel Reason': 'first' if 'Cancel Reason' in df.columns else lambda x: None
        }).reset_index()

        canceled_orders_detail['출고여부'] = canceled_orders_detail['Tracking ID'].notna() & (canceled_orders_detail['Tracking ID'] != '')
        canceled_orders_detail['출고여부'] = canceled_orders_detail['출고여부'].map({True: '출고됨', False: '미출고'})

        col1, col2, col3 = st.columns([2, 1, 2])

        shipped = canceled_orders_detail[canceled_orders_detail['출고여부'] == '출고됨']
        not_shipped = canceled_orders_detail[canceled_orders_detail['출고여부'] == '미출고']

        with col1:
            ship_summary = canceled_orders_detail.groupby('출고여부').agg({
                'Order ID': 'count', 'Order Amount': 'sum'
            }).reset_index()
            ship_summary.columns = ['출고여부', 'Count', 'Amount']

            fig_ship = px.pie(
                ship_summary, values='Count', names='출고여부', hole=0.4,
                color_discrete_map={'출고됨': '#FF9800', '미출고': '#9E9E9E'}
            )
            fig_ship.update_traces(textposition='inside', textinfo='percent+value')
            fig_ship.update_layout(legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5), margin=dict(t=20, b=40))
            st.plotly_chart(fig_ship, use_container_width=True)

        with col2:
            st.metric("출고 후 취소", f"{len(shipped):,}건", fmt_money(shipped['Order Amount'].sum(), currency))
            st.metric("미출고 취소", f"{len(not_shipped):,}건", fmt_money(not_shipped['Order Amount'].sum(), currency))

        with col3:
            if len(shipped) > 0 and 'Cancel Reason' in canceled_orders_detail.columns:
                cancel_reason = shipped['Cancel Reason'].value_counts().head(5).reset_index()
                cancel_reason.columns = ['Cancel Reason', 'Count']
                fig_reason = px.bar(
                    cancel_reason, x='Count', y='Cancel Reason', orientation='h',
                    title='출고 후 취소 사유 TOP 5', color_discrete_sequence=['#FF9800']
                )
                fig_reason.update_layout(height=300)
                st.plotly_chart(fig_reason, use_container_width=True)

        st.markdown("---")

    # ===== Payment Method Analysis =====
    if 'Payment Method' in df.columns:
        st.subheader("💳 Payment Method별 현황")

        payment_summary = order_info.groupby('Payment Method').agg({
            'Order ID': 'count', 'Order Amount': 'sum'
        }).rename(columns={'Order ID': '전체주문수', 'Order Amount': '전체매출'})

        payment_canceled = order_info[order_info['Order Status'].isin(('Canceled', 'Cancelled'))].groupby('Payment Method').agg({
            'Order ID': 'count'
        }).rename(columns={'Order ID': '취소주문수'})

        payment_df = payment_summary.join(payment_canceled).fillna(0).reset_index()
        payment_df['취소율(%)'] = (payment_df['취소주문수'] / payment_df['전체주문수'] * 100).round(1)
        payment_df = payment_df.sort_values('전체주문수', ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            fig_payment = px.bar(
                payment_df.head(10), x='Payment Method', y='전체주문수',
                title='Payment Method별 주문 수', color='취소율(%)', color_continuous_scale='RdYlGn_r'
            )
            fig_payment.update_layout(xaxis_tickangle=-45, height=400, margin=dict(t=40, b=30, l=10, r=10))
            st.plotly_chart(fig_payment, use_container_width=True)

        with col2:
            # 사용자가 비교할 Payment Method 두 개 선택
            all_methods = sorted(order_info['Payment Method'].dropna().unique().tolist())
            default_methods = all_methods[:2] if len(all_methods) >= 2 else all_methods
            selected_methods = st.multiselect(
                "비교할 결제방식 선택 (2개)",
                options=all_methods,
                default=default_methods,
                max_selections=2,
                key="payment_compare_methods",
            )

            if len(selected_methods) == 2:
                group_a = order_info[order_info['Payment Method'] == selected_methods[0]]
                group_b = order_info[order_info['Payment Method'] == selected_methods[1]]
                rate_a = len(group_a[group_a['Order Status'].isin(('Canceled', 'Cancelled'))]) / len(group_a) * 100 if len(group_a) > 0 else 0
                rate_b = len(group_b[group_b['Order Status'].isin(('Canceled', 'Cancelled'))]) / len(group_b) * 100 if len(group_b) > 0 else 0

                compare_df = pd.DataFrame({
                    '결제방식': [selected_methods[0], selected_methods[1]],
                    '주문수': [len(group_a), len(group_b)],
                    '취소율(%)': [rate_a, rate_b]
                })
                fig_compare = px.bar(
                    compare_df, x='결제방식', y='취소율(%)', title='결제방식별 취소율 비교',
                    color='결제방식', text='취소율(%)'
                )
                fig_compare.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_compare.update_layout(showlegend=False, height=300, margin=dict(t=40, b=30, l=10, r=10))
                st.plotly_chart(fig_compare, use_container_width=True)

                st.info(f"""
                **{selected_methods[0]}**: {len(group_a):,}건 (취소율 {rate_a:.1f}%)
                **{selected_methods[1]}**: {len(group_b):,}건 (취소율 {rate_b:.1f}%)
                """)
            elif len(selected_methods) == 1:
                st.warning("비교를 위해 결제방식을 2개 선택해주세요.")
            else:
                st.info("비교할 결제방식을 선택해주세요.")

        with st.expander("Payment Method별 상세 데이터"):
            payment_display = payment_df.copy()
            payment_display['전체매출'] = payment_display['전체매출'].apply(lambda x: fmt_money(x, currency))
            st.dataframe(payment_display, use_container_width=True)

    # Footer
    st.markdown("---")
    st.caption("데이터는 Google Sheets에서 자동으로 불러옵니다.")


# ===== MAIN APP ROUTING =====
if st.session_state.authenticated and st.session_state.is_admin:
    show_admin_panel()
elif st.session_state.authenticated and st.session_state.brand_data:
    show_brand_dashboard()
elif is_admin_route():
    # Reset any stale state
    st.session_state.authenticated = False
    st.session_state.brand_data = None
    show_admin_login_page()
else:
    st.session_state.authenticated = False
    st.session_state.brand_data = None
    show_brand_login_page()
