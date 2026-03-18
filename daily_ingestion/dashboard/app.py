#!/usr/bin/env python3
"""
HSE TrolleyGAR Dashboard — two-tab Dash app.

Tab 1 (Data):     choropleth map, time series, PACF, weekday means (from PostgreSQL)
Tab 2 (Modeling):  Bayesian model comparison (from CSV files)
"""

import dash
from dash import dcc, html

from about_tab import about_layout
from data_tab import data_layout, register_data_callbacks
from modeling_tab import modeling_layout, register_modeling_callbacks

FONT = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"

app = dash.Dash(__name__, suppress_callback_exceptions=True,
                external_scripts=[
                    'https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.min.js',
                ])

app.layout = html.Div([
    html.H1("HSE TrolleyGAR Dashboard",
            style={"margin": "0 0 16px 0", "fontSize": "24px"}),

    dcc.Tabs(id="main-tabs", value="data", children=[
        dcc.Tab(label="Data", value="data"),
        dcc.Tab(label="Modeling", value="modeling"),
        dcc.Tab(label="About", value="about"),
    ], style={"marginBottom": "16px"}),

    html.Div(id="tab-content"),

], style={"fontFamily": FONT, "padding": "20px",
          "backgroundColor": "#f0f2f5", "minHeight": "100vh"})


@app.callback(
    dash.Output("tab-content", "children"),
    dash.Input("main-tabs", "value"),
)
def render_tab(tab):
    if tab == "modeling":
        return modeling_layout()
    if tab == "about":
        return about_layout()
    return data_layout()


register_data_callbacks(app)
register_modeling_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
