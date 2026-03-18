"""
About tab — project background, motivation, and model specifications.
"""

from dash import dcc, html

FONT = 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'

CARD = {
    'backgroundColor': 'white', 'borderRadius': '2px',
    'padding': '24px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
    'marginBottom': '16px',
}

# ── LaTeX strings ─────────────────────────────────────────────────────

MODEL_V1_LATEX = r"""
**Likelihood**

$$y_{i,1} \sim \mathcal{N}(\mu_{i,1},\; \tau_i)$$

$$y_{i,t} \sim \mathcal{N}\!\Big(\mu_{i,t} + \phi\,(y_{i,t-1} - \mu_{i,t-1}),\; \tau_i\Big), \quad t = 2,\dots,T$$

**$\mu$ function**

$$\mu_{i,t} = \alpha_i + \beta_i \cos\!\Big(\frac{2\pi\, t}{52}\Big) + \gamma_i \sin\!\Big(\frac{2\pi\, t}{52}\Big)$$

**Priors**

$$\alpha_i \sim \mathcal{N}(0,\, 0.001), \quad
\beta_i \sim \mathcal{N}(0,\, 0.001), \quad
\gamma_i \sim \mathcal{N}(0,\, 0.001)$$

$$\tau_i \sim \text{Gamma}(0.001,\, 0.001), \quad
\phi \sim \text{Uniform}(-1,\, 1)$$
"""

MODEL_V2_LATEX = r"""
**Likelihood**

$$y_{i,1} \sim \mathcal{N}(\mu_{i,1},\; \tau_i)$$

$$y_{i,t} \sim \mathcal{N}\!\Big(\mu_{i,t} + \phi\,(y_{i,t-1} - \mu_{i,t-1}),\; \tau_i\Big), \quad t = 2,\dots,T$$

**$\mu$ function**

$$\mu_{i,t} = \alpha_i + \beta_i \cos\!\Big(\frac{2\pi\, t}{52}\Big) + \gamma_i \sin\!\Big(\frac{2\pi\, t}{52}\Big) + \sum_{k \in \{\text{pre, mid, post}\}} \delta_k \cdot \mathbb{1}_{\text{NY},k}(t) + \sum_{k \in \{\text{pre, mid, post}\}} \sigma_k \cdot \mathbb{1}_{\text{FR},k}(t) \cdot \mathbb{1}_{\text{MW}}(i)$$

Where $\mathbb{1}_{\text{NY},k}(t)$ are New Year indicator variables (weeks 52, 1, 2) and $\mathbb{1}_{\text{FR},k}(t)$ are fiscal reset indicators (weeks 86--88) applied only to the Mid West region.

**Additional priors**

$$\delta_{\text{pre}},\, \delta_{\text{mid}},\, \delta_{\text{post}} \sim \mathcal{N}(0,\, 0.001)$$

$$\sigma_{\text{pre}},\, \sigma_{\text{mid}},\, \sigma_{\text{post}} \sim \mathcal{N}(0,\, 0.001)$$
"""

MODEL_V3_LATEX = r"""
**Likelihood**

$$y_{i,1} \sim \mathcal{N}(\mu_{i,1},\; \tau_i)$$

$$y_{i,t} \sim \mathcal{N}\!\Big(\mu_{i,t} + \phi\,(y_{i,t-1} - \mu_{i,t-1}),\; \tau_i\Big), \quad t = 2,\dots,T$$

**$\mu$ function**

$$\mu_{i,t} = \alpha_i + \beta_i \cos\!\Big(\frac{2\pi\, t}{52}\Big) + \gamma_i \sin\!\Big(\frac{2\pi\, t}{52}\Big) + \sum_{k \in \{\text{pre, mid, post}\}} \delta_{k,i} \cdot \mathbb{1}_{\text{NY},k}(t) + \sum_{k \in \{\text{pre, mid, post}\}} \sigma_k \cdot \mathbb{1}_{\text{FR},k}(t) \cdot \mathbb{1}_{\text{MW}}(i)$$

**Additional priors**

$$\delta_{\text{pre},i},\, \delta_{\text{mid},i},\, \delta_{\text{post},i} \sim \mathcal{N}(0,\, 0.001) \quad \forall\, i$$

$$\sigma_{\text{pre}},\, \sigma_{\text{mid}},\, \sigma_{\text{post}} \sim \mathcal{N}(0,\, 0.001)$$
"""


# ── Layout ────────────────────────────────────────────────────────────

def about_layout():
    return html.Div([

        # Data source
        html.Div([
            html.H2('Data Source', style={'margin': '0 0 12px 0', 'fontSize': '20px'}),
            html.P([
                'Data is sourced from the HSE TrolleyGAR system, which records '
                'daily counts of patients on trolleys in emergency departments '
                'across Ireland.',
            ]),
            html.A('HSE Urgent & Emergency Care Report',
                   href='https://www2.hse.ie/services/urgent-emergency-care-report/',
                   target='_blank',
                   style={'color': '#2980b9', 'fontWeight': 'bold',
                          'fontSize': '15px'}),
        ], style=CARD),

        # Why this matters
        html.Div([
            html.H2('Why Trolley Waits Matter',
                     style={'margin': '0 0 12px 0', 'fontSize': '20px'}),
            html.P(
                'Patients waiting on trolleys in emergency departments is a '
                'well-documented patient safety concern. Prolonged trolley waits '
                'are associated with:'
            ),
            html.Ul([
                html.Li('Increased in-hospital mortality and adverse outcomes'),
                html.Li('Delayed diagnosis and treatment'),
                html.Li('Overcrowding, which compromises care for all patients '
                         'in the department'),
                html.Li('Increased risk of healthcare-associated infections'),
                html.Li('Staff burnout and reduced capacity to deliver care'),
            ]),
            html.P(
                'Ireland has experienced persistently high trolley counts relative '
                'to other comparable healthcare systems, making it a critical area '
                'for ongoing monitoring and analysis.'
            ),
        ], style=CARD),

        # Motivation
        html.Div([
            html.H2('Project Motivation',
                     style={'margin': '0 0 12px 0', 'fontSize': '20px'}),
            html.P(
                'This project applies Bayesian time series modelling to daily '
                'trolley count data across six HSE regions. The goal is to '
                'understand underlying temporal patterns, including:'
            ),
            html.Ul([
                html.Li('Annual seasonal cycles in emergency department demand'),
                html.Li('Day-of-week effects on trolley counts'),
                html.Li('Structural disruptions such as New Year dips and fiscal '
                         'year resets'),
                html.Li('Regional variation in baseline demand and seasonality'),
            ]),
            html.P(
                'By fitting progressively richer models and comparing them via '
                'the Deviance Information Criterion (DIC), we can identify which '
                'features of the data are statistically meaningful and which '
                'regions differ significantly from one another.'
            ),
        ], style=CARD),

        # Model specifications
        html.Div([
            html.H2('Model Specifications',
                     style={'margin': '0 0 12px 0', 'fontSize': '20px'}),
            dcc.Markdown(
                r'All models are AR(1) processes with an annual harmonic '
                r'$\mu$ function, fit using JAGS (Gibbs sampling) with 4 chains, '
                r'10,000 burn-in and 20,000 sampling iterations. '
                r'Notation: $i$ indexes region ($i = 1,\dots,6$), '
                r'$t$ indexes week ($t = 1,\dots,T$).',
                mathjax=True,
                style={'marginBottom': '20px', 'fontSize': '14px'},
            ),

            # V1
            html.H3('Model 1 — Base AR(1) + Annual Cycle',
                     style={'margin': '0 0 8px 0', 'fontSize': '17px',
                            'borderBottom': '1px solid #ddd',
                            'paddingBottom': '6px'}),
            dcc.Markdown(MODEL_V1_LATEX, mathjax=True,
                         style={'fontSize': '14px', 'lineHeight': '1.8'}),

            # V2
            html.H3('Model 2 — New Year + Fiscal Reset Effects',
                     style={'margin': '20px 0 8px 0', 'fontSize': '17px',
                            'borderBottom': '1px solid #ddd',
                            'paddingBottom': '6px'}),
            dcc.Markdown(MODEL_V2_LATEX, mathjax=True,
                         style={'fontSize': '14px', 'lineHeight': '1.8'}),

            # V3
            html.H3('Model 3 — Region-Specific New Year Effects',
                     style={'margin': '20px 0 8px 0', 'fontSize': '17px',
                            'borderBottom': '1px solid #ddd',
                            'paddingBottom': '6px'}),
            dcc.Markdown(MODEL_V3_LATEX, mathjax=True,
                         style={'fontSize': '14px', 'lineHeight': '1.8'}),

        ], style=CARD),

    ])
