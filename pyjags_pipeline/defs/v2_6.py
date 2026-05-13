import numpy as np

from ..base import BaseModel
from ..data import build_event_indicators


class Model(BaseModel):

    @property
    def version(self):
        return 'v2.6'

    @property
    def name(self):
        return 'Baseline + AR(1) + Annual Cycle + Regional New Year + MW Reset (3 weeks + 2 post)'

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
            alpha[i]      ~ dnorm(0, 0.001)
            beta[i]       ~ dnorm(0, 0.001)
            gamma[i]      ~ dnorm(0, 0.001)
            tau[i]        ~ dgamma(0.001, 0.001)
            delta_pre[i]  ~ dnorm(0, 0.001)
            delta_mid[i]  ~ dnorm(0, 0.001)
            delta_post[i] ~ dnorm(0, 0.001)
          }
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
        return ['alpha', 'beta', 'gamma', 'tau', 'phi',
                'delta_pre', 'delta_mid', 'delta_post',
                'sigma_w1', 'sigma_w2', 'sigma_w3', 'sigma_w4', 'sigma_w5',
                'mu', 'fullmod', 'resid']

    def jags_data(self, y, n_region, n_weeks, regions):
        ev = build_event_indicators(n_weeks, regions)
        return dict(
            y=y, I=n_region, T=n_weeks, pi=np.pi,
            ny_pre=ev['ny_pre'], ny_mid=ev['ny_mid'], ny_post=ev['ny_post'],
            fr3_w1=ev['fr3_w1'], fr3_w2=ev['fr3_w2'], fr3_w3=ev['fr3_w3'],
            fr3_w4=ev['fr3_w4'], fr3_w5=ev['fr3_w5'],
            mw=ev['mw'],
        )
