import numpy as np
import pandas as pd

from ..base import BaseModel
from ..data import (
    build_event_indicators,
    build_ny_indicators_by_date,
    load_observed,
)
from ..significance import summarize_global_parameters

_EAST_REGIONS = {
    'HSE Dublin and Midlands',
    'HSE Dublin and North East',
    'HSE Dublin and South East',
}


class Model(BaseModel):

    @property
    def version(self):
        return 'v2.10'

    @property
    def name(self):
        return (
            'Baseline + AR(1) + Annual Cycle + Regional New Year (date-anchored)'
            '+ MW Reset (3 weeks + 2 post)'
            '+ East/West group mean decomposition (alpha = mu_ew[group] + epsilon)'
        )

    @property
    def jags_model_string(self):
        return """
        model{
          for(i in 1:I){
            y[i,1] ~ dnorm(mu[i,1], tau[i])
            for(t in 2:T){
              y[i,t] ~ dnorm(mu[i,t] +
              (phi * (y[i,t-1] - mu[i,t-1])), tau[i])
            }
            for(t in 1:T){
              mu[i,t] <- alpha[i] +
                         beta[i]       * cos((2 * pi) * (t/52)) +
                         gamma[i]      * sin((2 * pi) * (t/52)) +
                         delta_pm1[i]  * ny_pm1[t]  +
                         delta_pre[i]  * ny_pre[t]  +
                         delta_mid[i]  * ny_mid[t]  +
                         delta_post[i] * ny_post[t] +
                         sigma_w1     * fr3_w1[t] * mw[i] +
                         sigma_w2     * fr3_w2[t] * mw[i] +
                         sigma_w3     * fr3_w3[t] * mw[i] +
                         sigma_w4     * fr3_w4[t] * mw[i] +
                         sigma_w5     * fr3_w5[t] * mw[i]
            }
            fullmod[i,1] <- mu[i,1]
            for(t in 2:T){
              fullmod[i,t] <- mu[i,t] + phi * (y[i,t-1] - mu[i,t-1])
            }
            for(t in 1:T){
              resid[i,t] <- y[i,t] - fullmod[i,t]
            }
            alpha[i]      <- mu_ew[ew_group[i]] + epsilon[i]
            epsilon[i]    ~ dnorm(0, tau_alpha)
            beta[i]       ~ dnorm(0, 0.001)
            gamma[i]      ~ dnorm(0, 0.001)
            tau[i]        ~ dgamma(0.001, 0.001)
            delta_pm1[i]  ~ dnorm(0, 0.001)
            delta_pre[i]  ~ dnorm(0, 0.001)
            delta_mid[i]  ~ dnorm(0, 0.001)
            delta_post[i] ~ dnorm(0, 0.001)
          }
          for(s in 1:2){
            mu_ew[s] ~ dnorm(0, 0.001)
          }
          tau_alpha ~ dgamma(0.001, 0.001)
          delta_ew  <- mu_ew[2] - mu_ew[1]
          phi      ~ dunif(-1, 1)
          sigma_w1 ~ dnorm(0, 0.001)
          sigma_w2 ~ dnorm(0, 0.001)
          sigma_w3 ~ dnorm(0, 0.001)
          sigma_w4 ~ dnorm(0, 0.001)
          sigma_w5 ~ dnorm(0, 0.001)
        }
        """

    @property
    def monitor_params(self):
        return [
            'alpha', 'epsilon', 'mu_ew', 'tau_alpha', 'delta_ew',
            'beta', 'gamma', 'tau', 'phi',
            'delta_pm1', 'delta_pre', 'delta_mid', 'delta_post',
            'sigma_w1', 'sigma_w2', 'sigma_w3', 'sigma_w4', 'sigma_w5',
            'mu', 'fullmod', 'resid',
        ]

    def _load_data(self, data_path):
        df_og_wide, regions, n_region, n_weeks, y_matrix = load_observed(data_path)
        df_og = pd.DataFrame(df_og_wide.values.T.astype(float), columns=regions)
        indicators = build_event_indicators(n_weeks, regions)
        self._dates = list(df_og_wide.columns)
        self._regions = regions
        indicators.update(build_ny_indicators_by_date(self._dates))
        return df_og, regions, n_region, n_weeks, y_matrix, indicators

    def jags_data(self, y, n_region, n_weeks, regions):
        ev = build_event_indicators(n_weeks, regions)
        ny = build_ny_indicators_by_date(self._dates)
        ew_group = np.array(
            [1 if r in _EAST_REGIONS else 2 for r in regions],
            dtype=int,
        )
        return dict(
            y=y, I=n_region, T=n_weeks, pi=np.pi,
            ew_group=ew_group,
            ny_pm1=ny['ny_pm1'],
            ny_pre=ny['ny_pre'], ny_mid=ny['ny_mid'], ny_post=ny['ny_post'],
            fr3_w1=ev['fr3_w1'], fr3_w2=ev['fr3_w2'], fr3_w3=ev['fr3_w3'],
            fr3_w4=ev['fr3_w4'], fr3_w5=ev['fr3_w5'],
            mw=ev['mw'],
        )

    def extra_significance_tests(self, result, output_dir):
        raw_df = result.raw_df
        # delta_ew is the primary quantity of interest: West mean - East mean
        ew_params = ['delta_ew', 'mu_ew[1]', 'mu_ew[2]', 'tau_alpha']
        available = [p for p in ew_params if p in raw_df.columns]
        summarize_global_parameters(raw_df, available).to_csv(
            output_dir / 'ew_contrast.csv', index=False
        )
        # region-level deviations from group mean
        eps_params = [f'epsilon[{i+1}]' for i in range(result.n_region)]
        available_eps = [p for p in eps_params if p in raw_df.columns]
        if available_eps:
            df_eps = summarize_global_parameters(raw_df, available_eps)
            df_eps.insert(1, 'Region', result.regions)
            df_eps.insert(2, 'EW_group',
                          ['East' if r in _EAST_REGIONS else 'West'
                           for r in result.regions])
            df_eps.to_csv(output_dir / 'epsilon_by_region.csv', index=False)
