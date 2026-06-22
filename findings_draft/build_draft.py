"""Build a static findings draft that presents the thesis results similarly.

Sections:
  1. Annual cycle peak timing (phases) — forest plot + table, mirrors the thesis
     `results-phase-plot` / `results-phase-table` chunks.
  2. Key events — the entries in key_events.xlsx.
  3. Selected model (v4.6) — DIC headline + regional posterior ranking.

Output: findings_draft/index.html + findings_draft/phase_forest.png
"""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import geopandas as gpd
from matplotlib.colors import LinearSegmentedColormap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "findings_draft")
PHASE_CSV = os.path.join(ROOT, "thesis", "phase_table.csv")
EVENTS_XLSX = os.path.join(OUT, "key_events.xlsx")
V46 = os.path.join(ROOT, "data", "models", "wide_weekly_scaledPer10k", "v4.6")

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def short_region(r):
    return r  # full official name, e.g. "HSE Mid West"


# -- 1. Phase forest plot ----------------------------------------------------
phase = pd.read_csv(PHASE_CSV).sort_values("region").reset_index(drop=True)

# Winter as defined in the thesis: 1 December to end of February (Met Eireann),
# in weeks relative to the New Year.
winter_lo, winter_hi = -31 / 7, 59 / 7
XMIN, XMAX = -12, 52  # right edge extended to +52
order = list(phase["region"])
y_pos = np.arange(len(order))[::-1]

fig, ax = plt.subplots(figsize=(8, 4), dpi=220)
ax.axvspan(winter_lo, winter_hi, color="lightblue", alpha=0.35, zorder=0)
ax.text((winter_lo + winter_hi) / 2, len(order) - 0.5 + 0.35, "winter",
        ha="center", va="center", fontsize=8, color="#3a6ea5")
ax.axvline(0, linestyle="--", color="grey", linewidth=1, zorder=1)
ax.errorbar(
    phase["mean_pk"], y_pos,
    xerr=[phase["mean_pk"] - phase["ci_lo"], phase["ci_hi"] - phase["mean_pk"]],
    fmt="o", color="black", ecolor="black", capsize=0, markersize=4, zorder=2,
)
if "HSE Mid West" in order:
    y_mw = y_pos[order.index("HSE Mid West")]
    mw_hi = phase.loc[phase["region"] == "HSE Mid West", "ci_hi"].iloc[0]
    ax.text(mw_hi, y_mw + 0.28, "timing uncertain ", ha="right", va="bottom",
            fontsize=7, color="#888", fontstyle="italic")
ax.set_yticks(y_pos)
ax.set_yticklabels([short_region(r) for r in order])
ax.set_ylim(-0.6, len(order) - 0.5 + 0.4)  # small headroom for the "winter" label
ax.set_xticks(np.arange(-8, 53, 8))
ax.set_xlim(XMIN, XMAX)
ax.set_xlabel("Weeks from New Year (0 = year change)")
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "phase_forest.png"), bbox_inches="tight")
plt.close(fig)

phase_rows = "".join(
    f"<tr><td>{short_region(r['region'])}</td>"
    f"<td>{r['mean_pk']:+.1f}</td>"
    f"<td>[{r['ci_lo']:+.1f}, {r['ci_hi']:+.1f}]</td>"
    f"<td>{r['p_winter']:.3f}</td></tr>"
    for _, r in phase.iterrows()
)

# -- 2. Events ---------------------------------------------------------------
ev = pd.read_excel(EVENTS_XLSX)


def fmt_date(v):
    s = str(v)
    return s.replace(" 00:00:00", "")


event_cards = "".join(
    f"<div class='event'><h3>{e['Name']}</h3>"
    f"<p class='meta'>{e['Regions']} &middot; {fmt_date(e['Date start'])} to {fmt_date(e['Date end'])}</p>"
    f"<p>{e['Description']}</p></div>"
    for _, e in ev.iterrows()
)

# -- 3. Selected model v4.6 --------------------------------------------------
dic = pd.read_csv(os.path.join(V46, "dic.csv")).iloc[0]
ranks = pd.read_csv(os.path.join(V46, "ranks.csv"), index_col=0)
ranks.columns = ["mean_rank", "sd", "q25", "median", "q75", "rank"]
ranks = ranks.sort_values("rank")
rank_rows = "".join(
    f"<tr><td>{int(r['rank'])}</td><td>{short_region(idx)}</td>"
    f"<td>{r['mean_rank']:.2f}</td><td>{r['sd']:.2f}</td></tr>"
    for idx, r in ranks.iterrows()
)

# -- Region map stats: alpha + rank, each with 95% CI ------------------------
# alpha[i] in raw_samples is indexed by JAGS row order = REGIONS order.
REGIONS = [
    "HSE Dublin and Midlands", "HSE Dublin and North East",
    "HSE Dublin and South East", "HSE Mid West",
    "HSE South West", "HSE West and North West",
]
_acols = [f"alpha[{i}]" for i in range(1, 7)]
A = pd.read_csv(os.path.join(V46, "raw_samples.csv"), usecols=_acols)[_acols].to_numpy()
# Per draw, rank descending so rank 1 = highest level (highest trolley burden).
order = (-A).argsort(axis=1).argsort(axis=1) + 1
final_rank = order.mean(0).argsort().argsort() + 1  # integer rank of the mean ranks
region_stats = pd.DataFrame({
    "region": REGIONS,
    "alpha_mean": A.mean(0).round(3),
    "alpha_lo": np.percentile(A, 2.5, 0).round(3),
    "alpha_hi": np.percentile(A, 97.5, 0).round(3),
    "rank": final_rank,
    "rank_mean": order.mean(0).round(2),
    "rank_lo": np.percentile(order, 2.5, 0).round(0).astype(int),
    "rank_hi": np.percentile(order, 97.5, 0).round(0).astype(int),
})
region_stats.to_csv(os.path.join(OUT, "region_map_stats.csv"), index=False)
print("wrote", os.path.join(OUT, "region_map_stats.csv"))

# -- Region maps: static green choropleths (thesis palette) -------------------
# Thesis alpha map uses scale_fill_gradient(low="#f7fcf5", high="#005a32").
GREEN = LinearSegmentedColormap.from_list("thesis_green", ["#f7fcf5", "#005a32"])
_NAME_MAP = {
    "HSE Dublin and Midlands":   "HSE Dublin and Midlands HR",
    "HSE Dublin and North East": "HSE Dublin and North East HR",
    "HSE Dublin and South East": "HSE Dublin and South East HR",
    "HSE Mid West":              "HSE Midwest HR",
    "HSE South West":            "HSE South West HR",
    "HSE West and North West":   "HSE West and North West HR",
}
_LABEL_POS = {  # (lat, lon)
    "HSE Dublin and Midlands":   (53.35, -7.5),
    "HSE Dublin and North East": (53.7,  -6.6),
    "HSE Dublin and South East": (52.5,  -6.8),
    "HSE Mid West":              (52.7,  -8.9),
    "HSE South West":            (51.9,  -9.2),
    "HSE West and North West":   (53.8,  -9.0),
}
_MAPDIR = os.path.join(ROOT, "data", "mapping")
_gdf = gpd.read_file(os.path.join(_MAPDIR, "hse_regions.geojson"))
_gdf = _gdf.merge(region_stats.assign(hr=region_stats["region"].map(_NAME_MAP)),
                  left_on="HR_operational_name", right_on="hr")
_ni = gpd.read_file(os.path.join(_MAPDIR, "northern_ireland.geojson")).dissolve()

_b1, _b2 = _gdf.total_bounds, _ni.total_bounds
_XLIM = (min(_b1[0], _b2[0]) - 0.15, max(_b1[2], _b2[2]) + 0.15)
_YLIM = (min(_b1[1], _b2[1]) - 0.15, max(_b1[3], _b2[3]) + 0.15)


def _draw_map(value_col, fname, label_fn, title, legend=False, legend_label=None):
    fig, ax = plt.subplots(figsize=(6, 6.4), dpi=220)
    _ni.plot(ax=ax, color="#ebebeb", edgecolor="#9aa0a6", linewidth=0.3, zorder=0)
    legend_kwds = {"shrink": 0.45, "label": legend_label} if legend else None
    _gdf.plot(ax=ax, column=value_col, cmap=GREEN, edgecolor="#555", linewidth=0.4,
              zorder=1, legend=legend, legend_kwds=legend_kwds)
    for _, r in _gdf.iterrows():
        lat, lon = _LABEL_POS[r["region"]]
        ax.text(lon, lat, label_fn(r), ha="center", va="center", zorder=4,
                fontsize=8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    ax.set_xlim(*_XLIM)
    ax.set_ylim(*_YLIM)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), bbox_inches="tight")
    plt.close(fig)


_draw_map("alpha_mean", "model_map_alpha.png",
          lambda r: f"{short_region(r['region'])}\n{r['alpha_mean']:.1f}",
          "", legend=True, legend_label="Rate per 10,000")
print("wrote", os.path.join(OUT, "model_map_alpha.png"))

# -- Event illustration plots (weekly per-10k series) ------------------------
_wk = pd.read_csv(os.path.join(ROOT, "data", "wide_weekly_scaledPer10k.csv"))
_long = _wk.melt(id_vars="Region", var_name="week", value_name="rate")
_long["week"] = pd.to_datetime(_long["week"])


def _event_plot(series, shade_spans, title, fname):
    fig, ax = plt.subplots(figsize=(5.2, 2.6), dpi=220)
    ax.plot(series["week"], series["rate"], color="#005a32", linewidth=1.1)
    for lo, hi, col in shade_spans:
        ax.axvspan(pd.Timestamp(lo), pd.Timestamp(hi), color=col, alpha=0.22)
    ax.set_xlim(series["week"].min(), series["week"].max())
    ax.set_ylim(bottom=0)
    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.set_ylabel("Trolleys per 10,000", fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(labelsize=8)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), bbox_inches="tight")
    plt.close(fig)


_mw = _long[_long["Region"] == "HSE Mid West"].sort_values("week")
_event_plot(_mw, [("2024-08-08", "2024-08-19", "#d62728")],
            "The Aug 2024 reset sharply cut Mid West trolleys", "event_midwest_reset.png")

# New Year: all six regions overlaid (as in the thesis), so the shared dip is visible.
REGION_PALETTE = {
    "HSE Dublin and Midlands":   "#E69F00",
    "HSE Dublin and North East": "#56B4E9",
    "HSE Dublin and South East": "#009E73",
    "HSE Mid West":              "#D55E00",
    "HSE South West":            "#0072B2",
    "HSE West and North West":   "#CC79A7",
}
fig, ax = plt.subplots(figsize=(5.2, 2.8), dpi=220)
for y in range(2022, 2026):
    ax.axvspan(pd.Timestamp(f"{y}-12-01"), pd.Timestamp(f"{y + 1}-01-31"),
               color="#3a6ea5", alpha=0.13)
for region, col in REGION_PALETTE.items():
    s = _long[_long["Region"] == region].sort_values("week")
    ax.plot(s["week"], s["rate"], color=col, linewidth=0.8, label=region.replace("HSE ", ""))
ax.set_xlim(_long["week"].min(), _long["week"].max())
ax.set_ylim(bottom=0)
ax.set_title("Trolley counts dip every New Year", fontsize=9, fontweight="bold")
ax.set_ylabel("Trolleys per 10,000", fontsize=8)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.tick_params(labelsize=8)
ax.legend(fontsize=5.5, ncol=3, frameon=False, loc="upper center",
          bbox_to_anchor=(0.5, -0.18))
for sp in ["top", "right"]:
    ax.spines[sp].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "event_newyear.png"), bbox_inches="tight")
plt.close(fig)
print("wrote event_newyear.png and event_midwest_reset.png")

# -- Event modelling results: model fit vs observed, zoomed to each event -----
_obs = pd.read_csv(os.path.join(ROOT, "data", "wide_weekly_scaledPer10k.csv")).set_index("Region")
_dates = pd.to_datetime(_obs.columns)
_mu = pd.read_csv(os.path.join(V46, "mu.csv"))
_mu_lo = pd.read_csv(os.path.join(V46, "mu_lower.csv"))
_mu_hi = pd.read_csv(os.path.join(V46, "mu_upper.csv"))


def _fit_plot(obs, fit, lo, hi, shade, xr, title, fname):
    fig, ax = plt.subplots(figsize=(5.2, 2.6), dpi=220)
    if lo is not None:
        ax.fill_between(_dates, lo, hi, color="#005a32", alpha=0.15, linewidth=0)
    ax.plot(_dates, obs, color="#999", linewidth=1.0, label="Observed")
    ax.plot(_dates, fit, color="#005a32", linewidth=1.5, label="Model fit")
    for a, b, c in shade:
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=c, alpha=0.22)
    x0, x1 = pd.Timestamp(xr[0]), pd.Timestamp(xr[1])
    ax.set_xlim(x0, x1)
    m = (_dates >= x0) & (_dates <= x1)
    # Rates cannot be negative — never show below 0 even if the ribbon dips there.
    top = (max(hi[m].max(), obs[m].max()) if lo is not None else obs[m].max()) * 1.08
    ax.set_ylim(0, top)
    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.set_ylabel("Trolleys per 10,000", fontsize=8)
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.tick_params(labelsize=7)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), bbox_inches="tight")
    plt.close(fig)


_fit_plot(_obs.mean(axis=0).values, _mu.mean(axis=1).values, None, None,
          [("2024-12-01", "2025-01-31", "#3a6ea5")],
          ("2024-09-01", "2025-03-15"),
          "The model reproduces the New Year dip", "event_newyear_fit.png")

_fit_plot(_obs.loc["HSE Mid West"].values, _mu["HSE Mid West"].values,
          _mu_lo["HSE Mid West"].values, _mu_hi["HSE Mid West"].values,
          [("2024-08-08", "2024-08-19", "#d62728")],
          ("2024-05-01", "2024-11-30"),
          "The model captures the Aug 2024 reset", "event_midwest_reset_fit.png")
print("wrote event fit plots")

# -- New Year dip by region (forest of the deepest block-effect week) ---------
_NY_REGIONS = [
    "HSE Dublin and Midlands", "HSE Dublin and North East",
    "HSE Dublin and South East", "HSE Mid West",
    "HSE South West", "HSE West and North West",
]
_dweeks = ["delta_pre", "delta_pm1", "delta_mid", "delta_post"]
_draw = pd.read_csv(os.path.join(V46, "raw_samples.csv"),
                    usecols=[f"{p}[{i}]" for p in _dweeks for i in range(1, 7)])
_rows = []
for i in range(1, 7):
    M = np.vstack([_draw[f"{p}[{i}]"].values for p in _dweeks]).T
    tr = M.min(axis=1)  # deepest of the four New Year weeks, per draw
    _rows.append((_NY_REGIONS[i - 1], tr.mean(),
                  np.percentile(tr, 2.5), np.percentile(tr, 97.5)))
_dip = pd.DataFrame(_rows, columns=["region", "mean", "lo", "hi"]).sort_values("mean")
_y = np.arange(len(_dip))[::-1]
fig, ax = plt.subplots(figsize=(8, 3.4), dpi=220)
ax.axvline(0, linestyle="--", color="grey", linewidth=1, zorder=1)
ax.errorbar(_dip["mean"], _y,
            xerr=[_dip["mean"] - _dip["lo"], _dip["hi"] - _dip["mean"]],
            fmt="o", color="black", ecolor="black", capsize=0, markersize=4, zorder=2)
ax.set_yticks(_y)
ax.set_yticklabels([short_region(r) for r in _dip["region"]], fontsize=12)
ax.set_xlabel("Change in weekly rate per 10,000 at the New Year", fontsize=12)
ax.tick_params(axis="x", labelsize=11)
for sp in ["top", "right"]:
    ax.spines[sp].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "event_newyear_dip.png"), bbox_inches="tight")
plt.close(fig)
print("wrote event_newyear_dip.png")

# -- Regions reference map (categorical, for the About tab) -------------------
_counties_ref = gpd.read_file(os.path.join(_MAPDIR, "ie_counties.geojson"))
fig, ax = plt.subplots(figsize=(4.8, 5.3), dpi=220)
_ni.plot(ax=ax, color="#ebebeb", edgecolor="#9aa0a6", linewidth=0.3, zorder=0)
_gdf.plot(ax=ax, color=_gdf["region"].map(REGION_PALETTE), edgecolor="#555",
          linewidth=0.5, zorder=1)
_counties_ref.plot(ax=ax, facecolor="none", edgecolor="white", linewidth=0.3,
                   alpha=0.6, zorder=2)
_REGION_LABEL = {
    "HSE Dublin and Midlands":   "HSE Dublin\nand Midlands",
    "HSE Dublin and North East": "HSE Dublin\nand North East",
    "HSE Dublin and South East": "HSE Dublin\nand South East",
    "HSE Mid West":              "HSE\nMid West",
    "HSE South West":            "HSE\nSouth West",
    "HSE West and North West":   "HSE West and\nNorth West",
}
for _, r in _gdf.iterrows():
    geom = r.geometry
    c = geom.centroid
    pt = c if geom.contains(c) else geom.representative_point()
    ax.text(pt.x, pt.y, _REGION_LABEL[r["region"]], ha="center", va="center", zorder=4,
            fontsize=9, fontweight="bold", linespacing=0.95,
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))
ax.set_xlim(*_XLIM)
ax.set_ylim(*_YLIM)
ax.set_title("The six HSE Health Regions", fontsize=13, fontweight="bold")
ax.set_xticks([]); ax.set_yticks([])
for sp in ax.spines.values():
    sp.set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "model_regions.png"), bbox_inches="tight")
plt.close(fig)
print("wrote model_regions.png")

# -- Assemble page -----------------------------------------------------------
html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HSE Trolley Findings — Draft</title>
<style>
  body {{ font-family: {FONT}; color: #222; max-width: 880px; margin: 2rem auto;
         padding: 0 1.25rem; line-height: 1.55; }}
  h1 {{ font-size: 1.6rem; margin-bottom: .25rem; }}
  h2 {{ font-size: 1.2rem; margin-top: 2.5rem; border-bottom: 2px solid #eee;
        padding-bottom: .35rem; }}
  .sub {{ color: #777; margin-top: 0; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: .75rem; font-size: .9rem; }}
  th, td {{ text-align: left; padding: .45rem .7rem; border-bottom: 1px solid #eee; }}
  th {{ background: #f0f0f0; font-weight: 600; }}
  tr:nth-child(even) td {{ background: #f8f9fa; }}
  img {{ max-width: 100%; border: 1px solid #eee; border-radius: 4px; margin-top: .75rem; }}
  .note {{ font-size: .8rem; color: #888; }}
  .event {{ border-left: 3px solid #d62728; padding: .25rem 0 .25rem 1rem; margin: 1rem 0; }}
  .event h3 {{ margin: 0 0 .25rem; font-size: 1rem; }}
  .event .meta {{ margin: 0 0 .4rem; font-size: .8rem; color: #777; }}
  .draft {{ background: #fff3cd; border: 1px solid #ffe69c; padding: .5rem .75rem;
            border-radius: 4px; font-size: .85rem; }}
</style></head><body>

<h1>HSE Trolley Findings</h1>
<p class="sub">Draft presentation of thesis results &mdash; phases, events, and the selected model.</p>
<p class="draft"><strong>Draft</strong> for review. Mirrors the thesis presentation. Once approved, this becomes the dashboard findings page (Dash) and ships via the bash snapshot.</p>

<h2>Annual cycle peak timing</h2>
<p>Per-region posterior of the annual-cycle peak week, relative to the New Year
(0 = year change). Points are posterior means, bars are 95% credible intervals.
The shaded band is winter (New Year &plusmn; 2 months).</p>
<img src="phase_forest.png" alt="Phase forest plot">
<table>
  <tr><th>Region</th><th>Mean peak (wk from NY)</th><th>95% CI</th><th>P(winter)</th></tr>
  {phase_rows}
</table>
<p class="note">Mid West peak is poorly identified (wide CI), consistent with its disrupted series.</p>

<h2>Key events</h2>
{event_cards}

<h2>Selected model</h2>
<p>AR(2) baseline with annual cycle, region-specific New Year, and the Mid West reset.
DIC {dic['DIC']:.1f} (deviance {dic['deviance']:.1f}, pD {dic['penalty']:.1f}).</p>
<table>
  <tr><th>Rank</th><th>Region</th><th>Mean rank</th><th>SD</th></tr>
  {rank_rows}
</table>
<p class="note">Rank 1 = highest posterior trolley burden (per 10k population).</p>

</body></html>
"""

with open(os.path.join(OUT, "index.html"), "w") as f:
    f.write(html)

print("wrote", os.path.join(OUT, "index.html"))
print("wrote", os.path.join(OUT, "phase_forest.png"))
