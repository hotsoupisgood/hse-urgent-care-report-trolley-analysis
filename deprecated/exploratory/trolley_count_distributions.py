"""
Trolley count distributions:
  1. Per-hospital distribution of daily total trolley counts (box plots)
  2. Per-region distribution of daily total trolley counts (box plots + violin)
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data",
                         "uec_data_2023_2025_full_with_regions.csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "misc_plots")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load & clean ────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
df["Total"] = pd.to_numeric(df["Total"], errors="coerce")
df = df.dropna(subset=["Total", "Hospital", "Region"])

# ── 1. Hospital-level box plots ────────────────────────────────────────────
# Order hospitals by median count (descending) for readability
hosp_medians = df.groupby("Hospital")["Total"].median().sort_values(ascending=True)
hospitals_ordered = hosp_medians.index.tolist()

fig, ax = plt.subplots(figsize=(14, max(10, len(hospitals_ordered) * 0.35)))
data_by_hosp = [df.loc[df["Hospital"] == h, "Total"].values for h in hospitals_ordered]

bp = ax.boxplot(data_by_hosp, vert=False, patch_artist=True,
                boxprops=dict(facecolor="#4C72B0", alpha=0.7),
                medianprops=dict(color="black", linewidth=1.5),
                flierprops=dict(marker=".", markersize=3, alpha=0.4),
                widths=0.6)
ax.set_yticks(range(1, len(hospitals_ordered) + 1))
ax.set_yticklabels(hospitals_ordered, fontsize=8)
ax.set_xlabel("Daily Total Trolley Count", fontsize=11)
ax.set_title("Distribution of Daily Trolley Counts by Hospital (2023-2025)", fontsize=13)
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "hospital_trolley_distributions.png"), dpi=200)
print(f"Saved hospital plot  →  {OUT_DIR}/hospital_trolley_distributions.png")
plt.close(fig)

# ── 2. Region-level box + violin plots ─────────────────────────────────────
# Aggregate daily total per region (sum of hospital totals per day)
region_daily = (df.groupby(["Date", "Region"])["Total"]
                  .sum()
                  .reset_index())

region_medians = region_daily.groupby("Region")["Total"].median().sort_values(ascending=True)
regions_ordered = region_medians.index.tolist()

fig, axes = plt.subplots(1, 2, figsize=(16, max(5, len(regions_ordered) * 1.0)),
                         sharey=True, gridspec_kw={"wspace": 0.05})

# Box plot
data_by_region = [region_daily.loc[region_daily["Region"] == r, "Total"].values
                  for r in regions_ordered]

axes[0].boxplot(data_by_region, vert=False, patch_artist=True,
                boxprops=dict(facecolor="#DD8452", alpha=0.7),
                medianprops=dict(color="black", linewidth=1.5),
                flierprops=dict(marker=".", markersize=3, alpha=0.4),
                widths=0.6)
axes[0].set_yticks(range(1, len(regions_ordered) + 1))
axes[0].set_yticklabels(regions_ordered, fontsize=10)
axes[0].set_xlabel("Daily Total Trolley Count (sum across hospitals)", fontsize=10)
axes[0].set_title("Box Plot", fontsize=12)
axes[0].xaxis.set_minor_locator(ticker.AutoMinorLocator())
axes[0].grid(axis="x", alpha=0.3)

# Violin plot
vp = axes[1].violinplot(data_by_region, vert=False, showmedians=True, showextrema=True)
for body in vp["bodies"]:
    body.set_facecolor("#55A868")
    body.set_alpha(0.7)
axes[1].set_xlabel("Daily Total Trolley Count (sum across hospitals)", fontsize=10)
axes[1].set_title("Violin Plot", fontsize=12)
axes[1].xaxis.set_minor_locator(ticker.AutoMinorLocator())
axes[1].grid(axis="x", alpha=0.3)

fig.suptitle("Distribution of Daily Trolley Counts by Health Region (2023-2025)",
             fontsize=13, y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "region_trolley_distributions.png"),
            dpi=200, bbox_inches="tight")
print(f"Saved region plot    →  {OUT_DIR}/region_trolley_distributions.png")
plt.close(fig)

# ── 3. Cumulative total trolley counts per hospital (2023-2025) ─────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data",
                          "hospital_model_classification.json")
with open(MODEL_PATH) as f:
    model_data = json.load(f)

MODEL_COLORS = {4: "#C44E52", 3: "#4C72B0", 2: "#55A868", None: "#8C8C8C"}
MODEL_LABELS = {4: "Model 4", 3: "Model 3", 2: "Model 2", None: "Specialty"}

hosp_totals = df.groupby("Hospital")["Total"].sum().sort_values(ascending=True)
hospitals_cum_ordered = hosp_totals.index.tolist()
bar_colors = [MODEL_COLORS[model_data["hospitals"].get(h, {}).get("model")]
              for h in hospitals_cum_ordered]

# Sort descending for vertical bars (tallest on left)
hosp_totals_desc = hosp_totals.sort_values(ascending=False)
hospitals_desc = hosp_totals_desc.index.tolist()
bar_colors_desc = [MODEL_COLORS[model_data["hospitals"].get(h, {}).get("model")]
                   for h in hospitals_desc]

n = len(hosp_totals)
fig = plt.figure(figsize=(26, 20))
gs = fig.add_gridspec(2, 2, height_ratios=[2, 2], width_ratios=[10, 1],
                      hspace=0.4, wspace=0.02)
ax_bar = fig.add_subplot(gs[0, 0])        # top-left: vertical bar chart
ax_dist = fig.add_subplot(gs[0, 1], sharey=ax_bar)  # top-right: aggregate boxplot

gs_bottom = gs[1, :].subgridspec(1, 2, wspace=0.25)
ax_daily = fig.add_subplot(gs_bottom[0])   # bottom-left: daily distribution
ax_weekly = fig.add_subplot(gs_bottom[1])  # bottom-right: weekly distribution

# Top-left: vertical bar chart
positions = np.arange(n)
ax_bar.bar(positions, hosp_totals_desc.values, color=bar_colors_desc, alpha=0.85)
ax_bar.set_xticks(positions)
ax_bar.set_xticklabels(hospitals_desc, rotation=90, ha="center", fontsize=7)
ax_bar.set_ylabel("Cumulative Total Trolley Count (2023-2025)", fontsize=11)
ax_bar.set_title("Cumulative Counts", fontsize=12)
ax_bar.yaxis.set_minor_locator(ticker.AutoMinorLocator())
ax_bar.grid(axis="y", alpha=0.3)
legend_handles = [mpatches.Patch(color=MODEL_COLORS[m], alpha=0.85, label=MODEL_LABELS[m])
                  for m in [4, 3, 2, None]]
ax_bar.legend(handles=legend_handles, loc="upper right", fontsize=8)

# Top-right: aggregate vertical boxplot (shares y-axis with bar chart)
ax_dist.boxplot(hosp_totals.values, vert=True, patch_artist=True,
                boxprops=dict(facecolor="#CCCCCC", alpha=0.7),
                medianprops=dict(color="black", linewidth=1.5),
                flierprops=dict(marker="o", markersize=5, alpha=0.6),
                widths=0.5)
ax_dist.set_xticklabels(["All"], fontsize=8)
ax_dist.tick_params(axis="y", labelleft=False)
ax_dist.set_title("Spread", fontsize=10)
ax_dist.grid(axis="y", alpha=0.3)

# Bottom-left: daily distribution box plots (horizontal, same hospital order as before)
data_by_hosp_daily = [df.loc[df["Hospital"] == h, "Total"].values for h in hospitals_cum_ordered]
box_colors = [MODEL_COLORS[model_data["hospitals"].get(h, {}).get("model")]
              for h in hospitals_cum_ordered]
hpos = np.arange(1, n + 1)
bp_d = ax_daily.boxplot(data_by_hosp_daily, vert=False, patch_artist=True,
                        positions=hpos,
                        medianprops=dict(color="black", linewidth=1.5),
                        flierprops=dict(marker=".", markersize=3, alpha=0.4),
                        widths=0.6)
for patch, color in zip(bp_d["boxes"], box_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax_daily.set_ylim(0.4, n + 0.6)
ax_daily.set_yticks(hpos)
ax_daily.set_yticklabels(hospitals_cum_ordered, fontsize=7)
ax_daily.set_xlabel("Daily Total Trolley Count", fontsize=11)
ax_daily.set_title("Daily Distribution", fontsize=12)
ax_daily.xaxis.set_minor_locator(ticker.AutoMinorLocator())
ax_daily.grid(axis="x", alpha=0.3)

# Bottom-right: weekly distribution box plots
df["Week"] = df["Date"].dt.isocalendar().week.astype(int)
df["Year"] = df["Date"].dt.year
weekly = df.groupby(["Year", "Week", "Hospital"])["Total"].sum().reset_index()
data_by_hosp_weekly = [weekly.loc[weekly["Hospital"] == h, "Total"].values
                       for h in hospitals_cum_ordered]
bp_w = ax_weekly.boxplot(data_by_hosp_weekly, vert=False, patch_artist=True,
                         positions=hpos,
                         medianprops=dict(color="black", linewidth=1.5),
                         flierprops=dict(marker=".", markersize=3, alpha=0.4),
                         widths=0.6)
for patch, color in zip(bp_w["boxes"], box_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax_weekly.set_ylim(0.4, n + 0.6)
ax_weekly.set_yticks(hpos)
ax_weekly.set_yticklabels([])
ax_weekly.set_xlabel("Weekly Total Trolley Count", fontsize=11)
ax_weekly.set_title("Weekly Distribution", fontsize=12)
ax_weekly.xaxis.set_minor_locator(ticker.AutoMinorLocator())
ax_weekly.grid(axis="x", alpha=0.3)

fig.tight_layout()
fig.subplots_adjust(top=0.94)
fig.suptitle("Trolley Counts by Hospital, Colour-Coded by Model (2023-2025)", fontsize=14, y=0.97)
fig.savefig(os.path.join(OUT_DIR, "hospital_trolley_cumulative.png"), dpi=200,
            bbox_inches="tight")
print(f"Saved hospital cumulative plot  →  {OUT_DIR}/hospital_trolley_cumulative.png")
plt.close(fig)

# ── 3b. Same plot, colour-coded by health region ───────────────────────────
hosp_region = df.drop_duplicates("Hospital").set_index("Hospital")["Region"].to_dict()
regions_unique = sorted(set(hosp_region.values()))
REGION_CMAP = plt.cm.get_cmap("tab10", len(regions_unique))
REGION_COLORS = {r: REGION_CMAP(i) for i, r in enumerate(regions_unique)}

bar_colors_reg_desc = [REGION_COLORS[hosp_region[h]] for h in hospitals_desc]
box_colors_reg = [REGION_COLORS[hosp_region[h]] for h in hospitals_cum_ordered]

fig_r = plt.figure(figsize=(26, 20))
gs_r = fig_r.add_gridspec(2, 2, height_ratios=[2, 2], width_ratios=[10, 1],
                           hspace=0.4, wspace=0.02)
ax_bar_r = fig_r.add_subplot(gs_r[0, 0])
ax_dist_r = fig_r.add_subplot(gs_r[0, 1], sharey=ax_bar_r)

gs_bottom_r = gs_r[1, :].subgridspec(1, 2, wspace=0.25)
ax_daily_r = fig_r.add_subplot(gs_bottom_r[0])
ax_weekly_r = fig_r.add_subplot(gs_bottom_r[1])

# Top-left: vertical bar chart
ax_bar_r.bar(positions, hosp_totals_desc.values, color=bar_colors_reg_desc, alpha=0.85)
ax_bar_r.set_xticks(positions)
ax_bar_r.set_xticklabels(hospitals_desc, rotation=90, ha="center", fontsize=7)
ax_bar_r.set_ylabel("Cumulative Total Trolley Count (2023-2025)", fontsize=11)
ax_bar_r.set_title("Cumulative Counts", fontsize=12)
ax_bar_r.yaxis.set_minor_locator(ticker.AutoMinorLocator())
ax_bar_r.grid(axis="y", alpha=0.3)
legend_handles_reg = [mpatches.Patch(color=REGION_COLORS[r], alpha=0.85, label=r)
                      for r in regions_unique]
ax_bar_r.legend(handles=legend_handles_reg, loc="upper right", fontsize=7)

# Top-right: aggregate vertical boxplot
ax_dist_r.boxplot(hosp_totals.values, vert=True, patch_artist=True,
                  boxprops=dict(facecolor="#CCCCCC", alpha=0.7),
                  medianprops=dict(color="black", linewidth=1.5),
                  flierprops=dict(marker="o", markersize=5, alpha=0.6),
                  widths=0.5)
ax_dist_r.set_xticklabels(["All"], fontsize=8)
ax_dist_r.tick_params(axis="y", labelleft=False)
ax_dist_r.set_title("Spread", fontsize=10)
ax_dist_r.grid(axis="y", alpha=0.3)

# Bottom-left: daily distribution box plots
bp_rd = ax_daily_r.boxplot(data_by_hosp_daily, vert=False, patch_artist=True,
                           positions=hpos,
                           medianprops=dict(color="black", linewidth=1.5),
                           flierprops=dict(marker=".", markersize=3, alpha=0.4),
                           widths=0.6)
for patch, color in zip(bp_rd["boxes"], box_colors_reg):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax_daily_r.set_ylim(0.4, n + 0.6)
ax_daily_r.set_yticks(hpos)
ax_daily_r.set_yticklabels(hospitals_cum_ordered, fontsize=7)
ax_daily_r.set_xlabel("Daily Total Trolley Count", fontsize=11)
ax_daily_r.set_title("Daily Distribution", fontsize=12)
ax_daily_r.xaxis.set_minor_locator(ticker.AutoMinorLocator())
ax_daily_r.grid(axis="x", alpha=0.3)

# Bottom-right: weekly distribution box plots
bp_rw = ax_weekly_r.boxplot(data_by_hosp_weekly, vert=False, patch_artist=True,
                            positions=hpos,
                            medianprops=dict(color="black", linewidth=1.5),
                            flierprops=dict(marker=".", markersize=3, alpha=0.4),
                            widths=0.6)
for patch, color in zip(bp_rw["boxes"], box_colors_reg):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax_weekly_r.set_ylim(0.4, n + 0.6)
ax_weekly_r.set_yticks(hpos)
ax_weekly_r.set_yticklabels([])
ax_weekly_r.set_xlabel("Weekly Total Trolley Count", fontsize=11)
ax_weekly_r.set_title("Weekly Distribution", fontsize=12)
ax_weekly_r.xaxis.set_minor_locator(ticker.AutoMinorLocator())
ax_weekly_r.grid(axis="x", alpha=0.3)

fig_r.tight_layout()
fig_r.subplots_adjust(top=0.94)
fig_r.suptitle("Trolley Counts by Hospital, Colour-Coded by Health Region (2023-2025)",
               fontsize=14, y=0.97)
fig_r.savefig(os.path.join(OUT_DIR, "hospital_trolley_cumulative_by_region.png"), dpi=200,
              bbox_inches="tight")
print(f"Saved region-coded plot  →  {OUT_DIR}/hospital_trolley_cumulative_by_region.png")
plt.close(fig_r)

# ── 4. Cumulative total trolley counts per region (2023-2025) ──────────────
region_totals = region_daily.groupby("Region")["Total"].sum().sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(12, max(5, len(region_totals) * 1.0)))
ax.barh(range(len(region_totals)), region_totals.values, color="#DD8452", alpha=0.8)
ax.set_yticks(range(len(region_totals)))
ax.set_yticklabels(region_totals.index, fontsize=10)
ax.set_xlabel("Cumulative Total Trolley Count (2023-2025)", fontsize=11)
ax.set_title("Cumulative Trolley Counts by Health Region (2023-2025)", fontsize=13)
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "region_trolley_cumulative.png"), dpi=200)
print(f"Saved region cumulative plot    →  {OUT_DIR}/region_trolley_cumulative.png")
plt.close(fig)

# ── Summary stats ───────────────────────────────────────────────────────────
print("\n── Hospital summary (top 10 by median) ──")
print(hosp_medians.sort_values(ascending=False).head(10).to_string())

print("\n── Region summary ──")
print(region_daily.groupby("Region")["Total"]
      .describe()
      .round(1)
      .sort_values("50%", ascending=False)
      .to_string())
