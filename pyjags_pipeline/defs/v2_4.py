import numpy as np
import pandas as pd

from ..base import BaseModel
from ..ar import compute_ar1_fitted
from ..data import build_event_indicators


class Model(BaseModel):

    @property
    def version(self):
        return 'v2.4'

    @property
    def name(self):
        return 'V1.1 + MW Reset Only'

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
                         beta[i]      * cos((2 * pi) * (t/52)) +
                         gamma[i]     * sin((2 * pi) * (t/52)) +
                         sigma_pre   * fr_pre[t]  * mw[i] +
                         sigma_mid   * fr_mid[t]  * mw[i] +
                         sigma_post  * fr_post[t] * mw[i]
            }
            fullmod[i,1] <- mu[i,1]
            for(t in 2:T){
              fullmod[i,t] <- mu[i,t] + phi * (y[i,t-1] - mu[i,t-1])
            }
            for(t in 1:T){
              resid[i,t] <- y[i,t] - fullmod[i,t]
            }
            alpha[i] ~ dnorm(0, 0.001)
            beta[i]  ~ dnorm(0, 0.001)
            gamma[i] ~ dnorm(0, 0.001)
            tau[i]   ~ dgamma(0.001, 0.001)
          }
          phi ~ dunif(-1, 1)
          sigma_pre  ~ dnorm(0, 0.001)
          sigma_mid  ~ dnorm(0, 0.001)
          sigma_post ~ dnorm(0, 0.001)
        }
        """

    @property
    def monitor_params(self):
        return ['alpha', 'beta', 'gamma', 'tau', 'phi',
                'sigma_pre', 'sigma_mid', 'sigma_post',
                'mu', 'fullmod', 'resid']

    def jags_data(self, y, n_region, n_weeks, regions):
        ev = build_event_indicators(n_weeks, regions)
        return dict(
            y=y, I=n_region, T=n_weeks, pi=np.pi,
            fr_pre=ev['fr_pre'], fr_mid=ev['fr_mid'], fr_post=ev['fr_post'],
            mw=ev['mw'],
        )

    def reconstruct_mu(self, raw_df, regions, n_weeks, indicators):
        n_region = len(regions)
        ev = indicators
        mu_mean = np.zeros((n_weeks, n_region))
        mu_lower = np.zeros((n_weeks, n_region))
        mu_upper = np.zeros((n_weeks, n_region))
        for i in range(n_region):
            mu_i = (raw_df[f'alpha[{i+1}]'].values[:,None]
                    + raw_df[f'beta[{i+1}]'].values[:,None] * ev['cos_t'][None,:]
                    + raw_df[f'gamma[{i+1}]'].values[:,None] * ev['sin_t'][None,:]
                    + raw_df['sigma_pre'].values[:,None] * (ev['fr_pre'] * ev['mw'][i])[None,:]
                    + raw_df['sigma_mid'].values[:,None] * (ev['fr_mid'] * ev['mw'][i])[None,:]
                    + raw_df['sigma_post'].values[:,None] * (ev['fr_post'] * ev['mw'][i])[None,:])
            mu_mean[:,i] = mu_i.mean(axis=0)
            mu_lower[:,i] = np.quantile(mu_i, 0.025, axis=0)
            mu_upper[:,i] = np.quantile(mu_i, 0.975, axis=0)
        return (pd.DataFrame(mu_mean, columns=regions),
                pd.DataFrame(mu_lower, columns=regions),
                pd.DataFrame(mu_upper, columns=regions))

    def compute_fitted(self, df_mu, df_og, raw_df):
        phi_mean = raw_df['phi'].mean()
        return compute_ar1_fitted(df_mu, df_og, phi_mean)
