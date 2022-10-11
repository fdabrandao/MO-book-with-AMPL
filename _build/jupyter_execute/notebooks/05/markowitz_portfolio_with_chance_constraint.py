#!/usr/bin/env python
# coding: utf-8

# # Portfolio optimization with chance constraint

# In[20]:


# install Pyomo and solvers
import requests
import types

url = "https://raw.githubusercontent.com/jckantor/MO-book/main/python/helper.py"
helper = types.ModuleType("helper")
exec(requests.get(url).content, helper.__dict__)

helper.install_pyomo()
helper.install_cbc()
helper.install_cplex()


# In[21]:


from IPython.display import Markdown, HTML
import io
import pyomo.environ as pyo
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time 
import requests
import math

cplex_solver = pyo.SolverFactory("cplex_direct")
cbc_solver = pyo.SolverFactory("cbc")


# Consider the following canonical stochastic optimization problem, the so-called _portfolio selection problem_. Assuming there is an initial unit capital $C=1$ that needs to be invested in a selection of $n$ possible assets, each of them with a unknown return rate $z_i$, $i=1,\dots,n$. Let $x$ be the vector whose $i$-th component $x_i$ describes the fraction of the capital invested in asset $i$. The return rate vector $z$ can be modelled by a multivariate Gaussian distribution with mean $\bar{z}$ and covariance $\Sigma$. 
# 
# Assuming to know the return rates, the portfolio return would be then equal to: 
# 
# $$
#     z^\top x = \sum_{i=1}^n x_i z_i.
# $$
# 
# We want to determine the portfolio that maximizes the _expected_ return $\mathbb{E} ( z^\top x )$, which in view of our assumptions rewrites as $ \mathbb{E} ( z^\top x ) = \bar{z}^\top x$.
# 
# Additionally, we includ a _loss risk chance constraint_ of the form $\mathbb{P} ( z^\top x \leq \alpha) \leq \beta$, which we learned in Lecture 8 can be rewritten explicitly.
# 
# Write the full portfolio optimization problem as a SOCP and solve it with Pyomo for a general $n$, $\alpha \in [0, 1]$, $\beta \in [0, 1/2]$, vector $\bar{z}$, and semi-definite positive covariance matrix $\Sigma$.

# A chance constraint of the form $\mathbb{P} ( z^\top x \leq \alpha) \leq \beta$ rewrites as 
# 
# $$
#   \bar{z}^\top x \geq \Phi^{-1}(1-\beta) \| \Sigma^{1/2} x \|_2 + \alpha,
# $$
# 
# and is a convex if $\beta \leq 1/2$. The portfolio optimization problem can then be formulated as a SOCP as
# 
# \begin{align*}
#     \max \; & \bar{z}^\top x\\
#     \quad \text{ s.t. } & \Phi^{-1}(1-\beta) \| \Sigma^{1/2} x \|_2 \leq \bar{z}^\top x - \alpha,\\
#     & \sum_{i=1}^n x_i = 1, \\
#     &  x \geq 0.
# \end{align*}

# In[22]:


# we import the inverse CDF or quantile function for the standard normal norm.ppf() from scipy.stats
from scipy.stats import norm

# We set our risk threshold and risk levels (sometimes you may get an infeasible problem if the chance constraint becomes too tight!)
alpha = 0.5
beta = 0.3

# We specify the number of assets, their expected returns and their covariance matrix. 
n = 3
z_mean = np.array([1.05, 1.15, 1.3])
z_cov = np.array([[1, 0.5, 2],[0.5, 2, 0],[2, 0, 5]])

# Check how dramatically the optimal solution changes if we assume i.i.d. deviations for the returns.
# z_cov = np.array([[1, 0, 0],[0, 1, 0],[0, 0, 1]])

# If you want to change covariance matriix, make sure you input a semi-definite positive one.
# The easiest way to generate a random covariance matrix is first generating a random n x n matrix A and then taking the matrix A^T A (which is always semi-definite positive)
# N = 3
# A = np.random.rand(N,N)
# z_cov = A.T @ A

model = pyo.ConcreteModel("Portfolio problem")

model.x = pyo.Var(range(n), within=pyo.NonNegativeReals)
model.y = pyo.Var(within=pyo.Reals)

model.objective = pyo.Objective(expr=z_mean @ model.x, sense=pyo.maximize)

model.chance_constraint = pyo.Constraint(expr=norm.ppf(1-beta) * (model.x @ (z_cov @ model.x)) <= (z_mean @ model.x - alpha))
model.total_assets = pyo.Constraint(expr=sum(model.x[i] for i in range(n)) == 1)

result = cplex_solver.solve(model)

display(Markdown(f"**Solver status:** *{result.solver.status}, {result.solver.termination_condition}*"))
display(Markdown(f"**Solution:** $x_1 = {model.x[0].value:.3f}$,  $x_2 = {model.x[1].value:.3f}$,  $x_3 = {model.x[2].value:.3f}$"))
display(Markdown(f"**Maximizes objective value to:** ${model.objective():.2f}$"))


# # Exercise 2: Portfolio selection with cardinality-constrained uncertainty set
# Remember that, if all the return rates $\xi_i$ for every asset $i$ are known, the classical deterministic portfolio selection problem can be formulated as the following LP:
# \begin{align*}
# \max \; & \xi^T {x} \\
# \quad \text{ s.t. } & \sum_{i=1}^n x_i = C, \\
# & x_i \geq 0, \quad i=1,\dots,n.
# \end{align*}
# We consider now the following variant, where each asset has a rate that varies in a specific interval.
# 
# A broker must allocate his capital among $n=100$ assets in order to maximize his return. She has established that the return $\xi_i$ of asset $i$ belongs to the interval $[r_i − s_i, r_i + s_i]$ centered around the value $r_i = 1.15 + i \cdot (0.05/100)$ and varying in both direction by at most $s_i = (0.05/300) \cdot \sqrt{45300 \cdot i}$. 
# 
# Obviously, in the deterministic problem where all returns are equal to their point forecasts, i.e., $\xi_i = r_i$ it is optimal to invest everything in the asset with the greatest nominal return, that is asset $100$. Similarly, in the conservative approach where all returns equal their worst-case values, it is optimal to invest everything in the asset with the greatest worst-case return, which is asset 1.
# 
# We consider now an alternative robust approach that uses cardinality-constrained uncertainty set. More specifically, we assume that at most $\Gamma$ assets can vary from their nominal return rates. 
# 
# (a) Find the tractable robust counterpart of this cardinality-constrainted uncertainty set or budget uncertainty set. Then, assuming that $\Gamma=20$ and $C=1000$, implement the model in Pyomo and solve it.
# 
# *Hint: you may want to "move" the uncertain parameters $\xi_i$'s from the objective function into a constraint, recovering a setting similar to the one presented in the lecture notes for cardinality-constrainted uncertainty set. We can do so by equivalently rewrite the portfolio selection problem as*
# \begin{align*}
# \max \; & w \\
# \quad \text{ s.t. } & \sum_{i=1}^n x_i = C, \\
# & \xi^T {x} \geq w,\\
# & w \geq 0,\\
# & x_i \geq 0, \quad i=1,\dots,n.
# \end{align*}
# *Note that the inequality has a different sign than the one in the lectures notes, hence the argument there has to be adopted accordingly*

# In[23]:


def portfolio(Gamma=1, printflag=False):

    model = pyo.ConcreteModel()

    model.n = 100

    def indices_rule(model):
        return range(1,model.n+1)

    model.indices = pyo.Set(initialize=indices_rule)

    model.capital = 1000
    model.x = pyo.Var(model.indices, within=pyo.NonNegativeReals) 
    model.w = pyo.Var(within=pyo.NonNegativeReals) 

    model.budget = pyo.Constraint(expr=pyo.summation(model.x) == model.capital)

    # introduce variable for tractable robust counterpart
    model.z = pyo.Var(model.indices, within=pyo.NonNegativeReals)
    model.l = pyo.Var(within=pyo.NonNegativeReals)

    def deltareturn(j):
        return (0.05/300) * math.sqrt(45300 * j)

    def nominalreturn(j):
        return 1.15 + j * (0.05/100)

    # tractable robust counterpart, two for every initial constraints with varying parameter
    model.lower = pyo.ConstraintList()
    model.upper = pyo.ConstraintList()
    model.cardinalityconstraint = pyo.Constraint(expr= -sum([nominalreturn(j)*model.x[j] for j in model.indices]) + model.l * Gamma + pyo.summation(model.z) <= -model.w)
    for j in model.indices:
        model.lower.add(expr=model.z[j] >= -model.x[j]*deltareturn(j) - model.l)
        model.upper.add(expr=model.z[j] >= model.x[j]*deltareturn(j) - model.l)

    def total_return(model):
        return model.w
    model.profit = pyo.Objective(rule=total_return, sense=pyo.maximize)

    result = cbc_solver.solve(model)
    if printflag:
        display(Markdown(f"**Solver status:** *{result.solver.status}, {result.solver.termination_condition}*"))
        display(Markdown(f"**Solution:**"))
        for i in model.indices:
            display(Markdown(f" $x_{ {i} } = {model.x[i].value:.3f}$"))
        display(Markdown(f"**Maximizes objective value to:** ${model.profit():.2f}$€"))
    return model.profit(), [round(model.x[i].value,3) for i in model.indices]

profit, x = portfolio(Gamma=20, printflag=True)


# We now solve the same problem by varying $\Gamma$ from $1$ to $50$ and observe how the optimal decision $x^*$ changes accordingly.

# In[24]:


for gamma in range(51):
    profit, x = portfolio(Gamma=gamma, printflag=False)
    display(Markdown(f"$\Gamma={gamma:.0f}$"))
    display(Markdown(f"**Profit:** {profit:.2f}€"))
    display(Markdown(f"**Optimal solution:** ${x}$"))


# In[25]:


def portfolio():

    model = pyo.ConcreteModel()

    model.n = 10

    def indices_rule(model):
        return range(1,model.n+1)

    model.indices = pyo.Set(initialize=indices_rule)

    model.capital = 1000
    model.x = pyo.Var(model.indices, within=pyo.NonNegativeReals) 
    model.xtilde = pyo.Var(model.indices, within=pyo.NonNegativeReals) 
    model.w = pyo.Var(within=pyo.NonNegativeReals) 

    model.budget = pyo.Constraint(expr=pyo.summation(model.x) +  model.xtilde == model.capital)

    def deltareturn(j):
        return (0.05/300) * math.sqrt(45300 * j)

    def nominalreturn(j):
        return 1.15 + j * (0.05/100)

    def total_return(model):
        return model.w
    
    model.profit = pyo.Objective(rule=total_return, sense=pyo.maximize)

    result = cbc_solver.solve(model)
    if printflag:
        display(Markdown(f"**Solver status:** *{result.solver.status}, {result.solver.termination_condition}*"))
        display(Markdown(f"**Solution:**"))
        for i in model.indices:
            display(Markdown(f" $x_{ {i} } = {model.x[i].value:.3f}$"))
        display(Markdown(f"**Maximizes objective value to:** ${model.profit():.2f}$€"))
    return model.profit(), [round(model.x[i].value,3) for i in model.indices]

profit, x = portfolio(Gamma=20, printflag=True)


# In[ ]:





# In[ ]:




