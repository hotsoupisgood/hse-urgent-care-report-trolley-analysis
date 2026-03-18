"""
Data tab — choropleth map, time series, PACF grid, weekday means.
All data sourced from PostgreSQL via analysis.queries.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from plotly.subplots import make_subplots
from statsmodels.nonparametric.smoothers_lowess import lowess

# Ensure daily_ingestion root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analysis.queries import (
    get_connection,
    load_daily_by_region,
    load_latest_day_by_region,
)
from analysis.pacf import compute_pacf_by_region
from analysis.weekday import WEEKDAY_LABELS, compute_weekday_means

# ── Shared config ────────────────────────────────────────────────────
GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "hse_regions.geojson")
FONT = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"

NAME_MAP = {
    "HSE Dublin and Midlands": "HSE Dublin and Midlands HR",
    "HSE Dublin and North East": "HSE Dublin and North East HR",
    "HSE Dublin and South East": "HSE Dublin and South East HR",
    "HSE Mid West": "HSE Midwest HR",
    "HSE South West": "HSE South West HR",
    "HSE West and North West": "HSE West and North West HR",
}
LABEL_POS = {
    "HSE Dublin and Midlands":      (53.35, -7.5),
    "HSE Dublin and North East":    (53.7,  -6.6),
    "HSE Dublin and South East":    (52.5,  -6.8),
    "HSE Mid West":                 (52.7,  -8.9),
    "HSE South West":               (51.9,  -9.2),
    "HSE West and North West":      (53.8,  -9.0),
}

with open(GEOJSON_PATH) as f:
    _geojson = json.load(f)

CARD = {
    "backgroundColor": "white",
    "borderRadius": "2px",
    "padding": "20px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
    "marginBottom": "16px",
}


# ── Layout ───────────────────────────────────────────────────────────

def data_layout():
    return html.Div([
        # Choropleth map
        html.Div([
            html.Div([
                html.H3(id="dat-map-title",
                         style={"margin": "0", "fontSize": "16px"}),
                html.Div([
                    dcc.RadioItems(
                        id="dat-metric-toggle",
                        options=[
                            {"label": "Count", "value": "count"},
                            {"label": "Per 10k Population", "value": "per10k"},
                        ],
                        value="count",
                        inline=True,
                        labelStyle={"marginRight": "12px"},
                        style={"fontSize": "13px"},
                    ),
                ], style={"display": "flex", "alignItems": "center"}),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "alignItems": "center", "marginBottom": "8px"}),
            html.Div(id="dat-map-subtitle",
                     style={"fontSize": "13px", "color": "#666", "marginBottom": "8px"}),
            dcc.Graph(id="dat-map", style={"height": "55vh"}),
        ], style=CARD),

        # Time series
        html.Div([
            html.H3(id="dat-ts-title",
                     style={"margin": "0 0 8px 0", "fontSize": "16px"}),
            dcc.Graph(id="dat-timeseries"),
        ], style=CARD),

        # PACF grid
        html.Div([
            html.Div([
                html.H3("Daily Partial Autocorrelation (PACF) by Region",
                         style={"margin": "0", "fontSize": "16px"}),
                html.Div([
                    html.Label("Lags:", style={"marginRight": "6px", "fontWeight": "bold"}),
                    dcc.Input(
                        id="dat-pacf-nlags",
                        type="number",
                        value=60,
                        min=10,
                        max=200,
                        step=10,
                        style={"width": "80px"},
                    ),
                ], style={"display": "flex", "alignItems": "center"}),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "alignItems": "center", "marginBottom": "8px"}),
            dcc.Graph(id="dat-pacf"),
        ], style=CARD),

        # Weekday means
        html.Div([
            html.H3(id="dat-weekday-title",
                     style={"margin": "0 0 8px 0", "fontSize": "16px"}),
            dcc.Graph(id="dat-weekday"),
        ], style=CARD),
    ])


# ── Callbacks ────────────────────────────────────────────────────────

def register_data_callbacks(app):

    # -- Choropleth map -----------------------------------------------
    @app.callback(
        Output("dat-map", "figure"),
        Output("dat-map-subtitle", "children"),
        Output("dat-map-title", "children"),
        Input("dat-metric-toggle", "value"),
    )
    def update_map(metric):
        conn = get_connection()
        df = load_latest_day_by_region(conn)
        conn.close()

        if df.empty:
            return go.Figure(), "No data available", ""

        is_count = metric == "count"
        color_col = "total_trolleys" if is_count else "trolleys_per_10k"
        color_label = "Total Trolleys" if is_count else "Per 10k"
        title = ("Most Recent Day: Total Trolleys by Region"
                 if is_count else
                 "Most Recent Day: Trolleys per 10k by Region")

        report_date = df["report_date"].iloc[0]
        subtitle = f"Data for {report_date.strftime('%d %B %Y')}"

        map_df = df.copy()
        map_df["geojson_name"] = map_df["region"].map(NAME_MAP)

        fig = px.choropleth_map(
            map_df,
            geojson=_geojson,
            locations="geojson_name",
            featureidkey="properties.HR_operational_name",
            color=color_col,
            color_continuous_scale="Reds",
            map_style="carto-positron",
            center={"lat": 53.5, "lon": -8},
            zoom=5.6,
            hover_name="region",
            hover_data={
                "geojson_name": False,
                "trolleys_per_10k": ":.2f",
                "total_trolleys": True,
            },
            labels={color_col: color_label},
            opacity=0.6,
        )
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title=dict(side="right"), thickness=15),
            font_family=FONT,
        )

        lats, lons, texts = [], [], []
        for _, row in map_df.iterrows():
            lat, lon = LABEL_POS.get(row["region"], (None, None))
            if lat is None:
                continue
            short = row["region"].replace("HSE ", "").replace(" and ", " & ")
            val = row[color_col]
            fmt = f"{val:.0f}" if is_count else f"{val:.2f}"
            lats.append(lat)
            lons.append(lon)
            texts.append(f"{short}<br>{fmt}")

        fig.add_trace(go.Scattermap(
            lat=lats, lon=lons, mode="markers+text",
            text=texts,
            textfont=dict(size=11, color="black", weight="bold"),
            textposition="middle center",
            marker=dict(size=65, color="rgba(255,255,255,0.75)"),
            hoverinfo="skip", showlegend=False,
        ))
        return fig, subtitle, title

    # -- Time series ---------------------------------------------------
    @app.callback(
        Output("dat-timeseries", "figure"),
        Output("dat-ts-title", "children"),
        Input("dat-metric-toggle", "value"),
    )
    def update_timeseries(metric):
        conn = get_connection()
        df = load_daily_by_region(conn)
        conn.close()

        if df.empty:
            return go.Figure(), ""

        is_count = metric == "count"
        y_col = "total_trolleys" if is_count else "trolleys_per_10k"
        y_label = "Total Trolleys" if is_count else "Trolleys per 10k"
        title = ("Daily Trolley Count Over Time"
                 if is_count else
                 "Daily Trolleys per 10k Over Time")

        colors = px.colors.qualitative.Plotly
        regions = sorted(df["region"].unique())
        fig = go.Figure()

        for i, region in enumerate(regions):
            rdf = df[df["region"] == region].sort_values("report_date")
            color = colors[i % len(colors)]
            short = region.replace("HSE ", "").replace(" and ", " & ")

            # Raw daily data (lighter)
            fig.add_trace(go.Scatter(
                x=rdf["report_date"], y=rdf[y_col],
                mode="lines", name=short,
                line=dict(color=color, width=1),
                opacity=0.3,
                legendgroup=short,
                hovertemplate="%{x|%d %b %Y}: %{y:.1f}<extra>" + short + "</extra>",
            ))

            # LOWESS trend (frac ~30 days / series length)
            y_vals = rdf[y_col].values.astype(float)
            x_num = np.arange(len(y_vals))
            frac = min(30 / len(y_vals), 0.3) if len(y_vals) > 30 else 0.3
            smoothed = lowess(y_vals, x_num, frac=frac, return_sorted=False)

            fig.add_trace(go.Scatter(
                x=rdf["report_date"], y=smoothed,
                mode="lines", name=f"{short} (trend)",
                line=dict(color=color, width=2.5),
                legendgroup=short,
                showlegend=False,
                hovertemplate="%{x|%d %b %Y}: %{y:.1f}<extra>" + short + " trend</extra>",
            ))

        # Default to last 6 months, with range slider for full history
        max_date = df["report_date"].max()
        six_months_ago = max_date - pd.DateOffset(months=6)

        fig.update_layout(
            font_family=FONT,
            legend_title_text="",
            xaxis=dict(
                range=[six_months_ago, max_date],
                rangeslider=dict(visible=True),
            ),
            yaxis_title=y_label,
        )
        return fig, title

    # -- PACF grid (always per 10k — autocorrelation structure) --------
    @app.callback(
        Output("dat-pacf", "figure"),
        Input("dat-pacf-nlags", "value"),
    )
    def update_pacf(nlags):
        nlags = int(nlags) if nlags else 60

        conn = get_connection()
        df = load_daily_by_region(conn)
        conn.close()

        if df.empty:
            return go.Figure()

        pacf_results = compute_pacf_by_region(df, nlags=nlags)
        if not pacf_results:
            return go.Figure()

        region_names = sorted(pacf_results.keys())
        n = len(region_names)
        ncols = min(n, 3)
        nrows = (n + ncols - 1) // ncols

        fig = make_subplots(
            rows=nrows, cols=ncols,
            subplot_titles=[r.replace("HSE ", "") for r in region_names],
            vertical_spacing=0.08,
            horizontal_spacing=0.06,
        )

        for idx, region in enumerate(region_names):
            r = idx // ncols + 1
            c = idx % ncols + 1
            data = pacf_results[region]
            lags = data["lags"]
            vals = data["pacf"]
            ci_lo = data["ci_lower"]
            ci_hi = data["ci_upper"]

            # Significance band (≈ ±1.96/√n)
            thresh = ci_hi[1]  # offset at lag 1 (representative)
            band_x = [lags[0], lags[-1], lags[-1], lags[0]]
            band_y = [thresh, thresh, -thresh, -thresh]
            fig.add_trace(go.Scatter(
                x=band_x, y=band_y,
                fill="toself",
                fillcolor="rgba(135,206,250,0.3)",
                mode="none",
                showlegend=False,
                hoverinfo="skip",
            ), row=r, col=c)

            # PACF bars
            fig.add_trace(go.Bar(
                x=lags, y=vals,
                marker_color="steelblue",
                showlegend=False,
                hovertemplate="Lag %{x}: %{y:.3f}<extra></extra>",
            ), row=r, col=c)

        fig.update_layout(
            height=280 * nrows,
            font_family=FONT,
            margin={"t": 40, "b": 30},
        )
        return fig

    # -- Weekday means -------------------------------------------------
    @app.callback(
        Output("dat-weekday", "figure"),
        Output("dat-weekday-title", "children"),
        Input("dat-metric-toggle", "value"),
    )
    def update_weekday(metric):
        conn = get_connection()
        df = load_daily_by_region(conn)
        conn.close()

        if df.empty:
            return go.Figure(), ""

        is_count = metric == "count"
        means = compute_weekday_means(df)
        y_col = "mean_total_trolleys" if is_count else "mean_trolleys_per_10k"
        y_label = "Mean Total Trolleys" if is_count else "Mean Trolleys per 10k"
        title = ("Mean Daily Trolley Count by Day of Week"
                 if is_count else
                 "Mean Daily Trolleys per 10k by Day of Week")

        fig = px.line(
            means,
            x="weekday_label",
            y=y_col,
            color="region",
            markers=True,
            category_orders={"weekday_label": WEEKDAY_LABELS},
            labels={
                "weekday_label": "Day of Week",
                y_col: y_label,
                "region": "Region",
            },
        )
        fig.update_layout(font_family=FONT, legend_title_text="")
        return fig, title
