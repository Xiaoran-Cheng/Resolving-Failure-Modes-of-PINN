import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from System import Transport_eq

from jax import numpy as jnp
from jax import jacfwd
import pandas as pd
import numpy as np
from flax.core.frozen_dict import unfreeze



class NewAugLag:
    def __init__(self, model, data, sample_data, IC_sample_data, BC_sample_data, ui, beta, N, M):
        self.model = model
        self.beta = beta
        self.data = data
        self.sample_data = sample_data
        self.IC_sample_data = IC_sample_data
        self.BC_sample_data = BC_sample_data
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
    
    
    def BC_cons(self, params):
        u_theta = self.model.u_theta(params=params, data=self.BC_sample_data)
        return Transport_eq(beta=self.beta).solution(\
            self.BC_sample_data[:,0], self.BC_sample_data[:,1]) - u_theta
    
    
    def pde_cons(self, params):
        grad_x = jacfwd(self.model.u_theta, 1)(params, self.sample_data)
        return Transport_eq(beta=self.beta).pde(jnp.diag(grad_x[:,:,0]),\
            jnp.diag(grad_x[:,:,1]))
    

    def eq_cons(self, params):
        return jnp.concatenate([self.IC_cons(params), self.BC_cons(params), self.pde_cons(params)])
    

    def eq_cons_loss(self, params):
        return  jnp.square(jnp.linalg.norm(self.eq_cons(params), ord=2))


    def L(self, params_mul):
        params, mul = params_mul
        return self.l_k(params) + self.eq_cons(params) @ mul
    
    
    def flat_single_dict(self, dicts):
        return np.concatenate(pd.DataFrame.from_dict(unfreeze(dicts["params"])).\
                        applymap(lambda x: x.primal.flatten()).values.flatten())
    

    def flat_multi_dict(self, dicts, group_labels):
        return np.concatenate(pd.DataFrame.from_dict(\
                unfreeze(dicts['params'])).\
                    apply(lambda x: x.explode()).set_index([group_labels]).\
                        sort_index().applymap(lambda x: x.primal.flatten()).values.flatten())
        

    def loss(self, params_mul, penalty_param, alpha, group_labels):
        params, mul = params_mul
        grads_fx = self.flat_single_dict(jacfwd(self.l_k, 0)(params))
        Mx = alpha
        gra_eq_cons = jnp.array(jnp.split(self.flat_multi_dict(jacfwd(self.eq_cons, 0)(params), group_labels), self.M))
        second_penalty_part = jnp.square(jnp.linalg.norm(Mx * (grads_fx + (gra_eq_cons.T @ mul)), ord=2))
        return self.L(params_mul) + penalty_param * self.eq_cons_loss(params) + second_penalty_part


