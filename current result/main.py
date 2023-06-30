import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from PINN_experiment.optim_PINN import PINN
from l1_Penalty_experiment.optim_l1_penalty import l1Penalty
from l2_Penalty_experiment.optim_l2_penalty import l2Penalty
from linfinity_Penalty_experiment.optim_linfinity_penalty import linfinityPenalty
from Han_Penalty_experiment.optim_han_penalty import HanPenalty
from Cubic_Penalty_experiment.optim_cubic_penalty import CubicPenalty
from Augmented_Lag_experiment.optim_aug_lag import AugLag
from Pillo_Penalty_experiment.optim_pillo_penalty import PilloPenalty
from SQP_experiment.optim_sqp import OptimComponents, SQP_Optim
from New_Augmented_Lag_experiment.optim_new_aug_lag import NewAugLag
from Fletcher_Penalty_experiment.optim_fletcher_penalty import FletcherPenalty

from data import Data
from NN import NN
from DataLoader import DataLoader
from Visualization import Visualization
from uncons_opt import Optim


from jax import random
import pandas as pd
from jax import numpy as jnp
from flax import linen as nn
from jaxopt import EqualityConstrainedQP
from multiprocessing import Pool






def mains(experiment_num):
    experiment = experiment_num[0]
    activation_input = experiment_num[1]

    n = 0
    current_dir = os.getcwd().replace("\\", "/")

    beta_list = [10**-4, 30]
    # beta_list = [10**-4]
    N=100 #change
    M=100 #change
    group_labels = list(range(1,2*M+1)) * 2
    data_key_num = 1000 #change
    dim = 2
    Datas = Data(N=N, M=M, key_num=data_key_num, dim=dim)
    dataloader = DataLoader(Data=Datas)

    x_data_min = 0 #change
    x_data_max = 2*jnp.pi #change
    t_data_min = 0 #change
    t_data_max = 1 #change
    x_sample_min = 0 #change
    x_sample_max = 2*jnp.pi #change
    t_sample_min = 0 #change
    t_sample_max = 1 #change

    evaluation_data_key_num = 256 #change
    eval_Datas = Data(N=N, M=M, key_num=evaluation_data_key_num, dim=dim)
    eval_dataloader = DataLoader(Data=eval_Datas)

    NN_key_num = 345  #change
    key = random.PRNGKey(NN_key_num)
    features = [2, 3, 1]  #change

    qp = EqualityConstrainedQP()
    visual = Visualization(current_dir)

    penalty_param_update_factor = 1.01
    penalty_param = 1
    mul = jnp.ones(2*M)
    mul_num_echos = 10
    uncons_optim_num_echos = 3000 #change
    uncons_optim_learning_rate = 0.001 #change
    SQP_num_iter = 10
    alpha = 150
    cons_violation = 10



    # for experiment in ['PINN_experiment', \
    #                     'l1_Penalty_experiment', \
    #                     'l2_Penalty_experiment', \
    #                     'linfinity_Penalty_experiment', \
    #                     'Cubic_Penalty_experiment', \
    #                     'Han_penalty_experiment', \
    #                     'Augmented_Lag_experiment', \    #得有increase penalty param
    #                     'Pillo_Penalty_experiment', \
    #                     'New_Augmented_Lag_experiment',\  #问题
    #                     'Fletcher_Penalty_experiment', \  #问题
    #                     'SQP_experiment']:

    # for experiment in ['Han_penalty_experiment', \
    #                 'Augmented_Lag_experiment', \
    #                     'New_Augmented_Lag_experiment', \
    #                         'Fletcher_Penalty_experiment']:

        
    #     for activation_input in ['sin', \
    #                             'tanh', \
    #                             'cos']:
            
            

        # for activation_input in ['sin']:

    if activation_input == "sin":
        activation = jnp.sin
    elif activation_input == "tanh":
        activation = nn.tanh
    elif activation_input == "cos":
        activation = jnp.cos
        
    activation_name = activation.__name__

    absolute_error_list = []
    l2_relative_error_list = []
    for beta in beta_list:

        data, sample_data, IC_sample_data, ui = dataloader.get_data(\
            x_data_min, x_data_max, t_data_min, t_data_max, x_sample_min, \
                x_sample_max, t_sample_min, t_sample_max, beta, M)

        model = NN(features=features, activation=activation)
        params = model.init_params(key=key, data=data)
        params_mul = [params, mul]

        eval_data, _, _, eval_ui = eval_dataloader.get_data(x_data_min, x_data_max, \
        t_data_min, t_data_max, x_sample_min, x_sample_max, t_sample_min, \
        t_sample_max, beta, M)

        if experiment == "SQP_experiment":
            optim_components = OptimComponents(model, data, sample_data, IC_sample_data, ui[0], beta)
            sqp_optim = SQP_Optim(model, optim_components, qp, features, dim)
            updated_params, loss_list = sqp_optim.SQP_optim(params, SQP_num_iter)

            absolute_error, l2_relative_error, eval_u_theta = \
                sqp_optim.evaluation(updated_params, N, eval_data, eval_ui[0])
            
        else:
            if experiment == "PINN_experiment":
                loss = PINN(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "l1_Penalty_experiment":
                loss = l1Penalty(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "l2_Penalty_experiment":
                loss = l2Penalty(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "linfinity_Penalty_experiment":
                loss = linfinityPenalty(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "Han_penalty_experiment":
                loss = HanPenalty(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "Cubic_Penalty_experiment":
                loss = CubicPenalty(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "Augmented_Lag_experiment":
                loss = AugLag(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "Pillo_Penalty_experiment":
                loss = PilloPenalty(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "New_Augmented_Lag_experiment":
                loss = NewAugLag(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            elif experiment == "Fletcher_Penalty_experiment":
                loss = FletcherPenalty(model, data, sample_data, IC_sample_data, ui[0], beta, \
                            N, M)
            
            optim = Optim(model, loss, cons_violation)
            updated_params, loss_list = optim.adam_update(params, \
                                                    uncons_optim_num_echos, uncons_optim_learning_rate, \
                                                    penalty_param, penalty_param_update_factor, \
                                                    experiment, mul, params_mul, mul_num_echos, alpha)

            absolute_error, l2_relative_error, eval_u_theta = optim.evaluation(\
                                            updated_params, N, eval_data, eval_ui[0])
            
        visual.line_graph(loss_list, "/{activation_name}/Total_Loss".\
            format(activation_name=activation_name), experiment=experiment, beta=beta)
        visual.line_graph(eval_ui[0], "/{activation_name}/True_sol".\
                format(activation_name=activation_name), experiment=experiment, beta=beta)
        visual.line_graph(eval_u_theta, "/{activation_name}/u_theta".\
                format(activation_name=activation_name), experiment=experiment, beta=beta)
        visual.heatmap(eval_data, eval_ui[0], "/{activation_name}/True_sol_heatmap".\
                format(activation_name=activation_name), experiment=experiment, beta=beta)
        visual.heatmap(eval_data, eval_u_theta, "/{activation_name}/u_theta_heatmap".\
                format(activation_name=activation_name), experiment=experiment, beta=beta)

        absolute_error_list.append(absolute_error)
        l2_relative_error_list.append(l2_relative_error)

        print("last loss: "+str(loss_list[-1]))
        print("absolute_error: " + str(absolute_error))
        print("l2_relative_error: " + str(l2_relative_error))

    error_df = pd.DataFrame({'Beta': beta_list, 'absolute_error': absolute_error_list, \
                            'l2_relative_error': l2_relative_error_list}).astype(float)
    folder_path = "{current_dir}/{experiment}/pics/{activation_name}/error".\
        format(experiment=experiment, \
                current_dir=current_dir, activation_name=activation_name)
    
    visual.error_graph(error_df, folder_path, "/{activation_name}".\
            format(activation_name=activation_name), experiment=experiment)




if __name__ == '__main__':

    import time
    start_time = time.time()

    experiment_list = [['Pillo_Penalty_experiment', 'sin'],
     ['Pillo_Penalty_experiment', 'tanh'],
     ['Pillo_Penalty_experiment', 'cos']]

    with Pool(3) as p:
        print(p.map(mains, experiment_list))

    end_time = time.time()
    print(f"Execution Time: {end_time - start_time} seconds")
