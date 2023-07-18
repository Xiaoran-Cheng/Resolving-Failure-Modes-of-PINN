import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from Transport_eq import Transport_eq

from jax import numpy as jnp
from jax import jacfwd
# from tqdm.notebook import tqdm
from tqdm import tqdm
import numpy as np
import pandas as pd
# from flax.core.frozen_dict import FrozenDict, unfreeze
from scipy.optimize import minimize
# import jaxlib.xla_extension as xla
import jax


class SQP_Optim:
    def __init__(self, model, feature, M, params, beta, data, sample_data, IC_sample_data, ui, N) -> None:
        self.model = model
        self.feature = feature
        self.M = M
        self.layer_names = params["params"].keys()
        self.beta = beta
        self.data = data
        self.sample_data = sample_data
        self.IC_sample_data = IC_sample_data
        self.ui = ui
        self.N = N
        shapes_and_sizes = [(p.shape, p.size) for p in jax.tree_util.tree_leaves(params)]
        self.shapes, self.sizes = zip(*shapes_and_sizes)
        self.indices = jnp.cumsum(jnp.array(self.sizes)[:-1])


    def obj(self, param_list, treedef, loss_values):
        params = self.unflatten_params(param_list, treedef)
        u_theta = self.model.u_theta(params=params, data=self.data)
        obj_value = 1 / self.N * jnp.square(jnp.linalg.norm(u_theta - self.ui, ord=2))
        loss_values.append(obj_value)
        return obj_value
    

    def grad_objective(self, param_list, treedef, loss_values):
        return jacfwd(self.obj, 0)(param_list, treedef, loss_values)


    def IC_cons(self, param_list, treedef):
        params = self.unflatten_params(param_list, treedef)
        u_theta = self.model.u_theta(params=params, data=self.IC_sample_data)
        return Transport_eq(beta=self.beta).solution(\
            self.IC_sample_data[:,0], self.IC_sample_data[:,1]) - u_theta
    
    
    def pde_cons(self, param_list, treedef):
        params = self.unflatten_params(param_list, treedef)
        grad_x = jacfwd(self.model.u_theta, 1)(params, self.sample_data)
        return Transport_eq(beta=self.beta).pde(jnp.diag(grad_x[:,:,0]),\
            jnp.diag(grad_x[:,:,1]))

    
    def eq_cons(self, param_list, treedef, eq_cons_loss_values):
        eq_cons = jnp.concatenate([self.IC_cons(param_list, treedef), self.pde_cons(param_list, treedef)])
        eq_cons_loss = jnp.square(jnp.linalg.norm(eq_cons, ord=2))
        eq_cons_loss_values.append(eq_cons_loss)
        return eq_cons
    

    def grads_eq_cons(self, param_list, treedef, eq_cons_loss_values):
        eq_cons_jac = jacfwd(self.eq_cons, 0)(param_list, treedef, eq_cons_loss_values)
        return eq_cons_jac

    # def get_li_in_eq_cons_index(self, param_list, treedef, eq_cons_loss_values):
    #     eq_cons_jac = jacfwd(self.eq_cons, 0)(param_list, treedef, eq_cons_loss_values)
    #     li_in_cons_index = self.get_li_in_cons_index(eq_cons_jac, 1e-5)
    #     return li_in_cons_index


    # def get_li_in_eq_cons(self, param_list, li_in_cons_index, treedef, eq_cons_loss_values):
    #     li_in_cons_index = self.get_li_in_eq_cons_index(param_list, treedef, eq_cons_loss_values)
    #     eq_cons = self.eq_cons(param_list, treedef, eq_cons_loss_values)
    #     return eq_cons[li_in_cons_index]


    # def get_li_in_eq_grads(self, param_list, li_in_cons_index, treedef, eq_cons_loss_values):
    #     eq_cons_jac = jacfwd(self.eq_cons, 0)(param_list, treedef, eq_cons_loss_values)
    #     li_in_cons_index = self.get_li_in_eq_cons_index(param_list, treedef, eq_cons_loss_values)
    #     return eq_cons_jac[li_in_cons_index, :]


    def flatten_params(self, params):
        flat_params_list, treedef = jax.tree_util.tree_flatten(params)
        return np.concatenate([param.ravel( ) for param in flat_params_list], axis=0), treedef
    
    # def flat_single_dict(self, dicts):
    #     return np.concatenate(pd.DataFrame.from_dict(unfreeze(dicts["params"])).\
    #                     applymap(lambda x: x.flatten()).values.flatten())


    def unflatten_params(self, param_list, treedef):
        param_groups = jnp.split(param_list, self.indices)
        reshaped_params = [group.reshape(shape) for group, shape in zip(param_groups, self.shapes)]
        return jax.tree_util.tree_unflatten(treedef, reshaped_params)


    # def get_li_in_cons_index(self, mat, qr_ind_tol):
    #     _, R = jnp.linalg.qr(mat)
    #     independent = jnp.where(jnp.abs(R.diagonal()) > qr_ind_tol)[0]
    #     return independent


    def SQP_optim(self, params, loss_values, eq_cons_loss_values, maxiter):
        flat_params, treedef = self.flatten_params(params)
        # li_in_cons_index = self.get_li_in_eq_cons_index(flat_params, treedef, eq_cons_loss_values)
        constraints = {
            'type': 'eq',
            'fun': self.eq_cons,
            'jac': self.grads_eq_cons,
            'args': (treedef, eq_cons_loss_values)}
        solution = minimize(self.obj, \
                            flat_params, \
                            args=(treedef,loss_values), \
                            jac=self.grad_objective, \
                            method='trust-constr', \
                            options={'maxiter': maxiter}, \
                            constraints=constraints)
        params_opt = self.unflatten_params(solution.x, treedef)
        print(solution)
        return params_opt


    def evaluation(self, params, data, ui):
        n = data.shape[0]
        u_theta = self.model.u_theta(params=params, data=data)
        absolute_error = 1/n * jnp.linalg.norm(u_theta-ui, ord = 2)
        l2_relative_error = 1/n * (jnp.linalg.norm((u_theta-ui), ord = 2) / jnp.linalg.norm((ui), ord = 2))
        return absolute_error, l2_relative_error, u_theta
 



