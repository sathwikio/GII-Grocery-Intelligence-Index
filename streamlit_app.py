import os

import pandas as pd
import plotly.express as px
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Grocery Intelligence Index (2017–2026)",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
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
    if "MoM_AbsoluteChange" in df.columns:
        df["MoM_AbsoluteChange"] = pd.to_numeric(df["MoM_AbsoluteChange"], errors="coerce")
    return df


df_gold = load_data()

# ----------------- SIDEBAR CONTROLS -----------------
st.sidebar.title("Filter & Slicing")

# Geography filter
all_geos = sorted(df_gold["Geography"].unique())
default_geo = "Canada" if "Canada" in all_geos else all_geos[0]
selected_geo = st.sidebar.selectbox(
    "Jurisdiction / Geography", all_geos, index=all_geos.index(default_geo)
)

# Category filter
all_categories = sorted(df_gold["BasketCategory"].dropna().unique())
selected_categories = st.sidebar.multiselect(
    "Basket Categories",
    options=all_categories,
    default=all_categories[:5] if len(all_categories) >= 5 else all_categories,
)

# Date range filter
min_date = df_gold["SnapshotDate"].min().to_pydatetime()
max_date = df_gold["SnapshotDate"].max().to_pydatetime()

selected_date_range = st.sidebar.slider(
    "Survey Time Window",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM",
)

# View Mode
view_mode = st.sidebar.radio(
    "Metric View Mode",
    ["Retail Price ($)", "Cumulative Index (Base 100)", "Month-over-Month Change (%)"],
)

# Filter dataset
filtered_df = df_gold[
    (df_gold["Geography"] == selected_geo)
    & (df_gold["BasketCategory"].isin(selected_categories))
    & (df_gold["SnapshotDate"] >= pd.Timestamp(selected_date_range[0]))
    & (df_gold["SnapshotDate"] <= pd.Timestamp(selected_date_range[1]))
].copy()

# ----------------- HEADER & OVERVIEW -----------------
st.markdown(
    '<div class="main-header">🇨🇦 Canadian Grocery Intelligence Index</div>',
    unsafe_allow_html=True,
)
sub_text = (
    f"Analytics-ready Gold dataset powered by <b>PySpark Medallion Lakehouse</b> "
    f"& Statistics Canada survey data (<b>{selected_geo}</b> | 2017–2026)"
)
st.markdown(f'<div class="sub-header">{sub_text}</div>', unsafe_allow_html=True)

# ----------------- TOP KPI METRIC CARDS -----------------
col1, col2, col3, col4 = st.columns(4)

total_records = len(filtered_df)
latest_date_str = (
    filtered_df["SnapshotDate"].max().strftime("%B %Y") if not filtered_df.empty else "N/A"
)

if not filtered_df.empty and len(filtered_df["SnapshotDate"].unique()) > 1:
    first_dt = filtered_df["SnapshotDate"].min()
    last_dt = filtered_df["SnapshotDate"].max()
    avg_start = filtered_df[filtered_df["SnapshotDate"] == first_dt]["AveragePrice"].mean()
    avg_end = filtered_df[filtered_df["SnapshotDate"] == last_dt]["AveragePrice"].mean()
    cum_pct = ((avg_end - avg_start) / avg_start) * 100 if avg_start > 0 else 0
    avg_price_display = f"${avg_end:.2f}"
    cum_pct_display = f"{cum_pct:+.1f}%"
else:
    avg_price_display = "N/A"
    cum_pct_display = "0.0%"

with col1:
    st.metric("Latest Survey Month", latest_date_str)
with col2:
    st.metric("Avg Basket Price", avg_price_display, delta=cum_pct_display)
with col3:
    st.metric("Tracked Categories", f"{len(selected_categories)} Selected")
with col4:
    st.metric("Curated Observations", f"{total_records:,}")

st.markdown("---")

# ----------------- MAIN CHARTS -----------------
if filtered_df.empty:
    st.warning("No survey records match the selected filters. Please adjust your selections.")
else:
    st.subheader(f"1. Price Trajectory: {view_mode}")

    if view_mode == "Retail Price ($)":
        fig_ts = px.line(
            filtered_df,
            x="SnapshotDate",
            y="AveragePrice",
            color="ProductName",
            title=f"Monthly Average Retail Price by Product ({selected_geo})",
            labels={
                "SnapshotDate": "Survey Date",
                "AveragePrice": "Average Price ($CAD)",
                "ProductName": "Product",
            },
        )
    elif view_mode == "Cumulative Index (Base 100)":

        def calc_indexed(group):
            base = group["AveragePrice"].iloc[0]
            group["IndexedPrice"] = (group["AveragePrice"] / base) * 100 if base > 0 else 100
            return group

        indexed_df = filtered_df.groupby(["Geography", "ProductName"], group_keys=False).apply(
            calc_indexed
        )
        start_label = selected_date_range[0].strftime("%b %Y")
        fig_ts = px.line(
            indexed_df,
            x="SnapshotDate",
            y="IndexedPrice",
            color="ProductName",
            title=f"Cumulative Inflation Index (Base = 100 at {start_label})",
            labels={
                "SnapshotDate": "Survey Date",
                "IndexedPrice": "Price Index (Base 100)",
                "ProductName": "Product",
            },
        )
        fig_ts.add_hline(
            y=100, line_dash="dash", line_color="gray", annotation_text="Baseline (100)"
        )
    else:
        fig_ts = px.line(
            filtered_df,
            x="SnapshotDate",
            y="MoM_PercentageChange",
            color="ProductName",
            title=f"Month-over-Month Price Movement (%) ({selected_geo})",
            labels={
                "SnapshotDate": "Survey Date",
                "MoM_PercentageChange": "MoM Change (%)",
                "ProductName": "Product",
            },
        )
        fig_ts.add_hline(y=0, line_dash="solid", line_color="gray")

    fig_ts.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=40, b=20),
        height=460,
    )
    st.plotly_chart(fig_ts, use_container_width=True)

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("2. Cumulative Price Inflation by Item")
        summary_rows = []
        for (prod, _uom, cat), group in filtered_df.groupby(
            ["ProductName", "UOM", "BasketCategory"]
        ):
            sorted_g = group.sort_values("SnapshotDate")
            if len(sorted_g) >= 2:
                p_start = sorted_g["AveragePrice"].iloc[0]
                p_end = sorted_g["AveragePrice"].iloc[-1]
                pct_chg = ((p_end - p_start) / p_start) * 100 if p_start > 0 else 0
                summary_rows.append(
                    {
                        "Product": prod,
                        "Category": cat,
                        "StartPrice": p_start,
                        "EndPrice": p_end,
                        "ChangePct": round(pct_chg, 1),
                    }
                )

        if summary_rows:
            summary_df = pd.DataFrame(summary_rows).sort_values("ChangePct", ascending=True)
            y_start = selected_date_range[0].strftime("%Y")
            y_end = selected_date_range[1].strftime("%Y")
            fig_bar = px.bar(
                summary_df,
                x="ChangePct",
                y="Product",
                orientation="h",
                color="ChangePct",
                color_continuous_scale="Reds",
                title=f"Price % Change ({y_start} → {y_end})",
                labels={"ChangePct": "Cumulative Inflation (%)", "Product": ""},
            )
            fig_bar.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.subheader("3. MoM Volatility Distribution")
        mom_clean = filtered_df.dropna(subset=["MoM_PercentageChange"])
        if not mom_clean.empty:
            fig_hist = px.box(
                mom_clean,
                x="BasketCategory",
                y="MoM_PercentageChange",
                color="BasketCategory",
                title="Monthly Price Volatility Range by Basket Category",
                labels={"MoM_PercentageChange": "MoM Change (%)", "BasketCategory": "Category"},
            )
            fig_hist.update_layout(
                height=380, showlegend=False, margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_hist, use_container_width=True)

# ----------------- DATA TABLE & LINEAGE -----------------
st.markdown("---")
with st.expander("🔍 View & Download Curated Gold Table Records"):
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
    sorted_df = filtered_df[table_cols].sort_values(
        ["SnapshotDate", "ProductName"], ascending=[False, True]
    )
    st.dataframe(
        sorted_df,
        use_container_width=True,
        hide_index=True,
    )

    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Gold Extract (CSV)",
        data=csv_data,
        file_name=f"grocery_index_{selected_geo.lower()}_extract.csv",
        mime="text/csv",
    )

with st.expander("🏛️ Data Engineering Pipeline & Lineage Overview"):
    st.markdown(
        """
        ### Medallion Lakehouse Architecture
        * **Bronze Tier:** Ingests raw Statistics Canada Table 18-10-0245-01 CSVs with UTF-8 BOM
          sanitization and audit lineage (`_batch_id`, `ingestion_timestamp`).
        * **Silver Tier:** Standardizes data types, trims product names, computes deterministic
          SHA-256 surrogate keys (`RecordId`), and routes malformed/duplicate rows to a
          **Dead-Letter Quarantine Table** (`quarantine_reason`).
        * **Gold Tier:** Applies decoupled prioritized regex taxonomy matching and performs
          strict consecutive calendar-month window analytics (`F.lag`) to compute valid MoM
          price movements.
        * **Serving Tier:** Curated Gold extract powers this Streamlit application for pricing
          intelligence.
        """
    )
