# -*- coding: utf-8 -*-
"""
Created on Tue Feb 23 11:49:11 2021

@author: peter
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import scipy.stats as stats
from abc import ABCMeta, abstractmethod

class BaseModel(object, metaclass = ABCMeta):
    def __init__(self, *args):
        self.args = args
        
    def transform(self, params, restrictions):
        params_trans = np.zeros(params.shape)
        for i in range(len(params)):
            if restrictions[i] == 'pos':
                params_trans[i] = np.log(params[i])
            elif restrictions[i] == '01':
                params_trans[i] = np.log(params[i]) - np.log(1 - params[i])
            else:
                params_trans[i] = params[i]
        return params_trans
    
    def transform_back(self, params_trans, restrictions):
        params = np.zeros(params_trans.shape)
        for i in range(len(params_trans)):
            if restrictions[i] == 'pos':
                params[i] = np.exp(params_trans[i])
            elif restrictions[i] == '01':
                params[i] = 1 / (1 + np.exp(-params_trans[i]))
            else:
                params[i] = params_trans[i]
        return params
    
    def gradient(self, param_trans, restrictions):
        g = np.zeros_like(param_trans)
        for i in range(len(g)):
            if restrictions[i] == '':
                g[i] = 1
            elif restrictions[i] == 'pos':
                g[i] = np.exp(param_trans[i])
            else:
                g[i] = np.exp(param_trans[i]) / np.power(1 + np.exp(param_trans[i]), 2)
        return g
    
    def standard_error(self, optimization, restrictions, y_len):
        grad = self.gradient(self.transform_back(optimization.x, restrictions), restrictions)
        variance = optimization.hess_inv.todense() / y_len
        return np.multiply(np.sqrt(np.diag(variance)), grad)
    
    @abstractmethod
    def initialize_params(self):
        pass
    
    @abstractmethod
    def loglikelihood(self):
        pass
    
    def loglikelihood_trans(self, params_trans, restrictions, X, *y):
        params = self.transform_back(params_trans, restrictions)
        return self.loglikelihood(params, X, *y)
    
    def fit(self, restrictions, X, *y):
        res = minimize(self.loglikelihood_trans,
                       self.transform(self.initialize_params(X), restrictions),
                       args = (restrictions, X, *y),
                       method = 'l-bfgs-b',
                       options = {'disp': False})
        self.opt = res
        self.optimized_params = self.transform_back(self.opt.x, restrictions)
        self.standard_errors = self.standard_error(self.opt, restrictions, len(X))
        high = self.optimized_params + stats.norm.ppf(0.975) * self.standard_errors
        low = self.optimized_params - stats.norm.ppf(0.975) * self.standard_errors
        
        self.table = pd.DataFrame(data = {'Parameters': self.optimized_params,
                                     'Standard Error': self.standard_errors,
                                     '95% CI Lower': low,
                                     '95% CI Higher': high})
        print('Loglikelihood: ', self.opt.fun, '\n')
        print(self.table)
        return