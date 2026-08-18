import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Canadian Grocery Price Intelligence (2017–2026)",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for a clean, friendly interface
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .receipt-box {
        background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
        border: 2px solid #CBD5E1;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .receipt-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .receipt-price {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        margin: 0.3rem 0;
    }
    .receipt-change {
        font-size: 1.05rem;
        font-weight: 700;
        color: #DC2626;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    base = os.path.dirname(__file__)
    data_path = os.path.join(base, "data", "export", "grocery_index_extract.csv")
    if not os.path.exists(data_path):
        data_path = os.path.join(base, "data", "sample", "statcan_grocery_sample.csv")

    df = pd.read_csv(data_path)
    df["SnapshotDate"] = pd.to_datetime(df["SnapshotDate"])
    df["AveragePrice"] = pd.to_numeric(df["AveragePrice"], errors="coerce")
    if "MoM_PercentageChange" in df.columns:
        df["MoM_PercentageChange"] = pd.to_numeric(df["MoM_PercentageChange"], errors="coerce")
    return df


df_gold = load_data()

# ----------------- SIDEBAR CONTROLS -----------------
st.sidebar.header("📍 Select Region")
all_geos = sorted(df_gold["Geography"].unique())
default_geo = "Canada" if "Canada" in all_geos else all_geos[0]
selected_geo = st.sidebar.selectbox("Jurisdiction", all_geos, index=all_geos.index(default_geo))

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **About this data:**
    * **Source:** Statistics Canada (Table 18-10-0245-01)
    * **Scope:** 2017 to 2026 (Monthly Survey)
    * **Pipeline:** Built with PySpark & Delta Lake
    """
)

# Filter dataset to selected geography
df_geo = df_gold[df_gold["Geography"] == selected_geo].copy()

# ----------------- HEADER & OVERVIEW -----------------
st.markdown(
    '<div class="main-title">🇨🇦 What Happened to Canadian Grocery Prices? (2017–2026)</div>',
    unsafe_allow_html=True,
)
sub_text = (
    f"Tracking real monthly supermarket prices for staple foods across "
    f"<b>{selected_geo}</b> over the past 9+ years."
)
st.markdown(f'<div class="sub-title">{sub_text}</div>', unsafe_allow_html=True)

# ----------------- SECTION 1: GROCERY RECEIPT SIMULATOR -----------------
st.subheader("🛒 1. The Grocery Cart Simulator: 2017 vs. Today")
st.caption(
    "Choose grocery staples to see what the exact same shopping bag cost in 2017 compared to today."
)

all_products = sorted(df_geo["ProductName"].unique())
keywords = [
    "eggs, 1 dozen",
    "butter, 454",
    "milk, 2",
    "white bread",
    "bacon, 500",
    "chicken breasts, per",
    "beef stewing",
    "bananas",
]
default_cart = [p for p in all_products if any(k in p.lower() for k in keywords)]
if not default_cart:
    default_cart = all_products[:5]

selected_cart = st.multiselect(
    "Select items in your grocery basket:",
    options=all_products,
    default=default_cart,
)

if selected_cart:
    cart_df = df_geo[df_geo["ProductName"].isin(selected_cart)].copy()

    earliest_date = cart_df["SnapshotDate"].min()
    latest_date = cart_df["SnapshotDate"].max()

    p_2017_total = 0.0
    p_2026_total = 0.0
    item_breakdown = []

    for item in selected_cart:
        item_df = cart_df[cart_df["ProductName"] == item].sort_values("SnapshotDate")
        if not item_df.empty:
            p_start = item_df["AveragePrice"].iloc[0]
            p_end = item_df["AveragePrice"].iloc[-1]
            diff = p_end - p_start
            pct = ((p_end - p_start) / p_start) * 100 if p_start > 0 else 0
            p_2017_total += p_start
            p_2026_total += p_end
            item_breakdown.append(
                {
                    "Grocery Item": item,
                    "2017 Price": f"${p_start:.2f}",
                    "2026 Price": f"${p_end:.2f}",
                    "Dollar Increase": f"+${diff:.2f}",
                    "% Increase": f"{pct:+.1f}%",
                }
            )

    total_diff = p_2026_total - p_2017_total
    total_pct = ((p_2026_total - p_2017_total) / p_2017_total) * 100 if p_2017_total > 0 else 0

    col_r1, col_r2, col_r3 = st.columns(3)
    start_label = earliest_date.strftime("%B %Y")
    end_label = latest_date.strftime("%B %Y")

    with col_r1:
        st.markdown(
            f"""
            <div class="receipt-box">
                <div class="receipt-label">📅 2017 Cart Total</div>
                <div class="receipt-price">${p_2017_total:.2f}</div>
                <div style="font-size: 0.85rem; color: #64748B;">
                    {len(selected_cart)} items ({start_label})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_r2:
        st.markdown(
            f"""
            <div class="receipt-box" style="border-color: #EF4444; background: #FEF2F2;">
                <div class="receipt-label" style="color: #991B1B;">📅 2026 Cart Total</div>
                <div class="receipt-price" style="color: #991B1B;">${p_2026_total:.2f}</div>
                <div style="font-size: 0.85rem; color: #991B1B;">
                    {len(selected_cart)} items ({end_label})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_r3:
        st.markdown(
            f"""
            <div class="receipt-box" style="border-color: #DC2626; background: #FFF1F2;">
                <div class="receipt-label" style="color: #9F1239;">💸 Extra Out of Pocket</div>
                <div class="receipt-price" style="color: #DC2626;">+${total_diff:.2f}</div>
                <div class="receipt-change">+{total_pct:.1f}% more expensive</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📋 View Itemized Price Breakdown Table"):
        st.dataframe(pd.DataFrame(item_breakdown), use_container_width=True, hide_index=True)
else:
    st.info("Please select at least one grocery item above to calculate your cart total.")

st.markdown("---")

# ----------------- SECTION 2: FOCUSED PRICE EXPLORER -----------------
st.subheader("📈 2. Interactive Price Explorer (1-on-1 Comparison)")
st.caption(
    "Select an item to see its monthly price timeline from 2017 to 2026 with key economic events."
)

col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    primary_item = st.selectbox(
        "Primary Grocery Item:",
        all_products,
        index=all_products.index("Eggs, 1 dozen") if "Eggs, 1 dozen" in all_products else 0,
    )
with col_sel2:
    compare_options = ["None"] + [p for p in all_products if p != primary_item]
    compare_item = st.selectbox("Compare With (Optional):", compare_options, index=0)

active_items = [primary_item]
if compare_item != "None":
    active_items.append(compare_item)

explore_df = df_geo[df_geo["ProductName"].isin(active_items)].copy()

fig_line = go.Figure()

colors = ["#2563EB", "#DC2626"]
for idx, item_name in enumerate(active_items):
    sub_df = explore_df[explore_df["ProductName"] == item_name].sort_values("SnapshotDate")
    fig_line.add_trace(
        go.Scatter(
            x=sub_df["SnapshotDate"],
            y=sub_df["AveragePrice"],
            mode="lines",
            name=item_name,
            line=dict(width=3, color=colors[idx % len(colors)]),
            hovertemplate="<b>%{x|%b %Y}</b><br>Price: <b>$%{y:.2f}</b><extra></extra>",
        )
    )

# Add event annotations
fig_line.add_vline(
    x="2020-03-01",
    line_dash="dot",
    line_color="#64748B",
    annotation_text="COVID Supply Shock (2020)",
)
fig_line.add_vline(
    x="2022-06-01",
    line_dash="dot",
    line_color="#DC2626",
    annotation_text="Peak Inflation (2022)",
)

title_text = f"Price History: {' vs '.join(active_items)} ({selected_geo})"
fig_line.update_layout(
    title=dict(text=title_text, font=dict(size=16)),
    xaxis=dict(title="Survey Year", showgrid=True, gridcolor="#F1F5F9"),
    yaxis=dict(title="Average Price ($CAD)", tickprefix="$", showgrid=True, gridcolor="#F1F5F9"),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
    height=440,
    plot_bgcolor="white",
    margin=dict(l=20, r=20, t=40, b=20),
)

st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

# ----------------- SECTION 3: INFLATION LEADERBOARD & WORST YEARS -----------------
col_chart_l, col_chart_r = st.columns(2)

with col_chart_l:
    st.subheader("🏆 3. Inflation Leaderboard (2017 → 2026)")
    st.caption("Which staple items had the highest percentage price increase?")

    all_summary = []
    for prod_name, group in df_geo.groupby("ProductName"):
        sorted_g = group.sort_values("SnapshotDate")
        if len(sorted_g) >= 2:
            p_s = sorted_g["AveragePrice"].iloc[0]
            p_e = sorted_g["AveragePrice"].iloc[-1]
            pct = ((p_e - p_s) / p_s) * 100 if p_s > 0 else 0
            all_summary.append(
                {
                    "Product": prod_name,
                    "Cumulative Inflation (%)": round(pct, 1),
                    "2017 Price": f"${p_s:.2f}",
                    "2026 Price": f"${p_e:.2f}",
                }
            )

    leader_df = pd.DataFrame(all_summary).sort_values("Cumulative Inflation (%)", ascending=True)

    fig_rank = px.bar(
        leader_df,
        x="Cumulative Inflation (%)",
        y="Product",
        orientation="h",
        color="Cumulative Inflation (%)",
        color_continuous_scale=["#10B981", "#F59E0B", "#EF4444", "#991B1B"],
        text="Cumulative Inflation (%)",
        title=f"Total Price Increase from 2017 to 2026 ({selected_geo})",
    )
    fig_rank.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
    fig_rank.update_layout(
        height=420,
        plot_bgcolor="white",
        margin=dict(l=10, r=30, t=40, b=10),
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
    )
    st.plotly_chart(fig_rank, use_container_width=True)

with col_chart_r:
    st.subheader("📅 4. The Worst Inflation Years")
    st.caption("Average year-over-year food inflation rate across all staples.")

    df_geo["Year"] = df_geo["SnapshotDate"].dt.year
    yearly_avg = df_geo.groupby("Year")["AveragePrice"].mean().reset_index()
    yearly_avg["YoY_Change"] = yearly_avg["AveragePrice"].pct_change() * 100
    yearly_clean = yearly_avg.dropna(subset=["YoY_Change"])

    fig_yearly = px.bar(
        yearly_clean,
        x="Year",
        y="YoY_Change",
        color="YoY_Change",
        color_continuous_scale="Reds",
        text="YoY_Change",
        title=f"Average Annual Price Change % ({selected_geo})",
        labels={"YoY_Change": "Annual Inflation (%)", "Year": "Year"},
    )
    fig_yearly.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
    fig_yearly.update_layout(
        height=420,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", ticksuffix="%"),
    )
    st.plotly_chart(fig_yearly, use_container_width=True)

# ----------------- SECTION 5: DATA LINEAGE & DOWNLOAD -----------------
st.markdown("---")
with st.expander("🔍 View & Download Curated Gold Records"):
    table_cols = [
        "SnapshotDate",
        "Geography",
        "BasketCategory",
        "ProductName",
        "UOM",
        "AveragePrice",
        "PreviousMonthPrice",
        "MoM_PercentageChange",
        "GoldRecordId",
    ]
    sorted_df = df_geo[table_cols].sort_values(
        ["SnapshotDate", "ProductName"], ascending=[False, True]
    )
    st.dataframe(
        sorted_df,
        use_container_width=True,
        hide_index=True,
    )
    csv_bytes = df_geo.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Gold Dataset (CSV)",
        data=csv_bytes,
        file_name=f"grocery_prices_{selected_geo.lower()}_gold.csv",
        mime="text/csv",
    )

with st.expander("🏛️ Data Engineering Pipeline & Architecture"):
    st.markdown(
        """
        ### Medallion Lakehouse Architecture
        * **Bronze Tier (Raw Ingestion):** Ingests raw Statistics Canada Table 18-10-0245-01 CSVs
          with automated UTF-8 BOM (`\\ufeff`) sanitization and batch audit metadata (`_batch_id`,
          `ingestion_timestamp`).
        * **Silver Tier (Cleansing & Quality):** Standardizes types, trims strings, generates
          deterministic SHA-256 surrogate keys (`RecordId`), and routes malformed/duplicate rows to
          a **Dead-Letter Quarantine Table** (`quarantine_reason`).
        * **Gold Tier (Analytics & Windowing):** Applies decoupled regex taxonomy matching and
          executes strict consecutive calendar-month window analytics (`F.lag`) to compute valid
          MoM price changes.
        * **Serving Tier:** Powers this interactive Streamlit application.
        """
    )
