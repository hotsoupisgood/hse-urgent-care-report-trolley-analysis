# Modeling HSE daily trolly data
[hsereport.ie](https://hsereport.ie)

Project exploring the HSE Emergency Care Report Trolley data. Current aim is to fit autoregressive models for exploration. Long term goals involve applying a bayesian ranking model such as in [this paper](http://arxiv.org/abs/2510.14723).
Note: Currently the organization of the repo is a bit of a mess.

![Our poster presentation](./Poster/Poster_Presentation.png "Poster 2026/02/04")
## Exploratory analysis
* Using bayes/rJAGS: AR(1) model of weekly rate (per 10,000 people) with an annual cycle component

## Trolley rate scalings
The weekly regional trolley count is normalised under several denominators (response = trolleys per unit). These are the complete set of scalings, all in `data/wide_weekly_scaled*.csv`:
* `Per10k` — per 10,000 residents (baseline population normalisation)
* `Per1kOver65` — per 1,000 residents aged 65+
* `Per1k75plus` — per 1,000 residents aged 75+
* `Per1kUnder65` — per 1,000 residents aged under 65
* `Per1kMedicalCard` — per 1,000 medical-card holders
* `PerBed` — per 100 inpatient beds (system overcapacity)
* `PerBudgetThousands` — per €1 billion of regional HSE budget
* `Per100Cancellations` — per 100 hospital-initiated cancellations
* `surge_scaledPer10k` — surge-bed-days per 10,000 residents (a separate demand variable, not a trolley-response scaling)

Model fitting and the DIC scaling comparison use the first four (`Per10k`, `Per1kOver65`, `PerBed`, `PerBudgetThousands`). The rest are sensitivity and presentation variants.

## Data sources
* [Emergency care report](https://www2.hse.ie/services/urgent-emergency-care-report/)
* [Health region populations (Census 2022)](https://www.cso.ie/en/releasesandpublications/fp/fp-hhr/hsehealthregions2022/)
* [NUTS3 population estimates 2022-2025 (CSO PEA04)](https://www.cso.ie/en/releasesandpublications/ep/p-pme/populationandmigrationestimatesapril2025/data/)