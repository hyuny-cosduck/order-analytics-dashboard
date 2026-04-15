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
    return sheets_manager.read_sheet_data(sheet_id)

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


# ===== BRAND LOGIN PAGE =====
def show_brand_login_page():
    st.title("📊 Order Analytics Dashboard")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.subheader("Brand Login")

        brand_name = st.text_input("Brand Name")
        password = st.text_input("Password", type="password")

        if st.button("Login", type="primary", use_container_width=True):
            if brand_name and password:
                brand_data = brands_manager.authenticate_brand(brand_name, password)
                if brand_data:
                    st.session_state.authenticated = True
                    st.session_state.is_admin = False
                    st.session_state.brand_name = brand_data['name']
                    st.session_state.brand_data = brand_data
                    st.rerun()
                else:
                    st.error("Invalid brand name or password")
            else:
                st.warning("Please enter brand name and password")


# ===== ADMIN LOGIN PAGE =====
def show_admin_login_page():
    st.title("🔧 Admin Login")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        password = st.text_input("Password", type="password")

        if st.button("Login", type="primary", use_container_width=True):
            if password:
                if brands_manager.authenticate_admin(password):
                    st.session_state.authenticated = True
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Invalid password")
            else:
                st.warning("Please enter password")


# ===== ADMIN PANEL =====
def show_admin_panel():
    st.title("🔧 Admin Panel")

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Logout", type="secondary"):
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
                        st.write(f"**Password:** `{data.get('password', 'N/A')}`")
                        if data.get('sheet_url'):
                            st.write(f"[Open Google Sheet]({data.get('sheet_url')})")

                        # Row count
                        row_count = sheets_manager.get_sheet_row_count(data.get('sheet_id', ''))
                        st.write(f"**Data Rows:** {row_count:,}")

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

        if st.button("Create Brand", type="primary"):
            if new_brand_name:
                with st.spinner("Creating brand and Google Sheet..."):
                    brand_data, error = brands_manager.add_brand(new_brand_name)
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

        if st.button("Import Sheet", type="primary"):
            if import_brand_name and import_sheet_id:
                with st.spinner("Importing sheet..."):
                    brand_data, error = brands_manager.import_existing_sheet(import_brand_name, import_sheet_id)
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
    brand_name = st.session_state.brand_name
    brand_data = st.session_state.brand_data
    sheet_id = brand_data.get('sheet_id')

    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"📊 {brand_name} Order Analytics")
    with col2:
        if st.button("Logout"):
            logout()

    st.markdown("---")

    # Tabs: Dashboard, Bundle Analysis, and Upload
    tab1, tab2, tab3 = st.tabs(["📈 Dashboard", "📦 번들 분석", "📤 Upload Data"])

    with tab1:
        show_dashboard_content(sheet_id)

    with tab2:
        show_bundle_analysis(sheet_id)

    with tab3:
        show_upload_section(sheet_id, brand_name)


def show_bundle_analysis(sheet_id: str):
    """번들 SKU별 구매/취소 분석"""
    st.subheader("📦 번들 SKU 분석")
    st.caption("BDL_BEPLAIN 번들 상품의 구매/취소 현황을 분석합니다.")

    with st.spinner("데이터를 불러오는 중..."):
        df, error = load_sheet_data(sheet_id)

    if error:
        st.error(f"데이터 로드 실패: {error}")
        st.stop()

    if df is None or len(df) == 0:
        st.warning("데이터가 없습니다. Upload 탭에서 데이터를 업로드해주세요.")
        st.stop()

    # Filter bundle SKUs
    if 'Seller SKU' not in df.columns:
        st.error("'Seller SKU' 컬럼이 없습니다.")
        st.stop()

    bundle_df = df[df['Seller SKU'].str.contains('BDL_BEPLAIN', na=False)].copy()

    if len(bundle_df) == 0:
        st.info("번들 상품 데이터가 없습니다. (BDL_BEPLAIN으로 시작하는 SKU)")
        st.stop()

    # Data preprocessing
    bundle_df['SKU Unit Original Price'] = pd.to_numeric(bundle_df['SKU Unit Original Price'], errors='coerce')
    bundle_df['Order Amount'] = pd.to_numeric(bundle_df['Order Amount'], errors='coerce')
    bundle_df['Quantity'] = pd.to_numeric(bundle_df['Quantity'], errors='coerce')

    if 'Created Time' in bundle_df.columns:
        bundle_df['Created Date'] = pd.to_datetime(bundle_df['Created Time'].astype(str).str.strip(), format='%d/%m/%Y %H:%M:%S', errors='coerce').dt.date

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
            st.info(f"📊 선택된 기간: **{start_date}** ~ **{end_date}** ({len(bundle_df):,}건)")

        st.markdown("---")

    st.info(f"📊 번들 상품 총 {len(bundle_df):,}건 (SKU {bundle_df['Seller SKU'].nunique()}개)")
    st.markdown("---")

    # ===== KPI Summary =====
    total_bundle = len(bundle_df)
    canceled_bundle = len(bundle_df[bundle_df['Order Status'] == 'Canceled'])
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
    st.subheader("📊 번들 SKU별 취소율")

    sku_stats = bundle_df.groupby('Seller SKU').agg({
        'SKU Unit Original Price': 'first',
        'Product Name': 'first',
        'Order ID': 'count',
        'Order Status': lambda x: (x == 'Canceled').sum()
    }).reset_index()
    sku_stats.columns = ['SKU', '단가', 'Product Name', '전체건수', '취소건수']
    sku_stats['취소율(%)'] = (sku_stats['취소건수'] / sku_stats['전체건수'] * 100).round(1)
    sku_stats = sku_stats.sort_values('전체건수', ascending=False)

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
            sku_stats, x='번호', y=['전체건수', '취소건수'],
            title='번들 상품별 주문/취소 현황',
            barmode='group',
            color_discrete_map={'전체건수': '#4CAF50', '취소건수': '#f44336'},
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

    with st.expander("📋 번들 번호 ↔ 상품 매칭 / 상세 데이터", expanded=True):
        display_df = sku_stats[['번호', 'Product Name', 'SKU', '단가', '전체건수', '취소건수', '취소율(%)']].copy()
        display_df['단가'] = display_df['단가'].apply(lambda x: f"Rp {x:,.0f}" if pd.notna(x) and x > 0 else "-")
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
        'Order Status': lambda x: (x == 'Canceled').sum()
    }).reset_index()
    price_stats.columns = ['가격대', '전체건수', '취소건수']
    price_stats['취소율(%)'] = (price_stats['취소건수'] / price_stats['전체건수'] * 100).round(1)

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
    st.subheader("🏷️ 번들 특성별 분석")

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
        'Order Status': lambda x: (x == 'Canceled').sum(),
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

    with st.expander("📋 번들 유형별 상세 데이터"):
        type_display = type_stats.copy()
        type_display['평균가격'] = type_display['평균가격'].apply(lambda x: f"Rp {x:,.0f}" if pd.notna(x) else "-")
        st.dataframe(type_display, use_container_width=True)

    st.markdown("---")

    # ===== 날짜별 추이 =====
    if 'Created Date' in bundle_df.columns:
        st.subheader("📅 날짜별 번들 취소율 추이")

        daily_stats = bundle_df.groupby('Created Date').agg({
            'Order ID': 'count',
            'Order Status': lambda x: (x == 'Canceled').sum()
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
                       mode='lines+markers', line=dict(color='#FF9800', width=2)), secondary_y=True
        )
        fig_daily.update_layout(barmode='overlay', height=400, title='날짜별 번들 주문/취소 추이')
        fig_daily.update_yaxes(title_text="주문 수", secondary_y=False)
        fig_daily.update_yaxes(title_text="취소율 (%)", secondary_y=True)
        st.plotly_chart(fig_daily, use_container_width=True)

        with st.expander("📋 날짜별 상세 데이터"):
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
                            st.success(f"➕ Added **{rows_added:,}** new rows")
                        if rows_updated > 0:
                            st.success(f"🔄 Updated **{rows_updated:,}** existing rows")
                        if duplicates_skipped > 0:
                            st.info(f"⏭️ Skipped **{duplicates_skipped:,}** unchanged rows")
                        if rows_added == 0 and rows_updated == 0:
                            st.warning("No changes - all data already up to date.")
                        st.cache_data.clear()
                        if rows_added > 0 or rows_updated > 0:
                            st.balloons()

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")


def show_dashboard_content(sheet_id: str):
    # Refresh button
    col_refresh, col_info = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 데이터 새로고침"):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("데이터를 불러오는 중..."):
        df, error = load_sheet_data(sheet_id)

    if error:
        st.error(f"데이터 로드 실패: {error}")
        st.stop()

    if df is None or len(df) == 0:
        st.warning("데이터가 없습니다. Upload 탭에서 데이터를 업로드해주세요.")
        st.stop()

    # Data preprocessing
    if 'Created Time' in df.columns:
        df = df[df['Created Time'] != 'Order created time.'].copy()

    if 'Order Amount' in df.columns:
        df['Order Amount'] = pd.to_numeric(df['Order Amount'], errors='coerce')
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')

    # Date conversion
    if 'Created Time' in df.columns:
        df['Created Date'] = pd.to_datetime(df['Created Time'].astype(str).str.strip(), format='%d/%m/%Y %H:%M:%S', errors='coerce').dt.date

    with col_info:
        st.caption(f"전체 데이터: {len(df):,}행")

    # Check for valid dates
    if 'Created Date' not in df.columns:
        st.error("'Created Time' 컬럼이 없습니다.")
        st.stop()

    valid_dates = df['Created Date'].dropna()
    if len(valid_dates) == 0:
        st.error("유효한 날짜 데이터가 없습니다.")
        st.stop()

    # Date filter setup
    min_date = pd.to_datetime(valid_dates.min()).date()
    max_date = pd.to_datetime(valid_dates.max()).date()

    # Month selector
    st.subheader("📅 기간 선택")

    df['Year-Month'] = df['Created Date'].apply(lambda x: x.strftime('%Y-%m') if pd.notna(x) else None)
    available_months = sorted(df['Year-Month'].dropna().unique(), reverse=True)

    # Promote any pending range (set by buttons on the previous run) into the
    # widget key BEFORE the widget is instantiated — Streamlit disallows
    # mutating a widget-bound key after its widget has already rendered.
    if '_pending_main_range' in st.session_state:
        st.session_state['main_range'] = st.session_state.pop('_pending_main_range')

    col_month, col_range = st.columns([1, 2])

    with col_month:
        month_options = ["전체 기간"] + list(available_months)
        selected_month = st.selectbox("월 선택", options=month_options, index=0)

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
            key="main_range",
        )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = default_start, default_end

    # Quick selection buttons — stash into a pending key, then rerun.
    st.write("빠른 선택:")
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)

    def _queue_range(start, end):
        st.session_state['_pending_main_range'] = (start, end)
        st.rerun()

    with quick_col1:
        if st.button("최근 7일"):
            _queue_range(max_date - datetime.timedelta(days=6), max_date)
    with quick_col2:
        if st.button("최근 14일"):
            _queue_range(max_date - datetime.timedelta(days=13), max_date)
    with quick_col3:
        if st.button("최근 30일"):
            _queue_range(max_date - datetime.timedelta(days=29), max_date)
    with quick_col4:
        if st.button("전체"):
            _queue_range(min_date, max_date)

    # Apply date filter
    df = df[(df['Created Date'] >= start_date) & (df['Created Date'] <= end_date)]

    st.info(f"📊 선택된 기간: **{start_date}** ~ **{end_date}** ({len(df):,}행)")
    st.markdown("---")

    # Order-level aggregation
    df_sorted = df.sort_values('Created Time', ascending=False) if 'Created Time' in df.columns else df
    order_info = df_sorted.groupby('Order ID').agg({
        'Order Amount': 'first',
        'Order Status': 'first',
        'Created Date': 'first',
        'Payment Method': 'first' if 'Payment Method' in df.columns else lambda x: None,
        'Tracking ID': 'first' if 'Tracking ID' in df.columns else lambda x: None
    }).reset_index()

    # ===== KPI Cards =====
    st.header("📈 주요 지표")

    total_orders = len(order_info)
    total_amount = order_info['Order Amount'].sum()
    canceled_orders = order_info[order_info['Order Status'] == 'Canceled']
    cancel_count = len(canceled_orders)
    cancel_rate = cancel_count / total_orders * 100 if total_orders > 0 else 0
    cancel_amount = canceled_orders['Order Amount'].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="총 주문 수", value=f"{total_orders:,}건")
    with col2:
        st.metric(label="총 주문 금액", value=f"Rp {total_amount:,.0f}")
    with col3:
        st.metric(label="취소 주문 수", value=f"{cancel_count:,}건", delta=f"{cancel_rate:.1f}%", delta_color="inverse")
    with col4:
        st.metric(label="취소 금액", value=f"Rp {cancel_amount:,.0f}")

    st.markdown("---")

    # ===== Order Status Distribution =====
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Order Status 분포")
        status_dist = order_info.groupby('Order Status').agg({
            'Order ID': 'count',
            'Order Amount': 'sum'
        }).reset_index()
        status_dist.columns = ['Order Status', 'Count', 'Amount']

        fig_status = px.pie(
            status_dist, values='Count', names='Order Status', hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_status.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_status, use_container_width=True)

    with col2:
        st.subheader("💰 Status별 금액")
        fig_amount = px.bar(
            status_dist, x='Order Status', y='Amount', color='Order Status',
            text_auto='.2s', color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_amount.update_layout(showlegend=False)
        st.plotly_chart(fig_amount, use_container_width=True)

    st.markdown("---")

    # ===== Daily Trends =====
    st.subheader("📅 날짜별 주문/취소 추이")

    daily_all = order_info.groupby('Created Date').agg({
        'Order ID': 'count', 'Order Amount': 'sum'
    }).rename(columns={'Order ID': '전체주문수', 'Order Amount': '전체매출'})

    daily_canceled = order_info[order_info['Order Status'] == 'Canceled'].groupby('Created Date').agg({
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
                   mode='lines+markers', line=dict(color='#FF9800', width=2)), secondary_y=True
    )
    fig_daily.update_layout(barmode='overlay', height=400)
    fig_daily.update_yaxes(title_text="주문 수", secondary_y=False)
    fig_daily.update_yaxes(title_text="취소율 (%)", secondary_y=True)
    st.plotly_chart(fig_daily, use_container_width=True)

    with st.expander("📋 날짜별 상세 데이터"):
        daily_display = daily_summary.copy()
        daily_display['전체매출'] = daily_display['전체매출'].apply(lambda x: f"Rp {x:,.0f}")
        daily_display['취소매출'] = daily_display['취소매출'].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(daily_display, use_container_width=True)

    st.markdown("---")

    # ===== Product Analysis =====
    if 'Seller SKU' in df.columns:
        st.subheader("📦 제품별 주문/취소 현황")

        product_name_map = df.groupby('Seller SKU')['Product Name'].first() if 'Product Name' in df.columns else {}

        sku_all = df.groupby('Seller SKU').agg({
            'Quantity': 'sum', 'Order ID': 'nunique'
        }).rename(columns={'Quantity': '전체수량', 'Order ID': '전체주문건수'})

        sku_canceled = df[df['Order Status'] == 'Canceled'].groupby('Seller SKU').agg({
            'Quantity': 'sum'
        }).rename(columns={'Quantity': '취소수량'})

        sku_summary = sku_all.join(sku_canceled).fillna(0).reset_index()
        if len(product_name_map) > 0:
            sku_summary['Product Name'] = sku_summary['Seller SKU'].map(product_name_map)
        sku_summary['정상수량'] = sku_summary['전체수량'] - sku_summary['취소수량']
        sku_summary['취소율(%)'] = (sku_summary['취소수량'] / sku_summary['전체수량'] * 100).round(1)
        sku_summary = sku_summary.sort_values('전체수량', ascending=False)

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
                top_sku, x='번호', y=['정상수량', '취소수량'], barmode='stack',
                title='상위 10개 제품 판매 현황 (전체 판매량 기준)',
                color_discrete_map={'정상수량': '#4CAF50', '취소수량': '#f44336'},
                hover_data={'Product Name Short': False, 'Product Name': True, 'Seller SKU': True, '번호': False} if 'Product Name' in top_sku.columns else {'Product Name Short': False, '번호': False},
            )
            fig_sku.update_layout(xaxis_title='제품 번호', xaxis={'categoryorder': 'array', 'categoryarray': top_sku['번호'].tolist()})
            st.plotly_chart(fig_sku, use_container_width=True)

        with col2:
            high_cancel_sku = sku_summary[sku_summary['전체수량'] >= 10].nlargest(10, '취소율(%)').reset_index(drop=True).copy()
            high_cancel_sku['번호'] = ['#' + str(i + 1) for i in range(len(high_cancel_sku))]
            fig_cancel_sku = px.bar(
                high_cancel_sku, x='번호', y='취소율(%)',
                title='취소율 상위 10개 제품 (최소 10개 이상 주문)',
                color='취소율(%)', color_continuous_scale='Reds',
                hover_data={'Product Name Short': False, 'Product Name': True, 'Seller SKU': True, '번호': False} if 'Product Name' in high_cancel_sku.columns else {'Product Name Short': False, '번호': False},
            )
            fig_cancel_sku.update_layout(xaxis_title='제품 번호', xaxis={'categoryorder': 'array', 'categoryarray': high_cancel_sku['번호'].tolist()})
            st.plotly_chart(fig_cancel_sku, use_container_width=True)

        # Mapping tables so users can see which # corresponds to which product
        map_col1, map_col2 = st.columns(2)
        with map_col1:
            st.caption("📋 상위 10개 제품 매칭")
            map_cols_top = ['번호', 'Product Name', '전체수량', '정상수량', '취소수량', '취소율(%)']
            st.dataframe(top_sku[[c for c in map_cols_top if c in top_sku.columns]], use_container_width=True, hide_index=True)
        with map_col2:
            st.caption("📋 취소율 상위 10개 제품 매칭")
            st.dataframe(high_cancel_sku[[c for c in map_cols_top if c in high_cancel_sku.columns]], use_container_width=True, hide_index=True)

        with st.expander("📋 전체 제품 상세 데이터"):
            display_cols = ['Product Name', 'Seller SKU', '전체수량', '정상수량', '취소수량', '취소율(%)', '전체주문건수']
            available_cols = [c for c in display_cols if c in sku_summary.columns]
            st.dataframe(sku_summary[available_cols], use_container_width=True)

        st.markdown("---")

    # ===== Canceled Orders Shipping Status =====
    if 'Tracking ID' in df.columns:
        st.subheader("🚚 취소 주문의 출고 여부 (Tracking ID 기준)")

        canceled_orders_detail = df[df['Order Status'] == 'Canceled'].groupby('Order ID').agg({
            'Order Amount': 'first',
            'Tracking ID': 'first',
            'Cancel By': 'first' if 'Cancel By' in df.columns else lambda x: None,
            'Cancel Reason': 'first' if 'Cancel Reason' in df.columns else lambda x: None
        }).reset_index()

        canceled_orders_detail['출고여부'] = canceled_orders_detail['Tracking ID'].notna() & (canceled_orders_detail['Tracking ID'] != '')
        canceled_orders_detail['출고여부'] = canceled_orders_detail['출고여부'].map({True: '출고됨', False: '미출고'})

        col1, col2, col3 = st.columns(3)

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
            st.plotly_chart(fig_ship, use_container_width=True)

        with col2:
            st.metric("출고 후 취소", f"{len(shipped):,}건", f"Rp {shipped['Order Amount'].sum():,.0f}")
            st.metric("미출고 취소", f"{len(not_shipped):,}건", f"Rp {not_shipped['Order Amount'].sum():,.0f}")

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

        payment_canceled = order_info[order_info['Order Status'] == 'Canceled'].groupby('Payment Method').agg({
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
            fig_payment.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_payment, use_container_width=True)

        with col2:
            cod_methods = ['Cash on delivery', 'Cash']
            cod_orders = order_info[order_info['Payment Method'].isin(cod_methods)]
            non_cod_orders = order_info[~order_info['Payment Method'].isin(cod_methods)]

            cod_cancel_rate = len(cod_orders[cod_orders['Order Status'] == 'Canceled']) / len(cod_orders) * 100 if len(cod_orders) > 0 else 0
            non_cod_cancel_rate = len(non_cod_orders[non_cod_orders['Order Status'] == 'Canceled']) / len(non_cod_orders) * 100 if len(non_cod_orders) > 0 else 0

            compare_df = pd.DataFrame({
                '결제유형': ['COD/현금', '선결제'],
                '주문수': [len(cod_orders), len(non_cod_orders)],
                '취소율(%)': [cod_cancel_rate, non_cod_cancel_rate]
            })

            fig_compare = px.bar(
                compare_df, x='결제유형', y='취소율(%)', title='COD vs 선결제 취소율 비교',
                color='결제유형', color_discrete_map={'COD/현금': '#f44336', '선결제': '#4CAF50'}, text='취소율(%)'
            )
            fig_compare.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_compare, use_container_width=True)

            st.info(f"""
            **COD/현금**: {len(cod_orders):,}건 (취소율 {cod_cancel_rate:.1f}%)
            **선결제**: {len(non_cod_orders):,}건 (취소율 {non_cod_cancel_rate:.1f}%)
            """)

        with st.expander("📋 Payment Method별 상세 데이터"):
            payment_display = payment_df.copy()
            payment_display['전체매출'] = payment_display['전체매출'].apply(lambda x: f"Rp {x:,.0f}")
            st.dataframe(payment_display, use_container_width=True)

    # Footer
    st.markdown("---")
    st.caption("📊 데이터는 Google Sheets에서 자동으로 불러옵니다.")


# ===== MAIN APP ROUTING =====
if not st.session_state.authenticated:
    if is_admin_route():
        show_admin_login_page()
    else:
        show_brand_login_page()
elif st.session_state.is_admin:
    show_admin_panel()
else:
    show_brand_dashboard()
