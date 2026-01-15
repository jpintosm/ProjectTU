import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="World Happiness Dashboard", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("Happiness.csv")

df = load_data()

st.title("World Happiness (2019–2024) Dashboard")

# ----- Sidebar filters -----
st.sidebar.header("Filters")

years = sorted(df["Year"].unique())
year_min, year_max = st.sidebar.select_slider(
    "Year range",
    options=years,
    value=(min(years), max(years))
)

df_f = df[(df["Year"] >= year_min) & (df["Year"] <= year_max)].copy()

countries = sorted(df_f["Country name"].unique())
selected_countries = st.sidebar.multiselect(
    "Select countries (optional)",
    options=countries,
    default=[]
)

# ----- KPI row -----
col1, col2, col3 = st.columns(3)
col1.metric("Countries", df_f["Country name"].nunique())
col2.metric("Years", df_f["Year"].nunique())
col3.metric("Rows", len(df_f))

st.divider()

# ----- Chart 1: Global + selected countries -----
st.subheader("Life Evaluation Over Time")

global_series = (
    df_f.groupby("Year", as_index=False)["Life evaluation (3-year average)"]
        .mean()
        .assign(**{"Country name": "Global average"})
        .rename(columns={"Life evaluation (3-year average)": "life_eval"})
)

if selected_countries:
    country_series = (
        df_f[df_f["Country name"].isin(selected_countries)]
          [["Year", "Country name", "Life evaluation (3-year average)"]]
          .rename(columns={"Life evaluation (3-year average)": "life_eval"})
    )
    plot_df = pd.concat([global_series, country_series], ignore_index=True)
else:
    plot_df = global_series.copy()

fig1 = px.line(
    plot_df,
    x="Year",
    y="life_eval",
    color="Country name",
    markers=True,
    title="Global average (always) + selected countries",
    labels={"life_eval": "Life evaluation (3-year average)", "Country name": "Series"},
)

# Ocultar países por defecto si no hay selección (solo global visible)
if not selected_countries:
    for tr in fig1.data:
        if tr.name != "Global average":
            tr.visible = "legendonly"

fig1.update_layout(
    hovermode="x unified",
    xaxis=dict(tickmode="linear", dtick=1, rangeslider=dict(visible=True)),
    template="plotly_white"
)

st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ----- Chart 2: Map (country averages) -----
st.subheader("Map: Average Life Evaluation (selected years)")

map_df = (
    df_f.groupby("Country name", as_index=False)["Life evaluation (3-year average)"]
        .mean()
        .rename(columns={"Life evaluation (3-year average)": "avg_life_eval"})
)

fig2 = px.choropleth(
    map_df,
    locations="Country name",
    locationmode="country names",
    color="avg_life_eval",
    color_continuous_scale="Turbo",
    title="Global Distribution of Life Evaluation",
    labels={"avg_life_eval": "Average life evaluation"}
)

vmin = float(map_df["avg_life_eval"].min())
vmax = float(map_df["avg_life_eval"].max())
tickvals = [round(vmin + i*(vmax-vmin)/4, 1) for i in range(5)]

fig2.update_coloraxes(
    cmin=vmin, cmax=vmax,
    colorbar=dict(
        title="Average life evaluation<br>(2019–2024)",
        tickmode="array",
        tickvals=tickvals,
        ticks="outside",
        len=0.6
    )
)

fig2.update_layout(template="simple_white", margin=dict(l=0, r=0, t=50, b=0))
st.plotly_chart(fig2, use_container_width=True)

