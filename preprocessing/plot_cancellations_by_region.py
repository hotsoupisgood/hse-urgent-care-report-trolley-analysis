"""Quarterly cancellations by HSE region: mean per hospital with 95% CI."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "supplementary data" / "cancellations_quarterly_by_hospital.csv"
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

df = pd.read_csv(SRC).drop_duplicates(["Hospital", "Year", "Quarter"])
df["Period"] = df["Year"].astype(str) + "Q" + df["Quarter"].astype(str)
periods = (
    df[["Year", "Quarter", "Period"]]
    .drop_duplicates()
    .sort_values(["Year", "Quarter"])["Period"]
    .tolist()
)


def agg(group):
    n = len(group)
    m = group["Cancellations"].mean()
    sd = group["Cancellations"].std(ddof=1) if n > 1 else 0.0
    se = sd / np.sqrt(n) if n > 1 else 0.0
    tcrit = stats.t.ppf(0.975, n - 1) if n > 1 else 0.0
    return pd.Series({"mean": m, "ci": tcrit * se, "n": n})


summary = (
    df.groupby(["Region", "Period"]).apply(agg, include_groups=False).reset_index()
)

agg_csv = OUT_DIR / "cancellations_by_region_quarterly_summary.csv"
summary.to_csv(agg_csv, index=False)

fig, ax = plt.subplots(figsize=(11, 5.5), dpi=140)
x = np.arange(len(periods))

for region, color in REGION_COLOR.items():
    sub = summary[summary["Region"] == region].set_index("Period").reindex(periods)
    ax.errorbar(
        x, sub["mean"], yerr=sub["ci"],
        marker="o", markersize=4, linewidth=1.4,
        color=color, ecolor=color, elinewidth=0.9, capsize=3,
        label=f"{region} (n={int(sub['n'].iloc[0])})",
    )

ax.set_xticks(x)
ax.set_xticklabels(periods, rotation=45, ha="right", fontsize=9)
ax.set_xlabel("Quarter")
ax.set_ylabel("Cancellations per hospital (mean ± 95% CI)")
ax.set_title("Quarterly elective cancellations per hospital, by HSE region (2022–2024)")
ax.grid(axis="y", linestyle=":", alpha=0.5)
ax.legend(fontsize=8, loc="upper left", framealpha=0.9)
plt.tight_layout()

out_png = OUT_DIR / "cancellations_by_region_quarterly.png"
out_pdf = OUT_DIR / "cancellations_by_region_quarterly.pdf"
plt.savefig(out_png)
plt.savefig(out_pdf)
plt.close()

print(f"saved: {out_png}")
print(f"saved: {out_pdf}")
print(f"saved: {agg_csv}")
