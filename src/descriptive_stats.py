'''
make summary table
'''
import pandas as pd
from pathlib import Path
import numpy as np

wd = Path.cwd()

# load data
df = pd.read_csv(wd.parent/'out'/'data'/'dataset_yearly.csv')

# prepare data
df = df[df.pop_dens != 0] # drop grid cells with no population
df = df[df.nl.notnull()]

# group grid cells by
# nothing if neither lmcp, nonlmcp, preexisting
df['group'] = np.nan
df.loc[(df.n_lmcp==0) & (df.n_nonlmcp==0) & (df.n_preexisting==0), 'group'] = 'no electricity'
# #lmcp > #nonlmcp + #preexising
df.loc[(df.len_lmcp >= df.len_nonlmcp) & (df.len_lmcp >=df.len_preexisting) & df.group.isnull(), 'group'] = 'lmcp'
# #nonlmcp > #lmcp + #preexising
df.loc[(df.len_nonlmcp >= df.len_lmcp) & (df.len_nonlmcp >= df.len_preexisting) & df.group.isnull(), 'group'] = 'nonlmcp'
# #preexisting > #lmcp + #nonlmcp
df.loc[(df.len_preexisting >= df.len_lmcp) & (df.len_preexisting >= df.len_nonlmcp) & df.group.isnull(), 'group'] = 'preexisting'


# https://stackoverflow.com/questions/54466196/descriptive-statistics-in-python-with-pandas-with-std-in-parentheses
idx = pd.IndexSlice
df_desc = (df[df.year.isin([2015,2020])]).groupby(['group','year'])[['nl','pol','pop_dens']].describe()

df_desc = df_desc.loc[idx[:],idx[:,["mean", "std"]]].T
df_desc.loc[idx[:,["std"]],idx[:]] = df_desc.loc[idx[:,["std"]],idx[:]].applymap(lambda x: "("+"{:.2f}".format(x)+")")

df_desc.loc[idx[:,["mean"]],idx[:]] = df_desc.loc[idx[:,["mean"]],idx[:]].applymap(lambda x: "{:.2f}".format(x))

groups = df['group'].unique().tolist()
df_desc.loc['pop_dens',pd.IndexSlice[groups,[2020]]] = "-"

df_desc=df_desc.reset_index(drop=True)

df_new = pd.DataFrame(df_desc.values, index=["nightlight", "", "pollution", "",'population',"density"], columns=pd.MultiIndex.from_tuples(df_desc.columns))

with open(wd.parent/'out'/'results'/'stats.tex','w') as tf:
    tf.write(df_new.style.to_latex(position='H', caption='descriptive statistics by group and year', hrules=True,  label='tab:stats', environment='longtable', multicol_align='c'))