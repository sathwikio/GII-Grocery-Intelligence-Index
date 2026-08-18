import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------- PAGE CONFIGURATION -----------------
st.set_page_config(
    page_title="Canadian Grocery Price Intelligence (2017–2026)",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------- DESIGN SYSTEM CSS -----------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .app-header-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #0F172A;
        margin-bottom: 0.25rem;
    }
    .app-header-sub {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.75rem;
        line-height: 1.5;
    }
    .checkout-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.06);
        margin-bottom: 1.5rem;
    }
    .checkout-badge {
        display: inline-block;
        background: #EEF2FF;
        color: #4F46E5;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 0.3rem 0.75rem;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.75rem;
    }
    .checkout-val-lg {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }
    .checkout-label {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
        margin-top: 0.25rem;
    }
    .stat-chip {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    .stat-chip-label {
        font-size: 0.8rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .stat-chip-value {
        font-size: 1.4rem;
        font-weight: 800;
        color: #0F172A;
        margin-top: 0.25rem;
    }
    .era-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.25rem;
        box-shadow: 0 2px 8px -2px rgba(15, 23, 42, 0.04);
    }
    .era-pill {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    .era-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.35rem;
    }
    .era-desc {
        font-size: 0.88rem;
        color: #475569;
        line-height: 1.45;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------- DATA LOADER -----------------
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
st.sidebar.markdown("### 📍 Location & Context")
all_geos = sorted(df_gold["Geography"].unique())
default_geo = "Canada" if "Canada" in all_geos else all_geos[0]
selected_geo = st.sidebar.selectbox("Jurisdiction", all_geos, index=all_geos.index(default_geo))

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Project Metadata:**
    * **Data Source:** Statistics Canada (Table 18-10-0245-01)
    * **Observations:** 2017 to 2026 Monthly Survey
    * **Engine:** PySpark Medallion Lakehouse on Delta Lake
    """
)

df_geo = df_gold[df_gold["Geography"] == selected_geo].copy()

# ----------------- APP HEADER -----------------
st.markdown(
    '<div class="app-header-title">🇨🇦 Canadian Grocery Price Intelligence</div>',
    unsafe_allow_html=True,
)
header_sub = (
    f"An interactive price tracker examining 9+ years of monthly supermarket price changes "
    f"across <b>{selected_geo}</b> (January 2017 – June 2026)."
)
st.markdown(f'<div class="app-header-sub">{header_sub}</div>', unsafe_allow_html=True)

# ----------------- 1. HERO CHECKOUT SIMULATOR -----------------
st.subheader("🛒 1. The Grocery Cart Simulator")
st.caption(
    "Select everyday staples to see what the exact same basket cost in 2017 compared to today."
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
    default_cart = all_products[:6]

selected_cart = st.multiselect(
    "Items in your grocery cart:",
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
                    "Dollar Jump": f"+${diff:.2f}",
                    "Total Inflation": f"{pct:+.1f}%",
                }
            )

    total_diff = p_2026_total - p_2017_total
    total_pct = ((p_2026_total - p_2017_total) / p_2017_total) * 100 if p_2017_total > 0 else 0

    baseline_ratio = (p_2017_total / p_2026_total) * 100 if p_2026_total > 0 else 100
    inflation_ratio = 100 - baseline_ratio

    checkout_badge = f"🛒 Basket Comparison ({len(selected_cart)} items)"
    checkout_html = f"""
    <div class="checkout-card">
        <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
            <div>
                <span class="checkout-badge">{checkout_badge}</span>
                <div style="font-size: 1.1rem; color: #1E293B; font-weight: 700;">
                    {selected_geo} Staple Basket Total
                </div>
            </div>
            <div>
                <span style="background: #FEE2E2; color: #991B1B; font-weight: 700;
                             font-size: 0.9rem; padding: 0.35rem 0.85rem; border-radius: 9999px;">
                    +{total_pct:.1f}% Total Increase
                </span>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1.5rem; margin: 1.25rem 0; padding: 1rem 0;
                    border-top: 1px solid #F1F5F9; border-bottom: 1px solid #F1F5F9;">
            <div>
                <div class="checkout-label">📅 2017 Baseline Total</div>
                <div class="checkout-val-lg" style="color: #0F172A;">${p_2017_total:.2f}</div>
                <div style="font-size: 0.8rem; color: #64748B;">
                    {earliest_date.strftime("%B %Y")}
                </div>
            </div>
            <div>
                <div class="checkout-label">📅 2026 Current Total</div>
                <div class="checkout-val-lg" style="color: #0F172A;">${p_2026_total:.2f}</div>
                <div style="font-size: 0.8rem; color: #64748B;">
                    {latest_date.strftime("%B %Y")}
                </div>
            </div>
            <div>
                <div class="checkout-label">💸 Extra Out-of-Pocket</div>
                <div class="checkout-val-lg" style="color: #DC2626;">+${total_diff:.2f}</div>
                <div style="font-size: 0.8rem; color: #DC2626; font-weight: 600;">
                    More for the same cart
                </div>
            </div>
        </div>
        <div>
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem;
                        font-weight: 600; color: #64748B; margin-bottom: 0.4rem;">
                <span>2017 Baseline ({baseline_ratio:.1f}%)</span>
                <span>Inflation Surcharge ({inflation_ratio:.1f}%)</span>
            </div>
            <div style="height: 10px; width: 100%; background: #F1F5F9; border-radius: 9999px;
                        overflow: hidden; display: flex;">
                <div style="width: {baseline_ratio}%; background: #6366F1; height: 100%;"></div>
                <div style="width: {inflation_ratio}%; background: #EF4444; height: 100%;"></div>
            </div>
        </div>
    </div>
    """
    st.markdown(checkout_html, unsafe_allow_html=True)

    with st.expander("📋 View Itemized Price Breakdown Table"):
        st.dataframe(pd.DataFrame(item_breakdown), use_container_width=True, hide_index=True)
else:
    st.info("Select at least one grocery item to calculate your cart total.")

st.markdown("---")

# ----------------- 2. FOCUSED 1-ON-1 PRICE TRAJECTORY -----------------
st.subheader("📈 2. Interactive Price Explorer")
st.caption(
    "Explore the 9-year historical curve for an individual product with economic milestone markers."
)

col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    primary_item = st.selectbox(
        "Primary Product:",
        all_products,
        index=all_products.index("Eggs, 1 dozen") if "Eggs, 1 dozen" in all_products else 0,
    )
with col_ctrl2:
    compare_options = ["None"] + [p for p in all_products if p != primary_item]
    compare_item = st.selectbox("Compare With (Optional):", compare_options, index=0)

active_items = [primary_item]
if compare_item != "None":
    active_items.append(compare_item)

prim_df = df_geo[df_geo["ProductName"] == primary_item].sort_values("SnapshotDate")
p_init = prim_df["AveragePrice"].iloc[0] if not prim_df.empty else 0
p_now = prim_df["AveragePrice"].iloc[-1] if not prim_df.empty else 0
peak_row = prim_df.loc[prim_df["AveragePrice"].idxmax()] if not prim_df.empty else None
p_peak = peak_row["AveragePrice"] if peak_row is not None else 0
p_peak_dt = peak_row["SnapshotDate"].strftime("%b %Y") if peak_row is not None else "N/A"
diff_prim = p_now - p_init
pct_prim = ((p_now - p_init) / p_init) * 100 if p_init > 0 else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""
        <div class="stat-chip">
            <div class="stat-chip-label">Jan 2017 Base</div>
            <div class="stat-chip-value">${p_init:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""
        <div class="stat-chip">
            <div class="stat-chip-label">Peak ({p_peak_dt})</div>
            <div class="stat-chip-value">${p_peak:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""
        <div class="stat-chip">
            <div class="stat-chip-label">Current (Jun 2026)</div>
            <div class="stat-chip-value">${p_now:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c4:
    diff_val_str = f"+${diff_prim:.2f} ({pct_prim:+.1f}%)"
    st.markdown(
        f"""
        <div class="stat-chip" style="border-color: #FCA5A5; background: #FEF2F2;">
            <div class="stat-chip-label" style="color: #991B1B;">Cumulative Change</div>
            <div class="stat-chip-value" style="color: #DC2626;">{diff_val_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

fig_price = go.Figure()
colors = ["#4F46E5", "#F43F5E"]
fill_colors = ["rgba(79, 70, 229, 0.08)", "rgba(244, 63, 94, 0.08)"]

for idx, item in enumerate(active_items):
    sub = df_geo[df_geo["ProductName"] == item].sort_values("SnapshotDate")
    fig_price.add_trace(
        go.Scatter(
            x=sub["SnapshotDate"],
            y=sub["AveragePrice"],
            mode="lines",
            name=item,
            line=dict(width=3.5, color=colors[idx % len(colors)], shape="spline"),
            fill="tozeroy" if idx == 0 and len(active_items) == 1 else "none",
            fillcolor=fill_colors[idx % len(fill_colors)],
            hovertemplate="<b>%{x|%B %Y}</b><br>Price: <b>$%{y:.2f} CAD</b><extra></extra>",
        )
    )

fig_price.add_vline(
    x="2020-03-01",
    line_dash="dash",
    line_color="#94A3B8",
    line_width=1.5,
    annotation_text="COVID-19 Shock (Mar 2020)",
    annotation_position="top left",
    annotation_font=dict(size=11, color="#64748B"),
)
fig_price.add_vline(
    x="2022-06-01",
    line_dash="dash",
    line_color="#F43F5E",
    line_width=1.5,
    annotation_text="Peak Inflation (Jun 2022)",
    annotation_position="top left",
    annotation_font=dict(size=11, color="#DC2626"),
)

fig_price.update_layout(
    xaxis=dict(
        title="",
        showgrid=True,
        gridcolor="#F1F5F9",
        tickformat="%Y",
        dtick="M24",
    ),
    yaxis=dict(
        title="Average Price ($CAD)",
        tickprefix="$",
        showgrid=True,
        gridcolor="#F1F5F9",
    ),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    height=420,
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    margin=dict(l=10, r=10, t=20, b=10),
)

st.plotly_chart(fig_price, use_container_width=True)

st.markdown("---")

# ----------------- 3. TIERED INFLATION LEADERBOARD & ERA STORY -----------------
col_lead, col_era = st.columns([1.1, 0.9])

with col_lead:
    st.subheader("🏆 3. The Grocery Inflation Leaderboard")
    st.caption("Ranked cumulative price increase across all monitored staples (2017 → 2026).")

    ranked_list = []
    for p_name, group in df_geo.groupby("ProductName"):
        s_g = group.sort_values("SnapshotDate")
        if len(s_g) >= 2:
            st_p = s_g["AveragePrice"].iloc[0]
            en_p = s_g["AveragePrice"].iloc[-1]
            p_chg = ((en_p - st_p) / st_p) * 100 if st_p > 0 else 0
            ranked_list.append(
                {
                    "Product": p_name,
                    "InflationPct": p_chg,
                    "Start": st_p,
                    "End": en_p,
                }
            )

    rank_df = pd.DataFrame(ranked_list).sort_values("InflationPct", ascending=True)

    fig_lb = px.bar(
        rank_df,
        x="InflationPct",
        y="Product",
        orientation="h",
        color="InflationPct",
        color_continuous_scale=[
            (0.0, "#10B981"),
            (0.35, "#F59E0B"),
            (0.65, "#EF4444"),
            (1.0, "#991B1B"),
        ],
        text="InflationPct",
    )
    fig_lb.update_traces(
        texttemplate="%{text:+.1f}%",
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Cumulative Increase: <b>+%{x:.1f}%</b><extra></extra>",
    )
    fig_lb.update_layout(
        height=480,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        coloraxis_showscale=False,
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(
            title="Total Price Increase (%)",
            showgrid=True,
            gridcolor="#F1F5F9",
            ticksuffix="%",
        ),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_lb, use_container_width=True)

with col_era:
    st.subheader("📅 4. The 3 Eras of Canadian Inflation")
    st.caption("How food inflation evolved over the 9-year historical timeframe.")

    era_html = """
    <div style="display: flex; flex-direction: column; gap: 1rem; margin-top: 0.5rem;">
        <div class="era-card" style="border-left: 4px solid #10B981;">
            <span class="era-pill" style="background: #D1FAE5; color: #065F46;">
                ERA 1 • 2017–2019
            </span>
            <div class="era-title">The Stable Years</div>
            <div class="era-desc">
                Food prices grew predictably at an average pace of <b>~1.5% to 2.0% per year</b>.
                Grocery budgets experienced minor seasonal fluctuations but high predictability.
            </div>
        </div>
        <div class="era-card" style="border-left: 4px solid #EF4444;">
            <span class="era-pill" style="background: #FEE2E2; color: #991B1B;">
                ERA 2 • 2020–2023
            </span>
            <div class="era-title">The Great Supply Shock & Surge</div>
            <div class="era-desc">
                Pandemic disruptions and fuel shocks caused rapid price acceleration.
                <b>Peak annual inflation reached +8.4% in 2022</b>, hitting meats and dairy hardest.
            </div>
        </div>
        <div class="era-card" style="border-left: 4px solid #6366F1;">
            <span class="era-pill" style="background: #EEF2FF; color: #4338CA;">
                ERA 3 • 2024–2026
            </span>
            <div class="era-title">The High Plateau (New Baseline)</div>
            <div class="era-desc">
                Month-over-month price spikes cooled down, but prices <b>did not decline</b>.
                Staples stabilized at a permanent <b>~40% to 100% higher baseline</b>.
            </div>
        </div>
    </div>
    """
    st.markdown(era_html, unsafe_allow_html=True)

# ----------------- 5. PIPELINE ARCHITECTURE & EXPORT -----------------
st.markdown("---")
with st.expander("🔍 View & Download Curated Gold Dataset"):
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

with st.expander("🏛️ Data Engineering Pipeline & Lineage Architecture"):
    st.markdown(
        """
        ### Medallion Lakehouse Architecture
        * **Bronze Tier (Raw Landing):** Ingests official Statistics Canada Table 18-10-0245-01 CSVs
          with automated UTF-8 BOM (`\\ufeff`) sanitization and batch lineage metadata (`_batch_id`,
          `ingestion_timestamp`).
        * **Silver Tier (Cleansing & Quality):** Standardizes types, trims strings, generates
          deterministic SHA-256 surrogate keys (`RecordId`), and routes malformed/duplicate records
          to a dedicated **Dead-Letter Quarantine Table** (`quarantine_reason`).
        * **Gold Tier (Analytics & Windowing):** Applies decoupled regex taxonomy matching and
          executes strict consecutive calendar-month window analytics (`F.lag`) to compute valid
          MoM price changes.
        * **Serving Tier:** Curated Gold extract powers this Streamlit application.
        """
    )
