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

    # Tabs: Dashboard and Upload
    tab1, tab2 = st.tabs(["📈 Dashboard", "📤 Upload Data"])

    with tab1:
        show_dashboard_content(sheet_id)

    with tab2:
        show_upload_section(sheet_id, brand_name)


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
                with st.spinner("Uploading data..."):
                    rows_added, error = sheets_manager.append_data_to_sheet(sheet_id, df_upload)
                    if error:
                        st.error(f"Upload failed: {error}")
                    else:
                        st.success(f"Successfully appended **{rows_added:,}** rows to the sheet!")
                        st.cache_data.clear()
                        st.balloons()

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")


def show_dashboard_content(sheet_id: str):
    # Load data
    @st.cache_data(ttl=300)
    def load_data(sid):
        return sheets_manager.read_sheet_data(sid)

    # Refresh button
    col_refresh, col_info = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 데이터 새로고침"):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("데이터를 불러오는 중..."):
        df, error = load_data(sheet_id)

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
        df['Created Date'] = pd.to_datetime(df['Created Time'], format='%d/%m/%Y %H:%M:%S', errors='coerce').dt.date

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

    col_month, col_filter1, col_filter2 = st.columns([1, 1, 1])

    with col_month:
        month_options = ["전체 기간"] + list(available_months)
        selected_month = st.selectbox("월 선택", options=month_options, index=0)

    if selected_month != "전체 기간":
        year, month = map(int, selected_month.split('-'))
        last_day = calendar.monthrange(year, month)[1]
        default_start = pd.Timestamp(year, month, 1).date()
        default_end = pd.Timestamp(year, month, last_day).date()
        default_start = max(default_start, min_date)
        default_end = min(default_end, max_date)
    else:
        default_start = min_date
        default_end = max_date

    with col_filter1:
        start_date = st.date_input("시작일", value=default_start, min_value=min_date, max_value=max_date)

    with col_filter2:
        end_date = st.date_input("종료일", value=default_end, min_value=min_date, max_value=max_date)

    # Quick selection buttons
    st.write("빠른 선택:")
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)

    with quick_col1:
        if st.button("최근 7일"):
            st.session_state['start_date'] = max_date - pd.Timedelta(days=6)
            st.session_state['end_date'] = max_date
            st.rerun()
    with quick_col2:
        if st.button("최근 14일"):
            st.session_state['start_date'] = max_date - pd.Timedelta(days=13)
            st.session_state['end_date'] = max_date
            st.rerun()
    with quick_col3:
        if st.button("최근 30일"):
            st.session_state['start_date'] = max_date - pd.Timedelta(days=29)
            st.session_state['end_date'] = max_date
            st.rerun()
    with quick_col4:
        if st.button("전체"):
            st.session_state['start_date'] = min_date
            st.session_state['end_date'] = max_date
            st.rerun()

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

        sku_summary['Product Name Short'] = sku_summary.get('Product Name', sku_summary['Seller SKU']).apply(
            lambda x: x[:30] + '...' if isinstance(x, str) and len(x) > 30 else x
        )

        col1, col2 = st.columns(2)

        with col1:
            top_sku = sku_summary.head(10)
            fig_sku = px.bar(
                top_sku, x='Product Name Short', y=['정상수량', '취소수량'], barmode='stack',
                title='상위 10개 제품 판매 현황',
                color_discrete_map={'정상수량': '#4CAF50', '취소수량': '#f44336'}
            )
            fig_sku.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_sku, use_container_width=True)

        with col2:
            high_cancel_sku = sku_summary[sku_summary['전체수량'] >= 10].nlargest(10, '취소율(%)')
            fig_cancel_sku = px.bar(
                high_cancel_sku, x='Product Name Short', y='취소율(%)',
                title='취소율 상위 10개 제품 (최소 10개 이상 주문)',
                color='취소율(%)', color_continuous_scale='Reds'
            )
            fig_cancel_sku.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_cancel_sku, use_container_width=True)

        with st.expander("📋 제품별 상세 데이터"):
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
