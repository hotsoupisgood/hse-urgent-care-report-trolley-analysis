"""Model tab — a plain-language digest of the thesis.

Order is finding-first:
  1. What we found        (lead)
  2. Regional level & ranking  (interactive map, Ranking / Baseline-rate toggle)
  3. Phases               (annual-cycle peak timing)
  4. Events               (the modelled disruptions)
  5. How the model works  (method, equations behind a toggle)

Self-contained: reads bundled findings from `findings/` and serves images from
`assets/`. Files are shipped by export_dashboard_snapshot.sh.
"""

import os

import pandas as pd
from dash import dcc, html

FONT = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
PAGE_WIDTH = "98vw"          # match the other tabs
READ_WIDTH = "820px"         # readable column for prose
MUTED = "#555"               # darkest gray that passes WCAG AA on white (~7:1)

CARD = {
    "backgroundColor": "white",
    "borderRadius": "0.125rem",
    "padding": "1rem 1.25rem",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
    "marginBottom": "0.5rem",
}
TOGGLE_BORDER = {
    "border": "1px solid #ccc", "borderRadius": "0.375rem",
    "padding": "0.25rem 0.625rem", "display": "inline-block",
}

HERE = os.path.dirname(__file__)
FINDINGS = os.path.join(HERE, "findings")
V46 = os.path.join(FINDINGS, "v4.6")
PHASE_CSV = os.path.join(FINDINGS, "phase_table.csv")
EVENTS_XLSX = os.path.join(HERE, "..", "key_events.xlsx")

MU_FIT_IMG = "/assets/models/v4.6/mu_fit.png"
PHASE_IMG = "/assets/phase_forest.png"
MAP_IMG = "/assets/model_map_alpha.png"

EVENT_DISPLAY = {"Full Reset": "Mid West reset"}  # rename the raw event name
EVENT_IMG = {  # EDA: raw weekly series with the event shaded
    "New Year": "/assets/event_newyear.png",
    "Full Reset": "/assets/event_midwest_reset.png",
}
EVENT_FIT_IMG = {  # modelling result: model fit vs observed, zoomed to the event
    "New Year": "/assets/event_newyear_fit.png",
    "Full Reset": "/assets/event_midwest_reset_fit.png",
}
EVENT_DIP = {  # average size of the dip, from the observed data
    "New Year": "On average the rate roughly halves over the New Year, from about 4.6 "
                "to 2.3 per 10,000 (a 50% drop).",
    "Full Reset": "During the reset the Mid West rate fell from about 8.5 to near zero "
                  "per 10,000 for that week.",
}


def _short(region):
    return region.replace("HSE ", "")


def _section_title(text):
    return html.H2(text, style={
        "fontSize": "1.2rem", "fontWeight": "600", "margin": "0 0 0.5rem",
        "borderBottom": "2px solid #eee", "paddingBottom": "0.3rem",
    })


def _md(text):
    """Markdown block with MathJax enabled; scrolls rather than clips on mobile."""
    return dcc.Markdown(text, mathjax=True,
                        style={"fontSize": "0.95rem", "maxWidth": READ_WIDTH,
                               "overflowX": "auto"})


def _card(children):
    return html.Div(children, style=CARD)


# -- Lead --------------------------------------------------------------------

def _lead():
    return _card([
        html.H1("The Model", style={"fontSize": "1.5rem", "margin": "0 0 0.25rem"}),
        html.P("A plain-language summary of what the model finds. The full method "
               "is at the bottom.", style={"color": MUTED, "marginTop": "0"}),
        _md(
            "**What we found.** The HSE Mid West has the highest trolley rate in the "
            "country. It is more than three times the lowest region. The three western "
            "regions all sit above the three eastern (Dublin) regions. This is an "
            "East-West divide. Waits peak in winter in five of the six regions. Two "
            "real-world events also mark the data. These are the turn of the year and "
            "the August 2024 reset at University Hospital Limerick. These are past "
            "patterns. They are not a forecast or a hospital league table."
        ),
    ])


# -- Section: regional level & ranking (static green maps) -------------------

def _regional_levels():
    return _card([
        _section_title("Regional trolley rate"),
        html.P("A modelled long-run rate for each region, not today's counts. See the "
               "Map tab for daily figures.",
               style={"color": MUTED, "fontSize": "0.85rem", "marginTop": "0"}),
        _md(
            "How high is each region's trolley rate? Rates are per 10,000 residents "
            "(a rate of 8 means about eight patients on trolleys per 10,000 people in "
            "a typical week). Each region shows its best estimate, with the "
            "95% probability range in parentheses."
        ),
        html.Img(src=MAP_IMG,
                 alt="Map of the six HSE regions shaded by modelled trolley rate. "
                     "Darker green is higher. The three western regions are darker "
                     "than the three eastern regions. Northern Ireland is shown grey "
                     "for context.",
                 style={"display": "block", "width": "100%", "maxWidth": "560px",
                        "margin": "0 auto"}),
        html.P("Darker green = higher. Northern Ireland is shown grey (it is not in "
               "the dataset).",
               style={"fontSize": "0.78rem", "color": MUTED, "textAlign": "center",
                      "marginTop": "0.3rem"}),
        html.P("The three western regions all sit above the three eastern regions. "
               "This is an East-West divide in trolley rate. The Mid West has the "
               "highest rate. Its emergency care is concentrated at a single site, "
               "University Hospital Limerick. The model measures the rate, not its "
               "cause.",
               style={"fontSize": "0.85rem", "color": MUTED, "marginTop": "0.4rem"}),
    ])


# -- Section: phases ---------------------------------------------------------

def _phases():
    p = pd.read_csv(PHASE_CSV).sort_values("p_winter", ascending=False).reset_index(drop=True)
    bullets = html.Ul(
        style={"fontSize": "0.95rem", "lineHeight": "1.6", "maxWidth": READ_WIDTH,
               "margin": "0.25rem 0 0.5rem"},
        children=[html.Li(f"{r['region']}: {r['p_winter']*100:.0f}%")
                  for _, r in p.iterrows()],
    )
    return _card([
        _section_title("Phases"),
        _md(
            "This shows when each region's annual cycle peaks. The scale is weeks "
            "from the New Year. 0 is the turn of the year. Dots are best estimates. "
            "Bars are the 95% probability range. The shaded band is winter, 1 December to "
            "end of February."
        ),
        html.Img(src=PHASE_IMG, alt="Forest plot of each region's annual-cycle peak "
                 "week relative to the New Year, with 95% probability ranges. Five regions "
                 "cluster just after New Year. The Mid West has a much wider range.",
                 style={"width": "100%", "maxWidth": "760px", "border": "1px solid #eee",
                        "borderRadius": "4px", "marginTop": "0.5rem", "display": "block"}),
        _md("Five of six regions peak in winter. The chance the peak is in winter, "
            "by region:"),
        bullets,
        _md("The Mid West is the exception. Its peak cannot be resolved. The "
            "95% probability range is very wide. The data was disrupted by the 2024 Mid "
            "West reset (see Events)."),
    ])


# -- Section: events ---------------------------------------------------------

def _fmt_date(v):
    s = str(v).replace(" 00:00:00", "")
    if s.lower().startswith("xxxx-"):
        return "every year, " + s[5:]
    return s


def _events():
    ev = pd.read_excel(EVENTS_XLSX)
    cards = []
    for _, e in ev.iterrows():
        name = EVENT_DISPLAY.get(e["Name"], e["Name"])
        img = EVENT_IMG.get(e["Name"])
        meta = f"{e['Regions']} · {_fmt_date(e['Date start'])} to {_fmt_date(e['Date end'])}"
        children = [
            html.H3(name, style={"margin": "0 0 0.25rem", "fontSize": "1rem"}),
            html.P(meta, style={"margin": "0 0 0.4rem", "fontSize": "0.8rem", "color": MUTED}),
            html.P(e["Description"], style={"margin": "0 0 0.4rem", "fontSize": "0.9rem"}),
        ]
        dip = EVENT_DIP.get(e["Name"])
        if dip:
            children.append(html.P(dip, style={"margin": "0 0 0.6rem", "fontSize": "0.85rem",
                                               "fontWeight": "600", "color": "#333"}))
        _cap = {"fontSize": "0.72rem", "color": MUTED, "fontWeight": "600",
                "margin": "0.4rem 0 0.15rem"}
        if img:
            children += [
                html.P("In the data", style=_cap),
                html.Img(src=img, alt=f"Weekly trolley rate per 10,000 showing the {name}.",
                         style={"width": "100%", "border": "1px solid #eee", "borderRadius": "4px"}),
            ]
        fit = EVENT_FIT_IMG.get(e["Name"])
        if fit:
            children += [
                html.P("Model fit vs observed", style=_cap),
                html.Img(src=fit, alt=f"Model fitted line against observed data for the {name}.",
                         style={"width": "100%", "border": "1px solid #eee", "borderRadius": "4px"}),
            ]
        cards.append(html.Div(children, style={
            "flex": "1 1 320px", "minWidth": "300px",
            "border": "1px solid #e5e5e5", "borderRadius": "6px",
            "padding": "0.85rem 1rem", "backgroundColor": "#fafafa",
        }))
    return _card([
        _section_title("Events"),
        _md("Two real-world events left a clear mark on the data. The model accounts "
            "for each one directly. The two charts use different vertical scales."),
        html.Div(cards, style={"display": "flex", "flexWrap": "wrap", "gap": "1.5rem"}),
    ])


def _about():
    return _card([
        _section_title("About this data"),
        _md(
            "Weekly trolley counts derived from the HSE daily TrolleyGAR report "
            "([uec.hse.ie](https://uec.hse.ie/uec/TGAR.php)), covering January 2023 "
            "to March 2026. A *trolley* is an admitted patient "
            "waiting on a trolley or chair in the emergency department or on a ward "
            "because no inpatient bed is free. Rates are per 10,000 residents so "
            "regions of different size can be compared. These figures describe past "
            "patterns and are not a forecast or a measure of individual hospital "
            "performance."
        ),
    ])


# -- Section: how the model works (method, last) -----------------------------

def _method():
    components = html.Ul(
        style={"fontSize": "0.95rem", "lineHeight": "1.7", "maxWidth": READ_WIDTH},
        children=[
            html.Li([html.B("Regional level (alpha). "), "Each region has its own "
                     "baseline rate."]),
            html.Li([html.B("Annual cycle. "), "A yearly rise and fall that peaks in "
                     "winter. Amplitude and phase vary by region. See ",
                     html.B("Phases"), "."]),
            html.Li([html.B("New Year effect. "), "A sharp turn-of-year change. Fitted "
                     "for each region. See ", html.B("Events"), "."]),
            html.Li([html.B("Mid West reset. "), "The August 2024 University Hospital "
                     "Limerick reset. Applied to the Mid West only."]),
            html.Li([html.B("Short-term memory (AR). "), "A busy week tends to follow a "
                     "busy week. The model carries the last week or two."]),
        ],
    )
    equations = html.Details(
        style={"marginTop": "0.75rem", "maxWidth": READ_WIDTH},
        children=[
            html.Summary("Show the equations (technical)",
                         style={"cursor": "pointer", "fontSize": "0.85rem",
                                "fontWeight": "600", "color": MUTED}),
            _md(r"$$\mu_{j,t} = \alpha_j + \mathcal{C}^{52}_{j,t} + \mathcal{R}_{j,t} + \mathbf{1}(j=\text{MW})\,\mathcal{MW}_t$$"),
            _md("The annual cycle is a single sine-and-cosine wave per region:"),
            _md(r"$$\mathcal{C}^{52}_{j,t} = \beta_j \cos\!\left(\tfrac{2\pi t}{52}\right) + \gamma_j \sin\!\left(\tfrac{2\pi t}{52}\right)$$"),
            _md("Fitted with Bayesian inference (JAGS) using diffuse priors. "
                "Components were added one at a time. Each was kept only if it improved "
                "fit (lower DIC). Two lags of short-term memory, AR(2), were retained."),
        ],
    )
    return _card([
        _section_title("How the model works"),
        _md("Each region's weekly trolley rate (per 10,000 people) is built by adding "
            "up a few pieces, plus a short memory of recent weeks:"),
        components,
        html.P("The fitted pattern against the actual weekly rates:",
               style={"fontSize": "0.95rem", "marginBottom": "0.25rem"}),
        html.Img(src=MU_FIT_IMG, alt="Fitted model line against observed weekly "
                 "trolley rates, one panel per region.",
                 style={"width": "100%", "border": "1px solid #eee",
                        "borderRadius": "4px"}),
        equations,
    ])


def model_page():
    return html.Div(
        style={"maxWidth": PAGE_WIDTH, "margin": "0 auto", "fontFamily": FONT,
               "color": "#222", "lineHeight": "1.55"},
        children=[
            _lead(),
            _regional_levels(),
            _phases(),
            _events(),
            _method(),
            _about(),
        ],
    )
