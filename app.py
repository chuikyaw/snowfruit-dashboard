import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SnowFruit Sales Dashboard",
    page_icon="🍍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .stApp { background-color: #0f1117; }
    h1, h2, h3 { color: #ffffff; }
    .metric-card {
        background: #1e2130;
        border-radius: 12px;
        padding: 18px 22px;
        border: 1px solid #2d3148;
    }
    .metric-label { color: #8b92a9; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #ffffff; font-size: 28px; font-weight: 700; margin-top: 4px; }
    .metric-sub   { color: #5eead4; font-size: 13px; margin-top: 2px; }
    .section-header {
        color: #c7d0e8;
        font-size: 16px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin: 24px 0 12px 0;
        border-bottom: 1px solid #2d3148;
        padding-bottom: 6px;
    }
    .day-btn button {
        background: #1e2130 !important;
        color: #c7d0e8 !important;
        border: 1px solid #2d3148 !important;
        border-radius: 8px !important;
        font-size: 13px !important;
    }
    .day-btn button:hover { background: #2d3148 !important; }
    div[data-testid="stHorizontalBlock"] > div { gap: 8px; }
    .upload-area {
        background: #1e2130;
        border: 2px dashed #3d4460;
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        color: #8b92a9;
    }
    .stDataFrame { background: #1e2130; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Column detection helpers ───────────────────────────────────────────────────
def find_column(df, candidates):
    """Return the first column name (case-insensitive) that matches any candidate."""
    col_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in col_lower:
            return col_lower[cand.lower()]
    return None


def load_and_parse(file) -> pd.DataFrame:
    """Load xlsx, auto-detect columns, return clean DataFrame."""
    # Try sheet named 'Transactions' first, then first sheet
    try:
        df = pd.read_excel(file, sheet_name="Transactions", engine="openpyxl")
    except Exception:
        df = pd.read_excel(file, sheet_name=0, engine="openpyxl")

    df.columns = df.columns.str.strip()

    # Detect date column
    date_col = find_column(df, ["date", "transaction date", "sale date", "trans date", "day"])
    if date_col is None:
        # Try to find any column with datetime-like values
        for col in df.columns:
            try:
                pd.to_datetime(df[col].dropna().head(5))
                date_col = col
                break
            except Exception:
                continue
    if date_col is None:
        st.error("❌ Could not find a date column. Please check your file.")
        st.stop()

    # Detect item name column
    item_col = find_column(df, [
        "product name", "item", "item name", "product", "description",
        "desc", "name", "menu item", "item description"
    ])
    if item_col is None:
        st.error("❌ Could not find an item/product name column.")
        st.stop()

    # Detect quantity column
    qty_col = find_column(df, [
        "qs", "qty", "quantity", "units", "count", "sold", "units sold",
        "qty sold", "amount", "number"
    ])

    # Detect revenue / price column
    rev_col = find_column(df, [
        "qs*rcp", "total", "revenue", "sales", "price", "amount", "gross",
        "net sales", "net total", "ext price", "extended price",
        "total price", "sale amount", "total amount"
    ])

    if qty_col is None and rev_col is None:
        st.error("❌ Could not find quantity or revenue columns.")
        st.stop()

    # Build clean df
    clean = pd.DataFrame()
    clean["date"] = pd.to_datetime(df[date_col], errors="coerce")
    clean["item"] = df[item_col].astype(str).str.strip()
    clean["qty"]  = pd.to_numeric(df[qty_col],  errors="coerce").fillna(0) if qty_col else 0
    clean["rev"]  = pd.to_numeric(df[rev_col],  errors="coerce").fillna(0) if rev_col else 0

    # Drop rows without a date or item
    clean = clean.dropna(subset=["date"])
    clean = clean[clean["item"].str.len() > 0]
    clean = clean[clean["item"] != "nan"]

    # Normalize: keep only date portion
    clean["date"] = clean["date"].dt.normalize()

    return clean


# ── Chart helpers ──────────────────────────────────────────────────────────────
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def make_daily_chart(daily_df, selected_date):
    """Bar (units) + Line (revenue) combo chart."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    colors = [
        "#5eead4" if row.date == selected_date else "#2d7a70"
        for _, row in daily_df.iterrows()
    ]
    x_labels = [
        f"{row.date.strftime('%a')}<br>{row.date.strftime('%b %-d')}"
        for _, row in daily_df.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=daily_df["qty"],
            name="Units Sold",
            marker_color=colors,
            hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=daily_df["rev"],
            name="Revenue ($)",
            line=dict(color="#f59e0b", width=3),
            mode="lines+markers",
            marker=dict(size=8, color="#f59e0b"),
            hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        paper_bgcolor="#1e2130",
        plot_bgcolor="#1e2130",
        font=dict(color="#c7d0e8", family="Inter, sans-serif"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12),
        ),
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        bargap=0.35,
    )
    fig.update_yaxes(
        title_text="Units Sold", secondary_y=False,
        gridcolor="#2d3148", title_font=dict(color="#8b92a9"),
        tickfont=dict(color="#8b92a9"),
    )
    fig.update_yaxes(
        title_text="Revenue ($)", secondary_y=True,
        gridcolor="rgba(0,0,0,0)", title_font=dict(color="#f59e0b"),
        tickfont=dict(color="#f59e0b"), tickprefix="$",
    )
    fig.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    return fig


def item_bar_chart(df, col, top=True, n=5, title=""):
    """Horizontal bar chart for top/bottom items."""
    agg = df.groupby("item").agg(qty=("qty", "sum"), rev=("rev", "sum")).reset_index()
    agg = agg.sort_values(col, ascending=(not top)).head(n)
    if not top:
        agg = agg.sort_values(col, ascending=True)

    bar_color = "#5eead4" if top else "#f87171"
    fig = go.Figure(go.Bar(
        x=agg[col],
        y=agg["item"],
        orientation="h",
        marker_color=bar_color,
        customdata=agg["rev"],
        hovertemplate=(
            "<b>%{y}</b><br>Units: %{x:,}<br>Revenue: $%{customdata:,.2f}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color="#c7d0e8", size=14)),
        paper_bgcolor="#1e2130",
        plot_bgcolor="#1e2130",
        font=dict(color="#c7d0e8"),
        margin=dict(l=10, r=10, t=36, b=10),
        xaxis=dict(gridcolor="#2d3148", tickfont=dict(color="#8b92a9")),
        yaxis=dict(tickfont=dict(color="#c7d0e8")),
        height=260,
    )
    return fig


# ── Main app ───────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown("""
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:4px;">
        <span style="font-size:36px;">🍍</span>
        <div>
            <h1 style="margin:0; font-size:28px; color:#ffffff;">SnowFruit Sales Dashboard</h1>
            <p style="margin:0; color:#8b92a9; font-size:14px;">Weekly store performance at a glance</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── File upload ──────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload weekly sales file (.xlsx)",
        type=["xlsx"],
        help="Sheet must be named 'Transactions' (or the first sheet is used as fallback)",
    )

    # ── Auto-load from gmail_puller output if present ────────────────────────
    auto_file = "latest_sales.xlsx"
    if uploaded is None and os.path.exists(auto_file):
        st.info(f"📂 Auto-loaded: `{auto_file}` (placed by Gmail puller)")
        with open(auto_file, "rb") as f:
            uploaded = f  # treat local file same as upload

    if uploaded is None:
        st.markdown("""
        <div class="upload-area">
            <p style="font-size:18px; margin:0;">⬆️ Upload your weekly <code>.xlsx</code> file above to get started</p>
            <p style="font-size:13px; color:#5a6080; margin-top:8px;">
                Supports any weekly export with columns for date, item name, quantity, and revenue.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Parse data ───────────────────────────────────────────────────────────
    with st.spinner("Parsing sales data…"):
        df = load_and_parse(uploaded)

    if df.empty:
        st.error("No valid data found in this file.")
        return

    # ── Extract metadata from filename ──────────────────────────────────────
    filename = getattr(uploaded, "name", "sales_file.xlsx")
    parts = filename.replace(".xlsx", "").split("_")
    store_id = parts[1] if len(parts) >= 2 else "—"
    date_range = parts[2] if len(parts) >= 3 else "—"

    # ── Summary metrics ──────────────────────────────────────────────────────
    total_rev   = df["rev"].sum()
    total_units = int(df["qty"].sum())
    unique_items = df["item"].nunique()
    days_in_file = df["date"].nunique()

    best_day_row = df.groupby("date")["rev"].sum().idxmax()
    best_day_rev = df.groupby("date")["rev"].sum().max()

    top_item_row = df.groupby("item")["qty"].sum().idxmax()

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, value, sub in [
        (c1, "Store",       f"#{store_id}",              date_range.replace("-", " → ") if date_range != "—" else ""),
        (c2, "Total Revenue",  f"${total_rev:,.2f}",     f"{days_in_file} days"),
        (c3, "Units Sold",  f"{total_units:,}",          f"{unique_items} unique items"),
        (c4, "Best Day",    best_day_row.strftime("%A"), f"${best_day_rev:,.2f}"),
        (c5, "Top Item",    top_item_row[:22],            "by units sold"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")  # spacer

    # ── Daily selector ───────────────────────────────────────────────────────
    dates_sorted = sorted(df["date"].unique())
    st.markdown('<div class="section-header">📅 Daily Breakdown — Click a day</div>', unsafe_allow_html=True)

    if "selected_date" not in st.session_state or st.session_state.selected_date not in dates_sorted:
        st.session_state.selected_date = dates_sorted[0]

    day_cols = st.columns(len(dates_sorted))
    for i, (col, d) in enumerate(zip(day_cols, dates_sorted)):
        day_rev = df[df["date"] == d]["rev"].sum()
        day_qty = int(df[df["date"] == d]["qty"].sum())
        label = f"**{pd.Timestamp(d).strftime('%a')}**  \n{pd.Timestamp(d).strftime('%b %-d')}  \n${day_rev:,.0f}  \n{day_qty:,} units"
        if col.button(label, key=f"day_{i}", use_container_width=True):
            st.session_state.selected_date = d

    selected = st.session_state.selected_date

    # ── Main chart ───────────────────────────────────────────────────────────
    daily_summary = (
        df.groupby("date")
        .agg(qty=("qty", "sum"), rev=("rev", "sum"))
        .reset_index()
        .sort_values("date")
    )
    st.plotly_chart(make_daily_chart(daily_summary, selected), use_container_width=True)

    # ── Daily top / bottom ───────────────────────────────────────────────────
    st.markdown(
        f'<div class="section-header">🗓 {pd.Timestamp(selected).strftime("%A, %B %-d")} — Top & Bottom Items</div>',
        unsafe_allow_html=True
    )

    day_df = df[df["date"] == selected]

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            item_bar_chart(day_df, "qty", top=True,  n=5, title="🏆 Top 5 by Units"),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(
            item_bar_chart(day_df, "qty", top=False, n=5, title="⚠️ Bottom 5 by Units"),
            use_container_width=True,
        )

    # ── Weekly rankings ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Full Week Rankings</div>', unsafe_allow_html=True)

    wcol1, wcol2 = st.columns(2)
    with wcol1:
        st.plotly_chart(
            item_bar_chart(df, "qty", top=True,  n=10, title="🥇 Top 10 Items — Full Week"),
            use_container_width=True,
        )
    with wcol2:
        st.plotly_chart(
            item_bar_chart(df, "qty", top=False, n=10, title="🔻 Bottom 10 Items — Full Week"),
            use_container_width=True,
        )

    # ── Weekly summary table ─────────────────────────────────────────────────
    st.markdown('<div class="section-header">📋 Full Week Item Summary</div>', unsafe_allow_html=True)

    summary = (
        df.groupby("item")
        .agg(total_units=("qty", "sum"), total_revenue=("rev", "sum"))
        .reset_index()
        .sort_values("total_units", ascending=False)
        .rename(columns={"item": "Item", "total_units": "Units Sold", "total_revenue": "Revenue"})
    )
    summary["Revenue"] = summary["Revenue"].map("${:,.2f}".format)
    summary["Units Sold"] = summary["Units Sold"].map("{:,.0f}".format)
    summary = summary.reset_index(drop=True)
    summary.index = summary.index + 1

    st.dataframe(
        summary,
        use_container_width=True,
        height=360,
    )

    st.caption(
        f"Data parsed from `{filename}` · {len(df):,} transactions · "
        f"{df['date'].min().strftime('%b %-d')}–{df['date'].max().strftime('%b %-d, %Y')}"
    )


if __name__ == "__main__":
    main()
