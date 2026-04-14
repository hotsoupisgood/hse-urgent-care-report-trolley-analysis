---
title: "Model V6 — Hospital Density Moderating Seasonal Amplitude"
output:
  pdf_document: default
---

Model V6 extends V3 by testing whether ED hospital density moderates the
*seasonal amplitude* rather than the baseline level. The hypothesis: regions
with more EDs per capita can better absorb winter surges by spreading the
load across facilities, resulting in a dampened seasonal swing in trolley
rates.

Hierarchical priors on seasonal coefficients:

$$\beta_i \sim \mathcal{N}(\mu_\beta + \eta_\beta \cdot h_i,\; \tau_\beta)$$
$$\gamma_i \sim \mathcal{N}(\mu_\gamma + \eta_\gamma \cdot h_i,\; \tau_\gamma)$$

where $h_i$ is the ED hospital density (per 10k population) for region $i$.

The seasonal amplitude is $A_i = \sqrt{\beta_i^2 + \gamma_i^2}$. If
$\eta_\beta$ and $\eta_\gamma$ shift the coefficients toward zero as $h_i$
increases, hospital density dampens the seasonal cycle.


``` r
library(rjags)
```

```
## Loading required package: coda
```

```
## Linked to JAGS 4.3.2
```

```
## Loaded modules: basemod,bugs
```

``` r
library(dplyr)
```

```
## 
## Attaching package: 'dplyr'
```

```
## The following objects are masked from 'package:stats':
## 
##     filter, lag
```

```
## The following objects are masked from 'package:base':
## 
##     intersect, setdiff, setequal, union
```

``` r
library(tibble)
library(stringr)
library(ggplot2)
library(tidyr)

output_folder <- "../data/models/v6/"
save_output   <- TRUE
if (save_output) dir.create(output_folder, recursive = TRUE, showWarnings = FALSE)
```

### Load Data


``` r
uecDf    <- read.csv('../data/wide_weekly_scaledPer10k.csv')
regions  <- uecDf$Region
n.region <- length(regions)
uecDf    <- uecDf %>% select(-Region)
n.weeks  <- length(names(uecDf))
uecMat   <- as.matrix(uecDf)
```

### ED Hospitals Per 10k Population


``` r
hpr_df <- read.csv('../data/hospitals_per_region.csv')

# Align to region order from uecDf
ed_hosp_per10k <- hpr_df$EDHospitalsPer10k[match(regions, hpr_df$Region)]

# Center for reduced posterior correlation
hosp_centered <- ed_hosp_per10k - mean(ed_hosp_per10k)

data.frame(
  Region       = regions,
  EDHospPer10k = round(ed_hosp_per10k, 4),
  HospCentered = round(hosp_centered, 6)
)
```

```
##                      Region EDHospPer10k HospCentered
## 1   HSE Dublin and Midlands       0.0835     0.010632
## 2 HSE Dublin and North East       0.0590    -0.013916
## 3 HSE Dublin and South East       0.0515    -0.021396
## 4              HSE Mid West       0.0968     0.023954
## 5            HSE South West       0.0675    -0.005373
## 6   HSE West and North West       0.0790     0.006099
```

### Model V6 Specification

Key change from V3: $\beta_i$ and $\gamma_i$ get hierarchical priors with
hospital density as a covariate, instead of flat uninformative priors.


``` r
model <-
"
model{
  for(i in 1:I){
    #------------
    # Likelihood
    #------------
    y[i,1] ~ dnorm(mu[i,1], tau[i])
    for(t in 2:T){
      y[i,t] ~ dnorm(mu[i,t] + (phi * (y[i,t-1] - mu[i,t-1])), tau[i])
    }

    # Mean function (same structure as V3)
    for(t in 1:T){
      mu[i,t] <- alpha[i] +
                 beta[i]       * cos((2 * pi) * (t/52)) +
                 gamma[i]      * sin((2 * pi) * (t/52)) +
                 delta_pre[i]  * ny_pre[t]  +
                 delta_mid[i]  * ny_mid[t]  +
                 delta_post[i] * ny_post[t] +
                 sigma_pre     * fr_pre[t]  * mw[i] +
                 sigma_mid     * fr_mid[t]  * mw[i] +
                 sigma_post    * fr_post[t] * mw[i]
    }

    # Priors
    alpha[i] ~ dnorm(0, 0.001)
    tau[i]   ~ dgamma(0.001, 0.001)
    delta_pre[i]  ~ dnorm(0, 0.001)
    delta_mid[i]  ~ dnorm(0, 0.001)
    delta_post[i] ~ dnorm(0, 0.001)

    # Hierarchical seasonal coefficients: hospital density moderates amplitude
    beta[i]  ~ dnorm(mu_beta  + eta_beta  * hosp_c[i], tau_beta)
    gamma[i] ~ dnorm(mu_gamma + eta_gamma * hosp_c[i], tau_gamma)
  }

  phi        ~ dunif(-1, 1)
  sigma_pre  ~ dnorm(0, 0.001)
  sigma_mid  ~ dnorm(0, 0.001)
  sigma_post ~ dnorm(0, 0.001)

  # Hyperpriors for seasonal hierarchy
  mu_beta    ~ dnorm(0, 0.001)
  mu_gamma   ~ dnorm(0, 0.001)
  eta_beta   ~ dnorm(0, 0.001)
  eta_gamma  ~ dnorm(0, 0.001)
  tau_beta   ~ dgamma(0.001, 0.001)
  tau_gamma  ~ dgamma(0.001, 0.001)
}
"

# Event indicators (same as V3)
week_mod <- (1:n.weeks) %% 52
ny_pre   <- as.numeric(week_mod == 0)
ny_mid   <- as.numeric(week_mod == 1)
ny_post  <- as.numeric(week_mod == 2)
fr_pre   <- as.numeric((1:n.weeks) == 86)
fr_mid   <- as.numeric((1:n.weeks) == 87)
fr_post  <- as.numeric((1:n.weeks) == 88)
mw       <- as.numeric(regions == "HSE Mid West")
```

### Fit


``` r
exp_jags <- jags.model(
  textConnection(model),
  data = list(
    y       = uecMat,
    I       = n.region,
    T       = n.weeks,
    pi      = pi,
    hosp_c  = hosp_centered,
    ny_pre  = ny_pre,
    ny_mid  = ny_mid,
    ny_post = ny_post,
    fr_pre  = fr_pre,
    fr_mid  = fr_mid,
    fr_post = fr_post,
    mw      = mw
  ),
  n.chains = 4
)
```

```
## Compiling model graph
##    Resolving undeclared variables
##    Allocating nodes
## Graph information:
##    Observed stochastic nodes: 906
##    Unobserved stochastic nodes: 52
##    Total graph size: 6064
## 
## Initializing model
```

``` r
update(exp_jags, n.iter = 10000)

model_parameters <- c(
  "alpha", "beta", "gamma", "tau", "phi",
  "delta_pre", "delta_mid", "delta_post",
  "sigma_pre", "sigma_mid", "sigma_post",
  "mu_beta", "mu_gamma",
  "eta_beta", "eta_gamma",
  "tau_beta", "tau_gamma"
)

exp_sim <- coda.samples(
  model          = exp_jags,
  variable.names = model_parameters,
  n.iter         = 20000
)
```

### Convergence


``` r
gelman_results <- gelman.diag(exp_sim, multivariate = FALSE)
gelman_results
```

```
## Potential scale reduction factors:
## 
##               Point est. Upper C.I.
## alpha[1]               1       1.00
## alpha[2]               1       1.00
## alpha[3]               1       1.00
## alpha[4]               1       1.00
## alpha[5]               1       1.00
## alpha[6]               1       1.00
## beta[1]                1       1.00
## beta[2]                1       1.00
## beta[3]                1       1.00
## beta[4]                1       1.01
## beta[5]                1       1.00
## beta[6]                1       1.00
## delta_mid[1]           1       1.00
## delta_mid[2]           1       1.00
## delta_mid[3]           1       1.00
## delta_mid[4]           1       1.00
## delta_mid[5]           1       1.00
## delta_mid[6]           1       1.00
## delta_post[1]          1       1.00
## delta_post[2]          1       1.00
## delta_post[3]          1       1.00
## delta_post[4]          1       1.00
## delta_post[5]          1       1.00
## delta_post[6]          1       1.00
## delta_pre[1]           1       1.00
## delta_pre[2]           1       1.00
## delta_pre[3]           1       1.00
## delta_pre[4]           1       1.00
## delta_pre[5]           1       1.00
## delta_pre[6]           1       1.00
## eta_beta               1       1.00
## eta_gamma              1       1.00
## gamma[1]               1       1.00
## gamma[2]               1       1.00
## gamma[3]               1       1.00
## gamma[4]               1       1.00
## gamma[5]               1       1.00
## gamma[6]               1       1.00
## mu_beta                1       1.00
## mu_gamma               1       1.00
## phi                    1       1.00
## sigma_mid              1       1.00
## sigma_post             1       1.00
## sigma_pre              1       1.00
## tau[1]                 1       1.00
## tau[2]                 1       1.00
## tau[3]                 1       1.00
## tau[4]                 1       1.00
## tau[5]                 1       1.00
## tau[6]                 1       1.00
## tau_beta               1       1.00
## tau_gamma              1       1.00
```

``` r
if (save_output) {
  write.csv(
    as.data.frame(gelman_results$psrf) %>% rownames_to_column("param"),
    paste0(output_folder, "gelman.csv"),
    row.names = FALSE
  )
}
```

### DIC


``` r
dic_v6 <- dic.samples(exp_jags, n.iter = 20000)
dic_v6
```

```
## Mean deviance:  2275 
## penalty 40.53 
## Penalized deviance: 2316
```

``` r
df_dic <- data.frame(
  deviance = sum(dic_v6$deviance),
  penalty  = sum(dic_v6$penalty),
  DIC      = sum(dic_v6$deviance) + sum(dic_v6$penalty)
)
df_dic
```

```
##   deviance  penalty      DIC
## 1 2275.135 40.52796 2315.663
```

``` r
if (save_output) write.csv(df_dic, paste0(output_folder, "dic.csv"), row.names = FALSE)
```

### Interpretation

Key parameters to examine:

- **`eta_beta`**: If the 95% credible interval excludes zero, hospital
  density significantly moderates the cosine (peak-timing) component of
  seasonality.
- **`eta_gamma`**: Same for the sine component.
- **Direction**: Negative values for both suggest higher hospital density
  dampens the seasonal swing (more EDs absorb winter surges better).

Post-hoc: compute the posterior seasonal amplitude per region as
$A_i = \sqrt{\beta_i^2 + \gamma_i^2}$ and check whether it correlates with
hospital density.

### Save


``` r
if (save_output) {
  samples_with_chain = do.call(rbind, lapply(seq_along(exp_sim), function(ch) {
    df = as.data.frame(exp_sim[[ch]])
    df$chain = ch
    df
  }))
  write.csv(samples_with_chain,
            paste0(output_folder, "raw_samples.csv"),
            row.names = FALSE)
}
```
