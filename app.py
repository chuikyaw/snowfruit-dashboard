import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from pathlib import Path

DATA_FILE = Path("data/sales_data.parquet")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SnowFruit Sales Dashboard",
    page_icon="🍍",
    layout="wide",
    initial_sidebar_state="auto",
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
    .metric-sub      { color: #5eead4; font-size: 13px; margin-top: 2px; }
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
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Column detection ───────────────────────────────────────────────────────────
def find_column(df, candidates):
    col_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in col_lower:
            return col_lower[cand.lower()]
    return None


def parse_file(file):
    try:
        df = pd.read_excel(file, sheet_name="Transactions", engine="openpyxl")
    except Exception:
        df = pd.read_excel(file, sheet_name=0, engine="openpyxl")
    df.columns = df.columns.str.strip()

    date_col = find_column(df, ["date", "transaction date", "sale date", "trans date", "day"])
    item_col = find_column(df, ["product name", "item", "item name", "product",
                                "description", "desc", "name", "menu item"])
    qty_col  = find_column(df, ["qs", "qty", "quantity", "units", "count", "sold", "units sold"])
    rev_col  = find_column(df, ["qs*rcp", "total", "revenue", "sales", "price", "amount",
                                "gross", "net sales", "ext price", "extended price", "total price"])

    if not date_col or not item_col:
        return pd.DataFrame()
    if not qty_col and not rev_col:
        return pd.DataFrame()

    clean = pd.DataFrame()
    clean["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
    clean["item"] = df[item_col].astype(str).str.strip()
    clean["qty"]  = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) if qty_col else 0.0
    clean["rev"]  = pd.to_numeric(df[rev_col], errors="coerce").fillna(0) if rev_col else 0.0
    clean = clean.dropna(subset=["date"])
    clean = clean[clean["item"].str.len() > 0]
    clean = clean[clean["item"] != "nan"]
    return clean


# ── Chart helpers ──────────────────────────────────────────────────────────────
def monthly_trend_chart(monthly_df, selected_month):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = ["#f59e0b" if r.month_label == selected_month else "#2d6b8a"
              for _, r in monthly_df.iterrows()]
    fig.add_trace(go.Bar(
        x=monthly_df["month_label"], y=monthly_df["rev"], name="Revenue ($)",
        marker_color=colors,
        hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=monthly_df["month_label"], y=monthly_df["qty"], name="Units Sold",
        line=dict(color="#5eead4", width=3), mode="lines+markers", marker=dict(size=8),
        hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>",
    ), secondary_y=True)
    fig.update_layout(
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130", font=dict(color="#c7d0e8"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified", bargap=0.35,
    )
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=False,
                     gridcolor="#2d3148", tickprefix="$", tickfont=dict(color="#8b92a9"))
    fig.update_yaxes(title_text="Units Sold", secondary_y=True,
                     gridcolor="rgba(0,0,0,0)", tickfont=dict(color="#5eead4"))
    fig.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    return fig


def horizontal_bar(items_df, col, top=True, n=10, title=""):
    df = items_df.sort_values(col, ascending=(not top)).head(n)
    if not top:
        df = df.sort_values(col, ascending=True)
    color = "#5eead4" if top else "#f87171"
    fig = go.Figure(go.Bar(
        x=df[col], y=df["item"], orientation="h", marker_color=color,
        customdata=df["rev"] if "rev" in df.columns else df[col],
        hovertemplate="<b>%{y}</b><br>Units: %{x:,}<br>Revenue: $%{customdata:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color="#c7d0e8", size=14)),
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130", font=dict(color="#c7d0e8"),
        margin=dict(l=10, r=10, t=36, b=10),
        xaxis=dict(gridcolor="#2d3148", tickfont=dict(color="#8b92a9")),
        yaxis=dict(tickfont=dict(color="#c7d0e8")),
        height=320,
    )
    return fig


def daily_chart(daily_df, selected_date):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = ["#5eead4" if r.date == selected_date else "#2d7a70"
              for _, r in daily_df.iterrows()]
    x_labels = [r.date.strftime("%a\n%b %d") for _, r in daily_df.iterrows()]
    fig.add_trace(go.Bar(
        x=x_labels, y=daily_df["qty"], name="Units Sold", marker_color=colors,
        hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=x_labels, y=daily_df["rev"], name="Revenue ($)",
        line=dict(color="#f59e0b", width=3), mode="lines+markers", marker=dict(size=8),
        hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
    ), secondary_y=True)
    fig.update_layout(
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130", font=dict(color="#c7d0e8"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified", bargap=0.35,
    )
    fig.update_yaxes(title_text="Units Sold", secondary_y=False,
                     gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=True,
                     gridcolor="rgba(0,0,0,0)", tickprefix="$", tickfont=dict(color="#f59e0b"))
    fig.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    return fig


def metric_card(label, value, sub, gold=False):
    cls = "metric-card gold" if gold else "metric-card"
    sub_cls = "metric-sub-gold" if gold else "metric-sub"
    return f"""<div class="{cls}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="{sub_cls}">{sub}</div>
    </div>"""


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

    # ── Sidebar: owner PIN ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🍍 SnowFruit Dashboard")
        st.markdown("---")
        st.markdown("#### 🔒 Owner Access")
        pin_input = st.text_input(
            "PIN", type="password", placeholder="Enter PIN",
            label_visibility="collapsed"
        )
        correct_pin = False
        try:
            correct_pin = (pin_input == st.secrets["PIN"])
        except Exception:
            if pin_input:
                st.warning("No PIN configured yet.")

        if correct_pin:
            st.success("Access granted")
            st.markdown("**Upload new weekly files:**")
            uploaded_files = st.file_uploader(
                "Weekly xlsx", type=["xlsx"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )
        else:
            uploaded_files = []
            if pin_input and not correct_pin:
                st.error("Incorrect PIN")

        st.markdown("---")
        st.caption("To save data permanently:\nrun `update_data.py` locally\nthen upload parquet to GitHub.")

    # ── Load data ─────────────────────────────────────────────────────────────
    df = None

    if DATA_FILE.exists():
        with st.spinner("Loading…"):
            df = pd.read_parquet(DATA_FILE)
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()

        if correct_pin and uploaded_files:
            new_frames = [parse_file(f) for f in uploaded_files]
            new_frames = [x for x in new_frames if not x.empty]
            if new_frames:
                new_data = pd.concat(new_frames, ignore_index=True)
                df = pd.concat([df, new_data], ignore_index=True).drop_duplicates()
                df = df.sort_values("date")
                st.sidebar.success(f"{len(new_frames)} file(s) merged (this session)")
                st.sidebar.info("Run `update_data.py` to make permanent.")

    elif correct_pin and uploaded_files:
        new_frames = [parse_file(f) for f in uploaded_files]
        new_frames = [x for x in new_frames if not x.empty]
        if not new_frames:
            st.error("No valid data in uploaded files.")
            return
        df = pd.concat(new_frames, ignore_index=True).drop_duplicates().sort_values("date")
        st.sidebar.info("Loaded for this session.\nRun `update_data.py` to save permanently.")

    else:
        st.markdown("""
        <div style="background:#1e2130;border:2px dashed #3d4460;border-radius:12px;
                    padding:48px;text-align:center;color:#8b92a9;margin-top:24px;">
            <p style="font-size:22px;margin:0;">📊 No data loaded yet</p>
            <p style="font-size:14px;color:#5a6080;margin-top:12px;">
                This dashboard is managed by the store owner.<br>
                If you were given this link, check back soon!
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    if df is None or df.empty:
        st.error("No data available.")
        return

    # ── Derived columns ───────────────────────────────────────────────────────
    df["month_num"]   = df["date"].dt.month
    df["month_label"] = df["date"].dt.strftime("%b")
    df["week_start"]  = df["date"] - pd.to_timedelta(df["date"].dt.dayofweek, unit="d")

    # ── YTD summary metrics ───────────────────────────────────────────────────
    total_rev    = df["rev"].sum()
    total_units  = int(df["qty"].sum())
    unique_items = df["item"].nunique()
    months_seen  = df["month_label"].nunique()

    monthly_agg = (df.groupby(["month_num", "month_label"])
                     .agg(rev=("rev", "sum"), qty=("qty", "sum"))
                     .reset_index().sort_values("month_num"))

    best_month_row  = monthly_agg.loc[monthly_agg["rev"].idxmax()]
    best_month_name = best_month_row["month_label"]
    best_month_rev  = best_month_row["rev"]
    top_item_ytd    = df.groupby("item")["qty"].sum().idxmax()
    top_item_qty    = int(df.groupby("item")["qty"].sum().max())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(metric_card("YTD Revenue",    f"${total_rev:,.2f}",  f"{months_seen} months"),              unsafe_allow_html=True)
    c2.markdown(metric_card("YTD Units Sold", f"{total_units:,}",    f"{unique_items} unique items"),        unsafe_allow_html=True)
    c3.markdown(metric_card("Best Month",     best_month_name,       f"${best_month_rev:,.2f}", gold=True),  unsafe_allow_html=True)
    c4.markdown(metric_card("Top Item YTD",   top_item_ytd[:20],     f"{top_item_qty:,} units sold"),        unsafe_allow_html=True)
    c5.markdown(metric_card("Data Range",
                f"{df['date'].min().strftime('%b %d')}",
                f"to {df['date'].max().strftime('%b %d, %Y')}"),     unsafe_allow_html=True)
    st.markdown("")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_monthly, tab_weekly, tab_item = st.tabs([
        "📅  Monthly Overview",
        "🗓  Weekly Drill-Down",
        "🔎  Item Search",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — MONTHLY
    # ══════════════════════════════════════════════════════════════════════════
    with tab_monthly:
        st.markdown('<div class="section-header">Revenue & Units by Month</div>',
                    unsafe_allow_html=True)

        available_months = monthly_agg["month_label"].tolist()
        if "selected_month" not in st.session_state or \
                st.session_state.selected_month not in available_months:
            st.session_state.selected_month = best_month_name

        month_cols = st.columns(len(available_months))
        for col, row in zip(month_cols, monthly_agg.itertuples()):
            is_best = row.month_label == best_month_name
            label = ("**🏆 " if is_best else "**") + row.month_label + \
                    f"**  \n${row.rev:,.0f}  \n{int(row.qty):,} units"
            if col.button(label, key=f"m_{row.month_label}", use_container_width=True):
                st.session_state.selected_month = row.month_label

        selected_month = st.session_state.selected_month
        st.plotly_chart(monthly_trend_chart(monthly_agg, selected_month), use_container_width=True)

        st.markdown(f'<div class="section-header">{selected_month} — Top & Bottom Sellers</div>',
                    unsafe_allow_html=True)

        month_df    = df[df["month_label"] == selected_month]
        month_items = (month_df.groupby("item")
                                .agg(qty=("qty", "sum"), rev=("rev", "sum"))
                                .reset_index())

        mk1, mk2, mk3 = st.columns(3)
        mk1.markdown(metric_card("Revenue",    f"${month_df['rev'].sum():,.2f}", selected_month),
                     unsafe_allow_html=True)
        mk2.markdown(metric_card("Units Sold", f"{int(month_df['qty'].sum()):,}",
                                 f"{month_df['item'].nunique()} unique items"), unsafe_allow_html=True)
        mk3.markdown(metric_card("Weeks of Data", str(month_df["week_start"].nunique()),
                                 f"{month_df['date'].min().strftime('%b %d')} – "
                                 f"{month_df['date'].max().strftime('%b %d')}"),
                     unsafe_allow_html=True)
        st.markdown("")

        lc, rc = st.columns(2)
        with lc:
            st.plotly_chart(horizontal_bar(month_items, "qty", top=True,  n=10,
                                           title="Top 10 Items — " + selected_month),
                            use_container_width=True)
        with rc:
            st.plotly_chart(horizontal_bar(month_items, "qty", top=False, n=10,
                                           title="Bottom 10 Items — " + selected_month),
                            use_container_width=True)

        with st.expander("Full item list for " + selected_month):
            tbl = (month_items.sort_values("qty", ascending=False)
                              .rename(columns={"item": "Item", "qty": "Units Sold", "rev": "Revenue"})
                              .reset_index(drop=True))
            tbl.index += 1
            tbl["Revenue"]    = tbl["Revenue"].map("${:,.2f}".format)
            tbl["Units Sold"] = tbl["Units Sold"].map("{:,.0f}".format)
            st.dataframe(tbl, use_container_width=True, height=320)

        st.markdown('<div class="section-header">Month-by-Month Comparison</div>',
                    unsafe_allow_html=True)
        comp = monthly_agg.copy()
        comp["Revenue"]    = comp["rev"].map("${:,.2f}".format)
        comp["Units Sold"] = comp["qty"].map("{:,.0f}".format)
        comp["vs. Best"]   = ((monthly_agg["rev"] / best_month_rev - 1) * 100).map(
            lambda x: ("+" if x >= 0 else "") + f"{x:.1f}%")
        comp = comp[["month_label", "Revenue", "Units Sold", "vs. Best"]].rename(
            columns={"month_label": "Month"}).reset_index(drop=True)
        comp.index += 1
        st.dataframe(comp, use_container_width=True, height=min(60 + len(comp) * 40, 380))

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — WEEKLY DRILL-DOWN
    # ══════════════════════════════════════════════════════════════════════════
    with tab_weekly:
        weeks         = sorted(df["week_start"].unique())
        available_dates = set(df["date"].dt.date.unique())
        min_date      = df["date"].min().date()
        max_date      = df["date"].max().date()

        st.markdown('<div class="section-header">Pick any date to load that week</div>',
                    unsafe_allow_html=True)

        import datetime
        cal_col, info_col = st.columns([1, 2])
        with cal_col:
            picked = st.date_input(
                "Select a date",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                label_visibility="collapsed",
            )

        # Find the Monday of the picked date's week
        picked_dt     = pd.Timestamp(picked).normalize()
        week_start_dt = picked_dt - pd.to_timedelta(picked_dt.dayofweek, unit="d")

        # Snap to nearest available week if the exact one isn't in the data
        if week_start_dt not in [pd.Timestamp(w) for w in weeks]:
            closest = min(weeks, key=lambda w: abs(pd.Timestamp(w) - week_start_dt))
            week_start_dt = pd.Timestamp(closest)
            with info_col:
                st.info(
                    f"No data for the week of {picked.strftime('%b %d')}. "
                    f"Showing nearest available week."
                )

        selected_week = week_start_dt
        week_df       = df[df["week_start"] == selected_week]
        dates_sorted  = sorted(week_df["date"].unique())

        with info_col:
            w_start_str = pd.Timestamp(selected_week).strftime("%b %d")
            w_end_str   = week_df["date"].max().strftime("%b %d, %Y")
            st.markdown(
                f'<div class="metric-card" style="margin-top:4px;">'
                f'<div class="metric-label">Showing week</div>'
                f'<div class="metric-value" style="font-size:20px;">{w_start_str} – {w_end_str}</div>'
                f'<div class="metric-sub">{len(dates_sorted)} days of data</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")

        week_df      = df[df["week_start"] == selected_week]
        dates_sorted = sorted(week_df["date"].unique())
        best_day     = week_df.groupby("date")["rev"].sum().idxmax()

        wk1, wk2, wk3 = st.columns(3)
        wk1.markdown(metric_card("Week Revenue", f"${week_df['rev'].sum():,.2f}",
                                 f"{pd.Timestamp(selected_week).strftime('%b %d')} – {week_df['date'].max().strftime('%b %d, %Y')}"),
                     unsafe_allow_html=True)
        wk2.markdown(metric_card("Units Sold", f"{int(week_df['qty'].sum()):,}",
                                 f"{week_df['item'].nunique()} unique items"), unsafe_allow_html=True)
        wk3.markdown(metric_card("Best Day", pd.Timestamp(best_day).strftime("%A"),
                                 f"${week_df.groupby('date')['rev'].sum().max():,.2f}"),
                     unsafe_allow_html=True)
        st.markdown("")

        st.markdown('<div class="section-header">Daily Breakdown — Click a day</div>',
                    unsafe_allow_html=True)

        if "selected_date" not in st.session_state or \
                st.session_state.selected_date not in dates_sorted:
            st.session_state.selected_date = dates_sorted[0]

        day_cols = st.columns(len(dates_sorted))
        for i, (col, d) in enumerate(zip(day_cols, dates_sorted)):
            day_rev = week_df[week_df["date"] == d]["rev"].sum()
            day_qty = int(week_df[week_df["date"] == d]["qty"].sum())
            ts      = pd.Timestamp(d)
            label   = f"**{ts.strftime('%a')}**  \n{ts.strftime('%b %d')}  \n${day_rev:,.0f}  \n{day_qty:,} units"
            if col.button(label, key=f"wd_{i}_{selected_week}", use_container_width=True):
                st.session_state.selected_date = d

        selected_date = st.session_state.selected_date
        daily_summary = (week_df.groupby("date").agg(qty=("qty", "sum"), rev=("rev", "sum"))
                                .reset_index().sort_values("date"))
        st.plotly_chart(daily_chart(daily_summary, selected_date), use_container_width=True)

        sel_ts = pd.Timestamp(selected_date)
        st.markdown(
            f'<div class="section-header">{sel_ts.strftime("%A, %B %d")} — Top & Bottom Items</div>',
            unsafe_allow_html=True)

        day_df   = week_df[week_df["date"] == selected_date]
        day_agg  = day_df.groupby("item").agg(qty=("qty", "sum"), rev=("rev", "sum")).reset_index()
        lc2, rc2 = st.columns(2)
        with lc2:
            st.plotly_chart(horizontal_bar(day_agg, "qty", top=True,  n=5, title="Top 5 by Units"),
                            use_container_width=True)
        with rc2:
            st.plotly_chart(horizontal_bar(day_agg, "qty", top=False, n=5, title="Bottom 5 by Units"),
                            use_container_width=True)

        st.markdown('<div class="section-header">Full Week Rankings</div>', unsafe_allow_html=True)
        week_items = week_df.groupby("item").agg(qty=("qty", "sum"), rev=("rev", "sum")).reset_index()
        wc1, wc2  = st.columns(2)
        with wc1:
            st.plotly_chart(horizontal_bar(week_items, "qty", top=True,  n=10, title="Top 10 — Full Week"),
                            use_container_width=True)
        with wc2:
            st.plotly_chart(horizontal_bar(week_items, "qty", top=False, n=10, title="Bottom 10 — Full Week"),
                            use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — ITEM SEARCH
    # ══════════════════════════════════════════════════════════════════════════
    with tab_item:
        st.markdown('<div class="section-header">Search an Item</div>', unsafe_allow_html=True)

        all_items     = sorted(df["item"].unique())
        default_idx   = all_items.index("Pineapple - 18oz") if "Pineapple - 18oz" in all_items else 0
        selected_item = st.selectbox("Item", options=all_items, index=default_idx,
                                     label_visibility="collapsed")

        item_df       = df[df["item"] == selected_item]
        total_i_units = int(item_df["qty"].sum())
        total_i_rev   = item_df["rev"].sum()
        avg_price     = (item_df["rev"] / item_df["qty"].replace(0, float("nan"))).mean()

        item_monthly  = (item_df.groupby(["month_num", "month_label"])
                                .agg(qty=("qty", "sum"), rev=("rev", "sum"))
                                .reset_index().sort_values("month_num"))

        best_im       = item_monthly.loc[item_monthly["qty"].idxmax(), "month_label"]
        best_im_qty   = int(item_monthly["qty"].max())
        best_im_rev   = item_monthly["rev"].max()

        ic1, ic2, ic3, ic4 = st.columns(4)
        ic1.markdown(metric_card("Total Units", f"{total_i_units:,}", "All time"), unsafe_allow_html=True)
        ic2.markdown(metric_card("Total Revenue", f"${total_i_rev:,.2f}", "All time"), unsafe_allow_html=True)
        ic3.markdown(metric_card("Best Month", best_im,
                                 f"{best_im_qty:,} units · ${best_im_rev:,.2f}", gold=True),
                     unsafe_allow_html=True)
        ic4.markdown(metric_card("Avg. Unit Price", f"${avg_price:.2f}", "Across all sales"),
                     unsafe_allow_html=True)
        st.markdown("")

        st.markdown(f'<div class="section-header">{selected_item} — Monthly Sales</div>',
                    unsafe_allow_html=True)

        fig_item = make_subplots(specs=[[{"secondary_y": True}]])
        fig_item.add_trace(go.Bar(
            x=item_monthly["month_label"], y=item_monthly["qty"], name="Units Sold",
            marker_color=["#f59e0b" if m == best_im else "#5eead4"
                          for m in item_monthly["month_label"]],
            hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>",
        ), secondary_y=False)
        fig_item.add_trace(go.Scatter(
            x=item_monthly["month_label"], y=item_monthly["rev"], name="Revenue ($)",
            line=dict(color="#f87171", width=3), mode="lines+markers", marker=dict(size=8),
            hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
        ), secondary_y=True)
        fig_item.update_layout(
            paper_bgcolor="#1e2130", plot_bgcolor="#1e2130", font=dict(color="#c7d0e8"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified", bargap=0.35,
        )
        fig_item.update_yaxes(title_text="Units Sold", secondary_y=False,
                              gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
        fig_item.update_yaxes(title_text="Revenue ($)", secondary_y=True,
                              gridcolor="rgba(0,0,0,0)", tickprefix="$",
                              tickfont=dict(color="#f87171"))
        fig_item.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
        st.plotly_chart(fig_item, use_container_width=True)

        st.markdown('<div class="section-header">Month-by-Month Breakdown</div>',
                    unsafe_allow_html=True)
        tbl = item_monthly.copy()
        tbl["Avg. Price"] = (tbl["rev"] / tbl["qty"].replace(0, float("nan"))).map("${:.2f}".format)
        tbl["Revenue"]    = tbl["rev"].map("${:,.2f}".format)
        tbl["Units Sold"] = tbl["qty"].map("{:,.0f}".format)
        tbl["Best"]       = tbl["month_label"].apply(lambda m: "🏆" if m == best_im else "")
        tbl = tbl[["month_label", "Units Sold", "Revenue", "Avg. Price", "Best"]].rename(
            columns={"month_label": "Month"}).reset_index(drop=True)
        tbl.index += 1
        st.dataframe(tbl, use_container_width=True, height=min(80 + len(tbl) * 40, 420))

        with st.expander("Week-by-week breakdown"):
            item_weekly = (item_df.groupby("week_start")
                                  .agg(qty=("qty", "sum"), rev=("rev", "sum"))
                                  .reset_index().sort_values("week_start"))
            item_weekly["Week"]       = item_weekly["week_start"].dt.strftime("Week of %b %d, %Y")
            item_weekly["Units Sold"] = item_weekly["qty"].map("{:,.0f}".format)
            item_weekly["Revenue"]    = item_weekly["rev"].map("${:,.2f}".format)
            out = item_weekly[["Week", "Units Sold", "Revenue"]].reset_index(drop=True)
            out.index += 1
            st.dataframe(out, use_container_width=True, height=min(80 + len(out) * 40, 360))

    st.caption(
        f"SnowFruit Store 327 · {len(df):,} transactions · "
        f"{df['date'].min().strftime('%b %d')} – {df['date'].max().strftime('%b %d, %Y')}"
    )


if __name__ == "__main__":
    main()
