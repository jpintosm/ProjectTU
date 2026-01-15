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


with tab4:
    st.subheader("Drivers of happiness (GDP, social support, and factor strength)")

    # Country-level averages (robusto y consistente con tu análisis)
    country_level = (
        df_f.groupby("Country name", as_index=False)
            .agg({
                "Life evaluation (3-year average)": "mean",
                "Explained by: Log GDP per capita": "mean",
                "Explained by: Social support": "mean"
            })
            .rename(columns={
                "Life evaluation (3-year average)": "life_eval",
                "Explained by: Log GDP per capita": "avg_log_gdp",
                "Explained by: Social support": "avg_social_support"
            })
    )

    # --- P4 (mejor versión): 1 punto = 1 país, GDP vs life_eval ---
    st.markdown("**P4. Relationship: GDP per capita vs Life Evaluation (country averages)**")
    fig4 = px.scatter(
        country_level,
        x="avg_log_gdp",
        y="life_eval",
        trendline="ols",
        hover_name="Country name",
        opacity=0.7,
        title="GDP per capita vs Life Evaluation (Country Averages)",
        labels={"avg_log_gdp": "Avg Log GDP per capita", "life_eval": "Avg Life evaluation"}
    )
    fig4.update_layout(template="plotly_white")
    st.plotly_chart(fig4, use_container_width=True)

    # --- P6: comparación en un solo gráfico (facets) ---
    st.markdown("**P6. Compare correlations: GDP vs Social Support (faceted)**")
    long_df = country_level.melt(
        id_vars=["Country name", "life_eval"],
        value_vars=["avg_log_gdp", "avg_social_support"],
        var_name="Factor",
        value_name="Factor value"
    )
    long_df["Factor"] = long_df["Factor"].replace({
        "avg_log_gdp": "Log GDP per capita",
        "avg_social_support": "Social support"
    })

    fig6 = px.scatter(
        long_df,
        x="Factor value",
        y="life_eval",
        facet_col="Factor",
        trendline="ols",
        hover_name="Country name",
        opacity=0.7,
        title="Life Evaluation vs Key Factors (Country Averages)",
        labels={"life_eval": "Avg Life evaluation", "Factor value": "Factor value"}
    )
    fig6.update_layout(template="plotly_white")
    st.plotly_chart(fig6, use_container_width=True)

    st.markdown("**P5. Which factor correlates most with life evaluation?**")

    # Construir country_level completo de factores
    factors_full = [
        "Explained by: Log GDP per capita",
        "Explained by: Social support",
        "Explained by: Healthy life expectancy",
        "Explained by: Freedom to make life choices",
        "Explained by: Generosity",
        "Explained by: Perceptions of corruption"
    ]

    country_full = (
        df_f.groupby("Country name", as_index=False)
            .agg({**{"Life evaluation (3-year average)": "mean"}, **{c: "mean" for c in factors_full}})
            .rename(columns={"Life evaluation (3-year average)": "life_eval"})
    )

    corr = (
        country_full[factors_full + ["life_eval"]]
            .corr(numeric_only=True)["life_eval"]
            .drop("life_eval")
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"index": "Factor", "life_eval": "Correlation"})
    )

    corr["Factor"] = corr["Factor"].replace({
        "Explained by: Log GDP per capita": "GDP per capita",
        "Explained by: Social support": "Social support",
        "Explained by: Healthy life expectancy": "Healthy life expectancy",
        "Explained by: Freedom to make life choices": "Freedom",
        "Explained by: Generosity": "Generosity",
        "Explained by: Perceptions of corruption": "Corruption"
    })

    fig5 = px.bar(
        corr,
        x="Correlation",
        y="Factor",
        orientation="h",
        title="Correlation with Life Evaluation (Country Averages)",
        labels={"Correlation": "Pearson correlation", "Factor": "Factor"}
    )
    fig5.update_layout(template="plotly_white", yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig5, use_container_width=True)
