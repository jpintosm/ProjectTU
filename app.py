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

st.sidebar.header("Chart settings")

top_n = st.sidebar.slider("Top N (rankings)", min_value=5, max_value=30, value=15, step=5)
change_n = st.sidebar.slider("Top N (changes 2019→2024)", min_value=5, max_value=30, value=15, step=5)

# Para gráficos que comparan países en líneas (evitar spaghetti)
max_countries = st.sidebar.slider("Max countries to show (line charts)", 3, 15, 8, 1)
if len(selected_countries) > max_countries:
    st.sidebar.warning(f"Too many countries selected. Showing first {max_countries}.")
    selected_countries = selected_countries[:max_countries]

# ----- KPI row -----
col1, col2, col3 = st.columns(3)
col1.metric("Countries", df_f["Country name"].nunique())
col2.metric("Years", df_f["Year"].nunique())
col3.metric("Rows", len(df_f))

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview", "Rankings", "Changes", "Drivers", "Groups", "Map"
])

# ----- Chart 1: Global + selected countries -----
with tab1:
    st.subheader("P1. Global trend of life evaluation (with optional country comparison)")

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
        plot_df, x="Year", y="life_eval", color="Country name", markers=True,
        title="Life Evaluation Over Time (Global + Selected Countries)",
        labels={"life_eval": "Life evaluation (3-year average)", "Country name": "Series"}
    )

    # Solo global visible si no seleccionas países
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


with tab2:
    st.subheader("P2. Differences between countries (Top vs Bottom)")

    country_avg = (
        df_f.groupby("Country name", as_index=False)["Life evaluation (3-year average)"]
            .mean()
            .rename(columns={"Life evaluation (3-year average)": "avg_life_eval"})
            .sort_values("avg_life_eval", ascending=False)
    )

    top_countries = country_avg.head(top_n).copy()
    bottom_countries = country_avg.tail(top_n).copy()
    top_countries["Group"] = "Top countries"
    bottom_countries["Group"] = "Bottom countries"
    plot_rank = pd.concat([top_countries, bottom_countries], ignore_index=True)

    fig2 = px.bar(
        plot_rank,
        x="avg_life_eval",
        y="Country name",
        color="Group",
        orientation="h",
        title=f"Top and Bottom {top_n} Countries by Average Life Evaluation",
        labels={"avg_life_eval": "Average life evaluation", "Country name": "Country"}
    )

    fig2.update_layout(template="plotly_white", yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("P3. Biggest changes from 2019 to 2024 (increase vs decrease)")

    # Verificar que existan ambos años en el df filtrado
    years_available = set(df_f["Year"].unique())
    if 2019 not in years_available or 2024 not in years_available:
        st.warning("To compute changes (2019 → 2024), please include both years in the Year range filter.")
        st.stop()

    df_2019 = df_f[df_f["Year"] == 2019][["Country name", "Life evaluation (3-year average)"]]
    df_2024 = df_f[df_f["Year"] == 2024][["Country name", "Life evaluation (3-year average)"]]

    change_df = df_2019.merge(df_2024, on="Country name", suffixes=("_2019", "_2024"))

    # Seguridad extra: si por alguna razón quedara vacío
    if change_df.empty:
        st.warning("No matching countries found between 2019 and 2024 within the current filters.")
        st.stop()

    change_df["change"] = (
        change_df["Life evaluation (3-year average)_2024"]
        - change_df["Life evaluation (3-year average)_2019"]
    )

    inc = change_df.sort_values("change", ascending=False).head(change_n).copy()
    dec = change_df.sort_values("change", ascending=True).head(change_n).copy()
    plot_change = pd.concat([inc, dec], ignore_index=True)

    # Dumbbell plot
    fig3 = px.scatter(
        plot_change,
        y="Country name",
        x="Life evaluation (3-year average)_2019",
        title=f"Changes in Life Evaluation (2019 → 2024): Top {change_n} increases & decreases",
        labels={"Life evaluation (3-year average)_2019": "Life evaluation"},
    )

    fig3.add_scatter(
        y=plot_change["Country name"],
        x=plot_change["Life evaluation (3-year average)_2024"],
        mode="markers",
        name="2024"
    )

    # Shapes: líneas entre 2019 y 2024
    for _, row in plot_change.iterrows():
        fig3.add_shape(
            type="line",
            x0=row["Life evaluation (3-year average)_2019"],
            x1=row["Life evaluation (3-year average)_2024"],
            y0=row["Country name"],
            y1=row["Country name"],
            line=dict(width=2)
        )

    fig3.update_layout(template="plotly_white", xaxis_title="Life evaluation", yaxis_title="Country")
    st.plotly_chart(fig3, use_container_width=True)

