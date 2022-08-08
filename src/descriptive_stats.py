'''
make summary table
'''
import pandas as pd
from pathlib import Path
import geopandas as gpd
from shapely import wkt
import numpy as np

wd = Path.cwd()
path_stats = wd.parent/'out'/'results'

# load data
df = pd.read_csv(wd.parent/'out'/'data'/'dataset_yearly.csv')

# prepare data
df = df[df.pop_dens != 0] # drop grid cells with no population
df = df[df.nl.notnull()]
df = df[df.date_first_vend_prepaid.notnull()]
df = df[df.dist_tr <= 0.02]

'''
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
'''

# https://stackoverflow.com/questions/54466196/descriptive-statistics-in-python-with-pandas-with-std-in-parentheses
idx = pd.IndexSlice
years = [x for x in range(2014,2020+1)]
df_desc = (df[df.year.isin(years)]).groupby(['year'])[['nl','pol','pop_dens']].describe()

df_desc = df_desc.loc[idx[:],idx[:,["mean", "std"]]].T
df_desc.loc[idx[:,["std"]],idx[:]] = df_desc.loc[idx[:,["std"]],idx[:]].applymap(lambda x: "("+"{:.2f}".format(x)+")")

df_desc.loc[idx[:,["mean"]],idx[:]] = df_desc.loc[idx[:,["mean"]],idx[:]].applymap(lambda x: "{:.2f}".format(x))

not2015 = [x for x in years if x != 2015]
df_desc.loc['pop_dens', not2015] = "-"

df_desc=df_desc.reset_index(drop=True)

df_new = pd.DataFrame(df_desc.values, index=["nightlight", "", "pollution", "",'population',"density"], columns=df_desc.columns)

col_align = 'l' + len(years)*'c'

with open(path_stats/'stats.tex','w') as tf:
    tf.write(df_new.style.to_latex(position='H', caption='descriptive statistics by group and year', hrules=True,  label='tab:stats', environment='longtable', multicol_align='c', column_format=col_align))


### transformer statistics
df_trans = df[['geometry_transformer','county']].drop_duplicates().reset_index(drop=True).dropna()
gdf_trans = gpd.GeoDataFrame(df_trans, geometry=df_trans['geometry_transformer'].apply(wkt.loads))

tab_counties = pd.DataFrame(gdf_trans.county.value_counts()).rename(columns={'county':'No'})
tab_counties.index = tab_counties.index.str.capitalize()

with open(path_stats/'tab_counties.tex','w') as tf:
    tf.write(tab_counties.style.to_latex(position='H', caption='number of transformers per county', hrules=True,  label='tab:counties', column_format='lc',environment='longtable'))