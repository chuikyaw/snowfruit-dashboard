import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from pathlib import Path

DATA_FILE = Path("data/sales_data.parquet")

st.set_page_config(page_title="SnowFruit Sales Dashboard", page_icon="🍍",
                   layout="wide", initial_sidebar_state="auto")

st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    h1, h2, h3 { color: #ffffff; }
    .metric-card { background:#1e2130;border-radius:12px;padding:18px 22px;
                   border:1px solid #2d3148;height:100%; }
    .metric-card.gold { border-color: #f59e0b; }
    .metric-label { color:#8b92a9;font-size:12px;text-transform:uppercase;letter-spacing:1px; }
    .metric-value { color:#ffffff;font-size:26px;font-weight:700;margin-top:4px; }
    .metric-sub      { color:#5eead4;font-size:13px;margin-top:2px; }
    .metric-sub-gold { color:#f59e0b;font-size:13px;margin-top:2px; }
    .section-header { color:#c7d0e8;font-size:15px;font-weight:600;
        text-transform:uppercase;letter-spacing:1.2px;
        margin:24px 0 12px 0;border-bottom:1px solid #2d3148;padding-bottom:6px; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
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
    date_col = find_column(df, ["date","transaction date","sale date","trans date"])
    item_col = find_column(df, ["product name","item","item name","product",
                                "description","desc","name","menu item"])
    qty_col  = find_column(df, ["qs","qty","quantity","units","count","sold"])
    rev_col  = find_column(df, ["qs*rcp","total","revenue","sales","price",
                                "amount","gross","net sales","ext price","total price"])
    if not date_col or not item_col or (not qty_col and not rev_col):
        return pd.DataFrame()
    clean = pd.DataFrame()
    clean["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
    clean["item"] = df[item_col].astype(str).str.strip()
    clean["qty"]  = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) if qty_col else 0.0
    clean["rev"]  = pd.to_numeric(df[rev_col], errors="coerce").fillna(0) if rev_col else 0.0
    clean = clean.dropna(subset=["date"])
    clean = clean[(clean["item"].str.len() > 0) & (clean["item"] != "nan")]
    return clean

def sun_week_start(dates):
    return dates - pd.to_timedelta((dates.dt.dayofweek + 1) % 7, unit="d")

def mc(label, value, sub, gold=False):
    cls = "metric-card gold" if gold else "metric-card"
    sc  = "metric-sub-gold" if gold else "metric-sub"
    return (f'<div class="{cls}"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div>'
            f'<div class="{sc}">{sub}</div></div>')

def section(title):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

# ── Charts ─────────────────────────────────────────────────────────────────────
def monthly_trend_chart(mdf, sel):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = ["#f59e0b" if r.month_label == sel else "#2d6b8a" for _,r in mdf.iterrows()]
    fig.add_trace(go.Bar(x=mdf["month_label"], y=mdf["rev"], name="Revenue ($)",
                         marker_color=colors,
                         hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=mdf["month_label"], y=mdf["qty"], name="Units Sold",
                             line=dict(color="#5eead4",width=3), mode="lines+markers",
                             marker=dict(size=8),
                             hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>"),
                  secondary_y=True)
    fig.update_layout(paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
                      font=dict(color="#c7d0e8"),
                      legend=dict(orientation="h",yanchor="bottom",y=1.02,
                                  xanchor="right",x=1,bgcolor="rgba(0,0,0,0)"),
                      margin=dict(l=20,r=20,t=40,b=20),
                      hovermode="x unified", bargap=0.35)
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=False,
                     gridcolor="#2d3148", tickprefix="$", tickfont=dict(color="#8b92a9"))
    fig.update_yaxes(title_text="Units Sold", secondary_y=True,
                     gridcolor="rgba(0,0,0,0)", tickfont=dict(color="#5eead4"))
    fig.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    return fig

def h_bar(idf, col, top=True, n=10, title=""):
    d = idf.sort_values(col, ascending=not top).head(n)
    if not top:
        d = d.sort_values(col, ascending=True)
    fig = go.Figure(go.Bar(
        x=d[col], y=d["item"], orientation="h",
        marker_color="#5eead4" if top else "#f87171",
        customdata=d["rev"] if "rev" in d.columns else d[col],
        hovertemplate="<b>%{y}</b><br>Units: %{x:,}<br>Revenue: $%{customdata:,.2f}<extra></extra>",
    ))
    fig.update_layout(title=dict(text=title, font=dict(color="#c7d0e8",size=14)),
                      paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
                      font=dict(color="#c7d0e8"),
                      margin=dict(l=10,r=10,t=36,b=10), height=320,
                      xaxis=dict(gridcolor="#2d3148", tickfont=dict(color="#8b92a9")),
                      yaxis=dict(tickfont=dict(color="#c7d0e8")))
    return fig

def daily_chart(ddf, sel_date):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors  = ["#5eead4" if r.date == sel_date else "#2d7a70" for _,r in ddf.iterrows()]
    xlabels = [r.date.strftime("%a\n%b %d") for _,r in ddf.iterrows()]
    fig.add_trace(go.Bar(x=xlabels, y=ddf["qty"], name="Units Sold",
                         marker_color=colors,
                         hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=xlabels, y=ddf["rev"], name="Revenue ($)",
                             line=dict(color="#f59e0b",width=3), mode="lines+markers",
                             marker=dict(size=8),
                             hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>"),
                  secondary_y=True)
    fig.update_layout(paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
                      font=dict(color="#c7d0e8"),
                      legend=dict(orientation="h",yanchor="bottom",y=1.02,
                                  xanchor="right",x=1,bgcolor="rgba(0,0,0,0)"),
                      margin=dict(l=20,r=20,t=40,b=20),
                      hovermode="x unified", bargap=0.35)
    fig.update_yaxes(title_text="Units Sold", secondary_y=False,
                     gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=True,
                     gridcolor="rgba(0,0,0,0)", tickprefix="$",
                     tickfont=dict(color="#f59e0b"))
    fig.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    return fig

def item_chart(im, best):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=im["month_label"], y=im["qty"], name="Units Sold",
                         marker_color=["#f59e0b" if m==best else "#5eead4"
                                       for m in im["month_label"]],
                         hovertemplate="%{x}<br>Units: %{y:,}<extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=im["month_label"], y=im["rev"], name="Revenue ($)",
                             line=dict(color="#f87171",width=3), mode="lines+markers",
                             marker=dict(size=8),
                             hovertemplate="%{x}<br>Revenue: $%{y:,.2f}<extra></extra>"),
                  secondary_y=True)
    fig.update_layout(paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
                      font=dict(color="#c7d0e8"),
                      legend=dict(orientation="h",yanchor="bottom",y=1.02,
                                  xanchor="right",x=1,bgcolor="rgba(0,0,0,0)"),
                      margin=dict(l=20,r=20,t=40,b=20),
                      hovermode="x unified", bargap=0.35)
    fig.update_yaxes(title_text="Units Sold", secondary_y=False,
                     gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=True,
                     gridcolor="rgba(0,0,0,0)", tickprefix="$",
                     tickfont=dict(color="#f87171"))
    fig.update_xaxes(gridcolor="#2d3148", tickfont=dict(color="#8b92a9"))
    return fig

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:4px;">
        <span style="font-size:36px;">🍍</span>
        <div>
            <h1 style="margin:0;font-size:28px;color:#fff;">SnowFruit Sales Dashboard</h1>
            <p style="margin:0;color:#8b92a9;font-size:14px;">Store 327 &middot; Year-to-date performance</p>
        </div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    # Sidebar
    with st.sidebar:
        st.markdown("### SnowFruit Dashboard")
        st.markdown("---")
        st.markdown("#### Owner Access")
        pin_input = st.text_input("PIN", type="password", placeholder="Enter PIN",
                                  label_visibility="collapsed")
        correct_pin = False
        try:
            correct_pin = (pin_input == st.secrets["PIN"])
        except Exception:
            if pin_input:
                st.warning("No PIN configured yet.")
        if correct_pin:
            st.success("Access granted")
            st.markdown("**Upload new weekly files:**")
            uploaded_files = st.file_uploader("xlsx", type=["xlsx"],
                                              accept_multiple_files=True,
                                              label_visibility="collapsed")
        else:
            uploaded_files = []
            if pin_input and not correct_pin:
                st.error("Incorrect PIN")
        st.markdown("---")
        st.caption("To save permanently:\nrun update_data.py,\nthen upload parquet to GitHub.")

    # Load data
    df = None
    if DATA_FILE.exists():
        with st.spinner("Loading..."):
            df = pd.read_parquet(DATA_FILE)
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        if correct_pin and uploaded_files:
            new_frames = [x for x in [parse_file(f) for f in uploaded_files] if not x.empty]
            if new_frames:
                df = pd.concat([df]+new_frames, ignore_index=True).drop_duplicates()
                df = df.sort_values("date")
                st.sidebar.success(f"{len(new_frames)} file(s) merged (session only)")
                st.sidebar.info("Run update_data.py to make permanent.")
    elif correct_pin and uploaded_files:
        frames = [x for x in [parse_file(f) for f in uploaded_files] if not x.empty]
        if not frames:
            st.error("No valid data in uploaded files.")
            return
        df = pd.concat(frames, ignore_index=True).drop_duplicates().sort_values("date")
        st.sidebar.info("Loaded for this session.\nRun update_data.py to save permanently.")
    else:
        st.markdown("""
        <div style="background:#1e2130;border:2px dashed #3d4460;border-radius:12px;
                    padding:48px;text-align:center;color:#8b92a9;margin-top:24px;">
            <p style="font-size:22px;margin:0;">No data loaded yet</p>
            <p style="font-size:14px;color:#5a6080;margin-top:12px;">
                This dashboard is managed by the store owner.<br>
                If you were given this link, check back soon!
            </p></div>""", unsafe_allow_html=True)
        return

    if df is None or df.empty:
        st.error("No data available.")
        return

    # Derived columns
    df["month_num"]  = df["date"].dt.month
    df["month_label"]= df["date"].dt.strftime("%b")
    df["week_start"] = sun_week_start(df["date"])   # Sun-Sat weeks

    # YTD metrics
    total_rev    = df["rev"].sum()
    total_units  = int(df["qty"].sum())
    unique_items = df["item"].nunique()
    months_seen  = df["month_label"].nunique()
    monthly_agg  = (df.groupby(["month_num","month_label"])
                      .agg(rev=("rev","sum"),qty=("qty","sum"))
                      .reset_index().sort_values("month_num"))
    best_month_row  = monthly_agg.loc[monthly_agg["rev"].idxmax()]
    best_month_name = best_month_row["month_label"]
    best_month_rev  = best_month_row["rev"]
    top_item_ytd    = df.groupby("item")["qty"].sum().idxmax()
    top_item_qty    = int(df.groupby("item")["qty"].sum().max())

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.markdown(mc("YTD Revenue",    f"${total_rev:,.2f}",  f"{months_seen} months"),        unsafe_allow_html=True)
    c2.markdown(mc("YTD Units Sold", f"{total_units:,}",    f"{unique_items} unique items"),  unsafe_allow_html=True)
    c3.markdown(mc("Best Month",     best_month_name,       f"${best_month_rev:,.2f}",True),  unsafe_allow_html=True)
    c4.markdown(mc("Top Item YTD",   top_item_ytd[:20],     f"{top_item_qty:,} units sold"),  unsafe_allow_html=True)
    c5.markdown(mc("Data Range",
                   df["date"].min().strftime("%b %d"),
                   "to "+df["date"].max().strftime("%b %d, %Y")),                             unsafe_allow_html=True)
    st.markdown("")

    tab_monthly, tab_weekly, tab_item = st.tabs([
        "📅  Monthly Overview", "🗓  Weekly Drill-Down", "🔎  Item Search"])

    # ── TAB 1: MONTHLY ────────────────────────────────────────────────────────
    with tab_monthly:
        section("Revenue & Units by Month")
        avail_months = monthly_agg["month_label"].tolist()
        if ("selected_month" not in st.session_state or
                st.session_state.selected_month not in avail_months):
            st.session_state.selected_month = best_month_name
        month_cols = st.columns(len(avail_months))
        for col, row in zip(month_cols, monthly_agg.itertuples()):
            pfx   = "🏆 " if row.month_label == best_month_name else ""
            label = f"**{pfx}{row.month_label}**  \n${row.rev:,.0f}  \n{int(row.qty):,} units"
            if col.button(label, key="m_"+row.month_label, use_container_width=True):
                st.session_state.selected_month = row.month_label
        sel_month = st.session_state.selected_month
        st.plotly_chart(monthly_trend_chart(monthly_agg, sel_month), use_container_width=True)

        section(sel_month+" - Top & Bottom Sellers")
        month_df    = df[df["month_label"]==sel_month]
        month_items = month_df.groupby("item").agg(qty=("qty","sum"),rev=("rev","sum")).reset_index()
        mk1,mk2,mk3 = st.columns(3)
        mk1.markdown(mc("Revenue",       f"${month_df['rev'].sum():,.2f}", sel_month),           unsafe_allow_html=True)
        mk2.markdown(mc("Units Sold",    f"{int(month_df['qty'].sum()):,}",
                        f"{month_df['item'].nunique()} unique items"),                            unsafe_allow_html=True)
        mk3.markdown(mc("Weeks of Data", str(month_df["week_start"].nunique()),
                        month_df["date"].min().strftime("%b %d")+" - "+
                        month_df["date"].max().strftime("%b %d")),                               unsafe_allow_html=True)
        st.markdown("")
        lc,rc = st.columns(2)
        with lc:
            st.plotly_chart(h_bar(month_items,"qty",top=True, n=10,title="Top 10 Items - "+sel_month),use_container_width=True)
        with rc:
            st.plotly_chart(h_bar(month_items,"qty",top=False,n=10,title="Bottom 10 Items - "+sel_month),use_container_width=True)
        with st.expander("Full item list for "+sel_month):
            tbl = (month_items.sort_values("qty",ascending=False)
                              .rename(columns={"item":"Item","qty":"Units Sold","rev":"Revenue"})
                              .reset_index(drop=True))
            tbl.index += 1
            tbl["Revenue"]    = tbl["Revenue"].map("${:,.2f}".format)
            tbl["Units Sold"] = tbl["Units Sold"].map("{:,.0f}".format)
            st.dataframe(tbl, use_container_width=True, height=320)

        section("Month-by-Month Comparison")
        comp = monthly_agg.copy()
        comp["Revenue"]    = comp["rev"].map("${:,.2f}".format)
        comp["Units Sold"] = comp["qty"].map("{:,.0f}".format)
        comp["vs. Best"]   = ((monthly_agg["rev"]/best_month_rev-1)*100).map(
            lambda x: ("+") if x>=0 else "")+((monthly_agg["rev"]/best_month_rev-1)*100).map(
            lambda x: f"{x:.1f}%")
        comp = (comp[["month_label","Revenue","Units Sold","vs. Best"]]
                .rename(columns={"month_label":"Month"}).reset_index(drop=True))
        comp.index += 1
        st.dataframe(comp, use_container_width=True, height=min(60+len(comp)*40,380))

    # ── TAB 2: WEEKLY ─────────────────────────────────────────────────────────
    with tab_weekly:
        weeks    = sorted(df["week_start"].unique())
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()

        section("Pick any date to load that week (Sun - Sat)")
        cal_col, info_col = st.columns([1,2])
        with cal_col:
            picked = st.date_input("date", value=max_date,
                                   min_value=min_date, max_value=max_date,
                                   label_visibility="collapsed")

        picked_ts     = pd.Timestamp(picked).normalize()
        week_start_dt = picked_ts - pd.to_timedelta((picked_ts.dayofweek+1)%7, unit="d")
        weeks_ts      = [pd.Timestamp(w) for w in weeks]
        if week_start_dt not in weeks_ts:
            week_start_dt = min(weeks_ts, key=lambda w: abs(w-week_start_dt))
            with info_col:
                st.info("No data for that week. Showing nearest available week.")

        selected_week = week_start_dt
        week_df       = df[df["week_start"]==selected_week]
        dates_sorted  = sorted(week_df["date"].unique())
        w_start_str   = pd.Timestamp(selected_week).strftime("%b %d")
        w_end_str     = week_df["date"].max().strftime("%b %d, %Y")
        with info_col:
            st.markdown(mc("Showing week", w_start_str+" - "+w_end_str,
                           str(len(dates_sorted))+" days of data"),
                        unsafe_allow_html=True)
        st.markdown("")

        best_day = week_df.groupby("date")["rev"].sum().idxmax()
        wk1,wk2,wk3 = st.columns(3)
        wk1.markdown(mc("Week Revenue", f"${week_df['rev'].sum():,.2f}",
                        w_start_str+" - "+w_end_str),                                           unsafe_allow_html=True)
        wk2.markdown(mc("Units Sold",   f"{int(week_df['qty'].sum()):,}",
                        f"{week_df['item'].nunique()} unique items"),                            unsafe_allow_html=True)
        wk3.markdown(mc("Best Day",     pd.Timestamp(best_day).strftime("%A"),
                        "$"+f"{week_df.groupby('date')['rev'].sum().max():,.2f}"),              unsafe_allow_html=True)
        st.markdown("")

        section("Daily Breakdown - Click a day")
        if ("selected_date" not in st.session_state or
                st.session_state.selected_date not in dates_sorted):
            st.session_state.selected_date = dates_sorted[0]
        day_cols = st.columns(len(dates_sorted))
        for i,(col,d) in enumerate(zip(day_cols, dates_sorted)):
            day_rev = week_df[week_df["date"]==d]["rev"].sum()
            day_qty = int(week_df[week_df["date"]==d]["qty"].sum())
            ts      = pd.Timestamp(d)
            day_lbl = ts.strftime("%a")+"  \n"+ts.strftime("%b %d")+"  \n$"+f"{day_rev:,.0f}"+"  \n"+f"{day_qty:,} units"
            if col.button(day_lbl, key=f"wd_{i}_{str(selected_week)}", use_container_width=True):
                st.session_state.selected_date = d

        sel_date      = st.session_state.selected_date
        daily_summary = (week_df.groupby("date").agg(qty=("qty","sum"),rev=("rev","sum"))
                                .reset_index().sort_values("date"))
        st.plotly_chart(daily_chart(daily_summary, sel_date), use_container_width=True)

        sel_ts = pd.Timestamp(sel_date)
        section(sel_ts.strftime("%A, %B %d")+" - Top & Bottom Items")
        day_agg  = (week_df[week_df["date"]==sel_date]
                    .groupby("item").agg(qty=("qty","sum"),rev=("rev","sum")).reset_index())
        lc2,rc2 = st.columns(2)
        with lc2:
            st.plotly_chart(h_bar(day_agg,"qty",top=True, n=5,title="Top 5 by Units"),    use_container_width=True)
        with rc2:
            st.plotly_chart(h_bar(day_agg,"qty",top=False,n=5,title="Bottom 5 by Units"), use_container_width=True)

        section("Full Week Rankings")
        week_items = week_df.groupby("item").agg(qty=("qty","sum"),rev=("rev","sum")).reset_index()
        wc1,wc2 = st.columns(2)
        with wc1:
            st.plotly_chart(h_bar(week_items,"qty",top=True, n=10,title="Top 10 - Full Week"),    use_container_width=True)
        with wc2:
            st.plotly_chart(h_bar(week_items,"qty",top=False,n=10,title="Bottom 10 - Full Week"), use_container_width=True)

    # ── TAB 3: ITEM SEARCH ────────────────────────────────────────────────────
    with tab_item:
        section("Search an Item")
        all_items   = sorted(df["item"].unique())
        default_idx = all_items.index("Pineapple - 18oz") if "Pineapple - 18oz" in all_items else 0
        sel_item    = st.selectbox("Item", options=all_items, index=default_idx,
                                   label_visibility="collapsed")
        item_df       = df[df["item"]==sel_item]
        total_i_units = int(item_df["qty"].sum())
        total_i_rev   = item_df["rev"].sum()
        avg_price     = (item_df["rev"]/item_df["qty"].replace(0,float("nan"))).mean()
        item_monthly  = (item_df.groupby(["month_num","month_label"])
                                .agg(qty=("qty","sum"),rev=("rev","sum"))
                                .reset_index().sort_values("month_num"))
        best_im     = item_monthly.loc[item_monthly["qty"].idxmax(),"month_label"]
        best_im_qty = int(item_monthly["qty"].max())
        best_im_rev = item_monthly["rev"].max()

        ic1,ic2,ic3,ic4 = st.columns(4)
        ic1.markdown(mc("Total Units",     f"{total_i_units:,}",   "All time"),            unsafe_allow_html=True)
        ic2.markdown(mc("Total Revenue",   f"${total_i_rev:,.2f}", "All time"),            unsafe_allow_html=True)
        ic3.markdown(mc("Best Month",      best_im,
                        f"{best_im_qty:,} units - ${best_im_rev:,.2f}", True),             unsafe_allow_html=True)
        ic4.markdown(mc("Avg. Unit Price", f"${avg_price:.2f}",    "Across all sales"),    unsafe_allow_html=True)
        st.markdown("")

        section(sel_item+" - Monthly Sales")
        st.plotly_chart(item_chart(item_monthly, best_im), use_container_width=True)

        section("Month-by-Month Breakdown")
        tbl = item_monthly.copy()
        tbl["Avg. Price"] = (tbl["rev"]/tbl["qty"].replace(0,float("nan"))).map("${:.2f}".format)
        tbl["Revenue"]    = tbl["rev"].map("${:,.2f}".format)
        tbl["Units Sold"] = tbl["qty"].map("{:,.0f}".format)
        tbl["Best"]       = tbl["month_label"].apply(lambda m: "🏆" if m==best_im else "")
        tbl = (tbl[["month_label","Units Sold","Revenue","Avg. Price","Best"]]
               .rename(columns={"month_label":"Month"}).reset_index(drop=True))
        tbl.index += 1
        st.dataframe(tbl, use_container_width=True, height=min(80+len(tbl)*40,420))

        with st.expander("Week-by-week breakdown"):
            iw = (item_df.groupby("week_start").agg(qty=("qty","sum"),rev=("rev","sum"))
                         .reset_index().sort_values("week_start"))
            iw["Week"]       = iw["week_start"].dt.strftime("Week of %b %d, %Y")
            iw["Units Sold"] = iw["qty"].map("{:,.0f}".format)
            iw["Revenue"]    = iw["rev"].map("${:,.2f}".format)
            out = iw[["Week","Units Sold","Revenue"]].reset_index(drop=True)
            out.index += 1
            st.dataframe(out, use_container_width=True, height=min(80+len(out)*40,360))

    st.caption("SnowFruit Store 327 - "+f"{len(df):,}"+" transactions - "+
               df["date"].min().strftime("%b %d")+" to "+
               df["date"].max().strftime("%b %d, %Y"))

if __name__ == "__main__":
    main()
