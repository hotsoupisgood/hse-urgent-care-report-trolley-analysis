from ..base import BaseModel


class Model(BaseModel):

    @property
    def version(self):
        return 'v0.1'

    @property
    def name(self):
        return 'Baseline + AR(1)'

    @property
    def jags_model_string(self):
        return """
        model{
          for(i in 1:I){
            y[i,1] ~ dnorm(alpha[i], tau[i])
            for(t in 2:T){
              y[i,t] ~ dnorm(alpha[i] + phi * (y[i,t-1] - alpha[i]), tau[i])
            }
            for(t in 1:T){
              mu[i,t] <- alpha[i]
            }
            fullmod[i,1] <- alpha[i]
            for(t in 2:T){
              fullmod[i,t] <- alpha[i] + phi * (y[i,t-1] - alpha[i])
            }
            for(t in 1:T){
              resid[i,t] <- y[i,t] - fullmod[i,t]
            }
            alpha[i] ~ dnorm(0, 0.001)
            tau[i]   ~ dgamma(0.001, 0.001)
          }
          phi ~ dunif(-1, 1)
        }
        """

    @property
    def monitor_params(self):
        return ['alpha', 'tau', 'phi', 'mu', 'fullmod', 'resid']

    def jags_data(self, y, n_region, n_weeks, regions):
        return dict(y=y, I=n_region, T=n_weeks)
