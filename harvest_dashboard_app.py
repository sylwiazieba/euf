import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="EUF — Harvest Dashboard", layout="wide")

st.title("🌱 EUF — 2026 Harvest Dashboard")
st.markdown("""
**Data source:** Harvest tracker (updated weekly)  
**Purpose:** Track and visualize harvest records across crop types, unit types, and distribution channels to support grant reporting and farm operations.

---
""")

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_excel('harvest_tracker_euf_20260719.xlsx')
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("❌ Data file not found. Please ensure `harvest_tracker_euf_20260719.xlsx` is in the same directory.")
    st.stop()

# ── Data cleaning ─────────────────────────────────────────────────────────────
data = df[df["Wholesale"].isna()].copy()
data["Destination"] = data["Donation"].fillna("Food Pantry")
data["Unit Type"] = data["Unit Type"].str.lower().str.strip()

def to_lbs(row):
    if row["Unit Type"] == "weight":
        return row["Weight (lbs)"]
    elif row["Unit Type"] == "bunch":
        return row["Bunches (count)"] * 0.5
    else:
        return None

data["amount_lbs"] = data.apply(to_lbs, axis=1)
plot_df = data.dropna(subset=["amount_lbs"])

# ── Summary statistics ────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Harvested (lbs)", f"{plot_df['amount_lbs'].sum():.0f}")
with col2:
    st.metric("Unique Crops", data["Crop Type"].nunique())
with col3:
    st.metric("Distribution Partners", data["Destination"].nunique())
with col4:
    st.metric("Records", len(df))

st.markdown("---")

# ── Chart 1: Harvest by Crop Type ─────────────────────────────────────────────
st.subheader("📊 Harvest by Crop Type (lbs)")

agg = plot_df.groupby(["Crop Type", "Destination"], as_index=False)["amount_lbs"].sum()
crop_order = agg.groupby("Crop Type")["amount_lbs"].sum().sort_values(ascending=False).index.tolist()

color_map = {
    "Food Pantry":       "#2E8B57",
    "New Bethany":       "#ff7f0e",
    "Pembroke":          "#9467bd",
    "Project of Easton": "#d62728",
    "Safe Harbor":       "#17becf",
}

fig1 = go.Figure()

for dest, dest_df in agg.groupby("Destination"):
    fig1.add_trace(
        go.Bar(
            x=dest_df["Crop Type"],
            y=dest_df["amount_lbs"],
            name=dest,
            marker_color=color_map.get(dest, "#999999"),
            hovertemplate="%{y:.1f} lbs<extra></extra>",
        )
    )

totals = agg.groupby("Crop Type")["amount_lbs"].sum().reindex(crop_order)
fig1.add_trace(
    go.Scatter(
        x=totals.index,
        y=totals.values,
        text=[f"{round(v)}" for v in totals.values],
        mode="text",
        textposition="top center",
        showlegend=False,
        hoverinfo="skip",
    )
)

fig1.update_layout(
    barmode="stack",
    title="Colored by Distribution Destination",
    yaxis_title="Pounds harvested",
    xaxis_tickangle=-45,
    legend_title_text="Destination",
    height=500,
    xaxis={"categoryorder": "array", "categoryarray": crop_order},
    margin=dict(r=140, b=100),
)
fig1.update_yaxes(range=[0, totals.max() * 1.1])

st.plotly_chart(fig1, use_container_width=True)

# ── Chart 2: Pots Distributed ────────────────────────────────────────────────
st.subheader("🪴 Pots Distributed by Crop")

pots_by_crop = (
    data[data["Unit Type"] == "volume"]
    .groupby("Crop Type")["Volume (pots)"]
    .sum()
    .sort_values(ascending=False)
)

if len(pots_by_crop) > 0:
    colors = cm.tab20(np.linspace(0, 1, len(pots_by_crop)))
    
    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(
            x=pots_by_crop.index,
            y=pots_by_crop.values,
            marker_color=[f"rgba({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)},0.8)" for c in colors],
            text=[f"{int(v)}" for v in pots_by_crop.values],
            textposition="inside",
            textfont=dict(size=18, color="white"),
            hovertemplate="<b>%{x}</b><br>%{y} pots<extra></extra>",
        )
    )
    fig2.update_layout(
        title="Community Garden Starts",
        yaxis_title="Number of Pots",
        xaxis_tickangle=-45,
        height=450,
        margin=dict(b=100),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No pot distributions recorded yet.")

# ── Chart 3: Harvest Calendar ────────────────────────────────────────────────
st.subheader("📅 Harvest Calendar — Weekly Intensity by Crop")
st.caption("Green intensity shows relative harvest volume for each crop in each week")

data_cal = data.copy()
data_cal["Harvest Date"] = pd.to_datetime(data_cal["Harvest Date"])
data_cal["Month"] = data_cal["Harvest Date"].dt.month
data_cal = data_cal[data_cal["amount_lbs"].notna()]

def week_of_month(day):
    return min(((day - 1) // 7) + 1, 4)

data_cal["WeekOfMonth"] = data_cal["Harvest Date"].dt.day.apply(week_of_month)

month_abbr = {4:"Apr", 5:"May", 6:"Jun", 7:"Jul"}
data_cal["MonthName"] = data_cal["Month"].map(month_abbr)
data_cal["WeekBucket"] = data_cal["MonthName"] + " W" + data_cal["WeekOfMonth"].astype(str)

months_in_data = sorted(data_cal["Month"].dropna().unique())
week_order = [f"{month_abbr[m]} W{w}" for m in months_in_data for w in range(1, 5) if f"{month_abbr[m]} W{w}" in data_cal["WeekBucket"].unique()]

pivot = (
    data_cal.groupby(["Crop Type", "WeekBucket"])["amount_lbs"].sum()
    .unstack(fill_value=0)
    .reindex(columns=week_order, fill_value=0)
)

row_max = pivot.max(axis=1).replace(0, np.nan)
normalized = pivot.div(row_max, axis=0).fillna(0)

crop_order_cal = pivot.sum(axis=1).sort_values(ascending=True).index.tolist()
pivot = pivot.reindex(crop_order_cal)
normalized = normalized.reindex(crop_order_cal)

text_array = [[f"{v:.1f} lbs" if v > 0 else "—" for v in row] for row in pivot.values]

fig3 = go.Figure(
    data=go.Heatmap(
        z=normalized.values,
        x=week_order,
        y=normalized.index,
        text=text_array,
        colorscale=[
            [0.0, "#f0f0f0"],
            [0.01, "#c7e9c0"],
            [0.5, "#41ab5d"],
            [1.0, "#00441b"],
        ],
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
        xgap=1, ygap=1,
        showscale=False,
    )
)

# Build month bands (orange headers)
month_to_weeks = {}
for wb in week_order:
    month_name = wb.split(" W")[0]
    month_to_weeks.setdefault(month_name, []).append(wb)

month_shapes = []
month_annotations = []

for month_name, weeks in month_to_weeks.items():
    indices = [week_order.index(w) for w in weeks]
    x_start = min(indices) - 0.5
    x_end = max(indices) + 0.5
    center = (x_start + x_end) / 2

    month_shapes.append(dict(
        type="rect",
        xref="x", yref="paper",
        x0=x_start, x1=x_end,
        y0=1.01, y1=1.09,
        fillcolor="#e67e22",
        line=dict(color="#e67e22", width=0),
        layer="above",
    ))

    month_annotations.append(dict(
        x=center, xref="x",
        y=1.055, yref="paper",
        text=f"<b>{month_name}</b>",
        showarrow=False,
        font=dict(size=13, color="white"),
        xanchor="center",
        yanchor="middle",
    ))

# Month dividers
month_dividers = []
prev_month = None
for i, wb in enumerate(week_order):
    current_month = wb.split(" W")[0]
    if prev_month is not None and current_month != prev_month:
        month_dividers.append(dict(
            type="line",
            xref="x", yref="paper",
            x0=i - 0.5, x1=i - 0.5,
            y0=0, y1=1.0,
            line=dict(color="#888888", width=2),
            layer="above",
        ))
    prev_month = current_month

fig3.update_layout(
    title="",
    yaxis_title="Crop",
    height=500,
    plot_bgcolor="white",
    margin=dict(b=80, t=100),
    annotations=month_annotations,
    shapes=month_shapes + month_dividers,
)
st.plotly_chart(fig3, use_container_width=True)

# ── Data notes ────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📋 Data Notes"):
    st.markdown("""
    **Unit types:**
    - **weight** — pounds (lbs)
    - **bunch** — counted bunches (herbs) — converted to ~0.5 lbs per bunch
    - **volume** — individual pots donated to community for home growing
    - **bin** — full harvested bins (not converted to lbs if unweighed at time of logging). Note, there are currently 7 bins and they are not reflected in the above visualizations.
    
    **Distribution logic:**
    - If **Donation** or **Wholesale** columns are blank → recorded as **Food Pantry**
    - Otherwise recorded by organization name
    
    **Data source:** `harvest_tracker_euf_20260719.xlsx`  
    **Last updated:** July 19, 2026
    """)
