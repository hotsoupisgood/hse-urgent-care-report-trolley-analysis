#!/usr/bin/env python3
"""
An Unofficial Urgent and Emergency Care Report (Daily).
Multi-page Dash app: choropleth map + hospital table, time series trends, about page.
URL params sync state for bookmarking/sharing.
"""

import datetime
import json
import os
from pathlib import Path
import re
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import ALL, Dash, Input, Output, State, dash_table, dcc, html

from config import (HOSPITAL_COORDS, REGION_BEDS, REGION_BUDGET_BILLIONS,
                    REGION_BUDGET_PER_CAPITA)
from queries import (get_connection, load_day_by_region, load_day_by_hospital,
                     load_available_dates, load_weekly_national,
                     load_weekly_by_region, load_daily_national,
                     load_daily_by_region)

# -- Config ---------------------------------------------------------------

GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "hse_regions.geojson")
KEY_EVENTS_PATH = os.path.join(os.path.dirname(__file__), "key_events.xlsx")
FONT = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
PAGE_WIDTH = "98vw"

# -- Key events -----------------------------------------------------------

_EVENT_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]


_RECURRING_RE = re.compile(r'(?i)^xxxx-(\d{2})-(\d{2})$')


def _parse_event_date(val):
    """Return a datetime, a raw 'xxxx-MM-DD' string, or None."""
    if val is None:
        return None
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val
    s = str(val).strip()
    if _RECURRING_RE.match(s):
        return s  # recurring annual pattern
    try:
        return pd.to_datetime(s).to_pydatetime()
    except Exception:
        return None


def _date_label(ev):
    """Human-readable date label for the Key Events card."""
    ds, de = ev["date_start"], ev["date_end"]
    if ds is None:
        return "No specific dates"
    if isinstance(ds, str):  # recurring xxxx-MM-DD
        months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
        sm, sd = int(ds[5:7]), int(ds[8:10])
        label = f"{months[sm-1]} {sd:02d}"
        if de and isinstance(de, str):
            em, ed = int(de[5:7]), int(de[8:10])
            label += f" – {months[em-1]} {ed:02d}"
        return label + " (annual)"
    start = ds.strftime('%d %b %Y')
    return f"{start} – {de.strftime('%d %b %Y')}" if de else start


def _expand_date_ranges(ev, data_min, data_max):
    """Return list of (x0, x1) date pairs, expanding xxxx patterns across all years."""
    ds, de = ev["date_start"], ev["date_end"]
    if ds is None:
        return []
    if not isinstance(ds, str):
        x0 = ds.date() if hasattr(ds, 'date') else ds
        x1 = (de.date() if hasattr(de, 'date') else de) if de else x0
        return [(x0, x1)]
    # Recurring annual pattern
    m = _RECURRING_RE.match(ds)
    if not m:
        return []
    sm, sd = int(m.group(1)), int(m.group(2))
    em, ed = (int(de[5:7]), int(de[8:10])) if de and isinstance(de, str) else (sm, sd)
    cross_year = em < sm  # e.g. Dec→Jan
    dmin = data_min.date() if hasattr(data_min, 'date') else data_min
    dmax = data_max.date() if hasattr(data_max, 'date') else data_max
    ranges = []
    for year in range(dmin.year - 1, dmax.year + 2):
        try:
            x0 = datetime.date(year, sm, sd)
            x1 = datetime.date(year + 1 if cross_year else year, em, ed)
            if x1 >= dmin and x0 <= dmax:
                ranges.append((x0, x1))
        except ValueError:
            pass
    return ranges


def _load_key_events():
    try:
        df = pd.read_excel(KEY_EVENTS_PATH)
        events = []
        for _, row in df.iterrows():
            bib_raw = str(row.get("Bib") or "")
            url_match = re.search(r'https?://\S+', bib_raw)
            url = url_match.group(0).rstrip('.,)') if url_match else None
            bib_text = bib_raw[:bib_raw.find(url)].strip().rstrip('.') if url and url in bib_raw else bib_raw
            events.append({
                "name": str(row["Name"]),
                "description": str(row["Description"]),
                "region": str(row.get("Regions") or "All").strip(),
                "date_start": _parse_event_date(row.get("Date start")),
                "date_end": _parse_event_date(row.get("Date end")),
                "bib": bib_text,
                "url": url,
            })
        return events
    except Exception:
        return []


_key_events = _load_key_events()

NAME_MAP = {
    "HSE Dublin and Midlands":   "HSE Dublin and Midlands HR",
    "HSE Dublin and North East": "HSE Dublin and North East HR",
    "HSE Dublin and South East": "HSE Dublin and South East HR",
    "HSE Mid West":              "HSE Midwest HR",
    "HSE South West":            "HSE South West HR",
    "HSE West and North West":   "HSE West and North West HR",
}

LABEL_POS = {
    "HSE Dublin and Midlands":   (53.35, -7.5),
    "HSE Dublin and North East": (53.7,  -6.6),
    "HSE Dublin and South East": (52.5,  -6.8),
    "HSE Mid West":              (52.7,  -8.9),
    "HSE South West":            (51.9,  -9.2),
    "HSE West and North West":   (53.8,  -9.0),
}

with open(GEOJSON_PATH) as f:
    _geojson = json.load(f)

CARD = {
    "backgroundColor": "white",
    "borderRadius": "0.125rem",
    "padding": "1rem",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
    "marginBottom": "0.125rem",
}

APP_TITLE = "Emergency Department Dashboard - Unofficial"

# Metric options for the dropdown
METRIC_OPTIONS = [
    {"label": "On Trolleys", "value": "trolleys"},
    {"label": "Waiting >24hrs", "value": "waiting_24"},
    {"label": "Delayed Transfers of Care", "value": "dtoc"},
]

# Mapping from metric dropdown value to DB/display config
METRIC_CONFIG = {
    "trolleys": {
        "region_col": "total_trolleys",
        "per10k_col": "trolleys_per_10k",
        "hosp_col": "total_trolleys",
        "label": "On Trolleys",
        "title": "Patients on Trolleys",
    },
    "waiting_24": {
        "region_col": "total_waiting_gt_24hrs",
        "per10k_col": None,
        "hosp_col": "total_waiting_gt_24hrs",
        "label": "Waiting >24hrs",
        "title": "Patients Waiting >24 Hours",
    },
    "dtoc": {
        "region_col": "delayed_transfers_of_care",
        "per10k_col": None,
        "hosp_col": "delayed_transfers_of_care",
        "label": "Delayed Transfers",
        "title": "Delayed Transfers of Care",
    },
}

# -- Trends config --------------------------------------------------------

TRENDS_METRICS = [
    ("ed_trolleys",                 "ED Trolleys",        "#e74c3c"),
    ("ward_trolleys",               "Ward Trolleys",      "#3498db"),
    ("total_trolleys",              "Total Trolleys",     "#2c3e50"),
    ("surge_capacity_in_use",       "Surge Capacity",     "#e67e22"),
    ("delayed_transfers_of_care",   "Delayed Transfers",  "#9b59b6"),
    ("total_waiting_gt_24hrs",      "Waiting >24hrs",     "#1abc9c"),
    ("age_75plus_waiting_gt_24hrs", "Age 75+ >24hrs",     "#f39c12"),
]

CARD_COMPACT = {
    "backgroundColor": "white",
    "borderRadius": "0.125rem",
    "padding": "0.25rem",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
}

TOGGLE_BORDER = {
    "border": "1px solid #ccc",
    "borderRadius": "0.375rem",
    "padding": "0.25rem 0.625rem",
}

REGION_COLORS = {
    "HSE Dublin and Midlands":   "#e74c3c",
    "HSE Dublin and North East": "#3498db",
    "HSE Dublin and South East": "#2ecc71",
    "HSE Mid West":              "#f39c12",
    "HSE South West":            "#9b59b6",
    "HSE West and North West":   "#1abc9c",
}


MODIFIER_DIVISORS = {
    "per_bed":           REGION_BEDS,
    "per_budget":        REGION_BUDGET_BILLIONS,
    "per_budget_capita": REGION_BUDGET_PER_CAPITA,
}

MODIFIER_LABELS = {
    "count":             "",
    "per10k":            " per 10k Pop.",
    "per_bed":           " per Inpatient Bed",
    "per_budget":        " per €B Budget",
    "per_budget_capita": " per Budget/Capita",
}


def _with_alpha(hex_color, alpha):
    """Convert #rrggbb to rgba(r,g,b,a)."""
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


# -- App ------------------------------------------------------------------

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = APP_TITLE
app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>body{margin:0;padding:0;}</style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>'''

# -- Page layouts ---------------------------------------------------------

def _date_options():
    """Build dropdown options from available dates in DB."""
    conn = get_connection()
    dates = load_available_dates(conn)
    conn.close()
    return [
        {"label": d.strftime("%d %b %Y"), "value": d.strftime("%Y-%m-%d")}
        for d in dates
    ]


def map_page(date=None, metric="trolleys", level="region", per10k="count"):
    date_opts = _date_options()
    default_date = date or (date_opts[0]["value"] if date_opts else None)

    return html.Div(style={"maxWidth": PAGE_WIDTH, "margin": "0 auto"}, children=[
        # -- Choropleth map card --
        html.Div(style=CARD, children=[
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "0.5rem"}, children=[
                html.H3(id="map-title",
                         style={"margin": "0", "fontSize": "1rem"}),
                html.Div(style={"display": "flex", "gap": "0.75rem",
                                "alignItems": "center"}, children=[
                    dcc.Dropdown(
                        id="date-dropdown",
                        options=date_opts,
                        value=default_date,
                        clearable=False,
                        style={"width": "9.375rem", "fontSize": "0.8125rem"},
                    ),
                    dcc.Dropdown(
                        id="metric-dropdown",
                        options=METRIC_OPTIONS,
                        value=metric,
                        clearable=False,
                        style={"width": "13.75rem", "fontSize": "0.8125rem"},
                    ),
                    html.Div(style=TOGGLE_BORDER, children=[
                        dcc.RadioItems(
                            id="level-toggle",
                            options=[
                                {"label": "Region", "value": "region"},
                                {"label": "Hospital", "value": "hospital"},
                            ],
                            value=level,
                            inline=True,
                            labelStyle={"marginRight": "0.75rem"},
                            style={"fontSize": "0.8125rem"},
                        ),
                    ]),
                    html.Div(id="per10k-toggle-wrapper",
                             style=TOGGLE_BORDER, children=[
                        dcc.RadioItems(
                            id="metric-toggle",
                            options=[
                                {"label": "Count",              "value": "count"},
                                {"label": "Per 10k Pop.",       "value": "per10k"},
                                {"label": "Per Inpatient Bed",  "value": "per_bed"},
                                {"label": "Per €B Budget",      "value": "per_budget"},
                                {"label": "Per Budget/Capita",  "value": "per_budget_capita"},
                            ],
                            value=per10k,
                            inline=True,
                            labelStyle={"marginRight": "0.75rem"},
                            style={"fontSize": "0.8125rem"},
                        ),
                    ]),
                ]),
            ]),
            html.Div(id="map-subtitle",
                     style={"fontSize": "0.8125rem", "color": "#666",
                            "marginBottom": "0.5rem"}),
            dcc.Loading(type="circle", color="#555", children=[
                dcc.Graph(id="choropleth-map", style={"height": "55vh"}),
            ]),
        ]),

        # -- Hospital table card --
        html.Div(style=CARD, children=[
            html.H3(id="table-title",
                     style={"margin": "0 0 0.75rem 0", "fontSize": "1rem"}),
            dash_table.DataTable(
                id="hospital-table",
                sort_action="native",
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#f8f9fa",
                    "fontWeight": "bold",
                    "fontSize": "0.8125rem",
                    "borderBottom": "2px solid #dee2e6",
                },
                style_cell={
                    "fontSize": "0.8125rem",
                    "padding": "0.5rem 0.75rem",
                    "textAlign": "left",
                    "fontFamily": FONT,
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"},
                     "backgroundColor": "#f8f9fa"},
                ],
            ),
        ]),
    ])


def about_page():
    link = {"color": "#0066cc"}
    p_style = {"marginBottom": "0.75rem", "lineHeight": "1.6"}

    return html.Div(style={"maxWidth": PAGE_WIDTH, "margin": "0 auto"}, children=[
        html.Div(style=CARD, children=[
            html.H2("About", style={"fontSize": "1.125rem", "marginBottom": "1rem"}),
            html.P(
                "This dashboard tracks daily on-trolley counts across Ireland\u2019s "
                "public hospitals. It is an unofficial project built as part of a "
                "master\u2019s degree and is not affiliated with the HSE.",
                style=p_style,
            ),

            html.H3("Data source",
                     style={"fontSize": "0.9375rem", "marginBottom": "0.5rem"}),
            html.P([
                "Data is scraped from the HSE\u2019s ",
                html.A("Urgent and Emergency Care Report",
                       href="https://www.hse.ie/services/urgent-emergency-care-report/",
                       target="_blank", style=link),
                ", which publishes on-trolley figures at 8am each morning for all "
                "public acute hospitals across Ireland\u2019s six HSE Health Regions.",
            ], style=p_style),
        ]),
    ])


def _event_row(i, ev):
    color = _EVENT_COLORS[i % len(_EVENT_COLORS)]
    has_dates = ev["date_start"] is not None
    date_label = _date_label(ev)

    return html.Div(
        style={"display": "flex", "alignItems": "flex-start", "gap": "0.5rem",
               "padding": "0.5rem 0", "borderBottom": "1px solid #f0f0f0"},
        children=[
            dcc.Checklist(
                id={"type": "event-check", "index": i},
                options=[{"label": "", "value": ev["name"]}],
                value=[ev["name"]],
                style={"marginTop": "0.1rem", "flexShrink": "0"},
            ) if has_dates else html.Div(
                style={"width": "1.25rem", "flexShrink": "0"},
                title="No date range — not plotted on graph",
            ),
            html.Div(style={
                "width": "0.625rem", "height": "0.625rem", "borderRadius": "50%",
                "backgroundColor": color if has_dates else "#ccc",
                "marginTop": "0.3rem", "flexShrink": "0",
            }),
            html.Div(style={"flex": "1", "minWidth": "0"}, children=[
                html.Div(
                    style={"display": "flex", "gap": "0.5rem",
                           "alignItems": "baseline", "flexWrap": "wrap"},
                    children=[
                        html.Span(ev["name"],
                                  style={"fontWeight": "600", "fontSize": "0.8125rem"}),
                        html.Span(date_label,
                                  style={"fontSize": "0.75rem", "color": "#999"}),
                    ],
                ),
                html.Div(ev["description"],
                         style={"fontSize": "0.75rem", "color": "#555",
                                "marginTop": "0.125rem", "lineHeight": "1.4"}),
                html.Div(
                    style={"marginTop": "0.2rem"},
                    children=[
                        html.Span("Source: ",
                                  style={"fontSize": "0.6875rem", "color": "#aaa"}),
                        html.A(
                            ev["bib"] or ev["url"],
                            href=ev["url"],
                            target="_blank",
                            style={"fontSize": "0.6875rem", "color": "#0066cc",
                                   "textDecoration": "none", "fontStyle": "italic",
                                   "wordBreak": "break-all"},
                        ) if ev["url"] else html.Span(
                            ev["bib"] or "–",
                            style={"fontSize": "0.6875rem", "color": "#888",
                                   "fontStyle": "italic"},
                        ),
                    ],
                ) if (ev["bib"] or ev["url"]) else None,
            ]),
        ],
    )


def trends_page(scope="region", freq="weekly", rate="count"):
    return html.Div(style={"maxWidth": PAGE_WIDTH, "margin": "0 auto"}, children=[
        html.Div(style=CARD, children=[
            # Controls bar
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "0.5rem"}, children=[
                html.H3("Trends", style={"margin": "0", "fontSize": "1rem"}),
                html.Div(style={"display": "flex", "gap": "0.75rem"}, children=[
                    html.Div(style=TOGGLE_BORDER, children=[
                        dcc.RadioItems(
                            id="trends-scope-toggle",
                            options=[
                                {"label": "National", "value": "national"},
                                {"label": "By Region", "value": "region"},
                            ],
                            value=scope,
                            inline=True,
                            labelStyle={"marginRight": "0.75rem"},
                            style={"fontSize": "0.8125rem"},
                        ),
                    ]),
                    html.Div(style=TOGGLE_BORDER, children=[
                        dcc.RadioItems(
                            id="trends-freq-toggle",
                            options=[
                                {"label": "Weekly", "value": "weekly"},
                                {"label": "Daily", "value": "daily"},
                            ],
                            value=freq,
                            inline=True,
                            labelStyle={"marginRight": "0.75rem"},
                            style={"fontSize": "0.8125rem"},
                        ),
                    ]),
                    html.Div(style=TOGGLE_BORDER, children=[
                        dcc.RadioItems(
                            id="trends-rate-toggle",
                            options=[
                                {"label": "Count",              "value": "count"},
                                {"label": "Per 10k Pop.",       "value": "per10k"},
                                {"label": "Per Inpatient Bed",  "value": "per_bed"},
                                {"label": "Per €B Budget",      "value": "per_budget"},
                                {"label": "Per Budget/Capita",  "value": "per_budget_capita"},
                            ],
                            value=rate,
                            inline=True,
                            labelStyle={"marginRight": "0.75rem"},
                            style={"fontSize": "0.8125rem"},
                        ),
                    ]),
                ]),
            ]),

            # All metrics in a single subplot figure
            dcc.Loading(type="circle", color="#555", children=[
                dcc.Graph(id="trends-subplot",
                          style={"height": "clamp(700px, 80vh, 99vw)"},
                          config={"displayModeBar": False}),
            ]),

            # Key events section
            html.Div(
                style={"borderTop": "1px solid #e9ecef",
                       "paddingTop": "0.625rem", "marginTop": "0.25rem"},
                children=[
                    html.Div("Key Events", style={
                        "fontSize": "0.6875rem", "fontWeight": "600", "color": "#888",
                        "textTransform": "uppercase", "letterSpacing": "0.05em",
                        "marginBottom": "0.25rem",
                    }),
                    html.Div(children=[_event_row(i, ev)
                                       for i, ev in enumerate(_key_events)]),
                ],
            ) if _key_events else None,
        ]),
    ])


# -- Model gallery --------------------------------------------------------

_SCALE_DATA_DIRS = {
    "per10k":      "wide_weekly_scaledPer10k",
    "per_bed":     "wide_weekly_scaledPerBed",
    "per_budget":  "wide_weekly_scaledPerBudgetThousands",
}
_MODEL_DATA_BASE = os.path.join(
    os.path.dirname(__file__), "..", "data", "models",
    _SCALE_DATA_DIRS["per10k"],
)

def _load_dic_table():
    """Load DIC CSVs for all fitted versions; auto-discovers from the per10k output dir."""
    rows = []
    for dic_path in sorted(Path(_MODEL_DATA_BASE).glob("*/dic.csv")):
        v = dic_path.parent.name
        df = pd.read_csv(dic_path)
        rows.append({
            "Version":     v,
            "Description": df["description"].iloc[0],
            "Deviance":    round(df["deviance"].iloc[0], 2),
            "Penalty":     round(df["penalty"].iloc[0], 2),
            "DIC":         round(df["DIC"].iloc[0], 2),
        })
    if not rows:
        return None
    out = pd.DataFrame(rows)
    best = out["DIC"].idxmin()
    out["_best"] = out.index == best
    return out


def _load_version_ranks(scale, version):
    """Load ranks.csv for a given scale + version; return DataFrame sorted by rank, or None."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "models",
        _SCALE_DATA_DIRS[scale], version, "ranks.csv",
    )
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, index_col=0).reset_index()
    df.columns = ["Region", "Mean Rank", "SD", "25%", "Median Rank", "75%", "Rank"]
    df["Rank"] = df["Rank"].astype(int)
    df["Median Rank"] = df["Median Rank"].astype(int)
    df["25%"] = df["25%"].astype(int)
    df["75%"] = df["75%"].astype(int)
    for col in ["Mean Rank", "SD"]:
        df[col] = df[col].round(3)
    df = df[["Region", "Rank", "Mean Rank", "Median Rank", "25%", "75%", "SD"]]
    return df.sort_values("Rank").reset_index(drop=True)


def _load_ranks_table():
    """Load ranks.csv for v4.1 across all three scales; return a merged DataFrame."""
    base = os.path.join(os.path.dirname(__file__), "..", "data", "models")
    frames = {}
    for key, folder in _SCALE_DATA_DIRS.items():
        path = os.path.join(base, folder, "v3.1", "ranks.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, index_col=0)
            frames[key] = df

    if not frames:
        return None

    scale_labels = {
        "per10k":     "Per 10k",
        "per_bed":    "Per Bed",
        "per_budget": "Per Budget",
    }
    rows = []
    # Use regions from the first available scale
    regions = list(next(iter(frames.values())).index)
    for region in regions:
        row = {"Region": region}
        for key, df in frames.items():
            if region in df.index:
                mean_rank = df.loc[region, "ranked_mean"]
                sd        = df.loc[region, "std"]
                row[f"Rank ({scale_labels[key]})"] = int(mean_rank)
                row[f"SD ({scale_labels[key]})"]   = round(sd, 3)
        rows.append(row)

    out = pd.DataFrame(rows).sort_values("Rank (Per 10k)")
    return out


def _discover_model_versions():
    """Discover available model versions from the per10k output dir (lexicographic order)."""
    return sorted(p.parent.name for p in Path(_MODEL_DATA_BASE).glob("*/dic.csv"))

MODEL_VERSIONS = _discover_model_versions()

MODEL_SCALE_OPTIONS = [
    {"label": "Per 10k Pop.", "value": "per10k"},
    {"label": "Per Bed",      "value": "per_bed"},
    {"label": "Per Budget",   "value": "per_budget"},
]

def _load_model_titles():
    """Build {version: title} from dic.csv files (per10k as canonical source)."""
    titles = {}
    for v in MODEL_VERSIONS:
        path = os.path.join(_MODEL_DATA_BASE, v, "dic.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            name = df["description"].iloc[0]
            titles[v] = f"{v.upper()} — {name}"
        else:
            titles[v] = v
    return titles


_MODEL_TITLES = _load_model_titles()

_IMG_STYLE = {
    "width": "100%",
    "borderRadius": "4px",
    "display": "block",
}

_PLOT_LABEL_STYLE = {
    "fontSize": "0.75rem",
    "fontWeight": "600",
    "color": "#555",
    "textTransform": "uppercase",
    "letterSpacing": "0.05em",
    "marginBottom": "0.25rem",
}


def _build_model_sections(scale):
    """Render all model version cards for a given scale key (most complex first)."""
    sections = []
    first = True
    for version in reversed(MODEL_VERSIONS):
        title = _MODEL_TITLES.get(version, version)
        mu_src  = f"/assets/models/{scale}/{version}/mu_fit.png"
        res_src = f"/assets/models/{scale}/{version}/residuals_combined.png"

        # -- Rankings drawer --
        ranks_df = _load_version_ranks(scale, version)
        if ranks_df is not None:
            ranks_drawer = html.Details(
                open=first,
                style={"marginTop": "1rem", "borderTop": "1px solid #eee",
                       "paddingTop": "0.75rem"},
                children=[
                    html.Summary(
                        "Posterior Regional Rankings",
                        style={"cursor": "pointer", "fontSize": "0.8125rem",
                               "fontWeight": "600", "color": "#444",
                               "userSelect": "none", "marginBottom": "0.5rem"},
                    ),
                    dash_table.DataTable(
                        columns=[{"name": c, "id": c} for c in ranks_df.columns],
                        data=ranks_df.to_dict("records"),
                        sort_action="native",
                        style_table={"overflowX": "auto", "marginTop": "0.5rem"},
                        style_cell={"textAlign": "left", "padding": "0.4rem 0.75rem",
                                    "fontSize": "0.8125rem", "fontFamily": FONT},
                        style_header={"fontWeight": "600", "backgroundColor": "#f0f0f0",
                                      "borderBottom": "2px solid #dee2e6"},
                        style_data_conditional=[
                            {"if": {"filter_query": "{Rank} = 1"},
                             "backgroundColor": "#fdecea", "fontWeight": "600"},
                            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
                        ],
                    ),
                    html.P("Rank 1 = highest trolley burden. SD of posterior rank samples shown.",
                           style={"fontSize": "0.7rem", "color": "#888",
                                  "marginTop": "0.4rem", "marginBottom": "0"}),
                ],
            )
        else:
            ranks_drawer = None

        sections.append(html.Div(
            style={**CARD, "marginBottom": "1rem"},
            children=[
                # Version header
                html.H3(
                    title,
                    style={"margin": "0 0 0.5rem", "fontSize": "1rem",
                           "borderBottom": "1px solid #eee", "paddingBottom": "0.5rem"},
                ),
                # Two-plot row
                html.Div(
                    style={"display": "flex", "gap": "1.5rem",
                           "alignItems": "flex-start"},
                    children=[
                        html.Div(style={"flex": "1", "minWidth": "0"}, children=[
                            html.P("Posterior Mean Fit (95% CI)", style=_PLOT_LABEL_STYLE),
                            html.Img(src=mu_src, alt=f"{version} mu_fit",
                                     style=_IMG_STYLE),
                        ]),
                        html.Div(style={"flex": "1", "minWidth": "0"}, children=[
                            html.P("Standardised Residuals", style=_PLOT_LABEL_STYLE),
                            html.Img(src=res_src, alt=f"{version} residuals",
                                     style=_IMG_STYLE),
                        ]),
                    ],
                ),
                # Collapsible rankings drawer
                ranks_drawer,
            ],
        ))
        first = False
    return sections


def model_page(scale="per10k"):
    """Model results tab — static plot gallery with scale toggle."""
    children = []

    # -- Version scheme explanation card --
    children.append(html.Div(style=CARD, children=[
        html.H3("Model Versioning", style={"margin": "0 0 0.5rem", "fontSize": "1rem"}),
        dcc.Markdown(
            "Models are numbered by family and iteration. "
            "**V0.x** — AR baseline with no harmonic component. "
            "**V2.x** — Period sweep: V2.1–V2.3 each test a single cycle period "
            "(52-week, 26-week, 8-week); V2.4–V2.5 add a second harmonic to the annual. "
            "**V3.x** — Annual cycle plus a structural event effect: "
            "V3.1 adds a global New Year step, V3.2 makes it region-specific, "
            "V3.3 replaces the New Year term with a Mid West one-time reset. "
            "**V4.x** — Combines the region-specific New Year effect (V3.2) "
            "and the Mid West reset (V3.3) — this is the selected family. "
            "**V5.x** — V4.1 with partial pooling of region-level parameters. "
            "V1.x and V6.x are intentionally absent (deprecated branches). "
            "The selected model is **V4.1**, chosen by lowest DIC.",
            style={"fontSize": "0.8125rem", "lineHeight": "1.7", "margin": "0"},
        ),
    ]))

    # -- DIC comparison table --
    dic_df = _load_dic_table()
    if dic_df is not None:
        children.append(html.Div(style=CARD, children=[
            html.H3("Model Comparison — DIC",
                    style={"margin": "0 0 0.5rem", "fontSize": "1rem"}),
            html.P(
                "Lower DIC indicates better out-of-sample predictive accuracy. "
                "Penalty = effective number of parameters (pD). "
                "✓ marks the selected model.",
                style={"fontSize": "0.8125rem", "color": "#666",
                       "margin": "0 0 0.75rem"},
            ),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in dic_df.columns if c != "_best"],
                data=dic_df.to_dict("records"),
                sort_action="native",
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "0.4rem 0.75rem",
                             "fontSize": "0.8125rem", "fontFamily": FONT},
                style_header={"fontWeight": "600", "backgroundColor": "#f0f0f0",
                              "borderBottom": "2px solid #dee2e6"},
                style_data_conditional=[
                    {"if": {"filter_query": "{_best} = True"},
                     "backgroundColor": "#eaf4ea", "fontWeight": "600"},
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
                ],
            ),
        ]))

    # -- Scale toggle card --
    children.append(html.Div(style=CARD, children=[
        html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "1rem",
                   "marginBottom": "0.4rem"},
            children=[
                html.Span("Response scale:", style={"fontWeight": "600",
                                                    "fontSize": "0.8125rem"}),
                dcc.RadioItems(
                    id="model-scale-toggle",
                    options=MODEL_SCALE_OPTIONS,
                    value=scale,
                    inline=True,
                    labelStyle={"marginRight": "0.75rem"},
                    style={"fontSize": "0.8125rem"},
                ),
            ],
        ),
        html.P(
            "Switching scale re-normalises the trolley count used to fit each model "
            "(e.g. trolleys per 10k population vs. per inpatient bed). "
            "The AR structure, cycle periods, and priors are identical across scales — "
            "only the magnitude and inter-regional comparability of the response changes.",
            style={"fontSize": "0.75rem", "color": "#888", "margin": "0",
                   "lineHeight": "1.5"},
        ),
    ]))

    # -- Model gallery (rebuilt by callback) --
    children.append(html.Div(id="model-content",
                             children=_build_model_sections(scale)))

    return html.Div(style={"maxWidth": PAGE_WIDTH, "margin": "0 auto"},
                    children=children)


# -- Main layout with navigation -----------------------------------------

app.layout = html.Div(
    style={"fontFamily": FONT, "backgroundColor": "#f5f5f5"},
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="url-params", data={}),

        # -- Compact header bar --
        html.Div(
            style={
                "backgroundColor": "#333",
                "color": "white",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "0 1.5rem",
                "height": "2.625rem",
                "boxShadow": "0 1px 3px rgba(0,0,0,0.2)",
            },
            children=[
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "0.75rem"},
                    children=[
                        html.Span(APP_TITLE,
                                  style={"fontSize": "0.875rem", "fontWeight": "600",
                                         "whiteSpace": "nowrap"}),
                        html.A("(HSE Source)",
                               href="https://www.hse.ie/services/urgent-emergency-care-report/",
                               target="_blank",
                               style={"fontSize": "0.6875rem", "color": "#bbb",
                                      "textDecoration": "none"}),
                    ],
                ),
                html.Div(
                    id="header-tabs",
                    style={"display": "flex", "alignItems": "center",
                           "height": "100%"},
                    children=[
                        html.Div(id=f"tab-{val}", children=[
                            html.Span(
                                label,
                                style={
                                    "padding": "0 1rem",
                                    "lineHeight": "2.625rem",
                                    "fontSize": "0.8125rem",
                                    "cursor": "pointer",
                                    "display": "inline-block",
                                    "height": "100%",
                                },
                            ),
                        ])
                        for label, val in [("Trends", "trends"), ("Map", "map"), ("Model", "model"), ("About", "about")]
                    ],
                ),
            ],
        ),

        # Hidden real Tabs component (drives callbacks but is invisible)
        html.Div(style={"display": "none"}, children=[
            dcc.Tabs(id="nav-tabs", value="trends", children=[
                dcc.Tab(label="Trends", value="trends"),
                dcc.Tab(label="Map", value="map"),
                dcc.Tab(label="Model", value="model"),
                dcc.Tab(label="About", value="about"),
            ]),
        ]),

        html.Div(id="page-content", style={"padding": "0.75rem 0.75rem 0.75rem"}),

        # Hidden divs for clientside URL-writing callbacks
        html.Div(id="url-writer-map", style={"display": "none"}),
        html.Div(id="url-writer-trends", style={"display": "none"}),
        html.Div(id="url-writer-tab", style={"display": "none"}),
        html.Div(id="url-writer-model", style={"display": "none"}),
    ],
)


# -- Header tab click + active styling ------------------------------------

# Click on custom header tab → update hidden dcc.Tabs value
for _tab_val in ["trends", "map", "model", "about"]:
    app.clientside_callback(
        f"function(n) {{ return '{_tab_val}'; }}",
        Output("nav-tabs", "value", allow_duplicate=True),
        Input(f"tab-{_tab_val}", "n_clicks"),
        prevent_initial_call=True,
    )

# Highlight active tab (black bg) based on hidden dcc.Tabs value
app.clientside_callback(
    """
    function(activeTab) {
        const tabs = ['trends', 'map', 'model', 'about'];
        const styles = [];
        for (const t of tabs) {
            if (t === activeTab) {
                styles.push({backgroundColor: '#111', height: '100%'});
            } else {
                styles.push({height: '100%'});
            }
        }
        return styles;
    }
    """,
    Output("tab-trends", "style"),
    Output("tab-map", "style"),
    Output("tab-model", "style"),
    Output("tab-about", "style"),
    Input("nav-tabs", "value"),
)


# -- URL param sync -------------------------------------------------------

# On load: read URL params → set active tab + store params
app.clientside_callback(
    """
    function(_) {
        const params = new URLSearchParams(window.location.search);
        const data = {};
        for (const [k, v] of params.entries()) { data[k] = v; }
        return [params.get('tab') || 'trends', data];
    }
    """,
    Output("nav-tabs", "value"),
    Output("url-params", "data"),
    Input("url", "pathname"),
)

# Map controls → URL
app.clientside_callback(
    """
    function(date, metric, level, per10k) {
        const p = new URLSearchParams();
        p.set('tab', 'map');
        if (date) p.set('date', date);
        if (metric) p.set('metric', metric);
        if (level) p.set('level', level);
        if (per10k) p.set('per10k', per10k);
        window.history.replaceState({}, '', '?' + p.toString());
        return '';
    }
    """,
    Output("url-writer-map", "children"),
    Input("date-dropdown", "value"),
    Input("metric-dropdown", "value"),
    Input("level-toggle", "value"),
    Input("metric-toggle", "value"),
    prevent_initial_call=True,
)

# Trends controls → URL
app.clientside_callback(
    """
    function(scope, freq, rate) {
        const p = new URLSearchParams();
        p.set('tab', 'trends');
        if (scope) p.set('scope', scope);
        if (freq) p.set('freq', freq);
        if (rate) p.set('rate', rate);
        window.history.replaceState({}, '', '?' + p.toString());
        return '';
    }
    """,
    Output("url-writer-trends", "children"),
    Input("trends-scope-toggle", "value"),
    Input("trends-freq-toggle", "value"),
    Input("trends-rate-toggle", "value"),
    prevent_initial_call=True,
)

# Model scale toggle → URL
app.clientside_callback(
    """
    function(scale) {
        const p = new URLSearchParams();
        p.set('tab', 'model');
        p.set('scale', scale);
        window.history.replaceState({}, '', '?' + p.toString());
        return '';
    }
    """,
    Output("url-writer-model", "children"),
    Input("model-scale-toggle", "value"),
    prevent_initial_call=True,
)

# Tab switch → URL (handles about tab which has no controls)
app.clientside_callback(
    """
    function(tab) {
        if (tab === 'about') {
            window.history.replaceState({}, '', '?tab=about');
        }
        if (tab === 'model') {
            window.history.replaceState({}, '', '?tab=model');
        }
        return '';
    }
    """,
    Output("url-writer-tab", "children"),
    Input("nav-tabs", "value"),
)


# -- Routing callback -----------------------------------------------------

@app.callback(
    Output("page-content", "children"),
    Input("nav-tabs", "value"),
    State("url-params", "data"),
)
def display_page(tab, params):
    params = params or {}
    if tab == "about":
        return about_page()
    if tab == "model":
        return model_page(scale=params.get("scale", "per10k"))
    if tab == "trends":
        return trends_page(
            scope=params.get("scope", "region"),
            freq=params.get("freq", "weekly"),
            rate=params.get("rate", "count"),
        )
    return map_page(
        date=params.get("date"),
        metric=params.get("metric", "trolleys"),
        level=params.get("level", "region"),
        per10k=params.get("per10k", "count"),
    )


# -- Map callbacks --------------------------------------------------------

# Show/hide the per10k toggle (only for trolleys + region)
@app.callback(
    Output("per10k-toggle-wrapper", "style"),
    Input("metric-dropdown", "value"),
    Input("level-toggle", "value"),
)
def toggle_per10k_visibility(metric, level):
    if metric == "trolleys" and level == "region":
        return TOGGLE_BORDER
    return {**TOGGLE_BORDER, "display": "none"}




@app.callback(
    Output("choropleth-map", "figure"),
    Output("map-subtitle", "children"),
    Output("map-title", "children"),
    Input("date-dropdown", "value"),
    Input("metric-dropdown", "value"),
    Input("metric-toggle", "value"),
    Input("level-toggle", "value"),
)
def update_map(selected_date, metric_key, per10k_toggle, level):
    conn = get_connection()
    df = load_day_by_region(conn, report_date=selected_date)
    hosp_df = load_day_by_hospital(conn, report_date=selected_date)
    conn.close()

    if df.empty:
        return go.Figure(), "No data available", ""

    cfg = METRIC_CONFIG[metric_key]
    is_hospital = level == "hospital"
    modifier = per10k_toggle
    use_per10k = modifier == "per10k" and cfg["per10k_col"] is not None
    use_custom = modifier in MODIFIER_DIVISORS
    report_date = df["report_date"].iloc[0]
    subtitle = f"Data for {report_date.strftime('%d %B %Y')}"

    map_df = df.copy()
    map_df["geojson_name"] = map_df["region"].map(NAME_MAP)

    # Region choropleth colour column
    if use_per10k:
        color_col = cfg["per10k_col"]
    elif use_custom:
        divisor_map = MODIFIER_DIVISORS[modifier]
        map_df["_scaled"] = map_df.apply(
            lambda r: round(r[cfg["region_col"]] / divisor_map.get(r["region"], float("nan")), 4),
            axis=1,
        )
        color_col = "_scaled"
    else:
        color_col = cfg["region_col"]
    color_label = (cfg["label"] + MODIFIER_LABELS.get(modifier, "")).strip()

    title = f"Single Day Map"

    col_max = map_df[color_col].max()
    fig = px.choropleth_map(
        map_df,
        geojson=_geojson,
        locations="geojson_name",
        featureidkey="properties.HR_operational_name",
        color=color_col,
        color_continuous_scale="Reds",
        range_color=[0, col_max],
        map_style="carto-positron",
        center={"lat": 53.5, "lon": -8},
        zoom=5.6,
        hover_name="region",
        hover_data={"geojson_name": False, color_col: True},
        labels={color_col: color_label},
        opacity=0.35 if is_hospital else 0.6,
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title=dict(side="right"), thickness=15),
        font_family=FONT,
    )

    if is_hospital:
        # Hospital pins
        hosp_lookup = {row["hospital"]: row for _, row in hosp_df.iterrows()}

        h_lats, h_lons, h_texts, h_hovers, h_colors = [], [], [], [], []
        hosp_col = cfg["hosp_col"]
        for name, (lat, lon) in HOSPITAL_COORDS.items():
            h_lats.append(lat)
            h_lons.append(lon)
            row = hosp_lookup.get(name)
            if row is not None:
                val = row[hosp_col]
                h_texts.append(str(int(val)) if pd.notna(val) else "\u2013")
                h_hovers.append(f"{name}<br>{cfg['label']}: {val}")
                h_colors.append("darkred")
            else:
                h_texts.append("\u2013")
                h_hovers.append(f"{name}<br>No data today")
                h_colors.append("grey")

        fig.add_trace(go.Scattermap(
            lat=h_lats, lon=h_lons, mode="markers+text",
            text=h_texts,
            hovertext=h_hovers,
            hoverinfo="text",
            textfont=dict(size=9, color="white", weight="bold"),
            textposition="middle center",
            marker=dict(size=16, color=h_colors, opacity=0.85),
            showlegend=False,
            name="Hospitals",
        ))
    else:
        # Region labels overlaid on map
        lats, lons, texts = [], [], []
        for _, row in map_df.iterrows():
            lat, lon = LABEL_POS.get(row["region"], (None, None))
            if lat is None:
                continue
            short = row["region"].replace("HSE ", "").replace(" and ", " & ")
            val = row[color_col]
            fmt = f"{val:.4f}" if use_custom else (f"{val:.2f}" if use_per10k else f"{val:.0f}")
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


@app.callback(
    Output("hospital-table", "data"),
    Output("hospital-table", "columns"),
    Output("table-title", "children"),
    Input("date-dropdown", "value"),
    Input("metric-dropdown", "value"),
    Input("level-toggle", "value"),
)
def update_table(selected_date, metric_key, level):
    conn = get_connection()
    is_region = level == "region"
    cfg = METRIC_CONFIG[metric_key]

    if is_region:
        df = load_day_by_region(conn, report_date=selected_date)
        conn.close()
        if df.empty:
            return [], [], "No data available"
        report_date = df["report_date"].iloc[0]
        title = f"{cfg['title']} by Region \u2014 {report_date.strftime('%d %B %Y')}"
        base_cols = [{"name": "Region", "id": "region"}]
        if metric_key == "trolleys":
            cols = base_cols + [
                {"name": "Total Trolleys", "id": "total_trolleys", "type": "numeric"},
                {"name": "Per 10k", "id": "trolleys_per_10k", "type": "numeric"},
            ]
            table_df = df[["region", "total_trolleys", "trolleys_per_10k"]]
        elif metric_key == "waiting_24":
            cols = base_cols + [
                {"name": "Waiting >24hrs", "id": "total_waiting_gt_24hrs", "type": "numeric"},
            ]
            table_df = df[["region", "total_waiting_gt_24hrs"]]
        else:
            cols = base_cols + [
                {"name": "Delayed Transfers", "id": "delayed_transfers_of_care", "type": "numeric"},
            ]
            table_df = df[["region", "delayed_transfers_of_care"]]
    else:
        df = load_day_by_hospital(conn, report_date=selected_date)
        conn.close()
        if df.empty:
            return [], [], "No data available"
        report_date = df["report_date"].iloc[0]
        title = f"{cfg['title']} by Hospital \u2014 {report_date.strftime('%d %B %Y')}"
        base_cols = [
            {"name": "Hospital", "id": "hospital"},
            {"name": "Region", "id": "region"},
        ]
        if metric_key == "trolleys":
            cols = base_cols + [
                {"name": "ED Trolleys", "id": "ed_trolleys", "type": "numeric"},
                {"name": "Ward Trolleys", "id": "ward_trolleys", "type": "numeric"},
                {"name": "Total Trolleys", "id": "total_trolleys", "type": "numeric"},
            ]
            table_df = df[["hospital", "region", "ed_trolleys", "ward_trolleys", "total_trolleys"]]
        elif metric_key == "waiting_24":
            cols = base_cols + [
                {"name": "Waiting >24hrs", "id": "total_waiting_gt_24hrs", "type": "numeric"},
            ]
            table_df = df[["hospital", "region", "total_waiting_gt_24hrs"]]
        else:
            cols = base_cols + [
                {"name": "Delayed Transfers", "id": "delayed_transfers_of_care", "type": "numeric"},
            ]
            table_df = df[["hospital", "region", "delayed_transfers_of_care"]]

    return table_df.to_dict("records"), cols, title


# -- Trends callback ------------------------------------------------------

@app.callback(
    Output("trends-subplot", "figure"),
    Input("trends-scope-toggle", "value"),
    Input("trends-freq-toggle", "value"),
    Input("trends-rate-toggle", "value"),
    Input({"type": "event-check", "index": ALL}, "value"),
)
def update_trends(scope, freq, rate, event_checks):
    loaders = {
        ("national", "weekly"): (load_weekly_national, "week_start"),
        ("region",   "weekly"): (load_weekly_by_region, "week_start"),
        ("national", "daily"):  (load_daily_national, "report_date"),
        ("region",   "daily"):  (load_daily_by_region, "report_date"),
    }
    loader, date_col = loaders[(scope, freq)]
    conn = get_connection()
    df = loader(conn)
    conn.close()

    if not df.empty:
        if rate == "per10k" and "population" in df.columns:
            for col, _, _ in TRENDS_METRICS:
                df[col] = (df[col].astype(float) / df["population"] * 10000).round(4)
        elif rate in MODIFIER_DIVISORS:
            divisor_map = MODIFIER_DIVISORS[rate]
            if scope == "national":
                nat_divisor = sum(divisor_map.values())
                for col, _, _ in TRENDS_METRICS:
                    df[col] = (df[col].astype(float) / nat_divisor).round(6)
            else:
                for col, _, _ in TRENDS_METRICS:
                    df[col] = df.apply(
                        lambda r, c=col: round(
                            float(r[c]) / divisor_map.get(r["region"], float("nan")), 6
                        ),
                        axis=1,
                    )

    rows, cols = 4, 2
    suffix = MODIFIER_LABELS.get(rate, "")
    subplot_titles = [f"{label}{suffix}" for _, label, _ in TRENDS_METRICS]

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=subplot_titles,
        vertical_spacing=0.07,
        horizontal_spacing=0.08,
    )

    if not df.empty:
        regions_seen = set()
        for i, (col, label, color) in enumerate(TRENDS_METRICS):
            r = i // cols + 1
            c = i % cols + 1

            if scope == "national":
                fig.add_trace(go.Scatter(
                    x=df[date_col], y=df[col],
                    fill="tozeroy",
                    line=dict(color=color, width=1.5),
                    fillcolor=_with_alpha(color, 0.2),
                    name=label,
                    showlegend=False,
                ), row=r, col=c)
            else:
                for region in sorted(df["region"].unique()):
                    rdf = df[df["region"] == region]
                    rcolor = REGION_COLORS.get(region, "#999")
                    short = region.replace("HSE ", "")
                    fig.add_trace(go.Scatter(
                        x=rdf[date_col], y=rdf[col],
                        line=dict(color=rcolor, width=1.5),
                        name=short,
                        legendgroup=region,
                        showlegend=(region not in regions_seen),
                    ), row=r, col=c)
                    regions_seen.add(region)

    fig.update_layout(
        margin=dict(l=30, r=10, t=50, b=30),
        hovermode="x unified",
        showlegend=(scope == "region"),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.05,
            xanchor="center", x=0.5,
            font=dict(size=10),
        ),
        plot_bgcolor="white",
        font=dict(family=FONT, size=11),
    )

    for i, (col, label, _) in enumerate(TRENDS_METRICS):
        axis_num = "" if i == 0 else str(i + 1)
        fig.update_layout(**{
            f"xaxis{axis_num}": dict(showgrid=False),
            f"yaxis{axis_num}": dict(gridcolor="#eee"),
        })

    for ann in fig.layout.annotations:
        ann.font.size = 13

    # Overlay key event bands
    active_events = {v for check in event_checks for v in (check or [])}
    if not df.empty:
        dates = pd.to_datetime(df[date_col])
        data_min = dates.min().to_pydatetime()
        data_max = dates.max().to_pydatetime()
        for i, ev in enumerate(_key_events):
            if ev["name"] not in active_events:
                continue
            # Region-specific events only shown in "By Region" scope
            if ev.get("region", "All") != "All" and scope != "region":
                continue
            color = _EVENT_COLORS[i % len(_EVENT_COLORS)]
            for x0, x1 in _expand_date_ranges(ev, data_min, data_max):
                fig.add_vrect(
                    x0=x0, x1=x1,
                    fillcolor=color, opacity=0.12,
                    layer="below", line_width=1, line_color=color, line_dash="dot",
                    row="all", col="all",
                )
                fig.add_vrect(
                    x0=x0, x1=x1,
                    fillcolor=color, opacity=0,
                    layer="above", line_width=0,
                    annotation_text=f" {ev['name']}",
                    annotation_position="top left",
                    annotation=dict(font=dict(size=9, color=color), showarrow=False),
                    row=1, col=1,
                )

    return fig


# -- Model tab callback ---------------------------------------------------

@app.callback(
    Output("model-content", "children"),
    Input("model-scale-toggle", "value"),
)
def update_model_scale(scale):
    return _build_model_sections(scale)


# -- Run ------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.environ.get("DASH_DEBUG", "true").lower() != "false"
    host = "0.0.0.0" if debug else "127.0.0.1"
    app.run(debug=debug, host=host, port=8050)
