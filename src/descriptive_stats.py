'''
make summary tables
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
df_quarter = pd.read_csv(wd.parent/'out'/'data'/'dataset_quarter.csv')

# prepare data
filter = 'date_first_vend_prepaid.notnull() & nl.notnull() & dist_tr <= 0.02 & pop_dens > 0'

df.query(filter, inplace=True)
df_quarter.query(filter, inplace=True)

# correlation table
name_dict = {"pol":"Air pollution", "nl":"Nightlight", "pop_dens":"Population density"}
cor_quar = df_quarter[["pol","nl"]].corr().applymap(lambda x: "{:.2f}".format(x))
# with population density at year 2015
cor_year = df.loc[df.year==2015,["pol","nl","pop_dens"]].corr().applymap(lambda x: "{:.2f}".format(x))

cor_table = cor_quar.append(cor_year['pop_dens'])

cor_table.loc["pol","nl"] = np.nan

cor_table = cor_table.fillna("-").rename(columns=name_dict, index=name_dict)

# export to latex
col_align = "r" + cor_table.shape[1]* "c"
cap_full = r"Correlation table\protect\footnotemark[1]"

with open(path_stats/'stats_corr.tex','w') as tf:
    tf.write(cor_table.style.to_latex(position='h!', hrules=True,  label='tab:stats-cor', multicol_align='c', environment = "longtable", column_format=col_align, caption=cap_full))

#############
# mean and standard deviation by year

# https://stackoverflow.com/questions/54466196/descriptive-statistics-in-python-with-pandas-with-std-in-parentheses
idx = pd.IndexSlice
years = [x for x in range(2012,2020+1)]
df_desc = (df[df.year.isin(years)]).groupby(['year'])[['nl','pol']].describe()

df_desc = df_desc.loc[idx[:],idx[:,["mean", "std"]]].T
df_desc.loc[idx[:,["std"]],idx[:]] = df_desc.loc[idx[:,["std"]],idx[:]].applymap(lambda x: "("+"{:.2f}".format(x)+")")

df_desc.loc[idx[:,["mean"]],idx[:]] = df_desc.loc[idx[:,["mean"]],idx[:]].applymap(lambda x: "{:.2f}".format(x))

df_desc=df_desc.reset_index(drop=True)

df_new = pd.DataFrame(df_desc.values, index=["Nightlight", "", "Air pollution", ""], columns=df_desc.columns)
df_new.columns.name = ""

col_align = 'l' + len(years)*'c'

cap = r"Mean and standard deviation (in parentheses) of nightlight (in $nW/cm^2/sr$) and air pollution (PM in $\mu g/m^3$) by year"

with open(path_stats/'stats.tex','w') as tf:
    tf.write(df_new.style.to_latex(position='ht', hrules=True,  label='tab:stats', environment='longtable', multicol_align='c', column_format=col_align, caption=cap))


### transformer statistics
df_trans = df[['geometry_transformer','county']].drop_duplicates().reset_index(drop=True).dropna()
gdf_trans = gpd.GeoDataFrame(df_trans, geometry=df_trans['geometry_transformer'].apply(wkt.loads))

tab_counties = pd.DataFrame(gdf_trans.county.value_counts()).rename(columns={'county':'No'})
tab_counties.index = tab_counties.index.str.capitalize()
tab_counties.loc['Total'] = sum(tab_counties.No)

# export to latex
with open(path_stats/'tab_counties.tex','w') as tf:
    tf.write(tab_counties.style.to_latex(position='H', caption='number of transformers per county',  label='tab:counties', hrules=True, column_format='lc',environment='longtable'))