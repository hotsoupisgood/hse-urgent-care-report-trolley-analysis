"""
Compute the 65+ share of population vs share of hospital discharges, Ireland 2022.

Lives in thesis/supporting_scripts/. Reads the two CSV inputs from the repo's
"supplementary data" folder (two levels up) and writes the result back there.
Discharges are inpatient + day case, NOT emergency department attendances.

Run:  python3 build_discharge_age_summary.py
"""

import re
from pathlib import Path
import pandas as pd

DATA = Path(__file__).parents[2] / "supplementary data"
YEAR = 2022
OVER_65 = ["65 - 74 years", "75 - 84 years", "85 years and over"]


def age_to_band(label):
    """'Under 1 year' -> 0, '100 years and over' -> 100, '37 years' -> 37, then bin to a DHA74 band."""
    age = 0 if label.startswith("Under 1") else int(re.match(r"(\d+)", label).group(1))
    upper = [14, 24, 34, 44, 54, 64, 74, 84]
    names = ["0 - 14 years", "15 - 24 years", "25 - 34 years", "35 - 44 years",
             "45 - 54 years", "55 - 64 years", "65 - 74 years", "75 - 84 years"]
    for cut, name in zip(upper, names):
        if age <= cut:
            return name
    return "85 years and over"


# Discharge counts per DHA74 band (CSO DHA74, 2022)
discharges = pd.read_csv(DATA / "2022_discharge_count_age.csv")
discharges = discharges[discharges["Year"] == YEAR].set_index("Age Group")["VALUE"]

# Population per DHA74 band, binned from Census single-year-of-age (CSO FY006B, 2022)
census = pd.read_csv(DATA / "FY006B.20260602T200616.csv")
census = census[census["Single Year of Age"] != "All ages"].copy()
census["band"] = census["Single Year of Age"].map(age_to_band)
pop = census.groupby("band")["VALUE"].sum()

# 65+ shares
df = pd.DataFrame({"discharges": discharges, "population": pop})
df["group"] = ["65plus" if band in OVER_65 else "under65" for band in df.index]
g = df.groupby("group")[["population", "discharges"]].sum()
pop_share_over = g.loc["65plus", "population"] / g["population"].sum() * 100
dis_share_over = g.loc["65plus", "discharges"] / g["discharges"].sum() * 100

summary = pd.DataFrame(
    [("65plus_pop_share_pct", round(pop_share_over, 1)),
     ("65plus_discharge_share_pct", round(dis_share_over, 1))],
    columns=["metric", "value"],
)
out = DATA / "discharge_age_65plus_vs_under65.csv"
summary.to_csv(out, index=False)

print(f"65+ = {pop_share_over:.1f}% of people but {dis_share_over:.1f}% of discharges (Ireland {YEAR})")
print(f"Wrote {out}")
