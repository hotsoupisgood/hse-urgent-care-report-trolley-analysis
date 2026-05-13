"""Quarterly cancellations per 1,000 people by HSE region.

Regional total cancellations (sum across hospitals) / region population.
95% CI by bootstrap resampling hospitals within region.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "supplementary data" / "cancellations_quarterly_by_hospital.csv"
POP = ROOT / "supplementary data" / "2022_hr_population.csv"
OUT_DIR = ROOT / "supplementary data" / "plots"
OUT_DIR.mkdir(exist_ok=True)

REGION_COLOR = {
    "Dublin and North East": "#1f77b4",
    "Dublin and Midlands":   "#ff7f0e",
    "Dublin and South East": "#2ca02c",
    "West and North West":   "#d62728",
    "South West":            "#9467bd",
    "Mid West":              "#8c564b",
}

N_BOOT = 5000
RNG = np.random.default_rng(20260507)

df = pd.read_csv(SRC).drop_duplicates(["Hospital", "Year", "Quarter"])
df["Period"] = df["Year"].astype(str) + "Q" + df["Quarter"].astype(str)
periods = (
    df[["Year", "Quarter", "Period"]]
    .drop_duplicates()
    .sort_values(["Year", "Quarter"])["Period"]
    .tolist()
)

pop = (
    pd.read_csv(POP)
    .rename(columns={"HSE Health Regions": "Region", "Number of persons": "Population"})
    .drop_duplicates(subset="Region")
    .set_index("Region")["Population"]
)


def boot_total_per_1k(values, population, n_boot=N_BOOT):
    """Bootstrap regional total per 1,000 by resampling hospitals with replacement."""
    n = len(values)
    if n == 0:
        return np.nan, np.nan, np.nan
    idx = RNG.integers(0, n, size=(n_boot, n))
    boot_totals = values[idx].sum(axis=1)
    boot_rate = boot_totals / population * 1000
    point = values.sum() / population * 1000
    lo, hi = np.percentile(boot_rate, [2.5, 97.5])
    return point, lo, hi


rows = []
for (region, period), grp in df.groupby(["Region", "Period"]):
    vals = grp["Cancellations"].to_numpy(dtype=float)
    point, lo, hi = boot_total_per_1k(vals, pop[region])
    rows.append({
        "Region": region, "Period": period,
        "rate_per_1k": point, "ci_lo": lo, "ci_hi": hi,
        "n_hospitals": len(vals), "population": pop[region],
    })
summary = pd.DataFrame(rows)
summary.to_csv(OUT_DIR / "cancellations_per_capita_by_region_quarterly_summary.csv", index=False)

fig, ax = plt.subplots(figsize=(11, 5.5), dpi=140)
x = np.arange(len(periods))

for region, color in REGION_COLOR.items():
    sub = summary[summary["Region"] == region].set_index("Period").reindex(periods)
    yerr = np.vstack([sub["rate_per_1k"] - sub["ci_lo"], sub["ci_hi"] - sub["rate_per_1k"]])
    ax.errorbar(
        x, sub["rate_per_1k"], yerr=yerr,
        marker="o", markersize=4, linewidth=1.4,
        color=color, ecolor=color, elinewidth=0.9, capsize=3,
        label=f"{region} (n={int(sub['n_hospitals'].iloc[0])}, pop={int(sub['population'].iloc[0]):,})",
    )

ax.set_xticks(x)
ax.set_xticklabels(periods, rotation=45, ha="right", fontsize=9)
ax.set_xlabel("Quarter")
ax.set_ylabel("Cancellations per 1,000 people (regional total ÷ 2022 population)")
ax.set_title("Quarterly elective cancellations per 1,000 people, by HSE region (2022–2024)")
ax.grid(axis="y", linestyle=":", alpha=0.5)
ax.legend(fontsize=7.5, loc="upper left", framealpha=0.9)
ax.set_ylim(bottom=0)
plt.tight_layout()

out_png = OUT_DIR / "cancellations_per_capita_by_region_quarterly.png"
out_pdf = OUT_DIR / "cancellations_per_capita_by_region_quarterly.pdf"
plt.savefig(out_png)
plt.savefig(out_pdf)
plt.close()

print(f"saved: {out_png}")
print(f"saved: {out_pdf}")
