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
    .stApp { background-color: #0f1117; }
    h1, h2, h3 { color: #ffffff; }
    .metric-card {
        background: #1e2130;
        border-radius: 12px;
        padding: 18px 22px;
        border: 1px solid #2d3148;
        height: 100%;
    }
    .metric-card.gold { border-color: #f59e0b; }
    .metric-label { color: #8b92a9; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #ffffff; font-size: 26px; font-weight: 700; margin-top: 4px; }
    .metric-sub   { color: #5eead4; font-size: 13px; margin-top: 2px; }
    .metric-sub-gold { color: #f59e0b; font-size: 13px; margin-top: 2px; }
    .section-header {
        color: #c7d0e8;
        font-size: 15px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin: 24px 0 12px 0;
        border-bottom: 1px solid #2d3148;
        padding-bottom: 6px;
    }
    div[data-testid="stTabs"] button {
        font-size: 15px !important;
        font-weight: 600 !important;
    }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# ── Column detection ───────────────────────────────────────────────────────────
def find_column(df, candidates):
    col_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in col_lower:
            return col_lower[cand.lower()]
    return None


def parse_file(file) -> pd.DataFrame:
    try:
        df = pd.read_excel(file, sheet_name="Transactions", engine="openpyxl")
    except Exception:
        df = pd.read_excel(file, sheet_name=0, engine="openpyxl")

    df.columns = df.columns.str.strip()

    date_col = find_column(df, ["date", "transaction date", "sale date", "trans date", "day"])
    item_col = find_column(df, ["product name", "item", "item name", "product", "description", "desc", "name", "menu item"])
    qty_col  = find_column(df, ["qs", "qty", "quantity", "units", "count", "sold", "units sold"])
    rev_col  = find_column(df, ["qs*rcp", "total", "revenue", "sales", "price", "amount", "gross", "net sales", "ext price", "extended price", "total price"])

    if date_col is None or item_col is None:
        return pd.DataFrame()
    if qty_col is None and rev_col is None:
        return pd.DataFrame()

    clean = pd.DataFrame()
    clean["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
    clean["item"] = df[item_col].astype(str).str.strip()
    clean["qty"]  = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) if qty_col else 0
    clean["rev"]  = pd.to_numeric(df[rev_col], errors="coerce").fillna(0) if rev_col else 0

    clean = clean.dropna(subset=["date"])
    clean = clean[clean["item"].str.len() > 0]
    clean = clean[clean["item"] != "nan"]
    return clean


# ── Chart helpers ──────────────────────────────────────────────────────────────
def monthly_trend_chart(monthly_df, selected_month):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    colors = [
        "#f59e0b" if row.month_label == selected_month else "#2d6b8a"
        for _, row in monthly_df.iterrows()
    ]

    fig.add_trace(go.Bar(
        x=monthly_df["month_label"],
        y=monthly_df["rev"],
        name="Revenue ($)",
        marker_color=colors,
        hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"],
        y=monthly_df["qty"],
        name="Units Sold",
        line=dict(color="#5eead4", width=3),
        mode="lines+markers",
        marker=dict(size=8),
        hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
        font=dict(color="#c7d0e8"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified", bargap=0.35,
    )
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=False,
                     gridcolor="#2d3148", tickprefix="$",
                     title_font=dict(color="#8b92a9"), tickfont=dict(color="#8b92a9"))
    fig.update_yaxes(title_text="Units Sold", secondary_y=True,
                     gridcolor="rgba(0,0,0,0)",
                     title_font=dict(color="#5eead4"), tickfont=dict(color="#5eead4"))
    fig.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    return fig


def horizontal_bar(items_df, qty_col, top=True, n=10, title=""):
    df = items_df.sort_values(qty_col, ascending=(not top)).head(n)
    if not top:
        df = df.sort_values(qty_col, ascending=True)
    color = "#5eead4" if top else "#f87171"
    fig = go.Figure(go.Bar(
        x=df[qty_col], y=df["item"], orientation="h",
        marker_color=color,
        customdata=df["rev"] if "rev" in df.columns else df[qty_col],
        hovertemplate="<b>%{y}</b><br>Units: %{x:,}<br>Revenue: $%{customdata:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color="#c7d0e8", size=14)),
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
        font=dict(color="#c7d0e8"),
        margin=dict(l=10, r=10, t=36, b=10),
        xaxis=dict(gridcolor="#2d3148", tickfont=dict(color="#8b92a9")),
        yaxis=dict(tickfont=dict(color="#c7d0e8")),
        height=320,
    )
    return fig


def daily_chart(daily_df, selected_date):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = ["#5eead4" if r.date == selected_date else "#2d7a70" for _, r in daily_df.iterrows()]
    x_labels = [f"{r.date.strftime('%a')}<br>{r.date.strftime('%b %-d')}" for _, r in daily_df.iterrows()]

    fig.add_trace(go.Bar(x=x_labels, y=daily_df["qty"], name="Units Sold",
                         marker_color=colors,
                         hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=x_labels, y=daily_df["rev"], name="Revenue ($)",
                             line=dict(color="#f59e0b", width=3), mode="lines+markers",
                             marker=dict(size=8),
                             hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>"),
                  secondary_y=True)
    fig.update_layout(
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
        font=dict(color="#c7d0e8"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified", bargap=0.35,
    )
    fig.update_yaxes(title_text="Units Sold", secondary_y=False,
                     gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=True,
                     gridcolor="rgba(0,0,0,0)", tickprefix="$", tickfont=dict(color="#f59e0b"))
    fig.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    return fig


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:4px;">
        <span style="font-size:36px;">🍍</span>
        <div>
            <h1 style="margin:0;font-size:28px;color:#ffffff;">SnowFruit Sales Dashboard</h1>
            <p style="margin:0;color:#8b92a9;font-size:14px;">Store 327 · Year-to-date performance</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # ── File uploader ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📂 Upload Weekly Files</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Upload one or more weekly .xlsx files (you can select all at once)",
        type=["xlsx"],
        accept_multiple_files=True,
        help="Hold Ctrl (or Cmd on Mac) to select multiple files at once",
    )

    # Auto-load latest_sales.xlsx if no manual upload
    if not uploaded_files and os.path.exists("latest_sales.xlsx"):
        st.info("📂 Auto-loaded: `latest_sales.xlsx` from Gmail puller")
        with open("latest_sales.xlsx", "rb") as f:
            uploaded_files = [f]

    if not uploaded_files:
        st.markdown("""
        <div style="background:#1e2130;border:2px dashed #3d4460;border-radius:12px;
                    padding:40px;text-align:center;color:#8b92a9;">
            <p style="font-size:18px;margin:0;">⬆️ Upload your weekly <code>.xlsx</code> files above</p>
            <p style="font-size:13px;color:#5a6080;margin-top:8px;">
                Select multiple files at once to see historical monthly trends.<br>
                Each file covers one week — upload all weeks for the full picture.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Parse all files ──────────────────────────────────────────────────────
    with st.spinner(f"Parsing {len(uploaded_files)} file(s)…"):
        frames = []
        skipped = []
        for f in uploaded_files:
            parsed = parse_file(f)
            if parsed.empty:
                skipped.append(getattr(f, "name", str(f)))
            else:
                frames.append(parsed)

        if not frames:
            st.error("No valid data found in any uploaded file.")
            return

        df = pd.concat(frames, ignore_index=True).drop_duplicates()
        df = df.sort_values("date")

    if skipped:
        st.warning(f"⚠️ Skipped {len(skipped)} file(s) — columns not recognized: {', '.join(skipped)}")

    # ── Derived columns ──────────────────────────────────────────────────────
    df["month_num"]   = df["date"].dt.month
    df["month_label"] = df["date"].dt.strftime("%b")
    df["week_label"]  = df["date"].dt.strftime("Week of %b %-d")
    df["week_start"]  = df["date"] - pd.to_timedelta(df["date"].dt.dayofweek, unit="d")

    # ── YTD summary metrics ──────────────────────────────────────────────────
    total_rev    = df["rev"].sum()
    total_units  = int(df["qty"].sum())
    unique_items = df["item"].nunique()
    months_seen  = df["month_label"].nunique()

    monthly_agg = (df.groupby(["month_num","month_label"])
                     .agg(rev=("rev","sum"), qty=("qty","sum"))
                     .reset_index()
                     .sort_values("month_num"))

    best_month_row  = monthly_agg.loc[monthly_agg["rev"].idxmax()]
    best_month_name = best_month_row["month_label"]
    best_month_rev  = best_month_row["rev"]

    top_item_ytd = df.groupby("item")["qty"].sum().idxmax()
    top_item_qty = int(df.groupby("item")["qty"].sum().max())

    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, "YTD Revenue",    f"${total_rev:,.2f}",     f"{months_seen} months of data",     ""),
        (c2, "YTD Units Sold", f"{total_units:,}",        f"{unique_items} unique items",      ""),
        (c3, "Best Month 🏆",  best_month_name,           f"${best_month_rev:,.2f} revenue",   "gold"),
        (c4, "Top Item YTD",   top_item_ytd[:20],         f"{top_item_qty:,} units sold",      ""),
        (c5, "Files Loaded",   str(len(frames)),          f"{df['date'].min().strftime('%b %-d')} – {df['date'].max().strftime('%b %-d, %Y')}", ""),
    ]
    for col, label, value, sub, style in cards:
        cls = f"metric-card {style}".strip()
        sub_cls = "metric-sub-gold" if style == "gold" else "metric-sub"
        col.markdown(f"""
        <div class="{cls}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="{sub_cls}">{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_monthly, tab_weekly = st.tabs(["📅  Monthly Overview", "🗓  Weekly Drill-Down"])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — MONTHLY
    # ════════════════════════════════════════════════════════════════════════
    with tab_monthly:
        st.markdown('<div class="section-header">📈 Revenue & Units by Month — click a bar to drill in</div>',
                    unsafe_allow_html=True)

        # Month selector
        available_months = monthly_agg["month_label"].tolist()
        if "selected_month" not in st.session_state or st.session_state.selected_month not in available_months:
            st.session_state.selected_month = best_month_name  # default to best month

        month_cols = st.columns(len(available_months))
        for col, row in zip(month_cols, monthly_agg.itertuples()):
            is_best = row.month_label == best_month_name
            label = f"{'🏆 ' if is_best else ''}**{row.month_label}**  \n${row.rev:,.0f}  \n{int(row.qty):,} units"
            if col.button(label, key=f"m_{row.month_label}", use_container_width=True):
                st.session_state.selected_month = row.month_label

        selected_month = st.session_state.selected_month

        # Trend chart
        st.plotly_chart(monthly_trend_chart(monthly_agg, selected_month), use_container_width=True)

        # Month deep-dive
        st.markdown(
            f'<div class="section-header">🔍 {selected_month} — Top & Bottom Sellers</div>',
            unsafe_allow_html=True)

        month_df = df[df["month_label"] == selected_month]
        month_items = (month_df.groupby("item")
                                .agg(qty=("qty","sum"), rev=("rev","sum"))
                                .reset_index())

        # Month KPIs
        mk1, mk2, mk3 = st.columns(3)
        mk1.markdown(f"""<div class="metric-card">
            <div class="metric-label">Revenue</div>
            <div class="metric-value">${month_df['rev'].sum():,.2f}</div>
            <div class="metric-sub">{selected_month}</div></div>""", unsafe_allow_html=True)
        mk2.markdown(f"""<div class="metric-card">
            <div class="metric-label">Units Sold</div>
            <div class="metric-value">{int(month_df['qty'].sum()):,}</div>
            <div class="metric-sub">{month_df['item'].nunique()} unique items</div></div>""", unsafe_allow_html=True)
        mk3.markdown(f"""<div class="metric-card">
            <div class="metric-label">Weeks of Data</div>
            <div class="metric-value">{month_df['week_start'].nunique()}</div>
            <div class="metric-sub">{month_df['date'].min().strftime('%b %-d')} – {month_df['date'].max().strftime('%b %-d')}</div></div>""",
            unsafe_allow_html=True)

        st.markdown("")

        lc, rc = st.columns(2)
        with lc:
            st.plotly_chart(
                horizontal_bar(month_items, "qty", top=True,  n=10, title=f"🏆 Top 10 Items — {selected_month}"),
                use_container_width=True)
        with rc:
            st.plotly_chart(
                horizontal_bar(month_items, "qty", top=False, n=10, title=f"⚠️ Bottom 10 Items — {selected_month}"),
                use_container_width=True)

        # Month full table
        with st.expander(f"📋 Full item list for {selected_month}"):
            tbl = (month_items.sort_values("qty", ascending=False)
                              .rename(columns={"item":"Item","qty":"Units Sold","rev":"Revenue"})
                              .reset_index(drop=True))
            tbl.index += 1
            tbl["Revenue"] = tbl["Revenue"].map("${:,.2f}".format)
            tbl["Units Sold"] = tbl["Units Sold"].map("{:,.0f}".format)
            st.dataframe(tbl, use_container_width=True, height=320)

        # Month comparison table
        st.markdown('<div class="section-header">📊 Month-by-Month Comparison</div>', unsafe_allow_html=True)
        comp = monthly_agg.copy()
        comp["Revenue"]     = comp["rev"].map("${:,.2f}".format)
        comp["Units Sold"]  = comp["qty"].map("{:,.0f}".format)
        comp["vs. Best"]    = ((monthly_agg["rev"] / best_month_rev - 1) * 100).map(
                                lambda x: f"+{x:.1f}%" if x >= 0 else f"{x:.1f}%")
        comp = comp[["month_label","Revenue","Units Sold","vs. Best"]].rename(
            columns={"month_label":"Month"}).reset_index(drop=True)
        comp.index += 1
        st.dataframe(comp, use_container_width=True, height=min(60 + len(comp)*40, 380))

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — WEEKLY DRILL-DOWN
    # ════════════════════════════════════════════════════════════════════════
    with tab_weekly:
        # Week picker
        weeks = sorted(df["week_start"].unique())
        week_labels = {w: df[df["week_start"]==w]["date"].min().strftime("Week of %b %-d, %Y") for w in weeks}

        st.markdown('<div class="section-header">📅 Select a Week</div>', unsafe_allow_html=True)
        selected_week = st.selectbox(
            "Choose week",
            options=weeks,
            format_func=lambda w: week_labels[w],
            index=len(weeks)-1,
            label_visibility="collapsed",
        )

        week_df = df[df["week_start"] == selected_week]
        dates_sorted = sorted(week_df["date"].unique())

        # Week summary
        wk1, wk2, wk3 = st.columns(3)
        wk1.markdown(f"""<div class="metric-card">
            <div class="metric-label">Week Revenue</div>
            <div class="metric-value">${week_df['rev'].sum():,.2f}</div>
            <div class="metric-sub">{week_labels[selected_week]}</div></div>""", unsafe_allow_html=True)
        wk2.markdown(f"""<div class="metric-card">
            <div class="metric-label">Units Sold</div>
            <div class="metric-value">{int(week_df['qty'].sum()):,}</div>
            <div class="metric-sub">{week_df['item'].nunique()} unique items</div></div>""", unsafe_allow_html=True)
        best_day = week_df.groupby("date")["rev"].sum().idxmax()
        wk3.markdown(f"""<div class="metric-card">
            <div class="metric-label">Best Day</div>
            <div class="metric-value">{pd.Timestamp(best_day).strftime('%A')}</div>
            <div class="metric-sub">${week_df.groupby('date')['rev'].sum().max():,.2f}</div></div>""",
            unsafe_allow_html=True)

        st.markdown("")

        # Day buttons
        st.markdown('<div class="section-header">📅 Daily Breakdown — Click a day</div>', unsafe_allow_html=True)

        if "selected_date" not in st.session_state or st.session_state.selected_date not in dates_sorted:
            st.session_state.selected_date = dates_sorted[0]

        day_cols = st.columns(len(dates_sorted))
        for i, (col, d) in enumerate(zip(day_cols, dates_sorted)):
            day_rev = week_df[week_df["date"]==d]["rev"].sum()
            day_qty = int(week_df[week_df["date"]==d]["qty"].sum())
            label   = f"**{pd.Timestamp(d).strftime('%a')}**  \n{pd.Timestamp(d).strftime('%b %-d')}  \n${day_rev:,.0f}  \n{day_qty:,} units"
            if col.button(label, key=f"wd_{i}_{selected_week}", use_container_width=True):
                st.session_state.selected_date = d

        selected_date = st.session_state.selected_date

        # Daily chart
        daily_summary = (week_df.groupby("date")
                                 .agg(qty=("qty","sum"), rev=("rev","sum"))
                                 .reset_index().sort_values("date"))
        st.plotly_chart(daily_chart(daily_summary, selected_date), use_container_width=True)

        # Day top/bottom
        st.markdown(
            f'<div class="section-header">🗓 {pd.Timestamp(selected_date).strftime("%A, %B %-d")} — Top & Bottom Items</div>',
            unsafe_allow_html=True)

        day_df = week_df[week_df["date"] == selected_date]
        lc2, rc2 = st.columns(2)
        with lc2:
            st.plotly_chart(
                horizontal_bar(
                    day_df.groupby("item").agg(qty=("qty","sum"),rev=("rev","sum")).reset_index(),
                    "qty", top=True,  n=5, title="🏆 Top 5 by Units"),
                use_container_width=True)
        with rc2:
            st.plotly_chart(
                horizontal_bar(
                    day_df.groupby("item").agg(qty=("qty","sum"),rev=("rev","sum")).reset_index(),
                    "qty", top=False, n=5, title="⚠️ Bottom 5 by Units"),
                use_container_width=True)

        # Weekly top/bottom
        st.markdown('<div class="section-header">📊 Full Week Rankings</div>', unsafe_allow_html=True)
        wc1, wc2 = st.columns(2)
        week_items = week_df.groupby("item").agg(qty=("qty","sum"),rev=("rev","sum")).reset_index()
        with wc1:
            st.plotly_chart(
                horizontal_bar(week_items, "qty", top=True,  n=10, title="🥇 Top 10 — Full Week"),
                use_container_width=True)
        with wc2:
            st.plotly_chart(
                horizontal_bar(week_items, "qty", top=False, n=10, title="🔻 Bottom 10 — Full Week"),
                use_container_width=True)

    st.caption(
        f"SnowFruit Store 327 · {len(frames)} file(s) loaded · "
        f"{len(df):,} transactions · "
        f"{df['date'].min().strftime('%b %-d')} – {df['date'].max().strftime('%b %-d, %Y')}"
    )


if __name__ == "__main__":
    main()
