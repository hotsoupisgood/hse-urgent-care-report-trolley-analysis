"""
Modeling tab — migrated from dash_app_test/app.py.
Shows DIC comparison, alpha map, parameter tables, significance tests,
and Gelman-Rubin diagnostics for Bayesian models.

All component IDs prefixed with 'mdl-' to avoid collision with the Data tab.
"""

import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html

# ── Config ───────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'models')
GEOJSON_PATH = os.path.join(os.path.dirname(__file__), 'hse_regions.geojson')
FONT = 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'

NAME_MAP = {
    'HSE Dublin and Midlands': 'HSE Dublin and Midlands HR',
    'HSE Dublin and North East': 'HSE Dublin and North East HR',
    'HSE Dublin and South East': 'HSE Dublin and South East HR',
    'HSE Mid West': 'HSE Midwest HR',
    'HSE South West': 'HSE South West HR',
    'HSE West and North West': 'HSE West and North West HR',
}
LABEL_POS = {
    'HSE Dublin and Midlands':      (53.35, -7.5),
    'HSE Dublin and North East':    (53.7,  -6.6),
    'HSE Dublin and South East':    (52.5,  -6.8),
    'HSE Mid West':                 (52.7,  -8.9),
    'HSE South West':               (51.9,  -9.2),
    'HSE West and North West':      (53.8,  -9.0),
}

PARAM_DISPLAY = {
    'delta_pre':  'New Years (Pre)',
    'delta_mid':  'New Years (Mid)',
    'delta_post': 'New Years (Post)',
    'sigma_pre':  'Full Reset (Pre)',
    'sigma_mid':  'Full Reset (Mid)',
    'sigma_post': 'Full Reset (Post)',
}

with open(GEOJSON_PATH) as f:
    geojson = json.load(f)

def get_model_choices():
    """Scan models dir for available models (live, not cached)."""
    if not os.path.isdir(MODELS_DIR):
        return []
    return sorted([
        d for d in os.listdir(MODELS_DIR)
        if os.path.isfile(os.path.join(MODELS_DIR, d, 'alpha.csv'))
    ])


def get_dic_df():
    """Build DIC comparison table across all models (live, not cached)."""
    rows = []
    for m in get_model_choices():
        dic_path = os.path.join(MODELS_DIR, m, 'dic.csv')
        if os.path.isfile(dic_path):
            row = pd.read_csv(dic_path).iloc[0].to_dict()
            row['Model'] = m
            rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df[['Model'] + [c for c in df.columns if c != 'Model']]
        df = df.round(2)
    return df

CARD = {
    'backgroundColor': 'white', 'borderRadius': '2px',
    'padding': '20px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
    'marginBottom': '16px',
}
TABLE_STYLE_CELL = {
    'textAlign': 'left', 'padding': '8px',
    'fontFamily': FONT, 'fontSize': '13px',
}
TABLE_STYLE_HEADER = {
    'fontWeight': 'bold', 'backgroundColor': '#f8f9fa',
}


# ── Helpers ──────────────────────────────────────────────────────────

def model_path(model_name, filename):
    return os.path.join(MODELS_DIR, model_name, filename)


def list_csvs(model_name):
    d = os.path.join(MODELS_DIR, model_name)
    return sorted([f[:-4] for f in os.listdir(d)
                   if f.endswith('.csv') and f != 'raw_samples.csv'])


def detect_param_csvs(model_name):
    params = []
    skip = ('summary', 'gelman', 'dic')
    for name in list_csvs(model_name):
        if name.startswith('sig_') or name in skip:
            continue
        params.append(name)
    return params


def detect_sig_csvs(model_name):
    overall = []
    pairwise = []
    for name in list_csvs(model_name):
        if name.startswith('sig_overall_'):
            overall.append(name.replace('sig_overall_', ''))
        elif name.startswith('sig_pairwise_'):
            pairwise.append(name.replace('sig_pairwise_', ''))
    return overall, pairwise


def make_map(alpha_df):
    map_df = alpha_df.copy()
    map_df['geojson_name'] = map_df['Region'].map(NAME_MAP)

    fig = px.choropleth_map(
        map_df, geojson=geojson,
        locations='geojson_name',
        featureidkey='properties.HR_operational_name',
        color='Mean', color_continuous_scale='Reds',
        map_style='carto-positron',
        center={'lat': 53.5, 'lon': -8}, zoom=5.6,
        hover_name='Region',
        hover_data={'geojson_name': False, 'Mean': ':.2f',
                    '2.5%': ':.2f', '97.5%': ':.2f'},
        labels={'Mean': 'Alpha (baseline)'},
        opacity=0.6,
    )
    fig.update_layout(
        margin={'r': 0, 't': 0, 'l': 0, 'b': 0},
        coloraxis_colorbar=dict(title=dict(side='right'), thickness=15),
        font_family=FONT,
    )

    lats, lons, texts = [], [], []
    for _, row in map_df.iterrows():
        lat, lon = LABEL_POS.get(row['Region'], (None, None))
        if lat is None:
            continue
        short = row['Region'].replace('HSE ', '').replace(' and ', ' & ')
        lats.append(lat)
        lons.append(lon)
        texts.append(f"{short}<br>{row['Mean']:.2f}")

    fig.add_trace(go.Scattermap(
        lat=lats, lon=lons, mode='markers+text',
        text=texts,
        textfont=dict(size=11, color='black', weight='bold'),
        textposition='middle center',
        marker=dict(size=65, color='rgba(255,255,255,0.75)'),
        hoverinfo='skip', showlegend=False,
    ))
    return fig


# ── Layout ───────────────────────────────────────────────────────────

def modeling_layout():
    choices = get_model_choices()
    return html.Div([
        # Hidden interval to trigger refreshes when tab is selected
        dcc.Interval(id='mdl-refresh-interval', interval=5_000,
                     n_intervals=0, max_intervals=1),

        # DIC comparison (all models)
        html.H2('DIC Comparison (all models)',
                 style={'margin': '0 0 12px 0', 'fontSize': '20px'}),
        html.Div([
            html.H3('Deviance Information Criterion (DIC)',
                     style={'margin': '0 0 8px 0', 'fontSize': '16px'}),
            dash_table.DataTable(
                id='mdl-dic-table',
                style_table={'overflowX': 'auto'},
                style_cell=TABLE_STYLE_CELL,
                style_header=TABLE_STYLE_HEADER,
                style_data_conditional=[{
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#fafafa',
                }],
            ),
        ], style=CARD),

        # Header + model selector
        html.Div([
            html.H2('Model Dashboard',
                     style={'margin': '0', 'fontSize': '20px'}),
            html.Div([
                html.Label('Model:', style={'marginRight': '8px',
                                            'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='mdl-model-select',
                    options=[{'label': m, 'value': m} for m in choices],
                    value=choices[0] if choices else None,
                    clearable=False, style={'width': '160px'},
                ),
            ], style={'display': 'flex', 'alignItems': 'center'}),
        ], style={'display': 'flex', 'justifyContent': 'space-between',
                  'alignItems': 'center', 'marginBottom': '20px'}),

        # Map
        html.Div([
            html.H3('Alpha (Baseline) by Region',
                     style={'margin': '0 0 8px 0', 'fontSize': '16px'}),
            dcc.Graph(id='mdl-map', style={'height': '55vh'}),
        ], style=CARD),

        # Parameter table
        html.Div([
            html.Div([
                html.Label('Parameter:',
                           style={'marginRight': '8px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='mdl-param-select', clearable=False,
                             style={'width': '200px'}),
            ], style={'display': 'flex', 'alignItems': 'center',
                       'marginBottom': '12px'}),
            html.H3(id='mdl-param-table-title',
                     style={'margin': '0 0 8px 0', 'fontSize': '16px'}),
            dash_table.DataTable(
                id='mdl-param-table',
                style_table={'overflowX': 'auto'},
                style_cell=TABLE_STYLE_CELL,
                style_header=TABLE_STYLE_HEADER,
                style_data_conditional=[{
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#fafafa',
                }],
            ),
        ], style=CARD),

        # Sig tests
        html.Div([
            html.Div([
                html.Label('Sig test:',
                           style={'marginRight': '8px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='mdl-sig-select', clearable=False,
                             style={'width': '280px'}),
            ], style={'display': 'flex', 'alignItems': 'center',
                       'marginBottom': '12px'}),
            html.H3(id='mdl-sig-table-title',
                     style={'margin': '0 0 8px 0', 'fontSize': '16px'}),
            dash_table.DataTable(
                id='mdl-sig-table',
                style_table={'overflowX': 'auto'},
                style_cell=TABLE_STYLE_CELL,
                style_header=TABLE_STYLE_HEADER,
                style_data_conditional=[
                    {'if': {'row_index': 'odd'},
                     'backgroundColor': '#fafafa'},
                    {'if': {'filter_query': '{Sig} = "Yes"'},
                     'backgroundColor': '#d4edda'},
                    {'if': {'filter_query': '{Sig} = "No"'},
                     'backgroundColor': '#f8d7da'},
                ],
            ),
        ], style=CARD),

        # Residual plot
        html.Div([
            html.H3('Residuals Over Time',
                     style={'margin': '0 0 8px 0', 'fontSize': '16px'}),
            dcc.Graph(id='mdl-resid-plot', style={'height': '45vh'}),
        ], style=CARD),

        # Gelman-Rubin table
        html.Div([
            html.H3('Gelman-Rubin (R-hat)',
                     style={'margin': '0 0 8px 0', 'fontSize': '16px'}),
            html.Div(id='mdl-gelman-status',
                     style={'marginBottom': '8px'}),
            dash_table.DataTable(
                id='mdl-gelman-table',
                style_table={'overflowX': 'auto'},
                style_cell=TABLE_STYLE_CELL,
                style_header=TABLE_STYLE_HEADER,
                style_data_conditional=[
                    {'if': {'row_index': 'odd'},
                     'backgroundColor': '#fafafa'},
                ],
            ),
        ], style=CARD),
    ])


# ── Callbacks ────────────────────────────────────────────────────────

def register_modeling_callbacks(app):

    @app.callback(
        Output('mdl-dic-table', 'columns'),
        Output('mdl-dic-table', 'data'),
        Output('mdl-model-select', 'options'),
        Input('mdl-refresh-interval', 'n_intervals'),
    )
    def refresh_models(_n):
        dic_df = get_dic_df()
        cols = [{'name': c, 'id': c} for c in dic_df.columns] if not dic_df.empty else []
        data = dic_df.to_dict('records') if not dic_df.empty else []
        choices = get_model_choices()
        opts = [{'label': m, 'value': m} for m in choices]
        return cols, data, opts

    @app.callback(
        Output('mdl-param-select', 'options'),
        Output('mdl-param-select', 'value'),
        Output('mdl-sig-select', 'options'),
        Output('mdl-sig-select', 'value'),
        Input('mdl-model-select', 'value'),
    )
    def update_dropdowns(model_name):
        if not model_name:
            return [], None, [], None

        params = detect_param_csvs(model_name)
        param_opts = [{'label': p, 'value': p} for p in params]
        param_default = 'alpha' if 'alpha' in params else (
            params[0] if params else None)

        overall, pairwise = detect_sig_csvs(model_name)
        sig_opts = []
        for p in overall:
            display = PARAM_DISPLAY.get(p, p)
            sig_opts.append({'label': f'Overall: {display}',
                             'value': f'sig_overall_{p}'})
        for p in pairwise:
            display = PARAM_DISPLAY.get(p, p)
            sig_opts.append({'label': f'Pairwise: {display}',
                             'value': f'sig_pairwise_{p}'})
        sig_default = sig_opts[0]['value'] if sig_opts else None

        return param_opts, param_default, sig_opts, sig_default

    @app.callback(
        Output('mdl-map', 'figure'),
        Output('mdl-resid-plot', 'figure'),
        Output('mdl-param-table-title', 'children'),
        Output('mdl-param-table', 'columns'),
        Output('mdl-param-table', 'data'),
        Output('mdl-sig-table-title', 'children'),
        Output('mdl-sig-table', 'columns'),
        Output('mdl-sig-table', 'data'),
        Output('mdl-gelman-status', 'children'),
        Output('mdl-gelman-table', 'columns'),
        Output('mdl-gelman-table', 'data'),
        Input('mdl-model-select', 'value'),
        Input('mdl-param-select', 'value'),
        Input('mdl-sig-select', 'value'),
    )
    def update_dashboard(model_name, param_name, sig_name):
        empty_fig = go.Figure()
        empty = (empty_fig, empty_fig, '', [], [], '', [], [], '', [], [])

        if not model_name:
            return empty

        # Map (always alpha)
        alpha_df = pd.read_csv(model_path(model_name, 'alpha.csv'))
        fig_map = make_map(alpha_df)

        # Residual plot
        resid_p = model_path(model_name, 'residuals.csv')
        if os.path.isfile(resid_p):
            resid_df = pd.read_csv(resid_p)
            fig_resid = px.line(
                resid_df, x='time', y='residual', color='Region',
                labels={'time': 'Week', 'residual': 'Residual'},
            )
            fig_resid.add_hline(y=0, line_dash='dash', line_color='grey',
                                opacity=0.5)
            fig_resid.update_layout(
                font_family=FONT,
                margin={'t': 10, 'b': 40},
                legend=dict(orientation='h', yanchor='bottom',
                            y=1.02, xanchor='left', x=0),
            )
        else:
            fig_resid = go.Figure()
            fig_resid.add_annotation(text='No residuals.csv',
                                     xref='paper', yref='paper',
                                     x=0.5, y=0.5, showarrow=False)

        # Param table
        if param_name:
            param_df = pd.read_csv(model_path(model_name, f'{param_name}.csv'))
            param_cols = [{'name': c, 'id': c} for c in param_df.columns]
            param_data = param_df.round(4).to_dict('records')
            param_title = f'Parameter: {param_name}'
        else:
            param_cols, param_data, param_title = [], [], ''

        # Sig table
        if sig_name:
            sig_df = pd.read_csv(model_path(model_name, f'{sig_name}.csv'))
            sig_cols = [{'name': c, 'id': c} for c in sig_df.columns]
            sig_data = sig_df.round(4).to_dict('records')
            kind = 'Overall' if 'overall' in sig_name else 'Pairwise'
            param = sig_name.split('_', 2)[-1]
            display = PARAM_DISPLAY.get(param, param)
            sig_title = f'{kind} Significance: {display} (Bonferroni)'
        else:
            sig_cols, sig_data, sig_title = [], [], ''

        # Gelman table
        gelman_p = model_path(model_name, 'gelman.csv')
        if os.path.isfile(gelman_p):
            gelman_df = pd.read_csv(gelman_p)
            gelman_df = gelman_df[['parameter', 'Point est.', 'Upper C.I.']]
            gelman_df = gelman_df.round(5)
            gelman_cols = [{'name': c, 'id': c} for c in gelman_df.columns]
            gelman_data = gelman_df.to_dict('records')
            max_rhat = gelman_df['Point est.'].max()
            color = '#27ae60' if max_rhat < 1.01 else '#e74c3c'
            gelman_status = html.Span(
                f"Max R-hat: {max_rhat:.5f} — "
                + ('All chains converged' if max_rhat < 1.01
                   else 'Possible convergence issues'),
                style={'fontWeight': 'bold', 'color': color,
                       'fontSize': '14px'})
        else:
            gelman_cols, gelman_data = [], []
            gelman_status = html.Span('No gelman.csv',
                                      style={'color': '#95a5a6'})

        return (fig_map, fig_resid,
                param_title, param_cols, param_data,
                sig_title, sig_cols, sig_data,
                gelman_status, gelman_cols, gelman_data)
