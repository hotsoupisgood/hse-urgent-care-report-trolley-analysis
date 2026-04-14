import numpy as np
import pandas as pd

from ..base import BaseModel
from ..ar import compute_ar2_fitted


class Model(BaseModel):

    @property
    def version(self):
        return 'v0.2'

    @property
    def name(self):
        return 'AR(2) Only'

    @property
    def jags_model_string(self):
        return """
        model{
          for(i in 1:I){
            y[i,1] ~ dnorm(alpha[i], tau[i])
            y[i,2] ~ dnorm(alpha[i] + phi1 * (y[i,1] - alpha[i]), tau[i])
            for(t in 3:T){
              y[i,t] ~ dnorm(alpha[i]
                              + phi1 * (y[i,t-1] - alpha[i])
                              + phi2 * (y[i,t-2] - alpha[i]), tau[i])
            }
            fullmod[i,1] <- alpha[i]
            fullmod[i,2] <- alpha[i] + phi1 * (y[i,1] - alpha[i])
            for(t in 3:T){
              fullmod[i,t] <- alpha[i]
                              + phi1 * (y[i,t-1] - alpha[i])
                              + phi2 * (y[i,t-2] - alpha[i])
            }
            for(t in 1:T){
              resid[i,t] <- y[i,t] - fullmod[i,t]
            }
            alpha[i] ~ dnorm(0, 0.001)
            tau[i]   ~ dgamma(0.001, 0.001)
          }
          phi1 ~ dunif(-1, 1)
          phi2 ~ dunif(-1, 1)
        }
        """

    @property
    def monitor_params(self):
        return ['alpha', 'tau', 'phi1', 'phi2']

    def jags_data(self, y, n_region, n_weeks, regions):
        return dict(y=y, I=n_region, T=n_weeks)

    def reconstruct_mu(self, raw_df, regions, n_weeks, indicators):
        """mu[i,t] = alpha[i] — constant intercept, no seasonality."""
        n_region = len(regions)
        mu_mean = np.zeros((n_weeks, n_region))
        mu_lower = np.zeros((n_weeks, n_region))
        mu_upper = np.zeros((n_weeks, n_region))
        for i in range(n_region):
            alpha_i = raw_df[f'alpha[{i + 1}]'].values
            mu_mean[:, i] = alpha_i.mean()
            mu_lower[:, i] = np.quantile(alpha_i, 0.025)
            mu_upper[:, i] = np.quantile(alpha_i, 0.975)
        return (pd.DataFrame(mu_mean, columns=regions),
                pd.DataFrame(mu_lower, columns=regions),
                pd.DataFrame(mu_upper, columns=regions))

    def compute_fitted(self, df_mu, df_og, raw_df):
        phi1_mean = raw_df['phi1'].mean()
        phi2_mean = raw_df['phi2'].mean()
        return compute_ar2_fitted(df_mu, df_og, phi1_mean, phi2_mean)
