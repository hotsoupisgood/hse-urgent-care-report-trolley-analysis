# Modeling HSE daily trolly data
[hsereport.ie](https://hsereport.ie)

Project exploring the HSE Emergency Care Report Trolley data. Current aim is to fit autoregressive models for exploration. Long term goals involve applying a bayesian ranking model such as in [this paper](http://arxiv.org/abs/2510.14723).
Note: Currently the organization of the repo is a bit of a mess.

![Our poster presentation](./Poster/Poster_Presentation.png "Poster 2026/02/04")
## Exploratory analysis
* Using bayes/rJAGS: AR(1) model of weekly rate (per 10,000 people) with an annual cycle component
## Data sources
* [Emergency care report](https://www2.hse.ie/services/urgent-emergency-care-report/)
* [Health region populations (Census 2022)](https://www.cso.ie/en/releasesandpublications/fp/fp-hhr/hsehealthregions2022/)
* [NUTS3 population estimates 2022-2025 (CSO PEA04)](https://www.cso.ie/en/releasesandpublications/ep/p-pme/populationandmigrationestimatesapril2025/data/)