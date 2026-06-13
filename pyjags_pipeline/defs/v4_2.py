import numpy as np

from ..base import BaseModel


class Model(BaseModel):

    @property
    def version(self):
        return 'v4.2'

    @property
    def name(self):
        return 'Baseline + Annual Cycle'

    @property
    def jags_model_string(self):
        return """
        model{
          for(i in 1:I){
            for(t in 1:T){
              y[i,t] ~ dnorm(mu[i,t], tau[i])
            }
            for(t in 1:T){
              mu[i,t] <- alpha[i] +
                         beta[i]  * cos((2 * pi) * (t/52)) +
                         gamma[i] * sin((2 * pi) * (t/52))
            }
            for(t in 1:T){
              fullmod[i,t] <- mu[i,t]
            }
            for(t in 1:T){
              resid[i,t] <- y[i,t] - fullmod[i,t]
            }
            alpha[i] ~ dnorm(0, 0.001)
            beta[i]  ~ dnorm(0, 0.001)
            gamma[i] ~ dnorm(0, 0.001)
            tau[i]   ~ dgamma(0.001, 0.001)
          }
        }
        """

    @property
    def monitor_params(self):
        return ['alpha', 'beta', 'gamma', 'tau', 'mu', 'fullmod', 'resid']

    def jags_data(self, y, n_region, n_weeks, regions):
        return dict(y=y, I=n_region, T=n_weeks, pi=np.pi)
