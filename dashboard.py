import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Order Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Order Analytics Dashboard")
st.markdown("---")

# Google Sheets URL
SHEET_ID = "1sGARLhKbDMMLm9V4XkSl0xBt9tcCXpZXIM4R8o9F95U"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# 데이터 로드
@st.cache_data(ttl=300)  # 5분마다 새로고침
def load_data_from_sheets():
    try:
        df = pd.read_csv(SHEET_URL)
        # 헤더 행 제거
        if 'Created Time' in df.columns:
            df = df[df['Created Time'] != 'Order created time.'].copy()
        df['Order Amount'] = pd.to_numeric(df['Order Amount'], errors='coerce')
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
        # 날짜 변환
        df['Created Date'] = pd.to_datetime(df['Created Time'], format='%d/%m/%Y %H:%M:%S', errors='coerce').dt.date
        return df, None
    except Exception as e:
        return None, str(e)

# 데이터 로드 시도
with st.spinner("데이터를 불러오는 중..."):
    df, error = load_data_from_sheets()

if error:
    st.error(f"데이터 로드 실패: {error}")
    st.info("Google Sheets 공유 설정을 확인해주세요. (링크가 있는 모든 사용자 - 뷰어)")
    st.stop()

if df is None or len(df) == 0:
    st.warning("데이터가 없습니다. Google Sheets에 데이터를 추가해주세요.")
    st.stop()

# 새로고침 버튼 및 날짜 필터
col_refresh, col_info = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    st.caption(f"전체 데이터: {len(df):,}행")

# ===== 날짜 필터 =====
st.subheader("📅 기간 선택")

min_date = df['Created Date'].min()
max_date = df['Created Date'].max()

# 월 목록 생성
df['Year-Month'] = pd.to_datetime(df['Created Date']).apply(lambda x: x.strftime('%Y-%m') if pd.notna(x) else None)
available_months = sorted(df['Year-Month'].dropna().unique(), reverse=True)

# 월 선택
col_month, col_filter1, col_filter2 = st.columns([1, 1, 1])

with col_month:
    month_options = ["전체 기간"] + list(available_months)
    selected_month = st.selectbox(
        "월 선택",
        options=month_options,
        index=0
    )

# 월 선택에 따른 날짜 범위 설정
if selected_month != "전체 기간":
    year, month = map(int, selected_month.split('-'))
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    default_start = pd.Timestamp(year, month, 1).date()
    default_end = pd.Timestamp(year, month, last_day).date()
else:
    default_start = min_date
    default_end = max_date

with col_filter1:
    start_date = st.date_input(
        "시작일",
        value=default_start,
        min_value=min_date,
        max_value=max_date
    )

with col_filter2:
    end_date = st.date_input(
        "종료일",
        value=default_end,
        min_value=min_date,
        max_value=max_date
    )

# 빠른 선택 버튼
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

# 날짜 필터 적용
df = df[(df['Created Date'] >= start_date) & (df['Created Date'] <= end_date)]

st.info(f"📊 선택된 기간: **{start_date}** ~ **{end_date}** ({len(df):,}행)")

st.markdown("---")

# Order ID별 정보 (중복 제거)
order_info = df.groupby('Order ID').agg({
    'Order Amount': 'first',
    'Order Status': 'first',
    'Created Date': 'first',
    'Payment Method': 'first',
    'Tracking ID': 'first'
}).reset_index()

# ===== 1. 주요 KPI 카드 =====
st.header("📈 주요 지표")

total_orders = len(order_info)
total_amount = order_info['Order Amount'].sum()
canceled_orders = order_info[order_info['Order Status'] == 'Canceled']
cancel_count = len(canceled_orders)
cancel_rate = cancel_count / total_orders * 100 if total_orders > 0 else 0
cancel_amount = canceled_orders['Order Amount'].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="총 주문 수",
        value=f"{total_orders:,}건"
    )

with col2:
    st.metric(
        label="총 주문 금액",
        value=f"Rp {total_amount:,.0f}"
    )

with col3:
    st.metric(
        label="취소 주문 수",
        value=f"{cancel_count:,}건",
        delta=f"{cancel_rate:.1f}%",
        delta_color="inverse"
    )

with col4:
    st.metric(
        label="취소 금액",
        value=f"Rp {cancel_amount:,.0f}"
    )

st.markdown("---")

# ===== 2. Order Status 분포 =====
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Order Status 분포")
    status_dist = order_info.groupby('Order Status').agg({
        'Order ID': 'count',
        'Order Amount': 'sum'
    }).reset_index()
    status_dist.columns = ['Order Status', 'Count', 'Amount']

    fig_status = px.pie(
        status_dist,
        values='Count',
        names='Order Status',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_status.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_status, use_container_width=True)

with col2:
    st.subheader("💰 Status별 금액")
    fig_amount = px.bar(
        status_dist,
        x='Order Status',
        y='Amount',
        color='Order Status',
        text_auto='.2s',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_amount.update_layout(showlegend=False)
    st.plotly_chart(fig_amount, use_container_width=True)

st.markdown("---")

# ===== 3. 날짜별 추이 =====
st.subheader("📅 날짜별 주문/취소 추이")

daily_all = order_info.groupby('Created Date').agg({
    'Order ID': 'count',
    'Order Amount': 'sum'
}).rename(columns={'Order ID': '전체주문수', 'Order Amount': '전체매출'})

daily_canceled = order_info[order_info['Order Status'] == 'Canceled'].groupby('Created Date').agg({
    'Order ID': 'count',
    'Order Amount': 'sum'
}).rename(columns={'Order ID': '취소주문수', 'Order Amount': '취소매출'})

daily_summary = daily_all.join(daily_canceled).fillna(0).reset_index()
daily_summary['취소율(%)'] = (daily_summary['취소주문수'] / daily_summary['전체주문수'] * 100).round(1)

# 복합 차트
fig_daily = make_subplots(specs=[[{"secondary_y": True}]])

fig_daily.add_trace(
    go.Bar(name='전체 주문', x=daily_summary['Created Date'], y=daily_summary['전체주문수'],
           marker_color='#4CAF50', opacity=0.7),
    secondary_y=False
)

fig_daily.add_trace(
    go.Bar(name='취소 주문', x=daily_summary['Created Date'], y=daily_summary['취소주문수'],
           marker_color='#f44336', opacity=0.7),
    secondary_y=False
)

fig_daily.add_trace(
    go.Scatter(name='취소율(%)', x=daily_summary['Created Date'], y=daily_summary['취소율(%)'],
               mode='lines+markers', line=dict(color='#FF9800', width=2)),
    secondary_y=True
)

fig_daily.update_layout(barmode='overlay', height=400)
fig_daily.update_yaxes(title_text="주문 수", secondary_y=False)
fig_daily.update_yaxes(title_text="취소율 (%)", secondary_y=True)

st.plotly_chart(fig_daily, use_container_width=True)

# 날짜별 테이블
with st.expander("📋 날짜별 상세 데이터"):
    daily_display = daily_summary.copy()
    daily_display['전체매출'] = daily_display['전체매출'].apply(lambda x: f"Rp {x:,.0f}")
    daily_display['취소매출'] = daily_display['취소매출'].apply(lambda x: f"Rp {x:,.0f}")
    st.dataframe(daily_display, use_container_width=True)

st.markdown("---")

# ===== 4. SKU별 현황 =====
st.subheader("📦 Seller SKU별 주문/취소 현황")

sku_all = df.groupby('Seller SKU').agg({
    'Quantity': 'sum',
    'Order ID': 'nunique'
}).rename(columns={'Quantity': '전체수량', 'Order ID': '전체주문건수'})

sku_canceled = df[df['Order Status'] == 'Canceled'].groupby('Seller SKU').agg({
    'Quantity': 'sum'
}).rename(columns={'Quantity': '취소수량'})

sku_summary = sku_all.join(sku_canceled).fillna(0).reset_index()
sku_summary['정상수량'] = sku_summary['전체수량'] - sku_summary['취소수량']
sku_summary['취소율(%)'] = (sku_summary['취소수량'] / sku_summary['전체수량'] * 100).round(1)
sku_summary = sku_summary.sort_values('전체수량', ascending=False)

col1, col2 = st.columns(2)

with col1:
    # 상위 10개 SKU
    top_sku = sku_summary.head(10)
    fig_sku = px.bar(
        top_sku,
        x='Seller SKU',
        y=['정상수량', '취소수량'],
        barmode='stack',
        title='상위 10개 SKU 판매 현황',
        color_discrete_map={'정상수량': '#4CAF50', '취소수량': '#f44336'}
    )
    st.plotly_chart(fig_sku, use_container_width=True)

with col2:
    # 취소율 높은 SKU (최소 10개 이상)
    high_cancel_sku = sku_summary[sku_summary['전체수량'] >= 10].nlargest(10, '취소율(%)')
    fig_cancel_sku = px.bar(
        high_cancel_sku,
        x='Seller SKU',
        y='취소율(%)',
        title='취소율 상위 10개 SKU (최소 10개 이상 주문)',
        color='취소율(%)',
        color_continuous_scale='Reds'
    )
    st.plotly_chart(fig_cancel_sku, use_container_width=True)

with st.expander("📋 SKU별 상세 데이터"):
    st.dataframe(sku_summary, use_container_width=True)

st.markdown("---")

# ===== 5. 취소 주문 출고 여부 =====
st.subheader("🚚 취소 주문의 출고 여부 (Tracking ID 기준)")

canceled_orders_detail = df[df['Order Status'] == 'Canceled'].groupby('Order ID').agg({
    'Order Amount': 'first',
    'Tracking ID': 'first',
    'Cancel By': 'first',
    'Cancel Reason': 'first'
}).reset_index()

canceled_orders_detail['출고여부'] = canceled_orders_detail['Tracking ID'].notna() & (canceled_orders_detail['Tracking ID'] != '')
canceled_orders_detail['출고여부'] = canceled_orders_detail['출고여부'].map({True: '출고됨', False: '미출고'})

col1, col2, col3 = st.columns(3)

shipped = canceled_orders_detail[canceled_orders_detail['출고여부'] == '출고됨']
not_shipped = canceled_orders_detail[canceled_orders_detail['출고여부'] == '미출고']

with col1:
    ship_summary = canceled_orders_detail.groupby('출고여부').agg({
        'Order ID': 'count',
        'Order Amount': 'sum'
    }).reset_index()
    ship_summary.columns = ['출고여부', 'Count', 'Amount']

    fig_ship = px.pie(
        ship_summary,
        values='Count',
        names='출고여부',
        hole=0.4,
        color_discrete_map={'출고됨': '#FF9800', '미출고': '#9E9E9E'}
    )
    fig_ship.update_traces(textposition='inside', textinfo='percent+value')
    st.plotly_chart(fig_ship, use_container_width=True)

with col2:
    st.metric("출고 후 취소", f"{len(shipped):,}건", f"Rp {shipped['Order Amount'].sum():,.0f}")
    st.metric("미출고 취소", f"{len(not_shipped):,}건", f"Rp {not_shipped['Order Amount'].sum():,.0f}")

with col3:
    # Cancel Reason 분석 (출고된 것만)
    if len(shipped) > 0:
        cancel_reason = shipped['Cancel Reason'].value_counts().head(5).reset_index()
        cancel_reason.columns = ['Cancel Reason', 'Count']
        fig_reason = px.bar(
            cancel_reason,
            x='Count',
            y='Cancel Reason',
            orientation='h',
            title='출고 후 취소 사유 TOP 5',
            color_discrete_sequence=['#FF9800']
        )
        fig_reason.update_layout(height=300)
        st.plotly_chart(fig_reason, use_container_width=True)

st.markdown("---")

# ===== 6. Payment Method 분석 =====
st.subheader("💳 Payment Method별 현황")

payment_summary = order_info.groupby('Payment Method').agg({
    'Order ID': 'count',
    'Order Amount': 'sum'
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
        payment_df.head(10),
        x='Payment Method',
        y='전체주문수',
        title='Payment Method별 주문 수',
        color='취소율(%)',
        color_continuous_scale='RdYlGn_r'
    )
    fig_payment.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_payment, use_container_width=True)

with col2:
    # COD vs 선결제 비교
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
        compare_df,
        x='결제유형',
        y='취소율(%)',
        title='COD vs 선결제 취소율 비교',
        color='결제유형',
        color_discrete_map={'COD/현금': '#f44336', '선결제': '#4CAF50'},
        text='취소율(%)'
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
st.caption("📊 데이터는 Google Sheets에서 자동으로 불러옵니다. 매주 Google Sheets를 업데이트하면 대시보드에 반영됩니다.")
