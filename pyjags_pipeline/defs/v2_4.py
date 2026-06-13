import numpy as np

from ..base import BaseModel
from ..data import build_event_indicators


class Model(BaseModel):

    @property
    def version(self):
        return 'v2.4'

    @property
    def name(self):
        return 'Baseline + AR(1) + Annual Cycle + MW Reset'

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
                         psi_pre   * fr_pre[t]  * mw[i] +
                         psi_mid   * fr_mid[t]  * mw[i] +
                         psi_post  * fr_post[t] * mw[i]
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
          psi_pre  ~ dnorm(0, 0.001)
          psi_mid  ~ dnorm(0, 0.001)
          psi_post ~ dnorm(0, 0.001)
        }
        """

    @property
    def monitor_params(self):
        return ['alpha', 'beta', 'gamma', 'tau', 'phi',
                'psi_pre', 'psi_mid', 'psi_post',
                'mu', 'fullmod', 'resid']

    def jags_data(self, y, n_region, n_weeks, regions):
        ev = build_event_indicators(n_weeks, regions)
        return dict(
            y=y, I=n_region, T=n_weeks, pi=np.pi,
            fr_pre=ev['fr_pre'], fr_mid=ev['fr_mid'], fr_post=ev['fr_post'],
            mw=ev['mw'],
        )

