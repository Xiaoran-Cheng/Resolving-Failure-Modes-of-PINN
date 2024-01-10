import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from System import Transport_eq

from jax import numpy as jnp
from jax import jacfwd
import numpy as np
import pandas as pd
from flax.core.frozen_dict import FrozenDict, unfreeze



class PilloPenalty:
    def __init__(self, model, data, sample_data, IC_sample_data, ui, beta, N, M):
        self.model = model
        self.beta = beta
        self.data = data
        self.sample_data = sample_data
        self.IC_sample_data = IC_sample_data
        self.ui = ui
        self.N = N
        self.M = M


    def l_k(self, params):
        u_theta = self.model.u_theta(params=params, data=self.data)
        return 1 / self.N * jnp.square(jnp.linalg.norm(u_theta - self.ui, ord=2))
    

    def IC_cons(self, params):
        u_theta = self.model.u_theta(params=params, data=self.IC_sample_data)
        return Transport_eq(beta=self.beta).solution(\
            self.IC_sample_data[:,0], self.IC_sample_data[:,1]) - u_theta
    
    
    def pde_cons(self, params):
        grad_x = jacfwd(self.model.u_theta, 1)(params, self.sample_data)
        return Transport_eq(beta=self.beta).pde(jnp.diag(grad_x[:,:,0]),\
            jnp.diag(grad_x[:,:,1]))
    

    def eq_cons(self, params):
        return jnp.concatenate([self.IC_cons(params), self.pde_cons(params)])
    

    def eq_cons_loss(self, params):
        return jnp.square(jnp.linalg.norm(self.eq_cons(params), ord=2))
    

    def L(self, params, mul):
        return self.l_k(params) - self.eq_cons(params) @ mul
    

    def flat_single_dict(self, dicts):
        return np.concatenate(pd.DataFrame.from_dict(unfreeze(dicts["params"])).\
                        applymap(lambda x: x.primal.flatten()).values.flatten())
    

    def get_mul_obj(self, params, mul, penalty_param_for_mul):
        # grad_L_norm = pd.DataFrame.from_dict(unfreeze(jacfwd(self.L, 0)(params, mul)["params"])).\
        #     applymap(lambda x: jnp.linalg.norm(x,ord=2)).values.sum()
        # sx = jnp.square(jnp.linalg.norm(self.eq_cons(params),ord=2))
        # mul_norm = jnp.square(jnp.linalg.norm(mul, ord=2))
        grad_L_norm = jnp.square(jnp.linalg.norm(self.flat_single_dict(jacfwd(self.L, 0)(params, mul)), ord=2))
        sx = jnp.square(jnp.linalg.norm(self.eq_cons(params),ord=2))
        mul_norm = jnp.square(jnp.linalg.norm(mul, ord=2))
        # print((grad_L_norm + penalty_param_for_mul * sx * mul_norm).primal)
        return grad_L_norm + penalty_param_for_mul * sx * mul_norm
             
        
    def loss(self, params, mul, penalty_param):
        return self.L(params, mul) +  0.5 * penalty_param * self.eq_cons_loss(params)
    