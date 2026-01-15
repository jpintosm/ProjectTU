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

top_n = st.sidebar.slider("Top N (rankings)", min_value=5, max_value=25, value=15, step=5)
change_n = st.sidebar.slider("Top N (changes 2019→2024)", min_value=5, max_value=25, value=15, step=5)

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
        title="Life evaluation over time (Global + Selected Countries)",
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
        title=f"Top and bottom {top_n} countries by average life evaluation",
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
        title=f"Changes in life evaluation (2019 → 2024): Top {change_n} increases & decreases",
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
    st.subheader("Drivers of happiness (GDP, Social Support, and factor strength)")

    required_cols = [
        "Country name",
        "Life evaluation (3-year average)",
        "Explained by: Log GDP per capita",
        "Explained by: Social support",
        "Explained by: Healthy life expectancy",
        "Explained by: Freedom to make life choices",
        "Explained by: Generosity",
        "Explained by: Perceptions of corruption",
    ]

    missing = [c for c in required_cols if c not in df_f.columns]
    if missing:
        st.error("Missing columns in the dataset: " + ", ".join(missing))
        st.stop()

    # --- Country-level averages (2019–2024 within current filter) ---
    country_full = (
        df_f.groupby("Country name", as_index=False)
            .agg({
                "Life evaluation (3-year average)": "mean",
                "Explained by: Log GDP per capita": "mean",
                "Explained by: Social support": "mean",
                "Explained by: Healthy life expectancy": "mean",
                "Explained by: Freedom to make life choices": "mean",
                "Explained by: Generosity": "mean",
                "Explained by: Perceptions of corruption": "mean",
            })
            .rename(columns={
                "Life evaluation (3-year average)": "life_eval",
                "Explained by: Log GDP per capita": "gdp",
                "Explained by: Social support": "social_support",
                "Explained by: Healthy life expectancy": "healthy_life",
                "Explained by: Freedom to make life choices": "freedom",
                "Explained by: Generosity": "generosity",
                "Explained by: Perceptions of corruption": "corruption",
            })
    )

    # Convertir a numérico por seguridad
    num_cols = ["life_eval", "gdp", "social_support", "healthy_life", "freedom", "generosity", "corruption"]
    for c in num_cols:
        country_full[c] = pd.to_numeric(country_full[c], errors="coerce")

    country_full = country_full.dropna(subset=["life_eval"])  # mínimo indispensable

    if country_full.empty:
        st.warning("No data available for the current filters.")
        st.stop()

    # ---------- P4: GDP vs Life Evaluation ----------
    st.markdown("**P4. Relationship: GDP per capita vs life evaluation (country averages)**")

    fig4 = px.scatter(
        country_full.dropna(subset=["gdp"]),
        x="gdp",
        y="life_eval",
        hover_name="Country name",
        opacity=0.7,
        title="GDP per capita vs life evaluation (country averages)",
        labels={"gdp": "Avg Log GDP per capita", "life_eval": "Avg Life evaluation"}
    )
    fig4.update_layout(template="plotly_white")
    st.plotly_chart(fig4, use_container_width=True)

    # ---------- P6: Facets (GDP vs Social support) ----------
    st.markdown("**P6. Compare associations: GDP vs social support (faceted)**")

    long_df = country_full.melt(
        id_vars=["Country name", "life_eval"],
        value_vars=["gdp", "social_support"],
        var_name="Factor",
        value_name="Factor value"
    )

    long_df["Factor"] = long_df["Factor"].replace({
        "gdp": "Log GDP per capita",
        "social_support": "Social support"
    })

    fig6 = px.scatter(
        long_df.dropna(subset=["Factor value"]),
        x="Factor value",
        y="life_eval",
        facet_col="Factor",
        hover_name="Country name",
        opacity=0.7,
        title="Life Evaluation vs key factors (Country averages)",
        labels={"life_eval": "Avg Life evaluation", "Factor value": "Factor value"}
    )
    fig6.update_layout(template="plotly_white")
    st.plotly_chart(fig6, use_container_width=True)

    # ---------- P5: Correlation ranking ----------
    st.markdown("**P5. Which factor correlates most with life evaluation?**")

    factors_cols = ["gdp", "social_support", "healthy_life", "freedom", "generosity", "corruption"]

    corr_rows = []
    for f in factors_cols:
        tmp = country_full[[f, "life_eval"]].dropna()
        if len(tmp) < 3:
            corr = None
        else:
            corr = tmp[f].corr(tmp["life_eval"])
        corr_rows.append({"Factor": f, "Correlation": corr})

    corr_df = pd.DataFrame(corr_rows).dropna().sort_values("Correlation", ascending=False)

    corr_df["Factor"] = corr_df["Factor"].replace({
        "gdp": "GDP per capita",
        "social_support": "Social support",
        "healthy_life": "Healthy life expectancy",
        "freedom": "Freedom",
        "generosity": "Generosity",
        "corruption": "Corruption",
    })

    fig5 = px.bar(
        corr_df,
        x="Correlation",
        y="Factor",
        orientation="h",
        title="Correlation with life evaluation (Country averages)",
        labels={"Correlation": "Pearson correlation", "Factor": "Factor"}
    )
    fig5.update_layout(template="plotly_white", yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig5, use_container_width=True)

    st.caption("Note: Correlation indicates association, not causation.")


with tab5:
    st.subheader("Groups & profiles")

    # =========================
    # P7: High life evaluation despite low GDP (bar)
    # =========================
    st.subheader("P7. High life evaluation despite low GDP (country averages)")
    
    # Country-level averages for life_eval and GDP
    cl7 = (
        df_f.groupby("Country name", as_index=False)
            .agg({
                "Life evaluation (3-year average)": "mean",
                "Explained by: Log GDP per capita": "mean"
            })
            .rename(columns={
                "Life evaluation (3-year average)": "life_eval",
                "Explained by: Log GDP per capita": "gdp"
            })
    )

    cl7["life_eval"] = pd.to_numeric(cl7["life_eval"], errors="coerce")
    cl7["gdp"] = pd.to_numeric(cl7["gdp"], errors="coerce")
    cl7 = cl7.dropna(subset=["life_eval", "gdp"])

    if cl7.empty:
        st.warning("No data available for P7 with the current filters.")
    else:
        gdp_median = cl7["gdp"].median()
        life_median = cl7["life_eval"].median()

        high_life_low_gdp = (
            cl7[(cl7["gdp"] < gdp_median) & (cl7["life_eval"] > life_median)]
              .sort_values("life_eval", ascending=False)
              .copy()
        )

        if high_life_low_gdp.empty:
            st.info("No countries fall into the 'high life eval & low GDP' quadrant under current filters.")
        else:
            fig7 = px.bar(
                high_life_low_gdp,
                x="life_eval",
                y="Country name",
                orientation="h",
                title="Countries with high life evaluation despite low GDP (averages)",
                labels={"life_eval": "Avg life evaluation", "Country name": "Country"}
            )
            fig7.update_layout(template="plotly_white", yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(fig7, use_container_width=True)

    st.divider()

    # =========================
    # P8: Factor profile (High vs Low life evaluation)
    # =========================
    st.subheader("P8. Factor profile: High vs Low life evaluation countries")

    needed = [
        "Country name",
        "Life evaluation (3-year average)",
        "Explained by: Log GDP per capita",
        "Explained by: Social support",
        "Explained by: Healthy life expectancy",
        "Explained by: Freedom to make life choices",
        "Explained by: Generosity",
        "Explained by: Perceptions of corruption",
    ]
    missing = [c for c in needed if c not in df_f.columns]
    if missing:
        st.warning("Skipping P8 (missing columns): " + ", ".join(missing))
    else:
        cl8 = (
            df_f.groupby("Country name", as_index=False)
                .agg({
                    "Life evaluation (3-year average)": "mean",
                    "Explained by: Log GDP per capita": "mean",
                    "Explained by: Social support": "mean",
                    "Explained by: Healthy life expectancy": "mean",
                    "Explained by: Freedom to make life choices": "mean",
                    "Explained by: Generosity": "mean",
                    "Explained by: Perceptions of corruption": "mean",
                })
                .rename(columns={
                    "Life evaluation (3-year average)": "life_eval",
                    "Explained by: Log GDP per capita": "gdp",
                    "Explained by: Social support": "social_support",
                    "Explained by: Healthy life expectancy": "healthy_life",
                    "Explained by: Freedom to make life choices": "freedom",
                    "Explained by: Generosity": "generosity",
                    "Explained by: Perceptions of corruption": "corruption",
                })
        )

        for c in ["life_eval", "gdp", "social_support", "healthy_life", "freedom", "generosity", "corruption"]:
            cl8[c] = pd.to_numeric(cl8[c], errors="coerce")

        cl8 = cl8.dropna(subset=["life_eval"])

        if cl8.empty:
            st.warning("No data available for P8 with the current filters.")
        else:
            life_median = cl8["life_eval"].median()
            cl8["Life group"] = cl8["life_eval"].apply(
                lambda x: "High life evaluation" if x >= life_median else "Low life evaluation"
            )

            group_means = (
                cl8.groupby("Life group", as_index=False)[
                    ["gdp", "social_support", "healthy_life", "freedom", "generosity", "corruption"]
                ].mean()
            )

            long_group = group_means.melt(
                id_vars="Life group",
                var_name="Factor",
                value_name="Average factor value"
            )

            # Etiquetas bonitas
            long_group["Factor"] = long_group["Factor"].replace({
                "gdp": "GDP per capita",
                "social_support": "Social support",
                "healthy_life": "Healthy life expectancy",
                "freedom": "Freedom",
                "generosity": "Generosity",
                "corruption": "Corruption",
            })

            fig8 = px.bar(
                long_group,
                x="Factor",
                y="Average factor value",
                color="Life group",
                barmode="group",
                title="Average factor values by life evaluation group (country averages)"
            )
            fig8.update_layout(template="plotly_white", xaxis_tickangle=-25)
            st.plotly_chart(fig8, use_container_width=True)

    st.divider()

    # =========================
    # P9: Evolution of factors over time (global yearly averages)
    # =========================
    st.subheader("P9. How do happiness factors evolve over time? (global averages)")

    factors = [
        "Explained by: Log GDP per capita",
        "Explained by: Social support",
        "Explained by: Healthy life expectancy",
        "Explained by: Freedom to make life choices",
        "Explained by: Generosity",
        "Explained by: Perceptions of corruption"
    ]
    missing_f = [c for c in factors if c not in df_f.columns]
    if missing_f:
        st.warning("Skipping P9 (missing columns): " + ", ".join(missing_f))
    else:
        yearly = df_f.groupby("Year", as_index=False)[factors].mean()
        long_yearly = yearly.melt(id_vars="Year", var_name="Factor", value_name="Avg contribution")

        long_yearly["Factor"] = long_yearly["Factor"].replace({
            "Explained by: Log GDP per capita": "GDP per capita",
            "Explained by: Social support": "Social support",
            "Explained by: Healthy life expectancy": "Healthy life expectancy",
            "Explained by: Freedom to make life choices": "Freedom",
            "Explained by: Generosity": "Generosity",
            "Explained by: Perceptions of corruption": "Corruption"
        })

        fig9 = px.line(
            long_yearly,
            x="Year",
            y="Avg contribution",
            color="Factor",
            markers=True,
            title="Evolution of happiness factors (global yearly averages)",
            labels={"Avg contribution": "Average factor value"}
        )
        fig9.update_layout(template="plotly_white", legend_title_text="Factor")
        st.plotly_chart(fig9, use_container_width=True)

with tab6:
    st.subheader("Map")

    # Promedio por país dentro del rango seleccionado
    map_df = (
        df_f.groupby("Country name", as_index=False)["Life evaluation (3-year average)"]
            .mean()
            .rename(columns={"Life evaluation (3-year average)": "avg_life_eval"})
    )

    map_df["avg_life_eval"] = pd.to_numeric(map_df["avg_life_eval"], errors="coerce")
    map_df = map_df.dropna(subset=["avg_life_eval"])

    if map_df.empty:
        st.warning("No data available for the map with the current filters.")
        st.stop()

    figm = px.choropleth(
        map_df,
        locations="Country name",
        locationmode="country names",
        color="avg_life_eval",
        color_continuous_scale="Turbo",  # llamativo
        title="Global distribution of life evaluation (selected years)",
        labels={"avg_life_eval": "Average life evaluation"}
    )

    vmin = float(map_df["avg_life_eval"].min())
    vmax = float(map_df["avg_life_eval"].max())
    tickvals = [round(vmin + i*(vmax - vmin)/4, 1) for i in range(5)]

    figm.update_coloraxes(
        cmin=vmin, cmax=vmax,
        colorbar=dict(
            title="Average life evaluation<br>(selected years)",
            tickmode="array",
            tickvals=tickvals,
            ticks="outside",
            len=0.6
        )
    )

    figm.update_layout(
        template="simple_white",
        margin=dict(l=0, r=0, t=50, b=0)
    )

    st.plotly_chart(figm, use_container_width=True)


